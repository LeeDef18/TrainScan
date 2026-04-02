from importlib import import_module


class S3Client:
    def __init__(self, endpoint: str, key: str | None, secret: str | None):
        boto3 = import_module("boto3")
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
        )

    def download(self, bucket: str, key: str, path: str) -> None:
        self.client.download_file(bucket, key, path)
