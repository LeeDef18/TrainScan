import os

from app.infrastructure.storage.storage_port import StoragePort


class FileDownloader:
    def __init__(self, storage: StoragePort):
        self.storage = storage

    def ensure_file(self, bucket: str, key: str, path: str) -> str:
        if os.path.exists(path):
            return path

        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        self.storage.download(bucket=bucket, key=key, path=path)
        return path
