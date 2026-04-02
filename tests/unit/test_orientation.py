from app.domain.entities.prediction import Detection, PredictionResult, Wagon
from app.domain.services.orientation_service import OrientationService
from app.infrastructure.repositories.csv_orientation_rules_repository import (
    CsvOrientationRulesRepository,
)


def test_orientation_positive(tmp_path):
    file = tmp_path / "rules.csv"
    file.write_text("Model,Objects\nA,door\n", encoding="utf-8")

    repository = CsvOrientationRulesRepository(str(file))
    service = OrientationService(repository)
    prediction = PredictionResult([Detection(0, "door", 0.9)])
    wagon = Wagon("A")

    result = service.check(prediction, wagon)

    assert result.label == "A"


def test_orientation_negative(tmp_path):
    file = tmp_path / "rules.csv"
    file.write_text("Model,Objects\nA,door\n", encoding="utf-8")

    repository = CsvOrientationRulesRepository(str(file))
    service = OrientationService(repository)
    prediction = PredictionResult([Detection(1, "window", 0.9)])
    wagon = Wagon("A")

    result = service.check(prediction, wagon)

    assert result.label == "B"
