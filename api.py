# pylint: disable=no-member,too-many-locals,broad-exception-caught

import base64
import io
import traceback

import cv2
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.templating import Jinja2Templates
from PIL import Image
from ultralytics import YOLO

app = FastAPI()
templates = Jinja2Templates(directory="templates")

model = YOLO("model/best.pt")
rule_table_df = pd.read_csv("rule_table.csv")


def preprocess_image(pil_image):

    img = np.array(pil_image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    alpha = 1.2
    beta = 30
    adjusted = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

    lab = cv2.cvtColor(adjusted, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    limg = cv2.merge((cl, a, b))
    final_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    final_img = cv2.GaussianBlur(final_img, (3, 3), 0)

    return final_img


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/predict")
async def predict(file: UploadFile = File(...), wagon_type: str = Form(...)):
    try:
        image_bytes = await file.read()

        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception:
            return {"success": False, "error": "Некорректный файл изображения"}

        preprocessed_img = preprocess_image(pil_image)

        results = model.predict(source=preprocessed_img, conf=0.25, iou=0.45)
        result = results[0]

        predictions = []
        detected_classes = []

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]

            detected_classes.append(cls_name)

            predictions.append(
                {
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "bbox_int": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": conf,
                    "class": cls_id,
                    "class_name": cls_name,
                }
            )

        detected_classes = list(set(detected_classes))

        rule_of_type = (
            rule_table_df[rule_table_df["Model"] == wagon_type]["Objects"]
            .str.split(", ")
            .explode()
        )

        correctness = "B"
        for c in detected_classes:
            if c in rule_of_type.tolist():
                correctness = "A"
                break

        result_img_bgr = result.plot()
        _, buffer = cv2.imencode(".jpg", result_img_bgr)

        result_base64 = base64.b64encode(buffer).decode()
        orig_base64 = base64.b64encode(image_bytes).decode()

        return {
            "success": True,
            "predictions": predictions,
            "result_image": result_base64,
            "original_image": orig_base64,
            "count": len(predictions),
            "detected_classes": detected_classes,
            "wagon_type": wagon_type,
            "orientation_check": correctness,
        }

    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
