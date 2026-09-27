from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image


def png_base64(width: int = 1, height: int = 1) -> str:
    buffer = BytesIO()
    Image.new("RGBA", (width, height), (255, 0, 0, 255)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()
