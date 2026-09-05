# pyrefly: ignore [missing-import]
import os
import sys
import unittest
import pygame as pg

# Ensure 'src' is in python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from db.manager import DatabaseManager
from db.auth_service import AuthService
from db.score_repository import ScoreRepository
from db.progress_repository import ProgressRepository
from game import Game
from ui.login_state import LoginState


class TestSprint13Backend(unittest.TestCase):
    """
    Automated test suite for Sprint 13 Phase 2 (Database & Backend Engine).
    """

    def setUp(self):
        # Use an isolated in-memory SQLite database for test runs
        self.db = DatabaseManager(":memory:")
        self.auth = AuthService(self.db)
        self.score_repo = ScoreRepository(self.db)
        self.progress_repo = ProgressRepository(self.db)

    def test_database_schema_initialization(self):
        """Verifies that all required tables and indices are created."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row["name"] for row in cursor.fetchall()]

            self.assertIn("users", tables)
            self.assertIn("scores", tables)
            self.assertIn("campaign_progress", tables)

            # Check users columns
            cursor.execute("PRAGMA table_info(users);")
            u_cols = [row["name"] for row in cursor.fetchall()]
            for expected in ("id", "username", "password_hash", "salt", "created_at", "last_login"):
                self.assertIn(expected, u_cols)

            # Check scores columns
            cursor.execute("PRAGMA table_info(scores);")
            s_cols = [row["name"] for row in cursor.fetchall()]
            for expected in ("id", "user_id", "player_name", "score", "hull", "color", "created_at"):
                self.assertIn(expected, s_cols)

            # Check campaign_progress columns
            cursor.execute("PRAGMA table_info(campaign_progress);")
            p_cols = [row["name"] for row in cursor.fetchall()]
            for expected in ("id", "user_id", "level", "stars", "high_score", "completed", "unlocked"):
                self.assertIn(expected, p_cols)

    def test_auth_service_hashing_and_verification(self):
        """Tests PBKDF2 hashing, unique salts, and constant-time verification."""
        pwd = "HyperDrivePassword!42"
        hash1, salt1 = AuthService.hash_password(pwd)
        hash2, salt2 = AuthService.hash_password(pwd)

        # Hashes with different random salts must differ
        self.assertNotEqual(salt1, salt2)
        self.assertNotEqual(hash1, hash2)

        # Verification must succeed with matching salt
        self.assertTrue(AuthService.verify_password(pwd, salt1, hash1))
        self.assertTrue(AuthService.verify_password(pwd, salt2, hash2))

        # Verification must fail with wrong password
        self.assertFalse(AuthService.verify_password("WrongPassword", salt1, hash1))
        self.assertFalse(AuthService.verify_password("", salt1, hash1))

        # Verification must fail with mismatched salt
        self.assertFalse(AuthService.verify_password(pwd, salt2, hash1))

    def test_auth_service_input_validation(self):
        """Tests validation rules for pilot callsigns and passcodes."""
        # Username validation
        self.assertFalse(AuthService.validate_username("ab")[0])  # too short
        self.assertFalse(AuthService.validate_username("A" * 25)[0])  # too long
        self.assertFalse(AuthService.validate_username("Pilot@#$")[0])  # invalid chars
        self.assertTrue(AuthService.validate_username("Ace_Pilot-99")[0])  # valid

        # Password validation
        self.assertFalse(AuthService.validate_password("123")[0])  # too short
        self.assertFalse(AuthService.validate_password("A" * 70)[0])  # too long
        self.assertTrue(AuthService.validate_password("pass1234")[0])  # valid

    def test_user_registration_and_authentication(self):
        """Tests user creation, duplicate prevention, and authentication workflow."""
        # 1. Register new pilot
        user, err = self.auth.register_user("StarViper", "SectorSevenPass")
        self.assertIsNone(err)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "StarViper")
        self.assertFalse(user["is_guest"])
        user_id = user["id"]

        # 2. Duplicate registration must fail
        dup_user, dup_err = self.auth.register_user("StarViper", "AnotherPass123")
        self.assertIsNone(dup_user)
        self.assertIn("already registered", dup_err)

        # Case-insensitive duplicate check
        dup_user2, dup_err2 = self.auth.register_user("starviper", "AnotherPass123")
        self.assertIsNone(dup_user2)
        self.assertIn("already registered", dup_err2)

        # 3. Authenticate with correct credentials
        auth_user, auth_err = self.auth.authenticate_user("StarViper", "SectorSevenPass")
        self.assertIsNone(auth_err)
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user["id"], user_id)
        self.assertEqual(auth_user["username"], "StarViper")
        self.assertIsNotNone(auth_user["last_login"])

        # 4. Authenticate with wrong password
        fail_user, fail_err = self.auth.authenticate_user("StarViper", "WrongPass123")
        self.assertIsNone(fail_user)
        self.assertIn("Invalid security passcode", fail_err)

        # 5. Authenticate non-existent pilot
        non_user, non_err = self.auth.authenticate_user("UnknownGhost", "AnyPass")
        self.assertIsNone(non_user)
        self.assertIn("not found", non_err)

        # 6. Retrieve profile by ID and username
        by_id = self.auth.get_user_by_id(user_id)
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id["username"], "StarViper")

        by_name = self.auth.get_user_by_username("starviper")
        self.assertIsNotNone(by_name)
        self.assertEqual(by_name["id"], user_id)

    def test_score_repository_recording_and_queries(self):
        """Tests arcade score recording, leaderboards, and user filtering."""
        # Create users
        u1, _ = self.auth.register_user("PilotAlpha", "pass1234")
        u2, _ = self.auth.register_user("PilotBeta", "pass1234")

        # Record scores for u1, u2, and guest
        self.score_repo.record_score("PILOTALPHA", 25000, hull="cruiser", color="orange", user_id=u1["id"])
        self.score_repo.record_score("PILOTALPHA", 12000, hull="interceptor", color="blue", user_id=u1["id"])
        self.score_repo.record_score("PILOTBETA", 35000, hull="vanguard", color="green", user_id=u2["id"])
        self.score_repo.record_score("GUESTPILOT", 8000, hull="interceptor", color="blue", user_id=None)

        # 1. Global Leaderboard
        global_top = self.score_repo.get_top_scores(limit=10)
        self.assertEqual(len(global_top), 4)
        self.assertEqual(global_top[0]["score"], 35000)
        self.assertEqual(global_top[0]["name"], "PILOTBETA")
        self.assertEqual(global_top[0]["hull"], "vanguard")
        self.assertEqual(global_top[0]["color"], "green")
        self.assertEqual(global_top[1]["score"], 25000)

        # 2. User-Filtered Scores
        u1_scores = self.score_repo.get_user_top_scores(u1["id"])
        self.assertEqual(len(u1_scores), 2)
        self.assertEqual(u1_scores[0]["score"], 25000)
        self.assertEqual(u1_scores[1]["score"], 12000)

        # 3. User Best Score
        best = self.score_repo.get_user_best_score(u1["id"])
        self.assertIsNotNone(best)
        self.assertEqual(best["score"], 25000)

        # 4. Clear Scores for specific user
        self.score_repo.clear_scores(user_id=u1["id"])
        self.assertEqual(len(self.score_repo.get_user_top_scores(u1["id"])), 0)
        self.assertEqual(len(self.score_repo.get_top_scores(10)), 2)

    def test_progress_repository_level_progression_and_stars(self):
        """Tests user-scoped level unlocks, 3-star rating upgrades, and high scores."""
        u1, _ = self.auth.register_user("CommanderNova", "pass1234")
        u2, _ = self.auth.register_user("CommanderZen", "pass1234")

        # Initial progress for u1
        p1 = self.progress_repo.get_progress(u1["id"])
        self.assertEqual(p1["highest_unlocked"], 1)
        self.assertEqual(p1["completed_levels"], [])

        # Complete Level 1 with 2 stars and 5,000 pts
        self.progress_repo.save_level_progress(u1["id"], level=1, stars=2, score=5000, completed=True)
        p1 = self.progress_repo.get_progress(u1["id"])
        self.assertEqual(p1["highest_unlocked"], 2)  # Level 2 unlocked!
        self.assertEqual(p1["completed_levels"], [1])
        self.assertEqual(p1["level_stars"].get("1"), 2)
        self.assertEqual(p1["level_scores"].get("1"), 5000)

        # Replay Level 1 with 3 stars and 4,000 pts (stars upgrade to 3, score stays 5000)
        self.progress_repo.save_level_progress(u1["id"], level=1, stars=3, score=4000, completed=True)
        p1 = self.progress_repo.get_progress(u1["id"])
        self.assertEqual(p1["level_stars"].get("1"), 3)
        self.assertEqual(p1["level_scores"].get("1"), 5000)

        # Replay Level 1 with 1 star and 9,000 pts (stars stay 3, score upgrades to 9000)
        self.progress_repo.save_level_progress(u1["id"], level=1, stars=1, score=9000, completed=True)
        p1 = self.progress_repo.get_progress(u1["id"])
        self.assertEqual(p1["level_stars"].get("1"), 3)
        self.assertEqual(p1["level_scores"].get("1"), 9000)

        # Complete Level 2 and Level 3
        self.progress_repo.save_level_progress(u1["id"], level=2, stars=2, score=12000, completed=True)
        self.progress_repo.save_level_progress(u1["id"], level=3, stars=3, score=20000, completed=True)
        p1 = self.progress_repo.get_progress(u1["id"])
        self.assertEqual(p1["highest_unlocked"], 4)
        self.assertEqual(p1["completed_levels"], [1, 2, 3])

        # Progress Isolation: u2 must still be at level 1
        p2 = self.progress_repo.get_progress(u2["id"])
        self.assertEqual(p2["highest_unlocked"], 1)
        self.assertEqual(p2["completed_levels"], [])

        # Reset u1 progress
        self.progress_repo.reset_progress(u1["id"])
        p1_reset = self.progress_repo.get_progress(u1["id"])
        self.assertEqual(p1_reset["highest_unlocked"], 1)
        self.assertEqual(p1_reset["completed_levels"], [])

    def test_login_state_live_auth_service_integration(self):
        """Verifies LoginState submits directly to Game's AuthService."""
        pg.init()
        if not pg.display.get_surface():
            pg.display.set_mode((1280, 720), pg.HIDDEN)

        game = Game()
        # Override with test in-memory database
        game.db = self.db
        game.auth_service = self.auth
        game.score_repo = self.score_repo
        game.progress_repo = self.progress_repo

        login_state = LoginState(game)

        # 1. Register via LoginState UI
        login_state.active_tab = "register"
        login_state.reg_user_input.set_text("ShadowPilot")
        login_state.reg_pass_input.set_text("TopSecretPass")
        login_state.reg_confirm_input.set_text("TopSecretPass")
        login_state._submit_register()

        self.assertEqual(login_state.status_type, "success")
        self.assertIsNotNone(login_state.pending_user)
        self.assertEqual(login_state.pending_user["username"], "ShadowPilot")
        self.assertFalse(login_state.pending_user["is_guest"])

        # 2. Login via LoginState UI
        login_state.active_tab = "login"
        login_state.login_user_input.set_text("ShadowPilot")
        login_state.login_pass_input.set_text("TopSecretPass")
        login_state._submit_login()

        self.assertEqual(login_state.status_type, "success")
        self.assertEqual(login_state.pending_user["username"], "ShadowPilot")

        # 3. Login with bad password via LoginState UI
        login_state.login_pass_input.set_text("WrongPassword")
        login_state._submit_login()
        self.assertEqual(login_state.status_type, "error")
        self.assertIn("INVALID SECURITY PASSCODE", login_state.status_message.upper())


if __name__ == "__main__":
    unittest.main()
