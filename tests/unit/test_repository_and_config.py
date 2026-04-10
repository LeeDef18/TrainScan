from app.config.config import get_settings
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
    monkeypatch.delenv("S3_KEY", raising=False)
    monkeypatch.delenv("S3_SECRET", raising=False)
    monkeypatch.setenv("MODEL_KEY", "weights.pt")
    monkeypatch.setenv("RULE_TABLE_KEY", "orientation.csv")
    monkeypatch.setenv("MODEL_CONF", "0.5")
    monkeypatch.setenv("MODEL_IOU", "0.6")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_HOST", "127.0.0.1")
    monkeypatch.setenv("APP_PORT", "9000")

    settings = get_settings()

    assert settings.model_path == "custom-model.pt"
    assert settings.model_bucket == "model-bucket"
    assert settings.rule_table_path == "rules.csv"
    assert settings.rule_table_bucket == "rules-bucket"
    assert settings.s3_endpoint == "https://example.com"
    assert settings.model_key == "weights.pt"
    assert settings.rule_table_key == "orientation.csv"
    assert settings.conf == 0.5
    assert settings.iou == 0.6
    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.host == "127.0.0.1"
    assert settings.port == 9000

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
