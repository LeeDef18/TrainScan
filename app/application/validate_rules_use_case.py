from app.application.dto.rule_validation_request import RuleValidationRequest
from app.application.dto.rule_validation_response import RuleValidationResponse
from app.domain.entities.prediction import Detection, PredictionResult, Wagon
from app.domain.services.orientation_service import OrientationService


class ValidateRulesUseCase:
    def __init__(self, orientation_service: OrientationService):
        self.orientation_service = orientation_service

    def execute(self, request: RuleValidationRequest) -> RuleValidationResponse:
        normalized_classes = sorted(
            {
                detected_class.strip()
                for detected_class in request.detected_classes
                if detected_class.strip()
            }
        )
        prediction = PredictionResult(
            detections=[
                Detection(class_id=-1, class_name=detected_class, confidence=1.0)
                for detected_class in normalized_classes
            ]
        )
        wagon = Wagon(wagon_type=request.wagon_type)
        allowed_classes = self.orientation_service.get_allowed_classes(wagon)
        matched_classes = sorted(set(normalized_classes) & set(allowed_classes))
        missing_classes = sorted(
            detected_class
            for detected_class in allowed_classes
            if detected_class not in normalized_classes
        )
        orientation = self.orientation_service.check(prediction, wagon)

        return RuleValidationResponse(
            wagon_type=request.wagon_type,
            detected_classes=normalized_classes,
            allowed_classes=allowed_classes,
            matched_classes=matched_classes,
            missing_classes=missing_classes,
            orientation=orientation.label,
        )
