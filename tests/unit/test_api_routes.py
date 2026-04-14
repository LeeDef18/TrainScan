import asyncio
import sys
from types import SimpleNamespace
from typing import Any

from app.domain.services.orientation_service import OrientationService


class DummySettings:
    s3_endpoint = "https://example.com"
    s3_key = None
    s3_secret = None
    model_bucket = "model-bucket"
    model_key = "best.pt"
    model_path = "model/best.pt"
    rule_table_bucket = "rules-bucket"
    rule_table_key = "rule_table.csv"
    rule_table_path = "data/rules/rule_table.csv"
    conf = 0.25
    iou = 0.45


class DummyS3Client:
    def __init__(self, endpoint, key, secret):
        self.endpoint = endpoint
        self.key = key
        self.secret = secret


class DummyFileDownloader:
    def __init__(self, storage):
        self.storage = storage

    def ensure_file(self, bucket: str, key: str, path: str) -> str:
        return path


class DummyModelLoader:
    def __init__(self, settings, s3_client=None):
        self.settings = settings
        self.s3_client = s3_client

    def get_model(self):
        return object()


class DummyYOLOInference:
    def __init__(self, model, conf: float, iou: float):
        self.model = model
        self.conf = conf
        self.iou = iou

    def predict(self, image):
        return SimpleNamespace(boxes=[])

    def get_class_names(self):
        return {0: "brake_valve"}


class DummyRulesRepository:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_rules_for_wagon(self, wagon_type: str) -> list[str]:
        return ["brake_valve"] if wagon_type == "19-752" else []


def patch_routes_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.interfaces.api.routes.get_settings", lambda: DummySettings()
    )
    monkeypatch.setattr(
        "app.interfaces.api.routes.S3Client", DummyS3Client, raising=False
    )
    monkeypatch.setattr(
        "app.interfaces.api.routes.FileDownloader",
        DummyFileDownloader,
        raising=False,
    )
    monkeypatch.setattr(
        "app.interfaces.api.routes.ModelLoader", DummyModelLoader, raising=False
    )
    monkeypatch.setattr(
        "app.interfaces.api.routes.YOLOInference",
        DummyYOLOInference,
        raising=False,
    )
    monkeypatch.setattr(
        "app.interfaces.api.routes.CsvOrientationRulesRepository",
        DummyRulesRepository,
        raising=False,
    )


def configure_orientation_services(routes) -> None:
    rules_repository = DummyRulesRepository("rules.csv")
    orientation_service = OrientationService(rules_repository)
    routes.use_case.orientation_service = orientation_service
    routes.validate_rules_use_case.orientation_service = orientation_service


def load_routes_module(monkeypatch):
    sys.modules.pop("app.interfaces.api.routes", None)
    patch_routes_dependencies(monkeypatch)

    import app.interfaces.api.routes as routes

    configure_orientation_services(routes)
    return routes


def test_validate_rules_endpoint_returns_diagnostics(monkeypatch):
    routes = load_routes_module(monkeypatch)

    class DummyValidateRulesUseCase:
        def execute(self, request):
            return type(
                "DummyResponse",
                (),
                {
                    "wagon_type": request.wagon_type,
                    "detected_classes": ["door", "window"],
                    "allowed_classes": ["door", "valve"],
                    "matched_classes": ["door"],
                    "missing_classes": ["valve"],
                    "orientation": "A",
                },
            )()

    monkeypatch.setattr(routes, "validate_rules_use_case", DummyValidateRulesUseCase())
    payload_model = routes.RulesValidationPayload(
        wagon_type="19-752", detected_classes=["door", "window"]
    )

    response = asyncio.run(routes.validate_rules(payload_model))

    assert response["matched_classes"] == ["door"]
    assert response["orientation_check"] == "A"


def test_predict_batch_endpoint_returns_aggregated_response(monkeypatch):
    routes = load_routes_module(monkeypatch)

    def dummy_run_prediction(payload: bytes, wagon_type: str) -> dict:
        assert payload == b"image-bytes"
        assert wagon_type == "19-752"
        return {
            "success": True,
            "predictions": [
                {
                    "bbox": [1.0, 2.0, 3.0, 4.0],
                    "bbox_int": [1, 2, 3, 4],
                    "confidence": 0.9,
                    "class": 0,
                    "class_name": "brake_valve",
                }
            ],
            "result_image": "result",
            "original_image": "original",
            "count": 1,
            "detected_classes": ["brake_valve"],
            "wagon_type": wagon_type,
            "orientation_check": "A",
        }

    class DummyUploadFile:
        def __init__(self, filename: str):
            self.filename = filename

        async def read(self) -> bytes:
            return b"image-bytes"

    monkeypatch.setattr(routes, "run_prediction", dummy_run_prediction)

    payload = asyncio.run(
        routes.predict_batch(
            files=cast_upload_files(
                [DummyUploadFile("frame1.jpg"), DummyUploadFile("frame2.jpg")]
            ),
            wagon_type="19-752",
        )
    )

    assert payload["frame_count"] == 2
    assert payload["orientation_check"] == "A"
    assert payload["summary"]["detections_total"] == 2
    assert payload["frames"][0]["filename"] == "frame1.jpg"


def cast_upload_files(files: list[Any]) -> list[Any]:
    return files
