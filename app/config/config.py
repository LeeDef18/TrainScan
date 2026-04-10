from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    model_path: str = Field(default="model/best.pt", alias="MODEL_PATH")
    model_bucket: str = Field(default="wagon-models", alias="MODEL_BUCKET")
    rule_table_path: str = Field(
        default="data/rules/rule_table.csv",
        alias="RULE_TABLE_PATH",
    )
    rule_table_bucket: str = Field(default="table-of-rule", alias="RULE_TABLE_BUCKET")
    s3_endpoint: str = Field(default="https://s3.selcdn.ru", alias="S3_ENDPOINT")
    s3_key: str | None = Field(default=None, alias="S3_KEY")
    s3_secret: str | None = Field(default=None, alias="S3_SECRET")
    model_key: str = Field(default="best.pt", alias="MODEL_KEY")
    rule_table_key: str = Field(default="rule_table.csv", alias="RULE_TABLE_KEY")
    conf: float = Field(default=0.25, alias="MODEL_CONF")
    iou: float = Field(default=0.45, alias="MODEL_IOU")
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="APP_HOST")
    port: int = Field(default=8000, alias="APP_PORT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
