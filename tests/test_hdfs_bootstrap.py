"""Bootstrap must never format an existing or damaged NameNode volume."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("state,code,formatted", [
    ("empty", 0, True), ("existing", 0, False), ("damaged", 1, False),
])
def test_namenode_bootstrap_formats_only_empty_storage(tmp_path, state, code, formatted):
    data = tmp_path / "name"
    data.mkdir()
    if state == "existing":
        (data / "current").mkdir()
        (data / "current/VERSION").write_text("existing-cluster")
    elif state == "damaged":
        (data / "fsimage_backup").write_text("do not overwrite")
    fake = tmp_path / "hdfs"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HDFS_TEST_CALLS"\n')
    fake.chmod(0o755)
    log = tmp_path / "calls"
    result = subprocess.run(
        ["bash", str(ROOT / "storage/hdfs/start-hdfs.sh"), "namenode"],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "HDFS_NAME_DIR": str(data), "HDFS_TEST_CALLS": str(log)},
        capture_output=True, text=True,
    )
    assert result.returncode == code, result.stderr
    calls = log.read_text() if log.exists() else ""
    assert ("-format" in calls) == formatted
    if state == "existing":
        assert (data / "current/VERSION").read_text() == "existing-cluster"
    if state == "damaged":
        assert calls == ""
        assert (data / "fsimage_backup").read_text() == "do not overwrite"


@pytest.mark.parametrize("registered,code", [("yes", 0), ("no", 1)])
def test_init_waits_for_registered_node_before_writing(tmp_path, registered, code):
    fake = tmp_path / "hdfs"
    fake.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$HDFS_TEST_CALLS"
case "$*" in
  'dfsadmin -report -live')
    if [ "$HDFS_TEST_READY" = yes ]; then printf 'Live datanodes (1):\\n'; fi ;;
  'dfs -cat '*) printf 'wikipulse-ready' ;;
esac
''')
    fake.chmod(0o755)
    sleeper = tmp_path / "sleep"
    sleeper.write_text('#!/bin/sh\nexit 0\n')
    sleeper.chmod(0o755)
    log = tmp_path / "calls"
    result = subprocess.run(
        ["bash", str(ROOT / "storage/hdfs/init-hdfs.sh")],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "HDFS_TEST_CALLS": str(log), "HDFS_TEST_READY": registered},
        capture_output=True, text=True,
    )
    assert result.returncode == code, result.stderr
    calls = log.read_text()
    assert ("dfs -put" in calls) == (registered == "yes")
