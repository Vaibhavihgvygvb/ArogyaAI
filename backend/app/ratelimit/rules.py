from app.core.config import settings
from app.ratelimit.base import RateLimitRule, RateLimitScope

DEFAULT_RULES: list[RateLimitRule] = [
    RateLimitRule(
        name="default",
        limit=settings.RATE_LIMIT_DEFAULT,
        window_seconds=settings.RATE_LIMIT_DEFAULT_WINDOW,
        scope=RateLimitScope.GLOBAL,
        burst_limit=settings.RATE_LIMIT_DEFAULT * settings.RATE_LIMIT_BURST_MULTIPLIER,
        burst_window_seconds=settings.RATE_LIMIT_DEFAULT_WINDOW,
    ),
    RateLimitRule(
        name="authenticated",
        limit=settings.RATE_LIMIT_AUTHENTICATED,
        window_seconds=settings.RATE_LIMIT_AUTHENTICATED_WINDOW,
        scope=RateLimitScope.USER,
        burst_limit=settings.RATE_LIMIT_AUTHENTICATED * settings.RATE_LIMIT_BURST_MULTIPLIER,
        burst_window_seconds=settings.RATE_LIMIT_AUTHENTICATED_WINDOW,
    ),
    RateLimitRule(
        name="login",
        limit=settings.RATE_LIMIT_LOGIN_MAX,
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW,
        scope=RateLimitScope.IP,
    ),
    RateLimitRule(
        name="register",
        limit=settings.RATE_LIMIT_REGISTER_MAX,
        window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW,
        scope=RateLimitScope.IP,
    ),
]

PUBLIC_ENDPOINT_RULES: dict[str, RateLimitRule] = {
    "/auth/login": DEFAULT_RULES[2],
    "/auth/register": DEFAULT_RULES[3],
}

AUTHENTICATED_ENDPOINT_RULES: dict[str, RateLimitRule] = {}
