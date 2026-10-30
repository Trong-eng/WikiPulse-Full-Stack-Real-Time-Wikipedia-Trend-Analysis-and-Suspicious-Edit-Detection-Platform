"""Fail fast for invalid scoring; YAML is data, not executable configuration."""

import copy
from pathlib import Path

import pytest

from processing.spark.wikipulse.scoring import DEFAULT_PATH, load_scoring

pytestmark = pytest.mark.spark  # PyYAML is a dependency of the Spark image.


@pytest.fixture
def yaml():
    import yaml
    return yaml


def test_repository_scoring_defaults():
    config = load_scoring()
    assert config.trend_weights == {"edit_count": 0.5, "unique_editors": 0.25, "abs_byte_delta": 0.25}
    assert config.large_deletion_bytes == 500
    assert config.max_score == 100


@pytest.mark.parametrize("section,field,key,value", [
    ("trend", "weights", "edit_count", -1),
    ("trend", "weights", "edit_count", 0.4),
    ("trend", "weights", "edit_count", float("nan")),
    ("trend", "normalization_caps", "edit_count", 0),
    ("trend", "normalization_caps", "unique_editors", float("inf")),
    ("risk", "weights", "LARGE_DELETION", 1.5),
    ("risk", "weights", "ANONYMOUS_EDIT", True),
    ("risk", "max_score", None, 101),
    ("risk", "large_deletion_bytes", None, 0),
])
def test_rejects_invalid_numbers(tmp_path, section, field, key, value, yaml):
    data = copy.deepcopy(yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8")))
    if key is None:
        data[section][field] = value
    else:
        data[section][field][key] = value
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_scoring(path)


@pytest.mark.parametrize("content", ["", "[]", "trend: {}", "trend: {}\nrisk: {}\nextra: 1"])
def test_rejects_missing_or_unknown_fields(tmp_path, content):
    path = tmp_path / "bad.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_scoring(path)


def test_rejects_yaml_object_tags(tmp_path, yaml):
    path = tmp_path / "bad.yaml"
    path.write_text("!!python/object:builtins.object {}", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_scoring(path)


def test_explicit_path_is_independent_of_working_directory(tmp_path, monkeypatch):
    path = tmp_path / "custom.yaml"
    path.write_bytes(Path(DEFAULT_PATH).read_bytes())
    monkeypatch.chdir(tmp_path)
    assert load_scoring().large_deletion_bytes == load_scoring(path).large_deletion_bytes
