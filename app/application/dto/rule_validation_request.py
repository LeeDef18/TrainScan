from dataclasses import dataclass


@dataclass(frozen=True)
class RuleValidationRequest:
    wagon_type: str
    detected_classes: list[str]
