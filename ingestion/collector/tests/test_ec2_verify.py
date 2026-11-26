"""Exercise the EC2 verifier without AWS, Docker, or a real checkout."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "terraform" / "verify.sh"
USER_DATA = SCRIPT.with_name("user-data.sh.tftpl")
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(os.name == "nt" or not BASH, reason="POSIX Bash required")
SHA = "a" * 40


def run_verify(tmp_path, state="READY", revision=SHA, dirty="", smoke_exit=0):
    state_dir = tmp_path / "state"
    repo = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    for path in (state_dir, repo / ".venv" / "bin", bin_dir):
        path.mkdir(parents=True, exist_ok=True)
    (state_dir / "status").write_text(state, encoding="utf-8")
    (state_dir / "source_revision").write_text(SHA, encoding="utf-8")
    git = bin_dir / "git"
    git.write_text(f'#!/bin/bash\nif [ "$1" = rev-parse ]; then echo {revision}; else printf "%s" "{dirty}"; fi\n', encoding="utf-8")
    docker = bin_dir / "docker"
    docker.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    python = repo / ".venv" / "bin" / "python"
    python.write_text(f"#!/bin/bash\nexit {smoke_exit}\n", encoding="utf-8")
    for path in (git, docker, python):
        path.chmod(0o755)
    content = SCRIPT.read_text(encoding="utf-8").replace("/var/lib/wikipulse", state_dir.as_posix()).replace("/opt/wikipulse", repo.as_posix())
    script = tmp_path / "verify.sh"
    script.write_text(content, encoding="utf-8")
    return subprocess.run([BASH, str(script)], capture_output=True, text=True,
                          env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]})


@pytest.mark.parametrize("state", ["RUNNING", "FAILED"])
def test_unready_bootstrap_is_rejected(tmp_path, state):
    result = run_verify(tmp_path, state=state)
    assert result.returncode != 0
    assert state in result.stdout + result.stderr


@pytest.mark.parametrize("kwargs", [{"revision": "b" * 40}, {"dirty": " M file"}])
def test_invalid_checkout_is_rejected(tmp_path, kwargs):
    assert run_verify(tmp_path, **kwargs).returncode != 0


def test_smoke_failure_propagates(tmp_path):
    assert run_verify(tmp_path, smoke_exit=17).returncode == 17


def test_ready_clean_checkout_runs_smoke(tmp_path):
    assert run_verify(tmp_path).returncode == 0


@pytest.mark.parametrize("bootstrap_exit,expected", [(0, "READY"), (19, "FAILED")])
def test_user_data_records_outcome_and_arms_timer_first(tmp_path, bootstrap_exit, expected):
    import base64

    state = tmp_path / "state"
    local_bin = tmp_path / "installed"
    fake_bin = tmp_path / "bin"
    local_bin.mkdir()
    fake_bin.mkdir()
    timer = tmp_path / "timer"
    systemd = fake_bin / "systemd-run"
    systemd.write_text(f"#!/bin/bash\ntouch '{timer}'\n", encoding="utf-8")
    systemd.chmod(0o755)
    bootstrap = f"#!/bin/bash\ntest -f '{timer}' || exit 91\nexit {bootstrap_exit}\n"
    encode = lambda value: base64.b64encode(value.encode()).decode()  # noqa: E731
    data = (USER_DATA.read_text(encoding="utf-8")
            .replace("/var/lib/wikipulse", state.as_posix())
            .replace("/var/log/wikipulse-bootstrap.log", (tmp_path / "bootstrap.log").as_posix())
            .replace("/usr/local/bin", local_bin.as_posix())
            .replace("${source_revision}", SHA)
            .replace("${bootstrap_b64}", encode(bootstrap))
            .replace("${verify_b64}", encode("#!/bin/bash\nexit 0\n")))
    script = tmp_path / "user-data.sh"
    script.write_text(data, encoding="utf-8")
    result = subprocess.run([BASH, str(script)], env={**os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"]})
    assert (state / "status").read_text().strip() == expected
    assert (result.returncode == 0) == (bootstrap_exit == 0)
