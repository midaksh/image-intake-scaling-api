from __future__ import annotations

import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from errors import AppError, PayloadTooLargeError
from image import decode_and_verify_image
from logging_config import configure_logging
from settings import settings

configure_logging()
logger = logging.getLogger("intake")

app = FastAPI(title="Image Intake API")


class ImagePayload(BaseModel):
    image: str = Field(..., min_length=1, description="Base64-encoded image")


def error_body(code: str, message: str, details: object | None = None) -> dict[str, object]:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        exc.message,
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method,
            "status": exc.status_code,
            "error_code": exc.code,
            "pid": os.getpid(),
        },
    )
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info(
        "Request validation failed",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method,
            "status": 422,
            "error_code": "validation_error",
            "pid": os.getpid(),
        },
    )
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", "Request body is invalid", details=exc.errors()),
    )


def too_large_response(request: Request) -> JSONResponse:
    response = JSONResponse(
        status_code=413,
        content=error_body("payload_too_large", "Request payload exceeds size limit"),
    )
    response.headers["X-Request-ID"] = request.state.request_id
    logger.warning(
        "Request payload exceeds size limit",
        extra={
            "request_id": request.state.request_id,
            "path": request.url.path,
            "method": request.method,
            "status": 413,
            "error_code": "payload_too_large",
            "pid": os.getpid(),
        },
    )
    return response


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            size = int(content_length)
        except ValueError:
            size = -1
        if size > settings.max_request_bytes:
            return too_large_response(request)

    body = await request.body()
    if len(body) > settings.max_request_bytes:
        return too_large_response(request)

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled error",
            extra={
                "request_id": request.state.request_id,
                "path": request.url.path,
                "method": request.method,
                "status": 500,
                "error_code": "internal_error",
                "pid": os.getpid(),
            },
        )
        response = JSONResponse(
            status_code=500,
            content=error_body("internal_error", "Internal server error"),
        )

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        "request",
        extra={
            "request_id": request.state.request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "pid": os.getpid(),
        },
    )
    return response


@app.post("/")
async def accept_image(payload: ImagePayload) -> dict[str, str]:
    if len(payload.image) > settings.max_base64_chars:
        raise PayloadTooLargeError("Base64 payload exceeds size limit")
    decode_and_verify_image(payload.image, settings.max_image_bytes)
    return {"message": "accepted"}


@app.get("/health")
async def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "pid": os.getpid(),
    }
