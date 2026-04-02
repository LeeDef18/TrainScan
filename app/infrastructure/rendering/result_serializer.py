import base64

import cv2

from app.application.dto.prediction_response import PredictionResponse
from app.domain.entities.prediction import BoundingBox


def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def serialize_prediction_response(
    response: PredictionResponse,
    raw_result,
    image_bytes: bytes,
    wagon_type: str,
) -> dict:
    predictions = []

    for box, detection in zip(raw_result.boxes, response.prediction.detections):
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
        predictions.append(
            {
                "bbox": bbox.as_list(),
                "bbox_int": bbox.as_int_list(),
                "confidence": detection.confidence,
                "class": detection.class_id,
                "class_name": detection.class_name,
            }
        )

    result_image = raw_result.plot()
    _, buffer = cv2.imencode(".jpg", result_image)

    return {
        "success": True,
        "predictions": predictions,
        "result_image": encode_image_to_base64(buffer.tobytes()),
        "original_image": encode_image_to_base64(image_bytes),
        "count": len(predictions),
        "detected_classes": response.prediction.detected_classes,
        "wagon_type": wagon_type,
        "orientation_check": response.orientation.label,
    }
