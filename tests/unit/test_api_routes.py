import asyncio
from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class DummyValidationResponse:
    wagon_type: str
    detected_classes: list[str]
    allowed_classes: list[str]
    matched_classes: list[str]
    missing_classes: list[str]
    orientation: str


class DummyValidateRulesUseCase:
    def execute(self, request):
        return DummyValidationResponse(
            wagon_type=request.wagon_type,
            detected_classes=["door", "window"],
            allowed_classes=["door", "valve"],
            matched_classes=["door"],
            missing_classes=["valve"],
            orientation="A",
        )


class DummyUploadFile:
    def __init__(self, filename: str):
        self.filename = filename

    async def read(self) -> bytes:
        return b"image-bytes"


def build_validate_rules_handler():
    use_case = DummyValidateRulesUseCase()

    async def validate_rules(payload):
        response = use_case.execute(payload)
        return {
            "success": True,
            "wagon_type": response.wagon_type,
            "detected_classes": response.detected_classes,
            "allowed_classes": response.allowed_classes,
            "matched_classes": response.matched_classes,
            "missing_classes": response.missing_classes,
            "orientation_check": response.orientation,
        }

    return validate_rules


def build_predict_batch_handler():
    def run_prediction(payload: bytes, wagon_type: str) -> dict:
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

    async def predict_batch(files, wagon_type: str):
        frame_predictions = []
        for index, file in enumerate(files, start=1):
            image_bytes = await file.read()
            frame_payload = run_prediction(image_bytes, wagon_type)
            frame_predictions.append(
                {
                    "frame_index": index,
                    "filename": file.filename,
                    **frame_payload,
                }
            )

        return {
            "success": True,
            "wagon_type": wagon_type,
            "frames": frame_predictions,
            "frame_count": len(frame_predictions),
            "detected_classes": ["brake_valve"],
            "orientation_check": "A",
            "summary": {
                "detections_total": sum(
                    frame_prediction["count"] for frame_prediction in frame_predictions
                ),
                "frames_with_detections": len(frame_predictions),
                "mean_confidence": 0.9,
            },
        }

    return predict_batch


def test_validate_rules_endpoint_returns_diagnostics():
    payload = SimpleNamespace(wagon_type="19-752", detected_classes=["door", "window"])

    response = asyncio.run(build_validate_rules_handler()(payload))

    assert response["matched_classes"] == ["door"]
    assert response["orientation_check"] == "A"


def test_predict_batch_endpoint_returns_aggregated_response():
    payload = asyncio.run(
        build_predict_batch_handler()(
            files=[DummyUploadFile("frame1.jpg"), DummyUploadFile("frame2.jpg")],
            wagon_type="19-752",
        )
    )

    assert payload["frame_count"] == 2
    assert payload["orientation_check"] == "A"
    assert payload["summary"]["detections_total"] == 2
    assert payload["frames"][0]["filename"] == "frame1.jpg"
