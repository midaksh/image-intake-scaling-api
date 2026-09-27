from __future__ import annotations

import asyncio
import base64
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as api
from errors import InvalidImageError, PayloadTooLargeError
from image import decode_and_verify_image
from tests.helpers import png_base64

TINY_PNG = png_base64()


@pytest.fixture
def client() -> TestClient:
    return TestClient(api.app)


@pytest.fixture(autouse=True)
def restore_settings() -> None:
    api.settings.reload()
    yield
    api.settings.reload()


def test_accepts_valid_png(client: TestClient) -> None:
    response = client.post("/", json={"image": TINY_PNG})
    assert response.status_code == 200
    assert response.json() == {"message": "accepted"}
    assert "X-Request-ID" in response.headers


def test_accepts_data_url(client: TestClient) -> None:
    response = client.post("/", json={"image": f"data:image/png;base64,{TINY_PNG}"})
    assert response.status_code == 200
    assert response.json() == {"message": "accepted"}


def test_rejects_missing_field(client: TestClient) -> None:
    response = client.post("/", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"


def test_rejects_invalid_base64(client: TestClient) -> None:
    response = client.post("/", json={"image": "not-valid-base64!!!"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"


def test_rejects_non_image_bytes(client: TestClient) -> None:
    payload = base64.b64encode(b"hello").decode()
    response = client.post("/", json={"image": payload})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"
    assert "valid image" in response.json()["error"]["message"]


def test_rejects_corrupt_png_checksum(client: TestClient) -> None:
    raw = base64.b64decode(TINY_PNG)
    corrupt = raw[:-8] + b"xxxxxxxx"
    response = client.post("/", json={"image": base64.b64encode(corrupt).decode()})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"


def test_rejects_oversized_content_length(client: TestClient) -> None:
    api.settings.max_request_bytes = 100
    response = client.post(
        "/",
        json={"image": TINY_PNG},
        headers={"Content-Length": "99999"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_rejects_oversized_base64_string(client: TestClient) -> None:
    api.settings.max_base64_chars = 8
    response = client.post("/", json={"image": TINY_PNG})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_rejects_oversized_decoded_image() -> None:
    with pytest.raises(PayloadTooLargeError):
        decode_and_verify_image(TINY_PNG, max_image_bytes=1)


def test_decode_rejects_plain_text() -> None:
    with pytest.raises(InvalidImageError):
        decode_and_verify_image(base64.b64encode(b"hello").decode(), max_image_bytes=1024)


def test_accepts_jpeg(client: TestClient) -> None:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="JPEG")
    payload = base64.b64encode(buffer.getvalue()).decode()
    response = client.post("/", json={"image": payload})
    assert response.status_code == 200
    assert response.json() == {"message": "accepted"}


def test_rejects_decompression_bomb(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 50)
    payload = png_base64(32, 32)
    response = client.post("/", json={"image": payload})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_image"


def test_decode_rejects_decompression_bomb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 50)
    with pytest.raises(InvalidImageError):
        decode_and_verify_image(png_base64(32, 32), max_image_bytes=10_000_000)


def test_rejects_oversized_body_without_content_length() -> None:
    api.settings.max_request_bytes = 10
    body = b'{"image":"%s"}' % TINY_PNG.encode()
    assert len(body) > 10

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    messages: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [
            (b"host", b"test"),
            (b"content-type", b"application/json"),
        ],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }

    asyncio.run(api.app(scope, receive, send))
    start = next(m for m in messages if m["type"] == "http.response.start")
    assert start["status"] == 413


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["pid"], int)
