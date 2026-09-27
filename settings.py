import os


def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


class Settings:
    """Runtime limits. Tests may mutate attributes; call reload() to re-read env."""

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.max_image_bytes = _int_env("MAX_IMAGE_BYTES", 8 * 1024 * 1024)
        extra = 4096
        self.max_base64_chars = _int_env(
            "MAX_BASE64_CHARS",
            (self.max_image_bytes * 4 // 3) + extra,
        )
        self.max_request_bytes = _int_env(
            "MAX_REQUEST_BYTES",
            self.max_base64_chars + extra,
        )


settings = Settings()
