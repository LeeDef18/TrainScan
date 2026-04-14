from typing import Any

import cv2
import numpy as np


def preprocess_image(image: Any):
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    adjusted = cv2.convertScaleAbs(image, alpha=1.2, beta=30)
    lab = cv2.cvtColor(adjusted, cv2.COLOR_BGR2LAB)
    lightness, channel_a, channel_b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_lightness = clahe.apply(lightness)

    merged = cv2.merge((contrast_lightness, channel_a, channel_b))
    final_image = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return cv2.GaussianBlur(final_image, (3, 3), 0)
