from app.domain.entities.prediction import OrientationResult, PredictionResult, Wagon
from app.domain.repositories.orientation_rules_repository import (
    OrientationRulesRepository,
)


class OrientationService:
    def __init__(self, rules_repository: OrientationRulesRepository):
        self.rules_repository = rules_repository

    def get_allowed_classes(self, wagon: Wagon) -> list[str]:
        return sorted(set(self.rules_repository.get_rules_for_wagon(wagon.wagon_type)))

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
