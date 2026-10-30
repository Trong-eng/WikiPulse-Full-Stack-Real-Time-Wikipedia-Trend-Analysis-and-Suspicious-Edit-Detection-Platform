"""Load and validate a fixed scoring configuration before starting queries."""

import math
from dataclasses import dataclass
from pathlib import Path

TREND_FEATURES = ("edit_count", "unique_editors", "abs_byte_delta")
RISK_REASONS = ("LARGE_DELETION", "REVERT_PATTERN", "ANONYMOUS_EDIT")
DEFAULT_PATH = Path(__file__).resolve().parents[3] / "config/scoring.yaml"


@dataclass(frozen=True)
class ScoringConfig:
    trend_weights: dict[str, float]
    normalization_caps: dict[str, float]
    risk_weights: dict[str, int]
    large_deletion_bytes: int
    max_score: int


def load_scoring(path=DEFAULT_PATH):
    import yaml

    with Path(path).open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    def fields(value, names, label):
        if not isinstance(value, dict) or set(value) != set(names):
            raise ValueError(f"{label}: expected fields {', '.join(names)}")
        return value

    def number(value, label, *, integer=False, minimum=0):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < minimum
                or (integer and not isinstance(value, int))):
            raise ValueError(f"{label}: invalid numeric value")
        return value

    fields(data, ("trend", "risk"), "scoring")
    trend = fields(data["trend"], ("weights", "normalization_caps"), "trend")
    risk = fields(data["risk"], ("weights", "large_deletion_bytes", "max_score"), "risk")
    weights = fields(trend["weights"], TREND_FEATURES, "trend.weights")
    caps = fields(trend["normalization_caps"], TREND_FEATURES, "trend.normalization_caps")
    risk_weights = fields(risk["weights"], RISK_REASONS, "risk.weights")
    weights = {k: float(number(v, f"trend.weights.{k}")) for k, v in weights.items()}
    if not math.isclose(sum(weights.values()), 1, rel_tol=0, abs_tol=1e-9):
        raise ValueError("trend.weights must sum to 1")
    caps = {k: float(number(v, f"caps.{k}", minimum=1)) for k, v in caps.items()}
    risk_weights = {
        k: number(v, f"risk.weights.{k}", integer=True) for k, v in risk_weights.items()
    }
    maximum = number(risk["max_score"], "risk.max_score", integer=True, minimum=1)
    if maximum > 100:
        raise ValueError("risk.max_score must be <= 100")
    threshold = number(risk["large_deletion_bytes"], "risk.large_deletion_bytes",
                       integer=True, minimum=1)
    return ScoringConfig(weights, caps, risk_weights, threshold, maximum)
