"""Idempotent bounded Cassandra schema initializer: python -m api.app.init_db."""

import logging
import re
import time
from pathlib import Path

from wikipulse_core.config import Settings
from wikipulse_core.logging import configure_logging
from wikipulse_core.serving import Cluster

logger = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "storage" / "cassandra" / "schema.cql"


def initialize_database(
    settings: Settings | None = None,
    *,
    max_attempts: int = 30,
    retry_delay: float = 2,
    sleep=time.sleep,
) -> None:
    settings = settings or Settings.from_env()
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", settings.cassandra_keyspace):
        raise ValueError("CASSANDRA_KEYSPACE must be a CQL identifier")
    if max_attempts < 1 or retry_delay < 0:
        raise ValueError("Retry attempts must be positive and delay must be nonnegative")
    schema = SCHEMA_PATH.read_text().replace("__KEYSPACE__", settings.cassandra_keyspace)
    statements = [statement.strip() for statement in schema.split(";") if statement.strip()]
    for attempt in range(1, max_attempts + 1):
        cluster = None
        try:
            cluster = Cluster(
                [settings.cassandra_host],
                port=settings.cassandra_port,
                connect_timeout=5,
                control_connection_timeout=5,
            )
            session = cluster.connect()
            session.default_timeout = 10
            for statement in statements:
                session.execute(statement)
            logger.info("Cassandra activity schema initialized")
            return
        except Exception as exc:
            logger.warning("Cassandra schema attempt %d/%d failed", attempt, max_attempts)
            if attempt == max_attempts:
                raise RuntimeError(
                    f"Cassandra schema initialization failed after {max_attempts} attempts"
                ) from exc
        finally:
            if cluster is not None:
                cluster.shutdown()
        sleep(retry_delay)


def main() -> None:
    configure_logging("cassandra-init")
    initialize_database()


if __name__ == "__main__":
    main()
