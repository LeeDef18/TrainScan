from importlib import import_module

from app.config.config import Settings
from app.infrastructure.storage.file_downloader import FileDownloader
from app.infrastructure.storage.storage_port import StoragePort


class ModelLoader:
    def __init__(self, settings: Settings, s3_client: StoragePort | None = None):
        self.settings = settings
        self.s3_client = s3_client
        self._model = None
        self.file_downloader = (
            FileDownloader(s3_client) if s3_client is not None else None
        )

    def _ensure_model_exists(self) -> None:
        if self.file_downloader is None:
            return

        self.file_downloader.ensure_file(
            bucket=self.settings.model_bucket,
            key=self.settings.model_key,
            path=self.settings.model_path,
        )

    def get_model(self):
        if self._model is None:
            self._ensure_model_exists()
            yolo_class = import_module("ultralytics").YOLO
            self._model = yolo_class(self.settings.model_path)
        return self._model
