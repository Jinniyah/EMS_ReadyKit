"""
core/limiter.py
Rate limiter singleton for EMS ReadyKit.

Defined here (not in main.py) to avoid a circular import:
  main.py imports routers → checks.py needs the limiter →
  if limiter lived in main.py that would be a circular dependency.

In the test environment (APP_ENV=test or TESTING=true), the limiter is
configured with a very high limit so it never fires during the test suite.
This is correct behaviour — rate limiting is an infrastructure concern;
its presence is tested by the decorator existing, not by exhausting the
counter in unit tests.

Usage in route handlers:
    from ems_readykit.core.limiter import limiter

    @router.post("/daily")
    @limiter.limit("30/minute")
    async def create_daily_check(request: Request, ...):
        ...

Usage in main.py (wiring the limiter into the app):
    from ems_readykit.core.limiter import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Rate limits (production):
    Global default : 200 requests / minute per IP
    POST /checks/daily : 30 requests / minute per IP (per-route override)
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Disable rate limiting in test environments so the suite does not exhaust
# the counter. TESTING=true is set by conftest.py; APP_ENV=test is an
# alternative. Any other value uses production limits.
_is_testing = (
    os.environ.get("TESTING", "").lower() == "true"
    or os.environ.get("APP_ENV", "").lower() == "test"
)

_default_limits = ["99999/minute"] if _is_testing else ["200/minute"]

# Per-route limit for POST /checks/daily.
# Uses a very high value in test environments so the suite never exhausts it.
# Import this constant in checks.py instead of hard-coding "30/minute" there.
DAILY_CHECK_RATE_LIMIT = "99999/minute" if _is_testing else "30/minute"

limiter = Limiter(key_func=get_remote_address, default_limits=_default_limits)
