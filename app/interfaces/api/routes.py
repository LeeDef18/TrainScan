import io
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from app.application.dto.prediction_response import PredictionResponse
from app.application.dto.rule_validation_request import (
    RuleValidationRequest,
    WeightedEvidenceItem,
)
from app.application.predict_use_case import PredictInferences, PredictUseCase
from app.application.validate_rules_use_case import ValidateRulesUseCase
from app.config.config import get_settings
from app.domain.entities.prediction import Detection, PredictionResult, Wagon
from app.domain.services.orientation_service import OrientationService
from app.infrastructure.model.detection_extractor import YoloDetectionExtractor
from app.infrastructure.model.model_loader import ModelLoader
from app.infrastructure.model.yolo_inference import YOLOInference
from app.infrastructure.preprocessing.image_preprocessor import preprocess_image
from app.infrastructure.rendering.batch_serializer import (
    build_batch_prediction_payload,
    build_weighted_evidence,
)
from app.infrastructure.rendering.result_serializer import serialize_prediction_response
from app.infrastructure.repositories.csv_orientation_rules_repository import (
    CsvOrientationRulesRepository,
)
from app.infrastructure.storage.file_downloader import FileDownloader
from app.infrastructure.storage.s3_client import S3Client

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[2] / "templates")
)


class WeightedEvidencePayload(BaseModel):
    frames_detected: int = Field(..., ge=0)
    max_confidence: float = Field(..., ge=0.0, le=1.0)
    mean_confidence: float = Field(..., ge=0.0, le=1.0)
    score: float = Field(..., ge=0.0)


class RulesValidationPayload(BaseModel):
    wagon_type: str = Field(..., min_length=1)
    weighted_evidence: dict[str, WeightedEvidencePayload] = Field(..., min_length=1)


def build_predict_use_case() -> PredictUseCase:
    settings = get_settings()
    s3_client = S3Client(settings.s3_endpoint, settings.s3_key, settings.s3_secret)
    file_downloader = FileDownloader(s3_client)
    right_model_loader = ModelLoader(
        settings,
        s3_client=s3_client,
        model_path=settings.model_path,
        model_key=settings.model_key,
    )
    left_model_loader = ModelLoader(
        settings,
        s3_client=s3_client,
        model_path=settings.second_model_path,
        model_key=settings.second_model_key,
    )
    right_model = right_model_loader.get_model()
    left_model = left_model_loader.get_model()
    rule_table_path = file_downloader.ensure_file(
        bucket=settings.rule_table_bucket,
        key=settings.rule_table_key,
        path=settings.rule_table_path,
        force_download=True,
    )
    right_inference = YOLOInference(
        model=right_model, conf=settings.conf, iou=settings.iou
    )
    left_inference = YOLOInference(
        model=left_model, conf=settings.conf, iou=settings.iou
    )
    rules_repository = CsvOrientationRulesRepository(rule_table_path)
    orientation_service = OrientationService(rules_repository)
    detection_extractor = YoloDetectionExtractor()

    def preprocess_for_use_case(image: Any) -> Any:
        return preprocess_image(image)

    return PredictUseCase(
        inferences=PredictInferences(right=right_inference, left=left_inference),
        preprocessor=preprocess_for_use_case,
        orientation_service=orientation_service,
        detection_extractor=detection_extractor,
    )


def build_validate_rules_use_case() -> ValidateRulesUseCase:
    settings = get_settings()
    s3_client = S3Client(settings.s3_endpoint, settings.s3_key, settings.s3_secret)
    file_downloader = FileDownloader(s3_client)
    rule_table_path = file_downloader.ensure_file(
        bucket=settings.rule_table_bucket,
        key=settings.rule_table_key,
        path=settings.rule_table_path,
        force_download=True,
    )
    rules_repository = CsvOrientationRulesRepository(rule_table_path)
    orientation_service = OrientationService(rules_repository)
    return ValidateRulesUseCase(orientation_service)


def get_predict_use_case() -> PredictUseCase:
    return build_predict_use_case()


def get_validate_rules_use_case() -> ValidateRulesUseCase:
    return build_validate_rules_use_case()


def read_image_bytes(image_bytes: bytes) -> Any:
    try:
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image") from exc


def run_side_prediction(
    image_bytes: bytes,
    wagon_type: str,
    use_case: PredictUseCase,
    side: str,
) -> dict:
    pil_image = read_image_bytes(image_bytes)
    processed_image = use_case.preprocessor(pil_image)
    inference = use_case.inference if side == "right" else use_case.left_inference
    raw_result = inference.predict(processed_image)
    prediction = use_case.detection_extractor.extract(
        raw_result,
        inference.get_class_names(),
    )
    response = PredictionResponse(
        prediction=prediction,
        orientation=use_case.orientation_service.check(prediction, Wagon(wagon_type)),
    )
    return serialize_prediction_response(
        response=response,
        raw_result=raw_result,
        image_bytes=image_bytes,
        wagon_type=wagon_type,
    )


def run_prediction(
    image_bytes: bytes,
    wagon_type: str,
    use_case: PredictUseCase,
) -> dict:
    return run_side_prediction(image_bytes, wagon_type, use_case, "right")


def run_two_camera_prediction(
    right_image_bytes: bytes,
    left_image_bytes: bytes,
    wagon_type: str,
    use_case: PredictUseCase,
) -> dict:
    wagon = Wagon(wagon_type=wagon_type)
    right_payload = run_side_prediction(
        right_image_bytes,
        wagon_type,
        use_case,
        "right",
    )
    right_prediction = PredictionResult(
        detections=[
            Detection(
                class_id=prediction["class"],
                class_name=prediction["class_name"],
                confidence=prediction["confidence"],
            )
            for prediction in right_payload["predictions"]
        ]
    )
    right_allowed_classes = use_case.orientation_service.get_allowed_classes_for_side(
        wagon,
        "right",
    )
    right_matched_classes = use_case.orientation_service.get_matched_classes_for_side(
        right_prediction,
        wagon,
        "right",
    )
    right_matched = bool(right_matched_classes)

    left_payload = None
    left_allowed_classes = use_case.orientation_service.get_allowed_classes_for_side(
        wagon,
        "left",
    )
    left_matched_classes: list[str] = []
    left_matched = False
    if not right_matched:
        left_payload = run_side_prediction(
            left_image_bytes,
            wagon_type,
            use_case,
            "left",
        )
        left_prediction = PredictionResult(
            detections=[
                Detection(
                    class_id=prediction["class"],
                    class_name=prediction["class_name"],
                    confidence=prediction["confidence"],
                )
                for prediction in left_payload["predictions"]
            ]
        )
        left_matched_classes = (
            use_case.orientation_service.get_matched_classes_for_side(
                left_prediction,
                wagon,
                "left",
            )
        )
        left_matched = bool(left_matched_classes)

    return {
        "success": True,
        "wagon_type": wagon_type,
        "orientation_check": "A" if right_matched or left_matched else "B",
        "decision_reason": (
            "Matched objects_right with best.pt"
            if right_matched
            else (
                "Matched objects_left with best_2.pt"
                if left_matched
                else "No rule objects matched on either side"
            )
        ),
        "right": {
            **right_payload,
            "matched_rule_side": "objects_right",
            "model_key": "best.pt",
            "allowed_rule_objects": right_allowed_classes,
            "matched_rule_objects": right_matched_classes,
            "rule_match": right_matched,
        },
        "left": (
            None
            if left_payload is None
            else {
                **left_payload,
                "matched_rule_side": "objects_left",
                "model_key": "best_2.pt",
                "allowed_rule_objects": left_allowed_classes,
                "matched_rule_objects": left_matched_classes,
                "rule_match": left_matched,
            }
        ),
    }


def build_batch_orientation(
    weighted_evidence: dict[str, dict],
    wagon_type: str,
    use_case: PredictUseCase,
) -> str:
    aggregated_classes = sorted(
        class_name
        for class_name, evidence in weighted_evidence.items()
        if evidence["score"] >= 0.3
    )
    prediction = PredictionResult(
        detections=[
            Detection(class_id=-1, class_name=detected_class, confidence=1.0)
            for detected_class in aggregated_classes
        ]
    )
    wagon = Wagon(wagon_type=wagon_type)
    return use_case.orientation_service.check(prediction, wagon).label


@router.get("/", response_class=HTMLResponse, tags=["ui"])
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/health", tags=["service"])
async def healthcheck():
    return {"status": "ok"}


@router.post("/predict", tags=["prediction"])
async def predict(
    right_file: UploadFile = File(...),
    left_file: UploadFile = File(...),
    wagon_type: str = Form(...),
    use_case: PredictUseCase = Depends(get_predict_use_case),
):
    right_image_bytes = await right_file.read()
    left_image_bytes = await left_file.read()

    return run_two_camera_prediction(
        right_image_bytes,
        left_image_bytes,
        wagon_type,
        use_case,
    )


@router.post("/predict-batch", tags=["prediction"])
async def predict_batch(
    files: list[UploadFile] = File(...),
    wagon_type: str = Form(...),
    use_case: PredictUseCase = Depends(get_predict_use_case),
):
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="At least one image is required")

    frame_predictions = []
    for index, file in enumerate(files, start=1):
        image_bytes = await file.read()
        frame_payload = run_prediction(image_bytes, wagon_type, use_case)
        frame_predictions.append(
            {
                "frame_index": index,
                "filename": file.filename,
                **frame_payload,
            }
        )

    weighted_evidence = build_weighted_evidence(frame_predictions)
    preliminary_orientation = build_batch_orientation(
        weighted_evidence,
        wagon_type,
        use_case,
    )
    return build_batch_prediction_payload(
        frame_predictions,
        wagon_type,
        weighted_evidence,
        preliminary_orientation,
    )


@router.post("/validate-rules", tags=["prediction"])
async def validate_rules(
    payload: RulesValidationPayload = Body(...),
    use_case: ValidateRulesUseCase = Depends(get_validate_rules_use_case),
):
    response = use_case.execute(
        RuleValidationRequest(
            wagon_type=payload.wagon_type,
            weighted_evidence={
                class_name: WeightedEvidenceItem(
                    frames_detected=evidence.frames_detected,
                    max_confidence=evidence.max_confidence,
                    mean_confidence=evidence.mean_confidence,
                    score=evidence.score,
                )
                for class_name, evidence in payload.weighted_evidence.items()
            },
        )
    )

    return {
        "success": True,
        "wagon_type": response.wagon_type,
        "allowed_classes": response.allowed_classes,
        "confirmed_classes": response.confirmed_classes,
        "matched_rule_objects": response.matched_rule_objects,
        "missing_rule_objects": response.missing_rule_objects,
        "weak_rule_objects": response.weak_rule_objects,
        "final_orientation": response.final_orientation,
        "decision_reason": response.decision_reason,
    }
