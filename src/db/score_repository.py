from db.manager import DatabaseManager


class ScoreRepository:
    """
    Arcade high scores database repository for Space Shooters.
    
    Provides persistent score tracking, global leaderboards, user-specific
    score filtering, and ship loadout metadata recording.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def record_score(
        self,
        name: str,
        score: int,
        hull: str = "interceptor",
        color: str = "blue",
        user_id: int = None,
    ) -> int:
        """
        Records an arcade run score along with ship loadout attributes.
        Returns the created record ID.
        """
        clean_name = str(name).strip().upper()[:20] or "UNKNOWN"
        clean_hull = str(hull).lower() if str(hull).lower() in ("interceptor", "cruiser", "vanguard") else "interceptor"
        clean_color = str(color).lower() if str(color).lower() in ("blue", "green", "orange", "red") else "blue"
        clean_score = max(0, int(score))

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scores (user_id, player_name, score, hull, color)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user_id, clean_name, clean_score, clean_hull, clean_color),
            )
            return cursor.lastrowid

    def get_top_scores(self, limit: int = 10) -> list[dict]:
        """
        Retrieves global top scores sorted in descending order.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.user_id, s.player_name, s.score, s.hull, s.color, s.created_at, u.username
                FROM scores s
                LEFT JOIN users u ON s.user_id = u.id
                ORDER BY s.score DESC, s.created_at ASC
                LIMIT ?;
                """,
                (max(1, int(limit)),),
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "name": row["player_name"],
                    "score": row["score"],
                    "hull": row["hull"],
                    "color": row["color"],
                    "created_at": row["created_at"],
                    "username": row["username"],
                }
                for row in rows
            ]

    def get_user_top_scores(self, user_id: int, limit: int = 10) -> list[dict]:
        """
        Retrieves the top scores achieved by a specific registered pilot.
        """
        if not user_id:
            return []

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.user_id, s.player_name, s.score, s.hull, s.color, s.created_at, u.username
                FROM scores s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.user_id = ?
                ORDER BY s.score DESC, s.created_at ASC
                LIMIT ?;
                """,
                (user_id, max(1, int(limit))),
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "name": row["player_name"],
                    "score": row["score"],
                    "hull": row["hull"],
                    "color": row["color"],
                    "created_at": row["created_at"],
                    "username": row["username"],
                }
                for row in rows
            ]

    def get_user_best_score(self, user_id: int) -> dict or None:
        """Returns the single highest score record for a user, or None if no scores exist."""
        scores = self.get_user_top_scores(user_id, limit=1)
        return scores[0] if scores else None

    def clear_scores(self, user_id: int = None):
        """Clears score records (for a user, or all if user_id is None)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute("DELETE FROM scores WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("DELETE FROM scores")
