import os
import sqlite3
from contextlib import contextmanager


class DatabaseManager:
    """
    Core SQLite database management engine for Space Shooters.
    
    Handles database connection lifecycle, WAL mode, foreign key enforcement,
    and automatic schema migration/initialization.
    """

    def __init__(self, db_path: str = None):
        self._mem_anchor = None
        self.is_memory = False

        if db_path is None:
            # Default to data/game_data.db under project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, "game_data.db")
        elif db_path == ":memory:" or db_path.startswith("file:"):
            self.is_memory = True
            self.db_path = f"file:mem_{id(self)}?mode=memory&cache=shared"
            # Keep an anchor connection alive so shared in-memory DB persists
            self._mem_anchor = sqlite3.connect(self.db_path, uri=True)
        else:
            self.db_path = db_path
            parent_dir = os.path.dirname(db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        self._init_schema()

    @contextmanager
    def get_connection(self):
        """
        Yields an active SQLite connection with row factory, foreign keys enabled,
        and transaction management (auto-commits on success, rolls back on error).
        """
        if self.is_memory:
            conn = sqlite3.connect(self.db_path, uri=True)
        else:
            conn = sqlite3.connect(self.db_path)

        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            if not self.is_memory:
                conn.execute("PRAGMA journal_mode = WAL;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """Initializes database tables and performance indices if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
            """)

            # 2. Arcade High Scores Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NULLABLE,
                    player_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    hull TEXT DEFAULT 'interceptor',
                    color TEXT DEFAULT 'blue',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );
            """)

            # 3. Campaign Progression Table (User-scoped level progress, stars, scores)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaign_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NULLABLE,
                    level INTEGER NOT NULL,
                    stars INTEGER DEFAULT 0,
                    high_score INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    unlocked INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, level)
                );
            """)

            # Indices for fast queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_user ON scores(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_progress_user_lvl ON campaign_progress(user_id, level);")
