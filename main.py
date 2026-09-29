"""Punto de entrada compatible con: python -m uvicorn main:app --reload"""

from app.main import app

__all__ = ["app"]
