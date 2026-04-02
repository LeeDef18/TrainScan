from typing import Protocol, runtime_checkable


@runtime_checkable
class InferencePort(Protocol):
    def predict(self, image):
        raise NotImplementedError

    def get_class_names(self):
        raise NotImplementedError
