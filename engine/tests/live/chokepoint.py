"""The mock backend must not answer anyone sitting where an agent sits."""
from __future__ import annotations

import subprocess

from tests.live.rig import http


def host_reaches(url: str) -> bool:
    try:
        http("GET", url, timeout=2.0)
    except Exception:
        return False
    return True


def outsider_reaches(stack, url: str) -> bool:
    proc = stack.exec(
        "outsider", "wget", "-q", "-T", "2", "-O", "-", url, check=False,
    )
    return proc.returncode == 0


def echo_ips(stack) -> list[str]:
    proc = stack._compose("ps", "-q", "echo")
    cid = proc.stdout.strip()
    assert cid, "echo container is not running"
    inspect = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}",
            cid,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [ip for ip in inspect.stdout.split() if ip]


def assert_backend_unreachable_from_outside(stack, host_port: int) -> None:
    """Fail if echo answers the host or a container that is not a permitted caller.

    Permitted callers are the gateway and custody. `outsider` is on `edge`
    only. These are different failures: a published port versus a shared
    network.
    """
    host_url = f"http://127.0.0.1:{host_port}/"
    assert not host_reaches(host_url), (
        f"host reached the backend at {host_url}; unpublish the echo port"
    )
    assert not outsider_reaches(stack, "http://echo:8080/"), (
        "a container that is not Kong, APISIX, or custody reached echo by name; "
        "echo must not share that container's network"
    )
    for ip in echo_ips(stack):
        assert not outsider_reaches(stack, f"http://{ip}:8080/"), (
            f"a non-permitted container reached echo at {ip}; "
            "echo must sit on an isolated network"
        )
