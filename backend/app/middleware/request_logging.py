import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability import request_id_ctx_var, user_id_ctx_var
from app.services.metrics import record_request_metric

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request_id_token = request_id_ctx_var.set(request_id)
        user_id_token = user_id_ctx_var.set(None)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            route_path = getattr(request.scope.get("route"), "path", None)
            record_request_metric(
                method=request.method,
                route_path=route_path,
                fallback_path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            logger.info(
                "request_complete",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            route_path = getattr(request.scope.get("route"), "path", None)
            record_request_metric(
                method=request.method,
                route_path=route_path,
                fallback_path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
            logger.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            raise
        finally:
            user_id_ctx_var.reset(user_id_token)
            request_id_ctx_var.reset(request_id_token)
