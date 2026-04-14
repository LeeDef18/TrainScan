from statistics import mean


def build_batch_prediction_payload(
    frame_predictions: list[dict],
    wagon_type: str,
    orientation: str,
) -> dict:
    detected_classes = sorted(
        {
            detected_class
            for frame_prediction in frame_predictions
            for detected_class in frame_prediction["detected_classes"]
        }
    )
    frame_confidences = [
        prediction["confidence"]
        for frame_prediction in frame_predictions
        for prediction in frame_prediction["predictions"]
    ]

    return {
        "success": True,
        "wagon_type": wagon_type,
        "frames": frame_predictions,
        "frame_count": len(frame_predictions),
        "detected_classes": detected_classes,
        "orientation_check": orientation,
        "summary": {
            "detections_total": sum(
                frame_prediction["count"] for frame_prediction in frame_predictions
            ),
            "frames_with_detections": sum(
                1
                for frame_prediction in frame_predictions
                if frame_prediction["count"] > 0
            ),
            "mean_confidence": (
                round(mean(frame_confidences), 4) if frame_confidences else None
            ),
        },
    }
