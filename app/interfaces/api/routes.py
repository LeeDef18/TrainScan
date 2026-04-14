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
from app.application.dto.rule_validation_request import RuleValidationRequest
from app.application.predict_use_case import PredictUseCase
from app.application.validate_rules_use_case import ValidateRulesUseCase
from app.config.config import get_settings
from app.domain.entities.prediction import Detection, PredictionResult, Wagon
from app.domain.services.orientation_service import OrientationService
from app.infrastructure.model.detection_extractor import YoloDetectionExtractor
from app.infrastructure.model.model_loader import ModelLoader
from app.infrastructure.model.yolo_inference import YOLOInference
from app.infrastructure.preprocessing.image_preprocessor import preprocess_image
from app.infrastructure.rendering.batch_serializer import build_batch_prediction_payload
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


class RulesValidationPayload(BaseModel):
    wagon_type: str = Field(..., min_length=1)
    detected_classes: list[str] = Field(..., min_length=1)


def build_predict_use_case() -> PredictUseCase:
    settings = get_settings()
    s3_client = S3Client(settings.s3_endpoint, settings.s3_key, settings.s3_secret)
    file_downloader = FileDownloader(s3_client)
    model_loader = ModelLoader(settings, s3_client=s3_client)
    model = model_loader.get_model()
    rule_table_path = file_downloader.ensure_file(
        bucket=settings.rule_table_bucket,
        key=settings.rule_table_key,
        path=settings.rule_table_path,
    )
    inference = YOLOInference(model=model, conf=settings.conf, iou=settings.iou)
    rules_repository = CsvOrientationRulesRepository(rule_table_path)
    orientation_service = OrientationService(rules_repository)
    detection_extractor = YoloDetectionExtractor()

    def preprocess_for_use_case(image: Any) -> Any:
        return preprocess_image(image)

    return PredictUseCase(
        inference=inference,
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


def run_prediction(
    image_bytes: bytes,
    wagon_type: str,
    use_case: PredictUseCase,
) -> dict:
    pil_image = read_image_bytes(image_bytes)
    processed_image = use_case.preprocessor(pil_image)
    raw_result = use_case.inference.predict(processed_image)
    prediction = use_case.detection_extractor.extract(
        raw_result,
        use_case.inference.get_class_names(),
    )
    wagon = Wagon(wagon_type=wagon_type)
    orientation = use_case.orientation_service.check(prediction, wagon)
    response = PredictionResponse(prediction=prediction, orientation=orientation)
    return serialize_prediction_response(
        response=response,
        raw_result=raw_result,
        image_bytes=image_bytes,
        wagon_type=wagon_type,
    )


def build_batch_orientation(
    frame_payloads: list[dict],
    wagon_type: str,
    use_case: PredictUseCase,
) -> str:
    aggregated_classes = sorted(
        {
            detected_class
            for frame_payload in frame_payloads
            for detected_class in frame_payload["detected_classes"]
        }
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
    file: UploadFile = File(...),
    wagon_type: str = Form(...),
    use_case: PredictUseCase = Depends(get_predict_use_case),
):
    image_bytes = await file.read()

    return run_prediction(image_bytes, wagon_type, use_case)


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

    orientation = build_batch_orientation(frame_predictions, wagon_type, use_case)
    return build_batch_prediction_payload(frame_predictions, wagon_type, orientation)


@router.post("/validate-rules", tags=["prediction"])
async def validate_rules(
    payload: RulesValidationPayload = Body(...),
    use_case: ValidateRulesUseCase = Depends(get_validate_rules_use_case),
):
    response = use_case.execute(
        RuleValidationRequest(
            wagon_type=payload.wagon_type,
            detected_classes=payload.detected_classes,
        )
    )

    return {
        "success": True,
        "wagon_type": response.wagon_type,
        "detected_classes": response.detected_classes,
        "allowed_classes": response.allowed_classes,
        "matched_classes": response.matched_classes,
        "missing_classes": response.missing_classes,
        "orientation_check": response.orientation,
    }
