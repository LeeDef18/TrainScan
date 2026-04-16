from app.application.dto.rule_validation_request import (
    RuleValidationRequest,
    WeightedEvidenceItem,
)
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
        RuleValidationRequest(
            wagon_type="A",
            weighted_evidence={
                "door": WeightedEvidenceItem(
                    frames_detected=2,
                    max_confidence=0.9,
                    mean_confidence=0.85,
                    score=0.6,
                ),
                "window": WeightedEvidenceItem(
                    frames_detected=1,
                    max_confidence=0.4,
                    mean_confidence=0.4,
                    score=0.2,
                ),
            },
        )
    )

    assert response.allowed_classes == ["door", "valve"]
    assert response.confirmed_classes == ["door"]
    assert response.matched_rule_objects == ["door"]
    assert response.missing_rule_objects == ["valve"]
    assert response.final_orientation == "A"
