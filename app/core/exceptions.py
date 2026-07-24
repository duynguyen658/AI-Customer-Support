from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from structlog.stdlib import BoundLogger


class AppException(Exception):
    """Base application exception with a client-safe error code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class TicketNotFoundError(AppException):
    def __init__(self, ticket_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TICKET_NOT_FOUND",
            message=f"Ticket '{ticket_id}' was not found.",
        )


class InfrastructureError(AppException):
    def __init__(
        self,
        message: str = "A required infrastructure dependency is unavailable.",
        code: str = "INFRASTRUCTURE_ERROR",
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
    ) -> None:
        super().__init__(status_code=status_code, code=code, message=message)


def add_exception_handlers(app: FastAPI, logger: BoundLogger) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        logger.warning(
            "application_error",
            path=request.url.path,
            code=exc.code,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "unexpected_application_error",
            path=request.url.path,
            error_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected application error occurred.",
                }
            },
        )

