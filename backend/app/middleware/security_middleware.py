from collections import defaultdict, deque
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.database import SessionLocal
from app.models import RequestLog, SecurityEvent


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_history = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        ip_address = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")

        now = datetime.utcnow()

        # Ignore browser docs/static noise for rate limit.
        rate_limit_exempt_paths = {
            "/docs",
            "/openapi.json",
            "/favicon.ico",
        }

        is_exempt = path in rate_limit_exempt_paths

        if not is_exempt:
            key = f"{ip_address}:{path}"
            history = self.request_history[key]

            # Keep only requests from the last 60 seconds.
            while history and history[0] < now - timedelta(seconds=60):
                history.popleft()

            history.append(now)

            # Simple local rate limit.
            if len(history) > 80:
                self._log_security_event(
                    ip_address=ip_address,
                    event_type="security.rate_limit_exceeded",
                    severity="warning",
                    method=method,
                    path=path,
                    user_agent=user_agent,
                    details=f"Too many requests to {path}: {len(history)} in 60 seconds",
                )

                self._log_request(
                    ip_address=ip_address,
                    method=method,
                    path=path,
                    status_code=429,
                    user_agent=user_agent,
                )

                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                )

        # Suspicious user-agent detection.
        if not user_agent or user_agent.strip() == "":
            self._log_security_event(
                ip_address=ip_address,
                event_type="security.missing_user_agent",
                severity="low",
                method=method,
                path=path,
                user_agent=user_agent,
                details="Request had missing or empty user-agent",
            )

        suspicious_user_agents = ["curl", "python-requests", "bot", "scraper"]

        if any(token in user_agent.lower() for token in suspicious_user_agents):
            self._log_security_event(
                ip_address=ip_address,
                event_type="security.suspicious_user_agent",
                severity="low",
                method=method,
                path=path,
                user_agent=user_agent,
                details=f"Suspicious user-agent detected: {user_agent}",
            )

        response = await call_next(request)

        self._log_request(
            ip_address=ip_address,
            method=method,
            path=path,
            status_code=response.status_code,
            user_agent=user_agent,
        )

        if response.status_code in [401, 403, 404]:
            self._log_security_event(
                ip_address=ip_address,
                event_type=f"security.http_{response.status_code}",
                severity="medium",
                method=method,
                path=path,
                user_agent=user_agent,
                details=f"Request returned status {response.status_code}",
            )

        return response

    def _log_request(
        self,
        ip_address: str,
        method: str,
        path: str,
        status_code: int,
        user_agent: str,
    ) -> None:
        db = SessionLocal()
        try:
            log = RequestLog(
                ip_address=ip_address,
                method=method,
                path=path,
                status_code=status_code,
                user_agent=user_agent,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()

    def _log_security_event(
        self,
        ip_address: str,
        event_type: str,
        severity: str,
        method: str,
        path: str,
        user_agent: str,
        details: str,
    ) -> None:
        db = SessionLocal()
        try:
            event = SecurityEvent(
                ip_address=ip_address,
                event_type=event_type,
                severity=severity,
                method=method,
                path=path,
                user_agent=user_agent,
                details=details,
            )
            db.add(event)
            db.commit()
        finally:
            db.close()