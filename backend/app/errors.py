import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("aegis")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code in {401, 403, 429}:
            from app.security_log import security_event

            peer = request.client.host if request.client else None
            security_event(
                "http_denied",
                ip_address=peer,
                outcome=exc.code,
                status=exc.status_code,
                path=str(request.url.path),
            )
        body: dict = {"error": {"code": exc.code, "message": exc.message}}
        if exc.details:
            body["error"]["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = [str(part) for part in error.get("loc", []) if part != "body"]
            details.append(
                {
                    "field": ".".join(location) if location else "request",
                    "message": error.get("msg", "Invalid value."),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Check the submitted fields.",
                    "details": details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "The request could not be completed."}},
        )
