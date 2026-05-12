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


class DummyRepository:
    def __init__(self, has_wagon=False, rules=None):
        self._has_wagon = has_wagon
        self._rules = rules or ["brake_valve"]

    def has_wagon(self, wagon_type):
        return self._has_wagon

    def get_rules_for_wagon_side(self, wagon_type, side):
        return self._rules

    def get_rules_for_wagon(self, wagon_type):
        return self._rules


class DummyRuleRepositories:
    def __init__(self, table="regular"):
        self.regular = DummyRepository(table == "regular")
        self.exceptions = DummyRepository(table == "exceptions")
        hoppers_rules = ["other_class"] if table == "hoppers" else ["brake_valve"]
        self.hoppers = DummyRepository(table == "hoppers", hoppers_rules)


class DummyPredictUseCase:
    def __init__(self, matched_side="right", table="regular"):
        self.matched_side = matched_side
        self.match_calls = []
        self.rule_repositories = DummyRuleRepositories(table)
        self.preprocessor = lambda image: image
        self.inference = self
        self.left_inference = self
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

    def has_match_for_side(self, prediction, wagon, side):
        return side == self.matched_side

    def get_allowed_classes_for_side(self, wagon, side):
        return ["brake_valve"]

    def get_matched_classes_for_side(self, prediction, wagon, side):
        self.match_calls.append(side)
        if self.matched_side == "right_left":
            return ["brake_valve"] if self.match_calls == ["right", "left"] else []
        if self.matched_side == "left":
            return (
                ["brake_valve"] if self.match_calls == ["right", "left", "left"] else []
            )
        return ["brake_valve"] if side == self.matched_side else []


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


def test_predict_endpoint_uses_two_camera_payload():
    image_bytes = make_image_bytes()

    response = asyncio.run(
        routes.predict(
            right_file=cast(Any, DummyUploadFile("right.jpg", image_bytes)),
            left_file=cast(Any, DummyUploadFile("left.jpg", image_bytes)),
            wagon_type="19-752",
            use_case=cast(Any, DummyPredictUseCase()),
        )
    )

    assert response["orientation_check"] == "A"
    assert response["right"]["rule_match"] is True
    assert response["right"]["allowed_rule_objects"] == ["brake_valve"]
    assert response["right"]["matched_rule_objects"] == ["brake_valve"]
    assert response["left"] is None


def test_predict_endpoint_returns_a_when_left_side_matches():
    image_bytes = make_image_bytes()

    response = asyncio.run(
        routes.predict(
            right_file=cast(Any, DummyUploadFile("right.jpg", image_bytes)),
            left_file=cast(Any, DummyUploadFile("left.jpg", image_bytes)),
            wagon_type="19-752",
            use_case=cast(Any, DummyPredictUseCase(matched_side="left")),
        )
    )

    assert response["orientation_check"] == "A"
    assert response["right"]["rule_match"] is False
    assert response["left"]["rule_match"] is True
    assert response["left"]["allowed_rule_objects"] == ["brake_valve"]
    assert response["left"]["matched_rule_objects"] == ["brake_valve"]
    assert response["decision_reason"] == (
        "Matched objects_left with best_2.pt in rule_table.csv"
    )


def test_predict_endpoint_returns_b_when_right_matches_left_rules():
    image_bytes = make_image_bytes()

    response = asyncio.run(
        routes.predict(
            right_file=cast(Any, DummyUploadFile("right.jpg", image_bytes)),
            left_file=cast(Any, DummyUploadFile("left.jpg", image_bytes)),
            wagon_type="19-752",
            use_case=cast(Any, DummyPredictUseCase(matched_side="right_left")),
        )
    )

    assert response["orientation_check"] == "B"
    assert response["right"]["matched_rule_side"] == "objects_left"
    assert response["right"]["rule_match"] is True
    assert response["left"] is None


def test_predict_endpoint_returns_undefined_for_regular_without_matches():
    image_bytes = make_image_bytes()

    response = asyncio.run(
        routes.predict(
            right_file=cast(Any, DummyUploadFile("right.jpg", image_bytes)),
            left_file=cast(Any, DummyUploadFile("left.jpg", image_bytes)),
            wagon_type="19-752",
            use_case=cast(Any, DummyPredictUseCase(matched_side="none")),
        )
    )

    assert response["decision_table"] == "rule_table.csv"
    assert response["orientation_check"] == "UNDEFINED"
    assert response["manual_review_required"] is True


def test_predict_endpoint_uses_exception_table_before_regular_rules():
    image_bytes = make_image_bytes()

    response = asyncio.run(
        routes.predict(
            right_file=cast(Any, DummyUploadFile("right.jpg", image_bytes)),
            left_file=cast(Any, DummyUploadFile("left.jpg", image_bytes)),
            wagon_type="13-exception",
            use_case=cast(Any, DummyPredictUseCase(table="exceptions")),
        )
    )

    assert response["decision_table"] == "exception_wagon.csv"
    assert response["orientation_check"] == "A"
    assert response["left"]["matched_rule_objects"] == ["brake_valve"]


def test_predict_endpoint_returns_b_for_hopper_without_matches():
    image_bytes = make_image_bytes()

    response = asyncio.run(
        routes.predict(
            right_file=cast(Any, DummyUploadFile("right.jpg", image_bytes)),
            left_file=cast(Any, DummyUploadFile("left.jpg", image_bytes)),
            wagon_type="hopper",
            use_case=cast(
                Any,
                DummyPredictUseCase(matched_side="none", table="hoppers"),
            ),
        )
    )

    assert response["decision_table"] == "hoppers_wagon_fis.csv"
    assert response["orientation_check"] == "B"
    assert response["manual_review_required"] is False


def test_predict_endpoint_rejects_unknown_wagon_type():
    image_bytes = make_image_bytes()

    try:
        asyncio.run(
            routes.predict(
                right_file=cast(Any, DummyUploadFile("right.jpg", image_bytes)),
                left_file=cast(Any, DummyUploadFile("left.jpg", image_bytes)),
                wagon_type="missing",
                use_case=cast(Any, DummyPredictUseCase(table="missing")),
            )
        )
    except routes.HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Unknown wagon type"
    else:
        raise AssertionError("Unknown wagon type must raise HTTPException")
