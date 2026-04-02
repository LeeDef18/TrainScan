from app.application.dto.prediction_response import PredictionResponse
from app.application.ports.detection_extractor_port import DetectionExtractorPort
from app.application.ports.inference_port import InferencePort
from app.application.ports.preprocessor_port import PreprocessorPort
from app.domain.entities.prediction import Wagon
from app.domain.services.orientation_service import OrientationService


class PredictUseCase:
    def __init__(
        self,
        inference: InferencePort,
        preprocessor: PreprocessorPort,
        orientation_service: OrientationService,
        detection_extractor: DetectionExtractorPort,
    ):
        self.inference = inference
        self.preprocessor = preprocessor
        self.orientation_service = orientation_service
        self.detection_extractor = detection_extractor

    def execute(self, pil_image, wagon_type: str) -> PredictionResponse:
        processed_image = self.preprocessor(pil_image)
        raw_result = self.inference.predict(processed_image)
        prediction = self.detection_extractor.extract(
            raw_result,
            self.inference.get_class_names(),
        )
        wagon = Wagon(wagon_type=wagon_type)
        orientation = self.orientation_service.check(prediction, wagon)
        return PredictionResponse(prediction=prediction, orientation=orientation)
