import asyncio
import importlib


def test_validate_rules_endpoint_returns_diagnostics(monkeypatch):
    routes = importlib.import_module("app.interfaces.api.routes")

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
    routes = importlib.import_module("app.interfaces.api.routes")

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
            files=[DummyUploadFile("frame1.jpg"), DummyUploadFile("frame2.jpg")],
            wagon_type="19-752",
        )
    )

    assert payload["frame_count"] == 2
    assert payload["orientation_check"] == "A"
    assert payload["summary"]["detections_total"] == 2
    assert payload["frames"][0]["filename"] == "frame1.jpg"
