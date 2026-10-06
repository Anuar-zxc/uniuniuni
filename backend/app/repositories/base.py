"""Small data-access helpers. Ownership checks live here so routes cannot forget them."""

from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base

M = TypeVar("M", bound=Base)


def get_owned(db: Session, model: type[M], obj_id: int, user_id: int) -> M:
    obj = db.get(model, obj_id)
    if obj is None or getattr(obj, "user_id", None) != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj


def get_or_404(db: Session, model: type[M], obj_id: int) -> M:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj


def list_owned(db: Session, model: type[M], user_id: int, limit: int = 100) -> list[M]:
    return list(db.scalars(select(model).where(model.user_id == user_id).order_by(model.id.desc()).limit(limit)).all())
