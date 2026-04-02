from app.application.ports.detection_extractor_port import DetectionExtractorPort
from app.domain.entities.prediction import Detection, PredictionResult


class YoloDetectionExtractor(DetectionExtractorPort):
    def extract(self, raw_result, model_names: dict[int, str]) -> PredictionResult:
        detections: list[Detection] = []

        for box in raw_result.boxes:
            class_id = int(box.cls[0])
            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=model_names[class_id],
                    confidence=float(box.conf[0]),
                )
            )

        return PredictionResult(detections)
