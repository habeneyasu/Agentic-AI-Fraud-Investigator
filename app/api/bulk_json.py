"""Normalize bulk request bodies: top-level JSON array or ``{key: [...]}``."""

from typing import Any, Dict, List, Union

from fastapi import HTTPException


def bulk_rows(
    body: Union[List[Dict[str, Any]], Dict[str, Any]],
    wrapped_key: str,
    error_detail: str,
) -> List[Dict[str, Any]]:
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        inner = body.get(wrapped_key)
        if isinstance(inner, list):
            return inner
    raise HTTPException(status_code=422, detail=error_detail)
