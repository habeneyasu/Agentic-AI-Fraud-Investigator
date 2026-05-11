"""Shared FastAPI dependencies (API key and role checks)."""

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(x_api_key: str | None = Security(api_key_header)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def require_analyst_role(
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> None:
    if x_user_role != "Analyst":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden — Analyst role required",
        )


def require_analyst_or_auditor_role(
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> None:
    if x_user_role not in ("Analyst", "Auditor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden — Analyst or Auditor role required",
        )


# Shorthand for routers that only need API key auth
RequireApiKey = Depends(require_api_key)
RequireAnalyst = Depends(require_analyst_role)
RequireAnalystOrAuditor = Depends(require_analyst_or_auditor_role)
