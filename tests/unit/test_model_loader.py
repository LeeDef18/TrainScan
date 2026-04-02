import sys
import types
from pathlib import Path

from app.core.config import Settings
from app.infrastructure.model.model_loader import ModelLoader


class DummyS3Client:
    def __init__(self):
        self.calls = []

    def download(self, bucket: str, key: str, path: str) -> None:
        self.calls.append((bucket, key, path))
        Path(path).write_text("weights", encoding="utf-8")


def test_model_loader_downloads_when_model_missing(monkeypatch, tmp_path):
    model_path = tmp_path / "model" / "best.pt"
    settings = Settings(
        model_path=str(model_path),
        s3_bucket="bucket",
        rule_table="rules.csv",
        s3_endpoint="https://example.com",
        s3_key=None,
        s3_secret=None,
        model_key="best.pt",
        conf=0.25,
        iou=0.45,
    )
    s3_client = DummyS3Client()
    created_models = []

    def fake_yolo(path):
        created_models.append(path)
        return {"path": path}

    monkeypatch.setitem(
        sys.modules,
        "ultralytics",
        types.SimpleNamespace(YOLO=fake_yolo),
    )

    loader = ModelLoader(settings, s3_client=s3_client)
    model = loader.get_model()

    assert model == {"path": str(model_path)}
    assert s3_client.calls == [("bucket", "best.pt", str(model_path))]
    assert created_models == [str(model_path)]


def test_model_loader_reuses_cached_model(monkeypatch, tmp_path):
    model_path = tmp_path / "best.pt"
    model_path.write_text("weights", encoding="utf-8")
    settings = Settings(
        model_path=str(model_path),
        s3_bucket="bucket",
        rule_table="rules.csv",
        s3_endpoint="https://example.com",
        s3_key=None,
        s3_secret=None,
        model_key="best.pt",
        conf=0.25,
        iou=0.45,
    )
    created_models = []

    def fake_yolo(path):
        created_models.append(path)
        return {"path": path}

    monkeypatch.setitem(
        sys.modules,
        "ultralytics",
        types.SimpleNamespace(YOLO=fake_yolo),
    )

    loader = ModelLoader(settings)

    first = loader.get_model()
    second = loader.get_model()

    assert first is second
    assert created_models == [str(model_path)]
