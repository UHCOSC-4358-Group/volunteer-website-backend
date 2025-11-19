from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from typing import Any, Dict, Optional, Callable, Awaitable
import uuid
from datetime import datetime
import logging


class BaseAPIError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.message = message  # Client-safe message
        self.detail = detail  # Internal detail (not sent to client)
        self.error_code = error_code
        self.metadata = metadata or {}
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class ClientError(BaseAPIError):
    pass


class ServerError(BaseAPIError):
    pass


class ValidationError(ClientError):
    def __init__(self, message: str, fields: Optional[Dict] = None):
        super().__init__(
            status_code=422,
            message=message,
            error_code="VALIDATION_ERROR",
            metadata={"fields": fields} if fields else {},
        )


class AuthenticationError(ClientError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(status_code=401, message=message, error_code="AUTH_ERROR")


class AuthorizationError(ClientError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(status_code=403, message=message, error_code="FORBIDDEN")


class NotFoundError(ClientError):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=404,
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            metadata={"resource": resource, "id": str(identifier)},
        )


class ConflictError(ClientError):
    def __init__(self, message: str):
        super().__init__(status_code=409, message=message, error_code="CONFLICT")


class DatabaseOperationError(ServerError):
    def __init__(self, operation: str, detail: str):
        super().__init__(
            status_code=500,
            message="Database operation failed",
            detail=f"Operation '{operation}' failed: {detail}",
            error_code="DB_ERROR",
            metadata={"operation": operation},
        )


class ExternalServiceError(ServerError):
    def __init__(self, service: str, detail: str):
        super().__init__(
            status_code=503,
            message="External service unavailable",
            detail=f"Service '{service}' error: {detail}",
            error_code="SERVICE_ERROR",
            metadata={"service": service},
        )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            response: Response = await call_next(request)
            return response
        except BaseAPIError as api_error:
            # Log based on error type
            logger = logging.getLogger(__name__)

            if isinstance(api_error, ServerError):
                logger.error(
                    f"Server Error [{api_error.error_id}]: {api_error.detail or api_error.message}",
                    extra={
                        "error_id": api_error.error_id,
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": api_error.status_code,
                        "metadata": api_error.metadata,
                    },
                )
            elif isinstance(api_error, ClientError):
                logger.warning(
                    f"Client Error [{api_error.error_id}]: {api_error.message}",
                    extra={
                        "error_id": api_error.error_id,
                        "path": request.url.path,
                        "status_code": api_error.status_code,
                    },
                )

            return JSONResponse(
                status_code=api_error.status_code,
                content={
                    "error": {
                        "id": api_error.error_id,
                        "code": api_error.error_code,
                        "message": api_error.message,
                        "timestamp": api_error.timestamp.isoformat(),
                        "path": request.url.path,
                    }
                },
            )
        except Exception as ex:
            # Log unexpected errors with full traceback
            error_id = str(uuid.uuid4())
            logger = logging.getLogger(__name__)
            logger.exception(
                f"Unhandled Exception [{error_id}]",
                extra={
                    "error_id": error_id,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "id": error_id,
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "timestamp": datetime.utcnow().isoformat(),
                        "path": request.url.path,
                    }
                },
            )


# Exception class for database files
# Provides hints for HTTPException class
class DatabaseError(Exception):
    """
    Custom class for database exceptions for HTTP Exception
    """

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)


# Error handlers for FastAPI
# Will handle HTTP Exceptions and validation exceptions
# If other exception occurs, it logs it and returns a 500 error


async def http_exception_handler(request: Request, exception: HTTPException):
    return JSONResponse(
        status_code=exception.status_code,
        content={"status_code": exception.status_code, "message": exception.detail},
    )


async def validation_exception_error(
    request: Request, exception: RequestValidationError
):

    exception_object = exception.errors()

    exception_strings: list[str] = []

    for string in exception_object:
        result = f"Validation Error in location '{string['loc']}'. {string['msg']}"
        exception_strings.append(result)

    return JSONResponse(
        status_code=422, content={"status_code": 422, "message": exception_strings}
    )


async def catch_all_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logging.basicConfig(filename="errors.log", level=logging.INFO)
        logging.info(f"Error happened! {e}")
        print(e)
        return JSONResponse(
            status_code=500, content={"message": "Internal server error."}
        )
