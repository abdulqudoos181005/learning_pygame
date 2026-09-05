"""
Database and Backend Engine Package for Space Shooters.
Provides SQLite database management, cryptographic authentication, and score/progression repositories.
"""

from db.manager import DatabaseManager
from db.auth_service import AuthService
from db.score_repository import ScoreRepository
from db.progress_repository import ProgressRepository

__all__ = [
    "DatabaseManager",
    "AuthService",
    "ScoreRepository",
    "ProgressRepository",
]
