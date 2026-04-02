from app.infrastructure.model.detection_extractor import YoloDetectionExtractor


class DummyBox:
    cls = [0]
    conf = [0.8]


class DummyResult:
    boxes = [DummyBox()]


def test_detection_extractor_returns_detected_classes():
    extractor = YoloDetectionExtractor()

    result = extractor.extract(DummyResult(), {0: "door"})

    assert result.detected_classes == ["door"]
    assert result.detections[0].confidence == 0.8
