from app.domain.entities.prediction import OrientationResult, PredictionResult, Wagon
from app.domain.repositories.orientation_rules_repository import (
    OrientationRulesRepository,
)


class OrientationService:
    def __init__(self, rules_repository: OrientationRulesRepository):
        self.rules_repository = rules_repository

    def get_allowed_classes(self, wagon: Wagon) -> list[str]:
        return sorted(set(self.rules_repository.get_rules_for_wagon(wagon.wagon_type)))

    def get_allowed_classes_for_side(self, wagon: Wagon, side: str) -> list[str]:
        return sorted(
            set(self.rules_repository.get_rules_for_wagon_side(wagon.wagon_type, side))
        )

    def check(
        self,
        prediction: PredictionResult,
        wagon: Wagon,
    ) -> OrientationResult:
        allowed_classes = set(self.get_allowed_classes(wagon))

        for detected_class in prediction.detected_classes:
            if detected_class in allowed_classes:
                return OrientationResult("A")

        return OrientationResult("B")

    def has_match_for_side(
        self,
        prediction: PredictionResult,
        wagon: Wagon,
        side: str,
    ) -> bool:
        return bool(self.get_matched_classes_for_side(prediction, wagon, side))

    def get_matched_classes_for_side(
        self,
        prediction: PredictionResult,
        wagon: Wagon,
        side: str,
    ) -> list[str]:
        allowed_classes = set(self.get_allowed_classes_for_side(wagon, side))
        normalized_allowed = {
            self._normalize_class_name(class_name) for class_name in allowed_classes
        }
        return sorted(
            detected_class
            for detected_class in prediction.detected_classes
            if self._normalize_class_name(detected_class) in normalized_allowed
        )

    @staticmethod
    def _normalize_class_name(class_name: str) -> str:
        return class_name.strip().lower()
