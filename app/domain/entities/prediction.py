from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float


@dataclass(frozen=True)
class PredictionResult:
    detections: list[Detection]

    @property
    def detected_classes(self) -> list[str]:
        return sorted({detection.class_name for detection in self.detections})


@dataclass(frozen=True)
class Wagon:
    wagon_type: str


@dataclass(frozen=True)
class OrientationResult:
    label: str


@dataclass(frozen=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def as_list(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]

    def as_int_list(self) -> list[int]:
        return [int(self.x1), int(self.y1), int(self.x2), int(self.y2)]
