import json
import sys
from pathlib import Path

import requests


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit(
            "Usage: python request_prediction.py <api-url> <image-path> "
            "<wagon-type> <output-path>"
        )

    api_url = sys.argv[1].rstrip("/")
    image_path = Path(sys.argv[2])
    wagon_type = sys.argv[3]
    output_path = Path(sys.argv[4])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        print(f"Prediction already exists: {output_path}")
        return 0

    with image_path.open("rb") as image_file:
        response = requests.post(
            f"{api_url}/predict",
            files={"file": (image_path.name, image_file, "image/jpeg")},
            data={"wagon_type": wagon_type},
            timeout=300,
        )

    response.raise_for_status()
    payload = response.json()

    with output_path.open("w", encoding="utf-8") as result_file:
        json.dump(payload, result_file, ensure_ascii=False, indent=2)

    print(f"Saved prediction to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
