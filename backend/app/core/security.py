import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Require X-API-Key only when an API key has been configured."""
    if not settings.api_key:
        return
    supplied = x_api_key.encode("utf-8") if x_api_key is not None else b""
    expected = settings.api_key.encode("utf-8")
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
