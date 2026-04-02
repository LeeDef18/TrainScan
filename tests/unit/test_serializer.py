import base64

import numpy as np

from app.application.dto.prediction_response import PredictionResponse
from app.domain.entities.prediction import (
    Detection,
    OrientationResult,
    PredictionResult,
)
from app.infrastructure.rendering.result_serializer import (
    encode_image_to_base64,
    serialize_prediction_response,
)


class DummyTensor:
    def __init__(self, coords):
        self._coords = coords

    def tolist(self):
        return self._coords


class DummyBox:
    xyxy = [DummyTensor([1.2, 2.3, 10.4, 12.8])]


class DummyRawResult:
    boxes = [DummyBox()]

    def plot(self):
        return np.zeros((10, 10, 3), dtype=np.uint8)


def test_encode_image_to_base64_returns_string():
    encoded = encode_image_to_base64(b"abc")

    assert encoded == base64.b64encode(b"abc").decode("utf-8")


def test_serialize_prediction_response_builds_api_payload():
    response = PredictionResponse(
        prediction=PredictionResult([Detection(0, "door", 0.95)]),
        orientation=OrientationResult("A"),
    )

    payload = serialize_prediction_response(
        response=response,
        raw_result=DummyRawResult(),
        image_bytes=b"img",
        wagon_type="A",
    )

    assert payload["success"] is True
    assert payload["orientation_check"] == "A"
    assert payload["count"] == 1
    assert payload["predictions"][0]["bbox_int"] == [1, 2, 10, 12]
