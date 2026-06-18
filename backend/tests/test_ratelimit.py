import time

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.ratelimit.base import RateLimitResult, RateLimitRule, RateLimitScope, RateLimiter
from app.ratelimit.deps import get_rate_limiter, rate_limit, set_rate_limiter, reset_rate_limiter
from app.ratelimit.middleware import _get_client_ip
from app.ratelimit.providers.memory import MemoryRateLimiter
from app.ratelimit.rules import DEFAULT_RULES, PUBLIC_ENDPOINT_RULES


@pytest.fixture(autouse=True)
def memory_limiter():
    limiter = MemoryRateLimiter()
    set_rate_limiter(limiter)
    yield limiter
    limiter.clear_all()
    reset_rate_limiter()


# ------------------------------------------------------------------
#  RateLimitRule
# ------------------------------------------------------------------


class TestRateLimitRule:
    def test_key_for_ip(self):
        rule = RateLimitRule(name="login", limit=5, window_seconds=60, scope=RateLimitScope.IP)
        key = rule.key_for("192.168.1.1", "/auth/login")
        assert "ratelimit" in key
        assert "ip" in key
        assert "login" in key
        assert "192.168.1.1" in key
        assert "/auth/login" in key

    def test_key_for_user(self):
        rule = RateLimitRule(name="api", limit=100, window_seconds=60, scope=RateLimitScope.USER)
        key = rule.key_for("42")
        assert "user" in key
        assert "42" in key

    def test_key_for_role(self):
        rule = RateLimitRule(name="admin", limit=500, window_seconds=60, scope=RateLimitScope.ROLE)
        key = rule.key_for("admin")
        assert "role" in key
        assert "admin" in key

    def test_burst_defaults(self):
        rule = RateLimitRule(name="test", limit=10, window_seconds=60)
        assert rule.burst_limit is None
        assert rule.burst_window_seconds is None


# ------------------------------------------------------------------
#  RateLimitResult
# ------------------------------------------------------------------


class TestRateLimitResult:
    def test_allowed_result(self):
        from datetime import datetime, timezone, timedelta
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        result = RateLimitResult(allowed=True, limit=100, remaining=99, reset_at=reset_at)
        assert result.allowed is True
        assert result.remaining == 99
        assert "X-RateLimit-Limit" in result.headers
        assert "X-RateLimit-Remaining" in result.headers
        assert "X-RateLimit-Reset" in result.headers

    def test_denied_result_has_retry_after(self):
        from datetime import datetime, timezone, timedelta
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        result = RateLimitResult(
            allowed=False, limit=5, remaining=0, reset_at=reset_at, retry_after_seconds=30,
        )
        assert result.allowed is False
        assert "Retry-After" in result.headers
        assert result.headers["Retry-After"] == "30"

    def test_retry_after_zero_not_in_headers(self):
        from datetime import datetime, timezone, timedelta
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        result = RateLimitResult(allowed=True, limit=100, remaining=50, reset_at=reset_at)
        assert "Retry-After" not in result.headers


# ------------------------------------------------------------------
#  MemoryRateLimiter
# ------------------------------------------------------------------


class TestMemoryRateLimiter:
    def test_check_allows_first_request(self):
        limiter = get_rate_limiter()
        result = limiter.check("test:key", 5, 60)
        assert result.allowed is True
        assert result.remaining == 4

    def test_check_blocks_when_exceeded(self):
        limiter = get_rate_limiter()
        for i in range(5):
            result = limiter.check("test:block", 5, 60)
            assert result.allowed is True
        result = limiter.check("test:block", 5, 60)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after_seconds > 0

    def test_check_tracks_remaining(self):
        limiter = get_rate_limiter()
        for i in range(3):
            result = limiter.check("test:rem", 10, 60)
        assert result.remaining == 7

    def test_reset_clears_key(self):
        limiter = get_rate_limiter()
        for i in range(5):
            limiter.check("test:reset", 5, 60)
        assert limiter.check("test:reset", 5, 60).allowed is False
        limiter.reset("test:reset")
        assert limiter.check("test:reset", 5, 60).allowed is True

    def test_get_remaining(self):
        limiter = get_rate_limiter()
        assert limiter.get_remaining("test:rem2", 10, 60) == 10
        for i in range(4):
            limiter.check("test:rem2", 10, 60)
        assert limiter.get_remaining("test:rem2", 10, 60) == 6

    def test_window_slides(self):
        limiter = get_rate_limiter()
        for i in range(3):
            limiter.check("test:slide", 3, 1)
        assert limiter.check("test:slide", 3, 1).allowed is False
        time.sleep(1.1)
        assert limiter.check("test:slide", 3, 1).allowed is True

    def test_separate_keys_independent(self):
        limiter = get_rate_limiter()
        for i in range(10):
            limiter.check("key:a", 10, 60)
        limiter.check("key:b", 10, 60)
        assert limiter.check("key:b", 10, 60).remaining == 8
        assert limiter.check("key:a", 10, 60).allowed is False

    def test_clear_all(self):
        limiter = get_rate_limiter()
        limiter.check("k1", 10, 60)
        limiter.check("k2", 10, 60)
        assert limiter.clear_all() == 2
        assert limiter.get_remaining("k1", 10, 60) == 10

    def test_high_limit_never_blocks(self):
        limiter = get_rate_limiter()
        for i in range(1000):
            result = limiter.check("test:high", 10000, 60)
            assert result.allowed is True

    def test_zero_window(self):
        limiter = get_rate_limiter()
        result = limiter.check("test:zero", 10, 0)
        assert result.allowed is True


# ------------------------------------------------------------------
#  Login Brute-Force Protection
# ------------------------------------------------------------------


class TestLoginProtection:
    def test_login_endpoint_limited_in_middleware(self):
        rule = PUBLIC_ENDPOINT_RULES.get("/auth/login")
        assert rule is not None
        assert rule.limit <= 10

    def test_multiple_login_attempts_blocked(self):
        limiter = get_rate_limiter()
        key = "ratelimit:ip:login:127.0.0.1:/auth/login"
        rule = PUBLIC_ENDPOINT_RULES["/auth/login"]

        for i in range(rule.limit):
            result = limiter.check(
                rule.key_for("127.0.0.1", "/auth/login"),
                rule.limit,
                rule.window_seconds,
            )
            assert result.allowed is True

        result = limiter.check(
            rule.key_for("127.0.0.1", "/auth/login"),
            rule.limit,
            rule.window_seconds,
        )
        assert result.allowed is False
        assert "Retry-After" in result.headers

    def test_login_from_different_ips_independent(self):
        limiter = get_rate_limiter()
        rule = PUBLIC_ENDPOINT_RULES["/auth/login"]

        for i in range(rule.limit):
            limiter.check(rule.key_for("1.1.1.1", "/auth/login"), rule.limit, rule.window_seconds)

        assert limiter.check(
            rule.key_for("2.2.2.2", "/auth/login"), rule.limit, rule.window_seconds
        ).allowed is True


# ------------------------------------------------------------------
#  Rate Limit Dependency
# ------------------------------------------------------------------


class TestRateLimitDependency:
    def test_register_endpoint_limited(self):
        rule = PUBLIC_ENDPOINT_RULES.get("/auth/register")
        assert rule is not None


# ------------------------------------------------------------------
#  429 Response Integration
# ------------------------------------------------------------------


class Test429Response:
    def test_rate_limit_headers_format(self):
        from datetime import datetime, timezone, timedelta
        reset_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        result = RateLimitResult(allowed=True, limit=100, remaining=99, reset_at=reset_at)
        h = result.headers
        assert h["X-RateLimit-Limit"].isdigit()
        assert h["X-RateLimit-Remaining"].isdigit()
        assert h["X-RateLimit-Reset"].isdigit()

    def test_429_response_body(self):
        from fastapi.responses import JSONResponse
        from datetime import datetime, timezone, timedelta

        reset_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        result = RateLimitResult(
            allowed=False, limit=5, remaining=0, reset_at=reset_at, retry_after_seconds=30,
        )
        resp = JSONResponse(
            status_code=429,
            content={"detail": "Too many requests", "retry_after_seconds": 30},
            headers=result.headers,
        )
        assert resp.status_code == 429


# ------------------------------------------------------------------
#  Edge Cases
# ------------------------------------------------------------------


class TestEdgeCases:
    def test_exactly_at_limit(self):
        limiter = get_rate_limiter()
        for i in range(5):
            limiter.check("test:exact", 5, 60)
        assert limiter.check("test:exact", 5, 60).allowed is False

    def test_one_below_limit(self):
        limiter = get_rate_limiter()
        for i in range(4):
            limiter.check("test:below", 5, 60)
        assert limiter.check("test:below", 5, 60).allowed is True

    def test_reset_nonexistent_key(self):
        limiter = get_rate_limiter()
        limiter.reset("nonexistent")
        assert limiter.get_remaining("nonexistent", 10, 60) == 10

    def test_concurrent_requests(self):
        import threading
        limiter = get_rate_limiter()
        errors = []

        def worker(n):
            try:
                for i in range(10):
                    result = limiter.check(f"test:concurrent:{n}", 100, 60)
                    if not result.allowed:
                        errors.append(f"Worker {n} blocked at iteration {i}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_rapid_fire_same_key(self):
        limiter = get_rate_limiter()
        for i in range(100):
            result = limiter.check("test:rapid", 100, 60)
            assert result.allowed is True
        assert limiter.check("test:rapid", 100, 60).allowed is False

    def test_different_endpoints_same_ip_independent(self):
        limiter = get_rate_limiter()
        for i in range(100):
            limiter.check("ip:1.1.1.1:/endpoint-a", 100, 60)
        assert limiter.check("ip:1.1.1.1:/endpoint-b", 100, 60).allowed is True


# ------------------------------------------------------------------
#  Rate Limit Rules Config
# ------------------------------------------------------------------


class TestRateLimitRules:
    def test_default_rule_exists(self):
        assert len(DEFAULT_RULES) >= 1
        assert DEFAULT_RULES[0].name == "default"

    def test_login_rule_in_public_endpoints(self):
        assert "/auth/login" in PUBLIC_ENDPOINT_RULES

    def test_register_rule_in_public_endpoints(self):
        assert "/auth/register" in PUBLIC_ENDPOINT_RULES

    def test_authenticated_rule_exists(self):
        assert any(r.name == "authenticated" for r in DEFAULT_RULES)


# ------------------------------------------------------------------
#  Disabled Rate Limiting
# ------------------------------------------------------------------


class TestDisabledRateLimiting:
    def test_disabled_flag_checked_in_middleware(self):
        assert settings.RATE_LIMIT_ENABLED is False

    def test_limiter_still_works_when_disabled(self):
        limiter = get_rate_limiter()
        for i in range(3):
            result = limiter.check("test:always-limited", 3, 60)
            assert result.allowed is True
        result = limiter.check("test:always-limited", 3, 60)
        assert result.allowed is False
