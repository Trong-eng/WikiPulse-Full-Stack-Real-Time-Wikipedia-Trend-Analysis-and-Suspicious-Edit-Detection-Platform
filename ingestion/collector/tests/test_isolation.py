from types import SimpleNamespace

import pytest

from ingestion.collector.tests.isolation import verify_broker


def test_rejects_broker_port_not_owned_by_project(monkeypatch):
    def fake_run(command, **kwargs):
        output = "wikipulse-thanh-w3-test\n" if "inspect" in command else "127.0.0.1:39092\n"
        return SimpleNamespace(stdout=output)

    monkeypatch.setattr("ingestion.collector.tests.isolation.subprocess.run", fake_run)
    with pytest.raises(ValueError):
        verify_broker("wikipulse-thanh-w3-test", "127.0.0.1:49092")


def test_rejects_non_loopback_without_docker_access(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("must not inspect Docker for invalid address")

    monkeypatch.setattr("ingestion.collector.tests.isolation.subprocess.run", forbidden)
    with pytest.raises(ValueError):
        verify_broker("wikipulse-thanh-w3-test", "example.invalid:39092")
