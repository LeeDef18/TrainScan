from app.application.predict_use_case import (
    PredictInferences,
    PredictRuleRepositories,
    PredictServices,
    PredictUseCase,
)
from app.domain.entities.prediction import Detection, Wagon
from app.domain.services.orientation_service import OrientationService
from app.infrastructure.model.detection_extractor import YoloDetectionExtractor
from app.infrastructure.repositories.csv_orientation_rules_repository import (
    CsvOrientationRulesRepository,
)


class DummyBox:
    cls = [0]
    conf = [0.9]


class DummyResult:
    boxes = [DummyBox()]


class DummyInference:
    def predict(self, image):
        return DummyResult()

    def get_class_names(self):
        return {0: "door"}


def test_usecase_returns_prediction_response(tmp_path):
    file = tmp_path / "rules.csv"
    file.write_text("Model,Objects\nA,door\n", encoding="utf-8")

    repository = CsvOrientationRulesRepository(str(file))
    inference = DummyInference()
    use_case = PredictUseCase(
        inferences=PredictInferences(right=inference, left=inference),
        rule_repositories=PredictRuleRepositories(
            regular=repository,
            exceptions=repository,
            hoppers=repository,
        ),
        preprocessor=lambda image: image,
        services=PredictServices(
            orientation=OrientationService(repository),
            detection_extractor=YoloDetectionExtractor(),
        ),
    )

    response = use_case.execute("img", "A")

    assert response.orientation.label == "A"
    assert response.prediction.detections == [Detection(0, "door", 0.9)]


def test_wagon_entity_stores_type():
    wagon = Wagon("hopper")

    assert wagon.wagon_type == "hopper"
