from statistics import mean


def build_weighted_evidence(frame_predictions: list[dict]) -> dict[str, dict]:
    evidence_map: dict[str, list[float]] = {}

    for frame_prediction in frame_predictions:
        for prediction in frame_prediction["predictions"]:
            class_name = prediction["class_name"]
            evidence_map.setdefault(class_name, []).append(prediction["confidence"])

    return {
        class_name: {
            "frames_detected": len(confidences),
            "max_confidence": round(max(confidences), 4),
            "mean_confidence": round(mean(confidences), 4),
            "score": round(sum(confidences) / len(frame_predictions), 4),
        }
        for class_name, confidences in sorted(evidence_map.items())
    }


def build_batch_prediction_payload(
    frame_predictions: list[dict],
    wagon_type: str,
    weighted_evidence: dict[str, dict],
    preliminary_orientation: str,
) -> dict:
    return {
        "success": True,
        "wagon_type": wagon_type,
        "frames": frame_predictions,
        "frame_count": len(frame_predictions),
        "aggregated_detections": sorted(weighted_evidence.keys()),
        "weighted_evidence": weighted_evidence,
        "preliminary_orientation": preliminary_orientation,
        "evidence_quality": (
            "sufficient"
            if preliminary_orientation == "A"
            else "inconclusive" if weighted_evidence else "weak"
        ),
        "summary": {
            "detections_total": sum(
                frame_prediction["count"] for frame_prediction in frame_predictions
            ),
            "frames_with_detections": sum(
                1
                for frame_prediction in frame_predictions
                if frame_prediction["count"] > 0
            ),
        },
    }
