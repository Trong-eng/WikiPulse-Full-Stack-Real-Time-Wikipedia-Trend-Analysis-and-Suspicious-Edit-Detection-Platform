"""Validate shared service settings before starting expensive dependencies."""

import os
import re
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    pipeline_mode: str = "REPLAY"
    run_id: str = "dev"
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_raw_topic: str = "wikipedia.recentchange.raw"
    kafka_dlq_topic: str = "wikipedia.recentchange.dlq"
    pipeline_version: str = "0.1.0"
    user_hash_salt: str = "local-demo-change-me"
    watermark_delay: str = "10 minutes"
    trigger_interval: str = "10 seconds"
    max_offsets_per_trigger: int = 1000
    data_base_path: str = "file:///data/wikipulse"
    spark_checkpoint_path: str = "/data/checkpoints"
    wiki_allowlist: tuple[str, ...] = ("enwiki", "viwiki")
    cassandra_host: str = "cassandra"
    cassandra_port: int = 9042
    cassandra_keyspace: str = "wikipulse"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        values = os.environ if env is None else env
        defaults = cls()
        kwargs = {}
        for name in cls.__dataclass_fields__:
            key = name.upper()
            value = values.get(key, getattr(defaults, name))
            if name in {"cassandra_port", "max_offsets_per_trigger"}:
                value = int(value)
            elif name == "wiki_allowlist" and isinstance(value, str):
                value = tuple(w.strip() for w in value.split(",") if w.strip())
            kwargs[name] = value
        settings = cls(**kwargs)
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.pipeline_mode not in {"LIVE", "REPLAY"}:
            raise ValueError("PIPELINE_MODE must be LIVE or REPLAY")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.run_id):
            raise ValueError("RUN_ID must be a safe directory identifier")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", self.cassandra_keyspace):
            raise ValueError("CASSANDRA_KEYSPACE must be a CQL identifier")
        if not 1 <= self.cassandra_port <= 65535:
            raise ValueError("CASSANDRA_PORT must be between 1 and 65535")
        if self.max_offsets_per_trigger < 1:
            raise ValueError("MAX_OFFSETS_PER_TRIGGER must be positive")
        if not self.wiki_allowlist or any(
            not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", wiki) for wiki in self.wiki_allowlist
        ):
            raise ValueError("WIKI_ALLOWLIST must contain valid wiki identifiers")
        for name in ("watermark_delay", "trigger_interval"):
            if not re.fullmatch(r"[1-9][0-9]* (seconds?|minutes?|hours?)", getattr(self, name)):
                raise ValueError(f"{name.upper()} must be a positive Spark duration")
        for name in ("kafka_bootstrap_servers", "user_hash_salt", "data_base_path", "spark_checkpoint_path"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name.upper()} must not be empty")
