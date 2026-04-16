from dataclasses import dataclass


@dataclass(frozen=True)
class WeightedEvidenceItem:
    frames_detected: int
    max_confidence: float
    mean_confidence: float
    score: float


@dataclass(frozen=True)
class RuleValidationRequest:
    wagon_type: str
    weighted_evidence: dict[str, WeightedEvidenceItem]
