from dataclasses import dataclass

from app.domain.entities.prediction import OrientationResult, PredictionResult


@dataclass(frozen=True)
class PredictionResponse:
    prediction: PredictionResult
    orientation: OrientationResult
