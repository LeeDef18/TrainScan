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
    file.write_text(
        "Model;objects_left;objects_right;;\n"
        "A;door, valve;window;;\n"
        "B;signal;None;;\n",
        encoding="utf-8",
    )

    repository = CsvOrientationRulesRepository(str(file))

    assert repository.get_rules_for_wagon("A") == ["door", "valve", "window"]
    assert repository.get_rules_for_wagon_side("A", "left") == ["door", "valve"]
    assert repository.get_rules_for_wagon_side("A", "right") == ["window"]
    assert repository.get_rules_for_wagon_side("B", "right") == []
    assert repository.get_rules_for_wagon("missing") == []


def test_csv_repository_reads_actual_semicolon_rule_table(tmp_path):
    file = tmp_path / "rule_table.csv"
    file.write_text(
        "Model;objects_left;objects_right;;\n"
        "13-935A-03;brake_cylinder,emergency_reservoir;None;;\n",
        encoding="utf-8",
    )

    repository = CsvOrientationRulesRepository(str(file))

    assert repository.get_rules_for_wagon_side("13-935A-03", "right") == []
    assert repository.get_rules_for_wagon_side("13-935A-03", "left") == [
        "brake_cylinder",
        "emergency_reservoir",
    ]


def test_csv_repository_reads_models_column(tmp_path):
    file = tmp_path / "exceptions.csv"
    file.write_text("Models\n13-192\n", encoding="utf-8")

    repository = CsvOrientationRulesRepository(str(file))

    assert repository.has_wagon("13-192") is True
    assert repository.has_wagon("missing") is False


def test_get_settings_reads_environment(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("MODEL_PATH", "custom-model.pt")
    monkeypatch.setenv("MODEL_2_PATH", "custom-model-2.pt")
    monkeypatch.setenv("MODEL_BUCKET", "model-bucket")
    monkeypatch.setenv("RULE_TABLE_PATH", "rules.csv")
    monkeypatch.setenv("EXCEPTION_TABLE_PATH", "exceptions.csv")
    monkeypatch.setenv("HOPPERS_TABLE_PATH", "hoppers.csv")
    monkeypatch.setenv("RULE_TABLE_BUCKET", "rules-bucket")
    monkeypatch.setenv("EXCEPTION_TABLE_BUCKET", "exceptions-bucket")
    monkeypatch.setenv("HOPPERS_TABLE_BUCKET", "hoppers-bucket")
    monkeypatch.setenv("S3_ENDPOINT", "https://example.com")
    monkeypatch.delenv("S3_KEY", raising=False)
    monkeypatch.delenv("S3_SECRET", raising=False)
    monkeypatch.setenv("MODEL_KEY", "weights.pt")
    monkeypatch.setenv("MODEL_2_KEY", "weights-2.pt")
    monkeypatch.setenv("RULE_TABLE_KEY", "orientation.csv")
    monkeypatch.setenv("EXCEPTION_TABLE_KEY", "exception_wagon.csv")
    monkeypatch.setenv("HOPPERS_TABLE_KEY", "hoppers_wagon_fis.csv")
    monkeypatch.setenv("MODEL_CONF", "0.5")
    monkeypatch.setenv("MODEL_IOU", "0.6")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_HOST", "127.0.0.1")
    monkeypatch.setenv("APP_PORT", "9000")

    settings = get_settings()

    assert settings.model_path == "custom-model.pt"
    assert settings.second_model_path == "custom-model-2.pt"
    assert settings.model_bucket == "model-bucket"
    assert settings.rule_table_path == "rules.csv"
    assert settings.exception_table_path == "exceptions.csv"
    assert settings.hoppers_table_path == "hoppers.csv"
    assert settings.rule_table_bucket == "rules-bucket"
    assert settings.exception_table_bucket == "exceptions-bucket"
    assert settings.hoppers_table_bucket == "hoppers-bucket"
    assert settings.s3_endpoint == "https://example.com"
    assert settings.model_key == "weights.pt"
    assert settings.second_model_key == "weights-2.pt"
    assert settings.rule_table_key == "orientation.csv"
    assert settings.exception_table_key == "exception_wagon.csv"
    assert settings.hoppers_table_key == "hoppers_wagon_fis.csv"
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
