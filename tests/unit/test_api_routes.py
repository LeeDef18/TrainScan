import asyncio
from io import BytesIO
from typing import Any, cast

from PIL import Image

from app.interfaces.api import routes


class DummyBox:
    cls = [0]
    conf = [0.9]

    class DummyTensor:
        def __init__(self, coords):
            self._coords = coords

        def tolist(self):
            return self._coords

    xyxy = [DummyTensor([1.0, 2.0, 3.0, 4.0])]


class DummyRawResult:
    boxes = [DummyBox()]

    def plot(self):
        import numpy as np

        return np.zeros((8, 8, 3), dtype=np.uint8)


class DummyPredictUseCase:
    def __init__(self):
        self.preprocessor = lambda image: image
        self.inference = self
        self.detection_extractor = self
        self.orientation_service = self

    def predict(self, image):
        return DummyRawResult()

    def get_class_names(self):
        return {0: "brake_valve"}

    def extract(self, raw_result, model_names):
        return type(
            "PredictionResultLike",
            (),
            {
                "detections": [
                    type(
                        "DetectionLike",
                        (),
                        {
                            "class_id": 0,
                            "class_name": "brake_valve",
                            "confidence": 0.9,
                        },
                    )()
                ],
                "detected_classes": ["brake_valve"],
            },
        )()

    def check(self, prediction, wagon):
        return type("OrientationLike", (), {"label": "A"})()


class DummyValidateRulesUseCase:
    def execute(self, request):
        return type(
            "DummyResponse",
            (),
            {
                "wagon_type": request.wagon_type,
                "allowed_classes": ["brake_valve", "brake_cylinder"],
                "confirmed_classes": ["brake_valve"],
                "matched_rule_objects": ["brake_valve"],
                "missing_rule_objects": ["brake_cylinder"],
                "weak_rule_objects": [],
                "final_orientation": "A",
                "decision_reason": (
                    "Matched rule objects: brake_valve. "
                    "Missing: brake_cylinder. Weak: none"
                ),
            },
        )()


class DummyUploadFile:
    def __init__(self, filename: str, payload: bytes):
        self.filename = filename
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (16, 16), color=0)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_validate_rules_endpoint_returns_diagnostics():
    payload = routes.RulesValidationPayload(
        wagon_type="19-752",
        weighted_evidence={
            "brake_valve": {
                "frames_detected": 2,
                "max_confidence": 0.9,
                "mean_confidence": 0.85,
                "score": 0.6,
            }
        },
    )

    response = asyncio.run(
        routes.validate_rules(
            payload=payload,
            use_case=cast(Any, DummyValidateRulesUseCase()),
        )
    )

    assert response["matched_rule_objects"] == ["brake_valve"]
    assert response["final_orientation"] == "A"


def test_predict_batch_endpoint_returns_aggregated_response():
    image_bytes = make_image_bytes()

    response = asyncio.run(
        routes.predict_batch(
            files=cast(
                Any,
                [
                    DummyUploadFile("frame1.jpg", image_bytes),
                    DummyUploadFile("frame2.jpg", image_bytes),
                ],
            ),
            wagon_type="19-752",
            use_case=cast(Any, DummyPredictUseCase()),
        )
    )

    assert response["frame_count"] == 2
    assert response["preliminary_orientation"] == "A"
    assert response["summary"]["detections_total"] == 2
    assert response["frames"][0]["filename"] == "frame1.jpg"
    assert response["weighted_evidence"]["brake_valve"]["frames_detected"] == 2
