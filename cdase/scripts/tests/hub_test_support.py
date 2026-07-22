"""Support for hub integration tests — start/stop ephemeral hub on a test port."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[3]
HUB_JAR = REPO_ROOT / "hub" / "target" / "cdase-hub-1.1.0.jar"
DEFAULT_TEST_PORT = 17423


def hub_health(url: str, timeout: float = 2.0) -> dict | None:
    try:
        with urlopen(f"{url.rstrip('/')}/health", timeout=timeout) as resp:
            return json.loads(resp.read())
    except (URLError, OSError, json.JSONDecodeError, ValueError):
        return None


def wait_for_hub(url: str, *, timeout_sec: float = 15.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if hub_health(url):
            return True
        time.sleep(0.2)
    return False


class EphemeralHub:
    """Start cdase-hub on an isolated port + data dir for integration tests."""

    def __init__(self, port: int = DEFAULT_TEST_PORT, env: dict[str, str] | None = None):
        self.port = port
        self.url = f"http://127.0.0.1:{port}"
        self.env = env or {}
        self._proc: subprocess.Popen | None = None
        self._data_dir: tempfile.TemporaryDirectory | None = None

    def start(self) -> str:
        if not HUB_JAR.is_file():
            raise FileNotFoundError(
                f"Hub jar missing: {HUB_JAR}. Run: cd hub && mvn -q package"
            )
        existing = hub_health(self.url)
        if existing and existing.get("ok"):
            return self.url

        self._data_dir = tempfile.TemporaryDirectory(prefix="cdase-hub-test-")
        data_path = Path(self._data_dir.name)
        process_env = os.environ.copy()
        process_env.update(self.env)
        self._proc = subprocess.Popen(
            [
                "java",
                "-jar",
                str(HUB_JAR),
                "--port",
                str(self.port),
                "--data",
                str(data_path),
            ],
            cwd=REPO_ROOT / "hub",
            env=process_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_hub(self.url):
            self.stop()
            raise RuntimeError(f"Hub did not become healthy on {self.url}")
        return self.url

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        if self._data_dir is not None:
            self._data_dir.cleanup()
            self._data_dir = None

    def __enter__(self) -> str:
        return self.start()

    def __exit__(self, *args) -> None:
        self.stop()


def test_app_cdase_root() -> Path:
    return REPO_ROOT / "tests" / "fixtures" / "app" / "cdase"


def ensure_test_member(
    cdase_root: Path | None = None,
    *,
    machine_id: str = "cdase-api-pool-test-machine",
    alias: str = "api-pool-tester",
) -> dict[str, str]:
    """Ensure a stable machine member record exists for integration tests."""
    import sys

    scripts = REPO_ROOT / "cdase" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from machine_identity import machine_user_id, write_member_record

    root = cdase_root or test_app_cdase_root()
    user_id = machine_user_id(machine_id)
    path = write_member_record(
        root, name=alias, user_id=user_id, role="developer", status="active"
    )
    return {
        "CDASE_MACHINE_ID": machine_id,
        "CDASE_ROOT": str(root),
        "member_path": str(path),
        "user_id": user_id,
        "alias": alias,
    }


def run_client(*args: str, env: dict | None = None) -> tuple[int, dict]:
    """Run cdase_client.py; return (exit_code, parsed_json)."""
    merged = os.environ.copy()
    merged.update({
        "CDASE_TESTING": "1",
        "CDASE_TEST_MEMBER_STATE": "committed",
    })
    if env:
        merged.update(env)
    script = REPO_ROOT / "cdase" / "scripts" / "cdase_client.py"
    proc = subprocess.run(
        ["python3", str(script), *args],
        capture_output=True,
        text=True,
        env=merged,
        cwd=REPO_ROOT,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"client did not emit JSON (exit {proc.returncode}):\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        ) from exc
    return proc.returncode, payload
