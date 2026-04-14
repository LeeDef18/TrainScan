from dataclasses import dataclass


@dataclass(frozen=True)
class RuleValidationResponse:
    wagon_type: str
    detected_classes: list[str]
    allowed_classes: list[str]
    matched_classes: list[str]
    missing_classes: list[str]
    orientation: str
