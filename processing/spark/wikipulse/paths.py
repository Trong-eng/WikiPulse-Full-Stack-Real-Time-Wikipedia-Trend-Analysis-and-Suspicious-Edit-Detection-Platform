"""Keep run namespaces and query checkpoints independent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelinePaths:
    data_root: str
    checkpoint_root: str

    @classmethod
    def from_settings(cls, settings):
        return cls(
            f"{settings.data_base_path.rstrip('/')}/{settings.run_id}",
            f"{settings.spark_checkpoint_path.rstrip('/')}/{settings.run_id}",
        )

    @property
    def bronze_raw(self):
        return f"{self.data_root}/bronze/raw"

    @property
    def bronze_invalid(self):
        return f"{self.data_root}/bronze/invalid"

    @property
    def silver(self):
        return f"{self.data_root}/silver/events"

    @property
    def gold_activity(self):
        return f"{self.data_root}/gold/activity"

    def checkpoint(self, query_name):
        return f"{self.checkpoint_root}/{query_name}"

    @property
    def gold_trends(self):
        return f"{self.data_root}/gold/trends"

    @property
    def provisional_trends(self):
        return f"{self.data_root}/provisional/trends"

    @property
    def suspicious(self):
        return f"{self.data_root}/serving/suspicious_edits"

    @property
    def event_details(self):
        return f"{self.data_root}/serving/events"
