from dataclasses import dataclass

from app.application.dto.prediction_response import PredictionResponse
from app.application.ports.detection_extractor_port import DetectionExtractorPort
from app.application.ports.inference_port import InferencePort
from app.application.ports.preprocessor_port import PreprocessorPort
from app.domain.entities.prediction import Wagon
from app.domain.repositories.orientation_rules_repository import (
    OrientationRulesRepository,
)
from app.domain.services.orientation_service import OrientationService


@dataclass(frozen=True)
class PredictInferences:
    right: InferencePort
    left: InferencePort


@dataclass(frozen=True)
class PredictRuleRepositories:
    regular: OrientationRulesRepository
    exceptions: OrientationRulesRepository
    hoppers: OrientationRulesRepository


@dataclass(frozen=True)
class PredictServices:
    orientation: OrientationService
    detection_extractor: DetectionExtractorPort


class PredictUseCase:
    def __init__(
        self,
        inferences: PredictInferences,
        rule_repositories: PredictRuleRepositories,
        preprocessor: PreprocessorPort,
        services: PredictServices,
    ):
        self.inference = inferences.right
        self.left_inference = inferences.left
        self.rule_repositories = rule_repositories
        self.preprocessor = preprocessor
        self.orientation_service = services.orientation
        self.detection_extractor = services.detection_extractor

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
