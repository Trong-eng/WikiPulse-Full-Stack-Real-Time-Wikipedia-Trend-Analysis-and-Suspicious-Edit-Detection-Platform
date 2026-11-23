from ingestion.collector.app import main as entrypoint


def test_live_collector_rejects_replay_mode(monkeypatch):
    monkeypatch.setenv("PIPELINE_MODE", "REPLAY")
    assert entrypoint.main() == 2


def test_main_producer_close_failure_reports_error(monkeypatch):
    class Producer:
        def __init__(self, **kwargs):
            assert kwargs["max_block_ms"] == 1000

        def flush(self, **kwargs):
            pass

        def close(self, **kwargs):
            raise RuntimeError("secret")

    monkeypatch.setenv("PIPELINE_MODE", "LIVE")
    monkeypatch.setattr(entrypoint, "KafkaProducer", Producer)
    monkeypatch.setattr(entrypoint, "run_collector", lambda *args: None)
    assert entrypoint.main() == 1


def test_record_path_outside_artifacts_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("PIPELINE_MODE", "LIVE")
    assert entrypoint.main(["--record", str(tmp_path / "outside.jsonl")]) == 2
