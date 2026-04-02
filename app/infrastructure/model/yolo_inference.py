from typing import cast


class YOLOInference:
    def __init__(self, model, conf: float, iou: float):
        self.model = model
        self.conf = conf
        self.iou = iou

    def predict(self, image):
        return self.model.predict(
            source=image,
            conf=self.conf,
            iou=self.iou,
        )[0]

    def get_class_names(self) -> dict[int, str]:
        return cast(dict[int, str], self.model.names)
