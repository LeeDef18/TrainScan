import io
from dataclasses import dataclass
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
from app.application.predict_use_case import (
    PredictInferences,
    PredictRuleRepositories,
    PredictServices,
    PredictUseCase,
)
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


@dataclass(frozen=True)
class RuleDecisionContext:
    orientation_service: OrientationService
    no_match_orientation: str
    decision_table: str
    right_left_match_orientation: str | None = None
    left_right_match_orientation: str | None = None


@dataclass(frozen=True)
class SideRuleResult:
    payload: dict
    allowed_classes: list[str]
    matched_classes: list[str]

    @property
    def is_matched(self) -> bool:
        return bool(self.matched_classes)


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
    rule_repositories = build_rule_repositories(settings, file_downloader)
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
    right_inference = YOLOInference(
        model=right_model, conf=settings.conf, iou=settings.iou
    )
    left_inference = YOLOInference(
        model=left_model, conf=settings.conf, iou=settings.iou
    )
    orientation_service = OrientationService(rule_repositories.regular)
    detection_extractor = YoloDetectionExtractor()

    def preprocess_for_use_case(image: Any) -> Any:
        return preprocess_image(image)

    return PredictUseCase(
        inferences=PredictInferences(right=right_inference, left=left_inference),
        rule_repositories=rule_repositories,
        preprocessor=preprocess_for_use_case,
        services=PredictServices(
            orientation=orientation_service,
            detection_extractor=detection_extractor,
        ),
    )


def build_rule_repositories(settings: Any, file_downloader: FileDownloader):
    rule_table_path = file_downloader.ensure_file(
        bucket=settings.rule_table_bucket,
        key=settings.rule_table_key,
        path=settings.rule_table_path,
        force_download=True,
    )
    exception_table_path = file_downloader.ensure_file(
        bucket=settings.exception_table_bucket,
        key=settings.exception_table_key,
        path=settings.exception_table_path,
        force_download=True,
    )
    hoppers_table_path = file_downloader.ensure_file(
        bucket=settings.hoppers_table_bucket,
        key=settings.hoppers_table_key,
        path=settings.hoppers_table_path,
        force_download=True,
    )
    return PredictRuleRepositories(
        regular=CsvOrientationRulesRepository(rule_table_path),
        exceptions=CsvOrientationRulesRepository(exception_table_path),
        hoppers=CsvOrientationRulesRepository(hoppers_table_path),
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


def build_prediction_from_payload(payload: dict) -> PredictionResult:
    return PredictionResult(
        detections=[
            Detection(
                class_id=prediction["class"],
                class_name=prediction["class_name"],
                confidence=prediction["confidence"],
            )
            for prediction in payload["predictions"]
        ]
    )


def has_detected_class(payload: dict, class_name: str) -> bool:
    expected_class_name = class_name.strip().lower()
    return any(
        prediction["class_name"].strip().lower() == expected_class_name
        for prediction in payload["predictions"]
    )


def enrich_side_payload(
    payload: dict,
    matched_rule_side: str,
    model_key: str,
    allowed_rule_objects: list[str],
    matched_rule_objects: list[str],
) -> dict:
    return {
        **payload,
        "matched_rule_side": matched_rule_side,
        "model_key": model_key,
        "allowed_rule_objects": allowed_rule_objects,
        "matched_rule_objects": matched_rule_objects,
        "rule_match": bool(matched_rule_objects),
    }


def get_side_rule_match(
    payload: dict,
    wagon: Wagon,
    side: str,
    orientation_service: OrientationService,
) -> tuple[list[str], list[str], bool]:
    prediction = build_prediction_from_payload(payload)
    allowed_classes = orientation_service.get_allowed_classes_for_side(wagon, side)
    matched_classes = orientation_service.get_matched_classes_for_side(
        prediction,
        wagon,
        side,
    )
    return allowed_classes, matched_classes, bool(matched_classes)


def build_side_rule_result(
    payload: dict,
    wagon: Wagon,
    side: str,
    orientation_service: OrientationService,
) -> SideRuleResult:
    allowed_classes, matched_classes, _ = get_side_rule_match(
        payload,
        wagon,
        side,
        orientation_service,
    )
    return SideRuleResult(payload, allowed_classes, matched_classes)


def get_side_rule_result(
    image_bytes: bytes,
    wagon: Wagon,
    side: str,
    use_case: PredictUseCase,
    orientation_service: OrientationService,
) -> SideRuleResult:
    payload = run_side_prediction(image_bytes, wagon.wagon_type, use_case, side)
    return build_side_rule_result(
        payload,
        wagon,
        side,
        orientation_service,
    )


def build_exception_prediction(
    right_image_bytes: bytes,
    left_image_bytes: bytes,
    wagon_type: str,
    use_case: PredictUseCase,
) -> dict:
    right_payload = run_side_prediction(
        right_image_bytes,
        wagon_type,
        use_case,
        "right",
    )
    left_payload = run_side_prediction(
        left_image_bytes,
        wagon_type,
        use_case,
        "left",
    )
    right_has_valve = has_detected_class(right_payload, "brake_valve")
    left_has_valve = has_detected_class(left_payload, "brake_valve")

    if left_has_valve:
        orientation = "A"
        decision_reason = "Exception wagon: brake_valve matched on left camera"
    elif right_has_valve:
        orientation = "B"
        decision_reason = "Exception wagon: brake_valve matched on right camera"
    else:
        orientation = "UNDEFINED"
        decision_reason = "Exception wagon: brake_valve was not detected"

    return {
        "success": True,
        "wagon_type": wagon_type,
        "decision_table": "exception_wagon.csv",
        "orientation_check": orientation,
        "manual_review_required": orientation == "UNDEFINED",
        "decision_reason": decision_reason,
        "right": enrich_side_payload(
            right_payload,
            "brake_valve",
            "best.pt",
            ["brake_valve"],
            ["brake_valve"] if right_has_valve else [],
        ),
        "left": enrich_side_payload(
            left_payload,
            "brake_valve",
            "best_2.pt",
            ["brake_valve"],
            ["brake_valve"] if left_has_valve else [],
        ),
    }


def run_side_rule_prediction(
    image_bytes: tuple[bytes, bytes],
    wagon_type: str,
    use_case: PredictUseCase,
    context: RuleDecisionContext,
) -> dict:
    wagon = Wagon(wagon_type=wagon_type)
    right_image_bytes, left_image_bytes = image_bytes
    right_result = get_side_rule_result(
        right_image_bytes,
        wagon,
        "right",
        use_case,
        context.orientation_service,
    )

    left_result = None
    right_left_result = None
    if not right_result.is_matched:
        if context.right_left_match_orientation is not None:
            right_left_result = build_side_rule_result(
                right_result.payload,
                wagon,
                "left",
                context.orientation_service,
            )

        if right_left_result is not None and right_left_result.is_matched:
            return {
                "success": True,
                "wagon_type": wagon_type,
                "decision_table": context.decision_table,
                "orientation_check": context.right_left_match_orientation,
                "manual_review_required": False,
                "decision_reason": (
                    "Matched objects_left with best.pt right camera "
                    f"in {context.decision_table}"
                ),
                "right": enrich_side_payload(
                    right_result.payload,
                    "objects_left",
                    "best.pt",
                    right_left_result.allowed_classes,
                    right_left_result.matched_classes,
                ),
                "left": None,
            }

        left_result = get_side_rule_result(
            left_image_bytes,
            wagon,
            "left",
            use_case,
            context.orientation_service,
        )

    left_matched = left_result.is_matched if left_result is not None else False
    left_right_result = None
    if (
        left_result is not None
        and not left_result.is_matched
        and context.left_right_match_orientation is not None
    ):
        left_right_result = build_side_rule_result(
            left_result.payload,
            wagon,
            "right",
            context.orientation_service,
        )

    if (
        left_result is not None
        and left_right_result is not None
        and left_right_result.is_matched
    ):
        return {
            "success": True,
            "wagon_type": wagon_type,
            "decision_table": context.decision_table,
            "orientation_check": context.left_right_match_orientation,
            "manual_review_required": False,
            "decision_reason": (
                "Matched objects_right with best_2.pt left camera "
                f"in {context.decision_table}"
            ),
            "right": enrich_side_payload(
                right_result.payload,
                "objects_right",
                "best.pt",
                right_result.allowed_classes,
                right_result.matched_classes,
            ),
            "left": enrich_side_payload(
                left_result.payload,
                "objects_right",
                "best_2.pt",
                left_right_result.allowed_classes,
                left_right_result.matched_classes,
            ),
        }

    orientation = (
        "A" if right_result.is_matched or left_matched else context.no_match_orientation
    )
    return {
        "success": True,
        "wagon_type": wagon_type,
        "decision_table": context.decision_table,
        "orientation_check": orientation,
        "manual_review_required": orientation == "UNDEFINED",
        "decision_reason": (
            f"Matched objects_right with best.pt in {context.decision_table}"
            if right_result.is_matched
            else (
                f"Matched objects_left with best_2.pt in {context.decision_table}"
                if left_matched
                else f"No rule objects matched in {context.decision_table}"
            )
        ),
        "right": enrich_side_payload(
            right_result.payload,
            "objects_right",
            "best.pt",
            right_result.allowed_classes,
            right_result.matched_classes,
        ),
        "left": (
            None
            if left_result is None
            else enrich_side_payload(
                left_result.payload,
                "objects_left",
                "best_2.pt",
                left_result.allowed_classes,
                left_result.matched_classes,
            )
        ),
    }


def run_two_camera_prediction(
    right_image_bytes: bytes,
    left_image_bytes: bytes,
    wagon_type: str,
    use_case: PredictUseCase,
) -> dict:
    repositories = use_case.rule_repositories
    if repositories.exceptions.has_wagon(wagon_type):
        return build_exception_prediction(
            right_image_bytes,
            left_image_bytes,
            wagon_type,
            use_case,
        )

    if repositories.regular.has_wagon(wagon_type):
        return run_side_rule_prediction(
            (right_image_bytes, left_image_bytes),
            wagon_type,
            use_case,
            RuleDecisionContext(
                orientation_service=use_case.orientation_service,
                no_match_orientation="UNDEFINED",
                decision_table="rule_table.csv",
                right_left_match_orientation="B",
                left_right_match_orientation="B",
            ),
        )

    if repositories.hoppers.has_wagon(wagon_type):
        return run_side_rule_prediction(
            (right_image_bytes, left_image_bytes),
            wagon_type,
            use_case,
            RuleDecisionContext(
                orientation_service=OrientationService(repositories.hoppers),
                no_match_orientation="B",
                decision_table="hoppers_wagon_fis.csv",
            ),
        )

    raise HTTPException(status_code=400, detail="Unknown wagon type")


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
