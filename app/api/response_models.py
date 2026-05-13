"""Shared FastAPI response models for CRUD-style data routes."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DataStatusResponse(BaseModel):
    success: bool
    count: int
    message: str
    data: Optional[List[Dict[str, Any]]] = None
