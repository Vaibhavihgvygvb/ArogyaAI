from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.ratelimit.deps import get_rate_limiter
from app.ratelimit.rules import DEFAULT_RULES, PUBLIC_ENDPOINT_RULES


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    client_host = request.client.host if request.client else "127.0.0.1"
    return client_host


def _apply_ip_rule(limiter, rule, client_ip: str, endpoint: str):
    key = rule.key_for(client_ip, endpoint)
    return limiter.check(key, rule.limit, rule.window_seconds)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        limiter = get_rate_limiter()
        client_ip = _get_client_ip(request)

        if path in PUBLIC_ENDPOINT_RULES:
            rule = PUBLIC_ENDPOINT_RULES[path]
            result = _apply_ip_rule(limiter, rule, client_ip, path)
            if not result.allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many requests",
                        "retry_after_seconds": result.retry_after_seconds,
                    },
                    headers=result.headers,
                )
            response = await call_next(request)
            for h, v in result.headers.items():
                response.headers[h] = v
            return response

        rule = DEFAULT_RULES[0]
        result = _apply_ip_rule(limiter, rule, client_ip, path)
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after_seconds": result.retry_after_seconds,
                },
                headers=result.headers,
            )
        response = await call_next(request)
        for h, v in result.headers.items():
            response.headers[h] = v
        return response
