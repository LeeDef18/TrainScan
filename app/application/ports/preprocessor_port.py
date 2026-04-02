from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PreprocessorPort(Protocol):
    def __call__(self, image: Any) -> Any:
        """Preprocess image before inference."""
        raise NotImplementedError
