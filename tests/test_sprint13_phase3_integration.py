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
from save_system import SaveSystem
from game import Game
from states import (
    MenuState,
    LevelSelectState,
    LevelCompleteState,
    GameOverState,
    GameCompleteState,
    HighScoresState,
)
from ui.login_state import LoginState


class TestSprint13Phase3Integration(unittest.TestCase):
    """
    Comprehensive test suite for Sprint 13 Phase 3.
    Verifies SaveSystem SQLite bridge, multi-user progression isolation,
    user-scoped high scores, and state machine authentication flows.
    """

    @classmethod
    def setUpClass(cls):
        pg.init()
        if not pg.display.get_surface():
            pg.display.set_mode((1280, 720), pg.HIDDEN)

    def setUp(self):
        # Isolated in-memory database and repositories
        self.db = DatabaseManager(":memory:")
        self.auth = AuthService(self.db)
        self.score_repo = ScoreRepository(self.db)
        self.progress_repo = ProgressRepository(self.db)
        self.save_system = SaveSystem(
            filename="test_high_scores.json",
            progress_filename="test_progress.json",
            settings_filename="test_settings.json",
            db_manager=self.db,
            score_repo=self.score_repo,
            progress_repo=self.progress_repo,
        )

        # Register test pilot accounts
        self.user_a, _ = self.auth.register_user("PilotAlpha", "passAlpha123")
        self.user_b, _ = self.auth.register_user("PilotBravo", "passBravo123")

    def tearDown(self):
        for f in ("test_high_scores.json", "test_progress.json", "test_settings.json"):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def test_save_system_database_bridge_scores(self):
        """Verifies SaveSystem records scores to SQLite with user_id and updates JSON fallback."""
        # 1. Save score for Pilot Alpha
        res_a = self.save_system.save_score(
            name="ALPHA",
            score=25000,
            hull="interceptor",
            color="blue",
            user_id=self.user_a["id"],
        )
        self.assertTrue(res_a)

        # 2. Save score for Pilot Bravo
        res_b = self.save_system.save_score(
            name="BRAVO",
            score=18000,
            hull="cruiser",
            color="orange",
            user_id=self.user_b["id"],
        )
        self.assertTrue(res_b)

        # 3. Save score for Guest Pilot (user_id=None)
        res_g = self.save_system.save_score(
            name="GUEST",
            score=5000,
            hull="vanguard",
            color="green",
            user_id=None,
        )
        self.assertTrue(res_g)

        # 4. Query global leaderboard via SaveSystem
        global_scores = self.save_system.load_scores()
        self.assertGreaterEqual(len(global_scores), 3)
        self.assertEqual(global_scores[0]["score"], 25000)
        self.assertEqual(global_scores[0]["name"], "ALPHA")
        self.assertEqual(global_scores[1]["score"], 18000)
        self.assertEqual(global_scores[1]["name"], "BRAVO")

        # 5. Query user-specific scores via SaveSystem
        alpha_scores = self.save_system.load_scores(user_id=self.user_a["id"])
        self.assertEqual(len(alpha_scores), 1)
        self.assertEqual(alpha_scores[0]["score"], 25000)

        bravo_scores = self.save_system.load_scores(user_id=self.user_b["id"])
        self.assertEqual(len(bravo_scores), 1)
        self.assertEqual(bravo_scores[0]["score"], 18000)

    def test_multi_user_campaign_progression_isolation(self):
        """
        Verifies that multiple registered pilots maintain distinct, isolated
        campaign progression records without overwriting each other.
        """
        # Pilot Alpha completes levels 1 and 2
        self.save_system.save_progress(
            selected_level=1,
            stars=3,
            score=12000,
            user_id=self.user_a["id"],
        )
        self.save_system.save_progress(
            selected_level=2,
            stars=2,
            score=15000,
            user_id=self.user_a["id"],
        )

        # Pilot Bravo completes level 1 only with 1 star
        self.save_system.save_progress(
            selected_level=1,
            stars=1,
            score=4500,
            user_id=self.user_b["id"],
        )

        # Retrieve progression for Pilot Alpha
        prog_a = self.save_system.load_progress(user_id=self.user_a["id"])
        self.assertEqual(prog_a["highest_unlocked"], 3)
        self.assertEqual(prog_a["completed_levels"], [1, 2])
        self.assertEqual(prog_a["level_stars"].get("1"), 3)
        self.assertEqual(prog_a["level_stars"].get("2"), 2)
        self.assertEqual(prog_a["level_scores"].get("1"), 12000)
        self.assertEqual(prog_a["level_scores"].get("2"), 15000)

        # Retrieve progression for Pilot Bravo
        prog_b = self.save_system.load_progress(user_id=self.user_b["id"])
        self.assertEqual(prog_b["highest_unlocked"], 2)
        self.assertEqual(prog_b["completed_levels"], [1])
        self.assertEqual(prog_b["level_stars"].get("1"), 1)
        self.assertNotIn("2", prog_b["level_stars"])
        self.assertEqual(prog_b["level_scores"].get("1"), 4500)

    def test_game_over_state_user_scoped_commitment(self):
        """Verifies GameOverState auto-populates pilot name and commits to DB with user_id."""
        game = Game()
        game.db = self.db
        game.auth_service = self.auth
        game.score_repo = self.score_repo
        game.progress_repo = self.progress_repo
        game.save_system = self.save_system

        # Authenticate Pilot Alpha
        game.set_user({"id": self.user_a["id"], "username": "PilotAlpha", "is_guest": False})
        self.assertTrue(game.is_logged_in())

        # Launch GameOverState with score 32000
        game_over = GameOverState(game, score=32000)
        self.assertEqual(game_over.player_name, "PILOTALP")

        # Save score
        game_over._save_score()

        # Verify DB score record
        scores = self.score_repo.get_user_top_scores(self.user_a["id"])
        self.assertTrue(any(s["score"] == 32000 for s in scores))

    def test_game_complete_state_user_scoped_commitment(self):
        """Verifies GameCompleteState commits victory score with user_id."""
        game = Game()
        game.db = self.db
        game.auth_service = self.auth
        game.score_repo = self.score_repo
        game.progress_repo = self.progress_repo
        game.save_system = self.save_system

        game.set_user({"id": self.user_b["id"], "username": "PilotBravo", "is_guest": False})
        game_complete = GameCompleteState(game, score=99999)
        game_complete._finalize()

        # Check DB
        scores = self.score_repo.get_user_top_scores(self.user_b["id"])
        self.assertTrue(any(s["score"] == 99999 for s in scores))

    def test_level_select_and_complete_user_scoped_flow(self):
        """Verifies LevelSelectState loads user progress and LevelCompleteState updates user DB."""
        game = Game()
        game.db = self.db
        game.auth_service = self.auth
        game.score_repo = self.score_repo
        game.progress_repo = self.progress_repo
        game.save_system = self.save_system

        # Set user
        game.set_user({"id": self.user_a["id"], "username": "PilotAlpha", "is_guest": False})

        # Complete level 4
        level_complete = LevelCompleteState(game, score=16000, cleared_level=4, lives_lost=0)
        self.assertEqual(level_complete.stars, 3)

        # Inspect LevelSelectState
        lvl_select = LevelSelectState(game)
        self.assertEqual(lvl_select.progress["highest_unlocked"], 5)
        self.assertIn(4, lvl_select.progress["completed_levels"])
        self.assertEqual(lvl_select.progress["level_stars"].get("4"), 3)

    def test_high_scores_state_dual_tabs_and_guest_prompt(self):
        """Verifies HighScoresState dual tabs (Global vs My Scores) and guest login prompts."""
        game = Game()
        game.db = self.db
        game.auth_service = self.auth
        game.score_repo = self.score_repo
        game.progress_repo = self.progress_repo
        game.save_system = self.save_system

        # Record a score
        self.score_repo.record_score("STARLORD", 50000, "interceptor", "blue", user_id=self.user_a["id"])

        # 1. As Guest Pilot
        game.logout()
        hs_state = HighScoresState(game)
        self.assertEqual(hs_state.active_tab, "global")
        self.assertGreaterEqual(len(hs_state.scores_list), 1)

        # Switch to "my_scores" tab as Guest
        tab_click = pg.event.Event(
            pg.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (hs_state.tab_my_rect.centerx, hs_state.tab_my_rect.centery)},
        )
        hs_state.handle_events([tab_click])
        self.assertEqual(hs_state.active_tab, "my_scores")
        self.assertEqual(len(hs_state.scores_list), 0)

        # Click login prompt button switches to LoginState
        login_btn_click = pg.event.Event(
            pg.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (hs_state.login_btn_rect.centerx, hs_state.login_btn_rect.centery)},
        )
        hs_state.handle_events([login_btn_click])
        self.assertIsInstance(game.state, LoginState)

        # 2. As Authenticated Pilot Alpha
        game.set_user({"id": self.user_a["id"], "username": "PilotAlpha", "is_guest": False})
        hs_state_auth = HighScoresState(game)
        hs_state_auth.active_tab = "my_scores"
        hs_state_auth._refresh_scores()
        self.assertEqual(len(hs_state_auth.scores_list), 1)
        self.assertEqual(hs_state_auth.scores_list[0]["score"], 50000)

        # Draw without error
        screen = pg.Surface((1280, 720))
        hs_state_auth.update(0.016)
        hs_state_auth.draw(screen)


if __name__ == "__main__":
    unittest.main()
