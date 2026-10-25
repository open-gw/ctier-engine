"""Start Kong DB-less + echo. Used only by the opt-in live suite."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
COMPOSE = REPO / "targets" / "kong" / "live" / "compose.yaml"
PROJECT = "ctier-kong-live"
PROXY = "http://127.0.0.1:18000"
STATUS = "http://127.0.0.1:18100/status"
CUSTODY = "http://127.0.0.1:18200"
# Unpublished. Host assertions in the chokepoint tests use this port.
ECHO_HOST_PORT = 18080
ECHO = f"http://127.0.0.1:{ECHO_HOST_PORT}"
ECHO_URL = "http://echo:8080"
KEYCLOAK = "http://127.0.0.1:18400"
SERVICE_TOKEN = "local-dev-custody-token"
CUSTODY_INTERNAL = "http://custody:8080"

MINIMAL = """\
_format_version: "3.0"
services:
- name: echo
  url: http://echo:8080
  routes:
  - name: all
    paths:
    - /
    strip_path: false
"""


def point_at_echo(text: str, url: str = ECHO_URL) -> str:
    deck = yaml.safe_load(text)
    for svc in deck.get("services") or []:
        svc["url"] = url
    return yaml.safe_dump(
        deck,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )


def http(method: str, url: str, headers: dict | None = None, body: bytes | None = None,
         timeout: float = 10.0) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(url, data=body, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, str(value))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, raw, hdrs
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        hdrs = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, raw, hdrs


def wait_url(url: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 300:
                    return
                last = f"status {resp.status}"
        except Exception as exc:
            last = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"not ready: {url} ({last})")


def wait_custody_accepts(base_url: str, timeout: float = 60.0) -> None:
    """Health can answer before the ledger and the pending queue do.

    A test that needs custody waits here. If custody never accepts,
    the failure names that, instead of a later 503 or a missing row.
    """
    deadline = time.time() + timeout
    root = base_url.rstrip("/")
    checks = (
        root + "/v1/ledger?type=decision",
        root + "/v1/pending",
    )
    last = "no response"
    while time.time() < deadline:
        failed = False
        for url in checks:
            try:
                code, raw, _ = http("GET", url, timeout=2)
            except Exception as exc:
                last = f"{url} {exc}"
                failed = True
                break
            if code != 200:
                snippet = raw[:160]
                last = f"{url} status {code} {snippet!r}"
                failed = True
                break
        if not failed:
            return
        time.sleep(0.4)
    raise RuntimeError(f"custody did not accept: {base_url} ({last})")


def _custody_unavailable(raw: bytes) -> bool:
    try:
        body = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        return False
    return isinstance(body, dict) and body.get("status") == "custody_unavailable"


def _custody_reads(base_url: str) -> bool:
    try:
        code, _, _ = http(
            "GET", base_url.rstrip("/") + "/v1/pending", timeout=0.5,
        )
    except Exception:
        return False
    return code == 200


def http_for_live(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    body: bytes | None = None,
    custody_base: str,
) -> tuple[int, bytes, dict[str, str]]:
    """Retry a 503 only while custody is answering.

    The gateway reports custody_unavailable when its persist does not
    come back in time. If custody is actually down, the 503 is returned
    at once so a fail-closed test still sees it. If custody is up, wait
    and send again. Eight misses while it is up is "custody did not accept".
    """
    last: tuple[int, bytes, dict[str, str]] | None = None
    for _attempt in range(8):
        status, raw, hdrs = http(method, url, headers=headers, body=body)
        last = (status, raw, hdrs)
        if status != 503 or not _custody_unavailable(raw):
            return status, raw, hdrs
        if not _custody_reads(custody_base):
            return status, raw, hdrs
        time.sleep(0.25)
    assert last is not None
    raise RuntimeError(
        f"custody did not accept: {custody_base} (gateway 503)"
    )


class KongStack:
    def __init__(self, workdir: Path, *, project: str = PROJECT):
        self.workdir = workdir
        self.project = project
        self.yaml_path = workdir / "kong.yaml"
        self.yaml_path.write_text(MINIMAL, encoding="utf-8")
        self.realm_path = workdir / "realm.json"
        self._token_cache: dict[str, tuple[str, float]] = {}
        self.nginx_workers = 1

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["CTIER_KONG_YAML"] = str(self.yaml_path)
        env["CTIER_KEYCLOAK_REALM"] = str(self.realm_path)
        env["CTIER_KONG_WORKERS"] = str(self.nginx_workers)
        return env

    def reconfigure_workers(self, count: int) -> None:
        if count < 1:
            raise ValueError("worker count must be at least 1")
        if count == self.nginx_workers:
            return
        self.nginx_workers = count
        recreated = self._compose("up", "-d", "--force-recreate", "kong", check=False)
        if recreated.returncode != 0:
            raise RuntimeError(
                f"kong recreate for {count} workers failed\nstdout:\n{recreated.stdout}\n"
                f"stderr:\n{recreated.stderr}"
            )
        wait_url(STATUS, timeout=90.0)

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
        files = generate(qualified, target="kong")
        self.realm_path.write_text(files["keycloak-realm.json"], encoding="utf-8")
        up = self._compose("up", "-d", "--build", check=False)
        if up.returncode != 0:
            raise RuntimeError(
                f"docker compose up failed\nstdout:\n{up.stdout}\nstderr:\n{up.stderr}"
            )
        wait_url(KEYCLOAK + "/realms/ctier/.well-known/openid-configuration", timeout=120.0)
        wait_url(STATUS, timeout=90.0)
        wait_url(CUSTODY + "/health", timeout=90.0)
        wait_custody_accepts(CUSTODY, timeout=90.0)

    def exec(self, service: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return self._compose("exec", "-T", service, *args, check=check)

    def harness_requests(self) -> list:
        """Echo request log, read from inside the echo container.

        The host has no route to echo (14a.1). Do not publish the port
        to make this callable from pytest.
        """
        proc = self.exec(
            "echo",
            "python",
            "-c",
            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/_harness/requests').read().decode())",
        )
        return json.loads(proc.stdout)

    def load(self, text: str, authorization: str | dict | None = None) -> None:
        self.yaml_path.write_text(text, encoding="utf-8")
        if authorization is not None:
            document = (
                yaml.safe_load(authorization)
                if isinstance(authorization, str)
                else authorization
            )
            from ctier.authz.directory import KeycloakDirectory

            KeycloakDirectory(
                KEYCLOAK,
                "ctier",
                admin_user="local-dev-admin",
                admin_password="local-dev-admin-password",
            ).ensure_granted(document)
            self._token_cache.clear()
        restarted = self._compose("restart", "-t", "5", "kong", check=False)
        if restarted.returncode != 0:
            raise RuntimeError(
                f"kong restart failed\nstdout:\n{restarted.stdout}\nstderr:\n{restarted.stderr}"
            )
        wait_url(STATUS, timeout=60.0)
        wait_custody_accepts(CUSTODY)

    def load_generated(self, files: dict[str, str], *, echo: bool = True) -> None:
        text = files["kong.yaml"]
        if echo:
            text = point_at_echo(text)
        self.load(text, authorization=files.get("authorization.yaml"))

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
        elif name == "kong":
            wait_url(STATUS, timeout=60.0)

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
        elif name == "kong":
            wait_url(STATUS, timeout=60.0)

    def stop(self) -> None:
        self._compose("down", "-v", "--remove-orphans", check=False)

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

    def fresh_token(self, client_id: str = "agent-a", *, scopes: str | None = None) -> str:
        prefix = f"{client_id}:"
        for key in list(self._token_cache):
            if key == client_id or key.startswith(prefix):
                self._token_cache.pop(key, None)
        return self.token(client_id, scopes=scopes)

    def _optional_scope_param(self, client_id: str) -> str | None:
        from ctier.authz.directory import KeycloakDirectory

        names = KeycloakDirectory(
            KEYCLOAK,
            "ctier",
            admin_user="local-dev-admin",
            admin_password="local-dev-admin-password",
        ).assigned_optional_scopes(client_id)
        return " ".join(names) if names else None

    def token(self, client_id: str = "agent-a", *, scopes: str | None = None) -> str:
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
        body = urlencode(fields).encode("utf-8")
        status, raw, _ = http(
            "POST",
            KEYCLOAK + "/realms/ctier/protocol/openid-connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=body,
        )
        if status != 200:
            raise RuntimeError(f"token request failed: {status} {raw!r}")
        payload = json.loads(raw.decode("utf-8"))
        access = str(payload["access_token"])
        expires = time.time() + int(payload.get("expires_in") or 30)
        self._token_cache[cache_key] = (access, expires)
        return access

    def auth_headers(self, **headers: str) -> dict[str, str]:
        out = {
            "Authorization": f"Bearer {self.token()}",
            "X-Agent-Id": "agent-a",
        }
        out.update(headers)
        return out

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
