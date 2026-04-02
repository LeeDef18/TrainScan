import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    model_path: str
    model_bucket: str
    rule_table_path: str
    rule_table_bucket: str
    s3_endpoint: str
    s3_key: str | None
    s3_secret: str | None
    model_key: str
    rule_table_key: str
    conf: float
    iou: float


@lru_cache
def get_settings() -> Settings:
    return Settings(
        model_path=os.getenv("MODEL_PATH", "model/best.pt"),
        model_bucket=os.getenv("MODEL_BUCKET", os.getenv("S3_BUCKET", "wagon-models")),
        rule_table_path=os.getenv("RULE_TABLE_PATH", "data/rules/rule_table.csv"),
        rule_table_bucket=os.getenv("RULE_TABLE_BUCKET", "table-of-rule"),
        s3_endpoint=os.getenv("S3_ENDPOINT", "https://s3.selcdn.ru"),
        s3_key=os.getenv("S3_KEY"),
        s3_secret=os.getenv("S3_SECRET"),
        model_key=os.getenv("MODEL_KEY", "best.pt"),
        rule_table_key=os.getenv("RULE_TABLE_KEY", "rule_table.csv"),
        conf=float(os.getenv("MODEL_CONF", "0.25")),
        iou=float(os.getenv("MODEL_IOU", "0.45")),
    )
