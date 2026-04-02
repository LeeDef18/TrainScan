from app.core.config import Settings, get_settings
from app.infrastructure.repositories.csv_orientation_rules_repository import (
    CsvOrientationRulesRepository,
)


def test_csv_repository_reads_multiple_objects(tmp_path):
    file = tmp_path / "rules.csv"
    file.write_text('Model,Objects\nA,"door, window"\nB,signal\n', encoding="utf-8")

    repository = CsvOrientationRulesRepository(str(file))

    assert repository.get_rules_for_wagon("A") == ["door", "window"]
    assert repository.get_rules_for_wagon("missing") == []


def test_get_settings_reads_environment(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("MODEL_PATH", "custom-model.pt")
    monkeypatch.setenv("S3_BUCKET", "bucket")
    monkeypatch.setenv("RULE_TABLE", "rules.csv")
    monkeypatch.setenv("S3_ENDPOINT", "https://example.com")
    monkeypatch.setenv("MODEL_KEY", "weights.pt")
    monkeypatch.setenv("MODEL_CONF", "0.5")
    monkeypatch.setenv("MODEL_IOU", "0.6")

    settings = get_settings()

    assert settings == Settings(
        model_path="custom-model.pt",
        s3_bucket="bucket",
        rule_table="rules.csv",
        s3_endpoint="https://example.com",
        s3_key=None,
        s3_secret=None,
        model_key="weights.pt",
        conf=0.5,
        iou=0.6,
    )

    get_settings.cache_clear()
