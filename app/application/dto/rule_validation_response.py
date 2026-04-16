from dataclasses import dataclass


@dataclass(frozen=True)
class RuleValidationResponse:
    wagon_type: str
    allowed_classes: list[str]
    confirmed_classes: list[str]
    matched_rule_objects: list[str]
    missing_rule_objects: list[str]
    weak_rule_objects: list[str]
    final_orientation: str
    decision_reason: str
