"""Domain-level errors and their mapping to clean JSON API responses.

Every error the client sees has the shape:

    {"error": {"code": "SOME_CODE", "message": "human readable message"}}

Internal details (stack traces, file paths, DB errors) are logged server-side
and never leaked to the client.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

logger = logging.getLogger("docchat")


class DocChatError(Exception):
    """Base class for all expected, user-facing application errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(DocChatError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class ValidationFailedError(DocChatError):
    code = "VALIDATION_FAILED"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class FileTooLargeError(DocChatError):
    code = "FILE_TOO_LARGE"
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


class InvalidFileTypeError(DocChatError):
    code = "INVALID_FILE_TYPE"
    status_code = status.HTTP_400_BAD_REQUEST


class CorruptedFileError(DocChatError):
    code = "CORRUPTED_FILE"
    status_code = status.HTTP_400_BAD_REQUEST


class DocumentNotReadyError(DocChatError):
    code = "DOCUMENT_NOT_READY"
    status_code = status.HTTP_409_CONFLICT


class DatabaseUnavailableError(DocChatError):
    code = "DATABASE_UNAVAILABLE"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class VectorSearchError(DocChatError):
    code = "VECTOR_SEARCH_FAILED"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class LLMUnavailableError(DocChatError):
    code = "LLM_UNAVAILABLE"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class LLMTimeoutError(DocChatError):
    code = "LLM_TIMEOUT"
    status_code = status.HTTP_504_GATEWAY_TIMEOUT


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocChatError)
    async def handle_docchat_error(request: Request, exc: DocChatError) -> JSONResponse:
        logger.warning("handled_error code=%s path=%s message=%s", exc.code, request.url.path, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(PyMongoError)
    async def handle_mongo_error(request: Request, exc: PyMongoError) -> JSONResponse:
        # Covers MongoDB being unreachable/down for any operation that isn't
        # already wrapped in a DocChatError (e.g. a transient Atlas outage
        # after a successful startup connection) — never leaks driver
        # internals (host, credentials-bearing URIs) to the client.
        logger.error("mongodb_error path=%s error=%s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "The database is currently unavailable. Please try again shortly.",
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error path=%s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again.",
                }
            },
        )
