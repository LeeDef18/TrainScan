from typing import Protocol, runtime_checkable


@runtime_checkable
class DetectionExtractorPort(Protocol):
    def extract(self, raw_result, model_names): ...
