from typing import Protocol, runtime_checkable


@runtime_checkable
class StoragePort(Protocol):
    def download(self, bucket: str, key: str, path: str) -> None: ...
