import numpy as np
from PIL import Image

from app.infrastructure.preprocessing.image_preprocessor import preprocess_image


def test_preprocessing_output_shape():
    img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))

    result = preprocess_image(img)

    assert result.shape == (100, 100, 3)
