from fastapi import FastAPI

from app.interfaces.api.routes import router

app = FastAPI(
    title="TrainScan API",
    description="API for wagon orientation detection using YOLO and rule engine.",
    version="1.0.0",
)
app.include_router(router)
