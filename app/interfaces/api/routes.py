import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.application.dto.prediction_response import PredictionResponse
from app.application.predict_use_case import PredictUseCase
from app.config.config import get_settings
from app.domain.entities.prediction import Wagon
from app.domain.services.orientation_service import OrientationService
from app.infrastructure.model.detection_extractor import YoloDetectionExtractor
from app.infrastructure.model.model_loader import ModelLoader
from app.infrastructure.model.yolo_inference import YOLOInference
from app.infrastructure.preprocessing.image_preprocessor import preprocess_image
from app.infrastructure.rendering.result_serializer import serialize_prediction_response
from app.infrastructure.repositories.csv_orientation_rules_repository import (
    CsvOrientationRulesRepository,
)
from app.infrastructure.storage.file_downloader import FileDownloader
from app.infrastructure.storage.s3_client import S3Client

router = APIRouter()


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

    return PredictUseCase(
        inference=inference,
        preprocessor=preprocess_image,
        orientation_service=orientation_service,
        detection_extractor=detection_extractor,
    )


use_case = build_predict_use_case()


@router.post("/predict")
async def predict(file: UploadFile = File(...), wagon_type: str = Form(...)):
    image_bytes = await file.read()

    try:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image") from exc

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
