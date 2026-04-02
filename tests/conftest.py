import pytest


@pytest.fixture
def dummy_image():
    import numpy as np
    from PIL import Image

    return Image.fromarray(np.zeros((64, 64, 3), dtype=np.uint8))
