"""Validate the resolved service boundary without a running Docker daemon."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not shutil.which("docker"), reason="Docker Compose CLI required")


def compose_config(full=False):
    command = ["docker", "compose", "--env-file", "/dev/null", "-f", "docker-compose.yml"]
    if full:
        command += ["-f", "docker-compose.hdfs.yml", "--profile", "full"]
    # Do not let developer .env/profile overrides decide what this test validates.
    result = subprocess.run(
        command + ["config", "--format", "json"], cwd=ROOT,
        env={key: value for key, value in os.environ.items()
             if key in {"PATH", "HOME", "DOCKER_CONFIG"}},
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_core_stays_local_and_has_spark_readiness():
    services = compose_config()["services"]
    assert "namenode" not in services
    assert services["spark"]["environment"]["DATA_BASE_PATH"].startswith("file://")
    assert "healthcheck" in services["spark"]
    assert services["spark"]["environment"]["SPARK_ANALYTICS_SINK"] == "parquet"


def test_full_routes_data_and_checkpoints_to_hdfs_after_init():
    services = compose_config(full=True)["services"]
    assert services["spark"]["environment"]["DATA_BASE_PATH"] == "hdfs://namenode:9000/wikipulse"
    assert services["spark"]["environment"]["SPARK_CHECKPOINT_PATH"] == "hdfs://namenode:9000/checkpoints"
    assert services["spark"]["depends_on"]["init-hdfs"]["condition"] == "service_completed_successfully"
    # DataNode can start while NameNode is in safe mode; no health dependency cycle.
    assert services["datanode"]["depends_on"]["namenode"]["condition"] == "service_started"
    assert services["init-hdfs"]["depends_on"]["namenode"]["condition"] == "service_healthy"
    assert services["init-hdfs"]["depends_on"]["datanode"]["condition"] == "service_healthy"
    for name in ("namenode", "datanode"):
        assert not services[name].get("ports"), "HDFS stays inside the Compose network"
        assert any(volume["type"] == "volume" for volume in services[name]["volumes"])
