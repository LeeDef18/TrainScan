import json
import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit(
            "Usage: python request_prediction.py <api-url> <image-path> "
            "<wagon-type> <output-key>"
        )

    api_url = sys.argv[1].rstrip("/")
    image_path = Path(sys.argv[2])
    wagon_type = sys.argv[3]
    output_key = sys.argv[4].lstrip("/")
    output_bucket = os.environ["AIRFLOW_OUTPUT_BUCKET"]

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

    import requests

    from app.infrastructure.storage.s3_client import S3Client

    with image_path.open("rb") as image_file:
        response = requests.post(
            f"{api_url}/predict",
            files={"file": (image_path.name, image_file, "image/jpeg")},
            data={"wagon_type": wagon_type},
            timeout=300,
        )

    response.raise_for_status()
    payload = response.json()

    client = S3Client(
        endpoint=os.environ["S3_ENDPOINT"],
        key=os.environ.get("S3_KEY"),
        secret=os.environ.get("S3_SECRET"),
    )
    client.client.put_object(
        Bucket=output_bucket,
        Key=output_key,
        Body=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    print(f"Saved prediction to s3://{output_bucket}/{output_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
