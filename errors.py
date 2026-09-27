class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class InvalidImageError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=400, code="invalid_image", message=message)


class PayloadTooLargeError(AppError):
    def __init__(self, message: str = "Request payload exceeds size limit") -> None:
        super().__init__(status_code=413, code="payload_too_large", message=message)
