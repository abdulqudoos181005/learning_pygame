from db.manager import DatabaseManager


class ProgressRepository:
    """
    Campaign progression repository for Space Shooters.
    
    Handles user-scoped level unlocks, 3-star mission ratings, and
    per-level high scores stored in the database.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_progress(self, user_id: int = None) -> dict:
        """
        Retrieves user-scoped campaign progress.
        Returns a dictionary compatible with the game's level system:
        {
            "highest_unlocked": int,
            "completed_levels": list[int],
            "level_stars": dict[str, int],
            "level_scores": dict[str, int]
        }
        """
        # Default baseline progression
        default_result = {
            "highest_unlocked": 1,
            "completed_levels": [],
            "level_stars": {},
            "level_scores": {},
        }

        if user_id is None:
            return default_result

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT level, stars, high_score, completed, unlocked
                FROM campaign_progress
                WHERE user_id = ?
                ORDER BY level ASC;
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

            if not rows:
                # Initialize level 1 as unlocked for this user
                cursor.execute(
                    """
                    INSERT INTO campaign_progress (user_id, level, stars, high_score, completed, unlocked)
                    VALUES (?, 1, 0, 0, 0, 1)
                    ON CONFLICT(user_id, level) DO NOTHING;
                    """,
                    (user_id,),
                )
                return default_result

            completed_levels = []
            level_stars = {}
            level_scores = {}
            highest_unlocked = 1

            for row in rows:
                lvl = row["level"]
                lvl_key = str(lvl)

                if row["unlocked"]:
                    highest_unlocked = max(highest_unlocked, lvl)

                if row["completed"]:
                    completed_levels.append(lvl)
                    highest_unlocked = max(highest_unlocked, min(lvl + 1, 10))

                if row["stars"] > 0:
                    level_stars[lvl_key] = row["stars"]

                if row["high_score"] > 0:
                    level_scores[lvl_key] = row["high_score"]

            highest_unlocked = max(1, min(highest_unlocked, 10))

            return {
                "highest_unlocked": highest_unlocked,
                "completed_levels": sorted(list(set(completed_levels))),
                "level_stars": level_stars,
                "level_scores": level_scores,
            }

    def save_level_progress(
        self,
        user_id: int,
        level: int,
        stars: int = 0,
        score: int = 0,
        completed: bool = True,
    ) -> bool:
        """
        Updates level completion, star ratings, and score for a user.
        Unlocks the next level upon completion.
        """
        if not user_id:
            return False

        lvl = max(1, min(int(level), 10))
        input_stars = max(0, min(int(stars), 3))
        input_score = max(0, int(score))
        is_completed = 1 if completed else 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Check existing progress for this level
            cursor.execute(
                "SELECT stars, high_score, completed FROM campaign_progress WHERE user_id = ? AND level = ?",
                (user_id, lvl),
            )
            existing = cursor.fetchone()

            if existing:
                best_stars = max(existing["stars"], input_stars)
                best_score = max(existing["high_score"], input_score)
                comp_flag = 1 if (existing["completed"] or is_completed) else 0

                cursor.execute(
                    """
                    UPDATE campaign_progress
                    SET stars = ?, high_score = ?, completed = ?, unlocked = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND level = ?;
                    """,
                    (best_stars, best_score, comp_flag, user_id, lvl),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO campaign_progress (user_id, level, stars, high_score, completed, unlocked)
                    VALUES (?, ?, ?, ?, ?, 1);
                    """,
                    (user_id, lvl, input_stars, input_score, is_completed),
                )

            # If completed, automatically unlock next level if <= 10
            if is_completed and lvl < 10:
                next_lvl = lvl + 1
                cursor.execute(
                    """
                    INSERT INTO campaign_progress (user_id, level, stars, high_score, completed, unlocked)
                    VALUES (?, ?, 0, 0, 0, 1)
                    ON CONFLICT(user_id, level) DO UPDATE SET unlocked = 1;
                    """,
                    (user_id, next_lvl),
                )

            return True

    def reset_progress(self, user_id: int) -> bool:
        """Resets user campaign progress back to Level 1."""
        if not user_id:
            return False

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM campaign_progress WHERE user_id = ?", (user_id,))
            cursor.execute(
                """
                INSERT INTO campaign_progress (user_id, level, stars, high_score, completed, unlocked)
                VALUES (?, 1, 0, 0, 0, 1);
                """,
                (user_id,),
            )
            return True
