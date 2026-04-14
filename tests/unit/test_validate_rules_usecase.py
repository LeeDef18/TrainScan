from app.application.dto.rule_validation_request import RuleValidationRequest
from app.application.validate_rules_use_case import ValidateRulesUseCase
from app.domain.services.orientation_service import OrientationService
from app.infrastructure.repositories.csv_orientation_rules_repository import (
    CsvOrientationRulesRepository,
)


def test_validate_rules_use_case_returns_rule_diagnostics(tmp_path):
    file = tmp_path / "rules.csv"
    file.write_text('Model,Objects\nA,"door, valve"\n', encoding="utf-8")

    repository = CsvOrientationRulesRepository(str(file))
    use_case = ValidateRulesUseCase(OrientationService(repository))

    response = use_case.execute(
        RuleValidationRequest(wagon_type="A", detected_classes=["door", "window"])
    )

    assert response.allowed_classes == ["door", "valve"]
    assert response.matched_classes == ["door"]
    assert response.missing_classes == ["valve"]
    assert response.orientation == "A"
