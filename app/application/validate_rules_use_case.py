from app.application.dto.rule_validation_request import RuleValidationRequest
from app.application.dto.rule_validation_response import RuleValidationResponse
from app.domain.entities.prediction import Wagon
from app.domain.services.orientation_service import OrientationService


class ValidateRulesUseCase:
    def __init__(self, orientation_service: OrientationService):
        self.orientation_service = orientation_service

    def execute(self, request: RuleValidationRequest) -> RuleValidationResponse:
        wagon = Wagon(wagon_type=request.wagon_type)
        allowed_classes = self.orientation_service.get_allowed_classes(wagon)
        confirmed_classes = sorted(
            class_name
            for class_name, evidence in request.weighted_evidence.items()
            if evidence.frames_detected > 0 and evidence.score >= 0.3
        )
        matched_rule_objects = sorted(
            class_name
            for class_name in allowed_classes
            if class_name in confirmed_classes
        )
        missing_rule_objects = sorted(
            class_name
            for class_name in allowed_classes
            if class_name not in request.weighted_evidence
        )
        weak_rule_objects = sorted(
            class_name
            for class_name in allowed_classes
            if class_name in request.weighted_evidence
            and class_name not in confirmed_classes
        )
        final_orientation = "A" if matched_rule_objects else "B"
        decision_reason = self._build_decision_reason(
            matched_rule_objects,
            missing_rule_objects,
            weak_rule_objects,
        )

        return RuleValidationResponse(
            wagon_type=request.wagon_type,
            allowed_classes=allowed_classes,
            confirmed_classes=confirmed_classes,
            matched_rule_objects=matched_rule_objects,
            missing_rule_objects=missing_rule_objects,
            weak_rule_objects=weak_rule_objects,
            final_orientation=final_orientation,
            decision_reason=decision_reason,
        )

    @staticmethod
    def _build_decision_reason(
        matched_rule_objects: list[str],
        missing_rule_objects: list[str],
        weak_rule_objects: list[str],
    ) -> str:
        if matched_rule_objects:
            return (
                "Matched rule objects: "
                + ", ".join(matched_rule_objects)
                + ". Missing: "
                + (", ".join(missing_rule_objects) if missing_rule_objects else "none")
                + ". Weak: "
                + (", ".join(weak_rule_objects) if weak_rule_objects else "none")
            )

        return (
            "No rule objects were confirmed. Missing: "
            + (", ".join(missing_rule_objects) if missing_rule_objects else "none")
            + ". Weak: "
            + (", ".join(weak_rule_objects) if weak_rule_objects else "none")
        )
