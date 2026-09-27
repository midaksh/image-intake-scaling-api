from __future__ import annotations

import base64
import binascii
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from errors import InvalidImageError, PayloadTooLargeError

_DATA_URL_MARK = "base64,"


def normalize_base64(value: str) -> str:
    text = value.strip()
    marker = text[:128].find(_DATA_URL_MARK)
    if marker != -1:
        text = text[marker + len(_DATA_URL_MARK) :]
    return "".join(text.split())


def decode_and_verify_image(value: str, max_image_bytes: int) -> bytes:
    raw = normalize_base64(value)
    if not raw:
        raise InvalidImageError("Image payload is empty")

    try:
        data = base64.b64decode(raw, validate=True)
    except binascii.Error as exc:
        raise InvalidImageError("Image is not valid base64") from exc

    if not data:
        raise InvalidImageError("Decoded image is empty")
    if len(data) > max_image_bytes:
        raise PayloadTooLargeError("Decoded image exceeds size limit")

    try:
        with Image.open(BytesIO(data)) as verified:
            verified.verify()
        with Image.open(BytesIO(data)) as loaded:
            loaded.load()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise InvalidImageError("Payload is not a valid image") from exc

    return data
