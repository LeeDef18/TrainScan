import os
from importlib import import_module

from app.core.config import Settings
from app.infrastructure.storage.storage_port import StoragePort


class ModelLoader:
    def __init__(self, settings: Settings, s3_client: StoragePort | None = None):
        self.settings = settings
        self.s3_client = s3_client
        self._model = None

    def _ensure_model_exists(self) -> None:
        if self.s3_client is None:
            return

        if os.path.exists(self.settings.model_path):
            return

        model_dir = os.path.dirname(self.settings.model_path)
        if model_dir:
            os.makedirs(model_dir, exist_ok=True)

        self.s3_client.download(
            bucket=self.settings.s3_bucket,
            key=self.settings.model_key,
            path=self.settings.model_path,
        )

    def get_model(self):
        if self._model is None:
            self._ensure_model_exists()
            yolo_class = import_module("ultralytics").YOLO
            self._model = yolo_class(self.settings.model_path)
        return self._model
