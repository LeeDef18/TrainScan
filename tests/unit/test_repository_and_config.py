from app.config.config import Settings, get_settings
from app.infrastructure.repositories.csv_orientation_rules_repository import (
    CsvOrientationRulesRepository,
)
from app.infrastructure.storage.file_downloader import FileDownloader


class DummyStorage:
    def __init__(self, content: str = ""):
        self.content = content
        self.calls = []

    def download(self, bucket: str, key: str, path: str) -> None:
        self.calls.append((bucket, key, path))
        with open(path, "w", encoding="utf-8") as file:
            file.write(self.content)


def test_csv_repository_reads_multiple_objects(tmp_path):
    file = tmp_path / "rules.csv"
    file.write_text('Model,Objects\nA,"door, window"\nB,signal\n', encoding="utf-8")

    repository = CsvOrientationRulesRepository(str(file))

    assert repository.get_rules_for_wagon("A") == ["door", "window"]
    assert repository.get_rules_for_wagon("missing") == []


def test_get_settings_reads_environment(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("MODEL_PATH", "custom-model.pt")
    monkeypatch.setenv("MODEL_BUCKET", "model-bucket")
    monkeypatch.setenv("RULE_TABLE_PATH", "rules.csv")
    monkeypatch.setenv("RULE_TABLE_BUCKET", "rules-bucket")
    monkeypatch.setenv("S3_ENDPOINT", "https://example.com")
    monkeypatch.setenv("MODEL_KEY", "weights.pt")
    monkeypatch.setenv("RULE_TABLE_KEY", "orientation.csv")
    monkeypatch.setenv("MODEL_CONF", "0.5")
    monkeypatch.setenv("MODEL_IOU", "0.6")

    settings = get_settings()

    assert settings == Settings(
        model_path="custom-model.pt",
        model_bucket="model-bucket",
        rule_table_path="rules.csv",
        rule_table_bucket="rules-bucket",
        s3_endpoint="https://example.com",
        s3_key=None,
        s3_secret=None,
        model_key="weights.pt",
        rule_table_key="orientation.csv",
        conf=0.5,
        iou=0.6,
        _env_file=None,
    )

    get_settings.cache_clear()


def test_file_downloader_downloads_missing_file(tmp_path):
    path = tmp_path / "rules" / "rule_table.csv"
    storage = DummyStorage("Model,Objects\nA,door\n")
    downloader = FileDownloader(storage)

    result = downloader.ensure_file("rules-bucket", "rule_table.csv", str(path))

    assert result == str(path)
    assert path.read_text(encoding="utf-8") == "Model,Objects\nA,door\n"
    assert storage.calls == [("rules-bucket", "rule_table.csv", str(path))]


def test_file_downloader_skips_existing_file(tmp_path):
    path = tmp_path / "rule_table.csv"
    path.write_text("existing", encoding="utf-8")
    storage = DummyStorage("new")
    downloader = FileDownloader(storage)

    result = downloader.ensure_file("rules-bucket", "rule_table.csv", str(path))

    assert result == str(path)
    assert path.read_text(encoding="utf-8") == "existing"
    assert storage.calls == []
