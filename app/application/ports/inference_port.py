from typing import Protocol, runtime_checkable


@runtime_checkable
class InferencePort(Protocol):
    def predict(self, image): ...

    def get_class_names(self): ...
