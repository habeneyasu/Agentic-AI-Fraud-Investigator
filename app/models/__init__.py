"""Application models: Pydantic API models live alongside ``db_base.Base`` for SQLAlchemy ORM."""

from app.models.db_base import Base

# Register ORM table classes on ``Base.metadata`` for ``create_all`` / migrations.
from app.models import orm_tables as _orm_tables  # noqa: F401

__all__ = ["Base"]
