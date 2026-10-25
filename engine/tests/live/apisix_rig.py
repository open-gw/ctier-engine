"""Start APISIX standalone + echo. Used only by the opt-in live suite."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

from tests.live.rig import http, http_for_live, wait_custody_accepts, wait_url

REPO = Path(__file__).resolve().parents[3]
COMPOSE = REPO / "targets" / "apisix" / "live" / "compose.yaml"
PROJECT = "ctier-apisix-live"
PROXY = "http://127.0.0.1:19000"
ECHO_HOST_PORT = 19080
ECHO = f"http://127.0.0.1:{ECHO_HOST_PORT}"
ECHO_URL = "http://echo:8080"
CUSTODY = "http://127.0.0.1:19200"
CUSTODY_INTERNAL = "http://custody:8080"
KEYCLOAK = "http://127.0.0.1:19400"

MINIMAL = """\
routes:
  - id: echo
    name: echo
    uris:
      - /*
    upstream:
      type: roundrobin
      nodes:
        "echo:8080": 1

#END
"""

HS256_SECRET = "ctier-apisix-a3-secret"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def hs256_token(payload: dict, *, secret: str = HS256_SECRET) -> str:
    """Mint a local HS256 JWT. Harness only — not a product signer."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode("utf-8"), f"{header}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(sig)}"


def rs256_token(payload: dict) -> str:
    """Mint an RS256 JWT with the realm key Kong already uses. Harness only."""
    from ctier.authz import DIR

    material = json.loads((DIR / "keycloak-rsa.json").read_text(encoding="utf-8"))
    raw = "".join(str(material["privateKey"]).split())
    wrapped = "\n".join(raw[i:i + 64] for i in range(0, len(raw), 64))
    pem = f"-----BEGIN PRIVATE KEY-----\n{wrapped}\n-----END PRIVATE KEY-----\n"
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode("ascii")
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as handle:
        handle.write(pem)
        handle.flush()
        key_path = handle.name
    try:
        signature = subprocess.check_output(
            ["openssl", "dgst", "-sha256", "-sign", key_path],
            input=signing_input,
        )
    finally:
        os.unlink(key_path)
    return f"{header}.{body}.{_b64url(signature)}"


def point_at_echo(text: str, node: str = "echo:8080") -> str:
    doc = yaml.safe_load(text)
    for route in doc.get("routes") or []:
        route["upstream"] = {
            "type": "roundrobin",
            "scheme": "http",
            "nodes": {node: 1},
        }
    dumped = yaml.safe_dump(
        doc,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )
    return with_end(dumped)


def with_end(text: str) -> str:
    body = text.rstrip()
    if not body.endswith("#END"):
        body = body + "\n\n#END\n"
    elif not body.endswith("\n"):
        body = body + "\n"
    return body


class ApisixStack:
    def __init__(self, workdir: Path, *, project: str = PROJECT):
        self.workdir = workdir
        self.project = project
        self.yaml_path = workdir / "apisix.yaml"
        self.yaml_path.write_text(MINIMAL, encoding="utf-8")
        self.realm_path = workdir / "realm.json"
        self.config_path = workdir / "apisix-config.yaml"
        self._scopes = ""
        self._token_cache: dict[str, tuple[str, float]] = {}
        self.nginx_workers = 1
        self._write_apisix_config()

    def _write_apisix_config(self) -> None:
        template = (REPO / "targets" / "apisix" / "live" / "config.yaml").read_text(
            encoding="utf-8"
        )
        text, n = re.subn(
            r"(worker_processes:\s*)\d+",
            rf"\g<1>{self.nginx_workers}",
            template,
            count=1,
        )
        if n != 1:
            raise RuntimeError("apisix live config.yaml: worker_processes not found")
        self.config_path.write_text(text, encoding="utf-8")

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["CTIER_APISIX_YAML"] = str(self.yaml_path)
        env["CTIER_KEYCLOAK_REALM"] = str(self.realm_path)
        env["CTIER_APISIX_CONFIG"] = str(self.config_path)
        return env

    def reconfigure_workers(self, count: int) -> None:
        if count < 1:
            raise ValueError("worker count must be at least 1")
        if count == self.nginx_workers:
            return
        self.nginx_workers = count
        self._write_apisix_config()
        recreated = self._compose("up", "-d", "--force-recreate", "apisix", check=False)
        if recreated.returncode != 0:
            raise RuntimeError(
                f"apisix recreate for {count} workers failed\nstdout:\n{recreated.stdout}\n"
                f"stderr:\n{recreated.stderr}"
            )
        self._wait_proxy(timeout=90.0)

    def _compose(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", "compose", "-p", self.project, "-f", str(COMPOSE), *args],
            check=check,
            env=self._env(),
            capture_output=True,
            text=True,
        )

    def start(self) -> None:
        if shutil.which("docker") is None:
            raise RuntimeError("docker is not on PATH")
        from ctier.compose import compose
        from ctier.generate import generate
        from ctier.spec_loader import SPEC_DIR
        from tests.golden_util import NOW

        qualified, _ = compose(SPEC_DIR / "consequence-tiered-api.yaml", [], NOW)
        files = generate(qualified, target="apisix")
        self.realm_path.write_text(files["keycloak-realm.json"], encoding="utf-8")
        up = self._compose("up", "-d", "--build", check=False)
        if up.returncode != 0:
            reused = self._compose("up", "-d", "--no-build", check=False)
            if reused.returncode != 0:
                raise RuntimeError(
                    f"docker compose up failed\nstdout:\n{up.stdout}\nstderr:\n{up.stderr}\n"
                    f"--no-build stdout:\n{reused.stdout}\nstderr:\n{reused.stderr}"
                )
        wait_url(KEYCLOAK + "/realms/ctier/.well-known/openid-configuration", timeout=120.0)
        wait_url(CUSTODY + "/health", timeout=90.0)
        wait_custody_accepts(CUSTODY, timeout=90.0)
        self._wait_proxy(timeout=90.0)

    def exec(self, service: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return self._compose("exec", "-T", service, *args, check=check)

    def load(self, text: str) -> None:
        self.yaml_path.write_text(with_end(text), encoding="utf-8")
        restarted = self._compose("restart", "-t", "5", "apisix", check=False)
        if restarted.returncode != 0:
            raise RuntimeError(
                f"apisix restart failed\nstdout:\n{restarted.stdout}\nstderr:\n{restarted.stderr}"
            )
        self._wait_proxy(timeout=60.0)
        wait_custody_accepts(CUSTODY)

    def stop(self) -> None:
        self._compose("down", "-v", "--remove-orphans", check=False)

    def _wait_proxy(self, timeout: float) -> None:
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                status, _raw, _ = http("GET", PROXY + "/_rig/ready", timeout=2.0)
                # Generated catch-all is 423. Any HTTP response means the
                # data plane is listening; connection errors are the wait.
                if status:
                    return
                last = f"status {status}"
            except Exception as exc:
                last = str(exc)
            time.sleep(0.5)
        raise TimeoutError(f"not ready: {PROXY} ({last})")

    def request(self, method: str, path: str, query: dict | None = None,
                headers: dict | None = None, body: str | None = None
                ) -> tuple[int, bytes, dict[str, str]]:
        url = PROXY + path
        if query:
            from urllib.parse import urlencode
            url = url + "?" + urlencode(query)
        data = None if body is None else body.encode("utf-8")
        return http_for_live(
            method, url, headers=headers, body=data, custody_base=CUSTODY,
        )

    def echo_json(self, method: str, path: str, **kwargs) -> tuple[int, dict]:
        status, raw, _hdrs = self.request(method, path, **kwargs)
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            payload = {"raw": raw.decode("utf-8", "replace")}
        return status, payload

    def echo_log(self) -> list[dict]:
        """Requests the echo recorded, including hops APISIX made as a client."""
        script = (
            "import urllib.request; "
            "print(urllib.request.urlopen('http://127.0.0.1:8080/_harness/requests').read().decode())"
        )
        got = self.exec("echo", "python", "-c", script, check=False)
        if got.returncode == 0 and got.stdout.strip():
            return json.loads(got.stdout)
        raise RuntimeError(
            f"could not read echo request log: {(got.stderr or got.stdout)!r}"
        )

    def load_generated(self, files: dict[str, str], *, echo: bool = True) -> None:
        text = files["apisix.yaml"]
        if echo:
            text = point_at_echo(text)
        auth = yaml.safe_load(files.get("authorization.yaml") or "{}") or {}
        scopes: list[str] = []
        for client in auth.get("clients") or []:
            if client.get("id") == "agent-a":
                scopes = list(client.get("scopes") or [])
                break
        if not scopes:
            for item in auth.get("scopes") or []:
                if not item.get("excluded"):
                    scopes.append(str(item["name"]))
        self._scopes = " ".join(scopes)
        if files.get("authorization.yaml"):
            from ctier.authz.directory import KeycloakDirectory

            KeycloakDirectory(
                KEYCLOAK,
                "ctier",
                admin_user="local-dev-admin",
                admin_password="local-dev-admin-password",
            ).ensure_granted(auth)
            self._token_cache.clear()
        self.load(text)

    def stop_service(self, name: str) -> None:
        stopped = self._compose("stop", name, check=False)
        if stopped.returncode != 0:
            raise RuntimeError(
                f"stop {name} failed\nstdout:\n{stopped.stdout}\nstderr:\n{stopped.stderr}"
            )

    def start_service(self, name: str) -> None:
        started = self._compose("start", name, check=False)
        if started.returncode != 0:
            raise RuntimeError(
                f"start {name} failed\nstdout:\n{started.stdout}\nstderr:\n{started.stderr}"
            )
        if name == "custody":
            wait_url(CUSTODY + "/health", timeout=60.0)
            wait_custody_accepts(CUSTODY)
        elif name == "apisix":
            self._wait_proxy(timeout=60.0)

    def token(self, *, scopes: str | None = None) -> str:
        return rs256_token({
            "cid": "ctier",
            "iss": "ctier",
            "exp": int(time.time()) + 180,
            "scope": scopes if scopes is not None else getattr(self, "_scopes", ""),
        })

    def fresh_token(self, client_id: str = "agent-a", *, scopes: str | None = None) -> str:
        prefix = f"{client_id}:"
        for key in list(self._token_cache):
            if key == client_id or key.startswith(prefix):
                self._token_cache.pop(key, None)
        return self.keycloak_token(client_id, scopes=scopes)

    def _optional_scope_param(self, client_id: str) -> str | None:
        from ctier.authz.directory import KeycloakDirectory

        names = KeycloakDirectory(
            KEYCLOAK,
            "ctier",
            admin_user="local-dev-admin",
            admin_password="local-dev-admin-password",
        ).assigned_optional_scopes(client_id)
        return " ".join(names) if names else None

    def keycloak_token(self, client_id: str = "agent-a", *, scopes: str | None = None) -> str:
        from urllib.parse import urlencode

        from ctier.authz import AGENT_SECRET

        if scopes is None:
            scopes = self._optional_scope_param(client_id)
        cache_key = f"{client_id}:{scopes or ''}"
        cached = self._token_cache.get(cache_key)
        if cached and cached[1] > time.time() + 3:
            return cached[0]
        fields = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": AGENT_SECRET,
        }
        if scopes:
            fields["scope"] = scopes
        status, raw, _ = http(
            "POST",
            KEYCLOAK + "/realms/ctier/protocol/openid-connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=urlencode(fields).encode("utf-8"),
        )
        if status != 200:
            raise RuntimeError(f"token request failed: {status} {raw!r}")
        payload = json.loads(raw.decode("utf-8"))
        access = str(payload["access_token"])
        expires = time.time() + int(payload.get("expires_in") or 30)
        self._token_cache[cache_key] = (access, expires)
        return access

    def exchange(
        self,
        subject_token: str,
        *,
        scopes: str | None = None,
        client_id: str = "agent-a",
    ) -> tuple[int, dict]:
        from urllib.parse import urlencode

        from ctier.authz import AGENT_SECRET

        fields = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "client_id": client_id,
            "client_secret": AGENT_SECRET,
        }
        if scopes is not None:
            fields["scope"] = scopes
        status, raw, _ = http(
            "POST",
            KEYCLOAK + "/realms/ctier/protocol/openid-connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=urlencode(fields).encode("utf-8"),
        )
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            payload = {"raw": raw.decode("utf-8", "replace")}
        return status, payload

    def auth_headers(self, **headers: str) -> dict[str, str]:
        out = {
            "Authorization": f"Bearer {self.token()}",
            "X-Agent-Id": "agent-a",
        }
        out.update(headers)
        return out
