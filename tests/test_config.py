import pytest


def test_defaults_are_replay_and_isolate_data_by_run():
    from wikipulse_core.config import Settings

    settings = Settings.from_env({})
    assert settings.pipeline_mode == "REPLAY"
    assert settings.run_id == "dev"
    assert settings.wiki_allowlist == ("enwiki", "viwiki")


@pytest.mark.parametrize("values", [
    {"PIPELINE_MODE": "TYPO"},
    {"RUN_ID": "../escape"},
    {"CASSANDRA_KEYSPACE": "name;DROP"},
    {"CASSANDRA_PORT": "0"},
    {"WIKI_ALLOWLIST": ""},
    {"WATERMARK_DELAY": "-5 minutes"},
])
def test_bad_configuration_fails_before_service_start(values):
    from wikipulse_core.config import Settings

    with pytest.raises(ValueError):
        Settings.from_env(values)


def test_host_overrides_are_not_hardcoded():
    from wikipulse_core.config import Settings

    s = Settings.from_env({"CASSANDRA_HOST": "db", "KAFKA_BOOTSTRAP_SERVERS": "broker:19092"})
    assert s.cassandra_host == "db"
    assert s.kafka_bootstrap_servers == "broker:19092"
