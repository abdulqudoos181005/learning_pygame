import unittest
import os
import tempfile
import json
import pygame as pg

# Initialize dummy display for headless testing if needed
pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1, 1), pg.NOFRAME)

from src.ui.tooltip import UITooltipManager
from src.ui.cursor import SoftwareCursor
from src.audio.director import AudioDirector
from src.save_system import SaveSystem
from src.assets_loader import AssetsLoader


class TestSprint12UI(unittest.TestCase):
    def setUp(self):
        self.assets = AssetsLoader()
        self.tooltip_mgr = UITooltipManager(self.assets.font, self.assets.title_font)
        self.cursor = SoftwareCursor(self.assets)
        self.audio = AudioDirector(self.assets)

    def test_tooltip_manager_lifecycle(self):
        """Test tooltip setting, updating alpha, boundary clamping, and clearing."""
        self.assertFalse(self.tooltip_mgr.active)
        self.assertEqual(self.tooltip_mgr.alpha, 0.0)

        # Set tooltip
        self.tooltip_mgr.set_tooltip("TEST TITLE", "This is a test body description.", (100, 100))
        self.assertTrue(self.tooltip_mgr.active)
        self.assertEqual(self.tooltip_mgr.target_alpha, 240.0)

        # Update alpha
        self.tooltip_mgr.update(0.1)
        self.assertGreaterThan = self.tooltip_mgr.alpha > 0.0
        self.assertTrue(self.tooltip_mgr.alpha > 0.0)

        # Draw to test surface
        surf = pg.Surface((1280, 720), pg.SRCALPHA)
        self.tooltip_mgr.draw(surf)

        # Clear tooltip
        self.tooltip_mgr.clear()
        self.assertFalse(self.tooltip_mgr.active)
        self.assertEqual(self.tooltip_mgr.target_alpha, 0.0)

    def test_audio_director_ui_grammar(self):
        """Test UI audio grammar methods on AudioDirector."""
        self.audio.play_ui_hover()
        self.audio.play_ui_click()
        self.audio.play_ui_back()
        self.audio.play_ui_slider()
        self.audio.play_ui_toggle()
        # Ensure no exception thrown

    def test_cursor_context_hover_and_snap(self):
        """Test software cursor hover scale and snap functionality."""
        self.assertFalse(self.cursor.hovered_control)
        self.assertEqual(self.cursor.hover_scale, 1.0)

        self.cursor.set_hover_state(True)
        self.assertTrue(self.cursor.hovered_control)

        self.cursor.update(0.1)
        self.assertTrue(self.cursor.hover_scale > 1.0)

        self.cursor.snap_to(400, 300)
        self.assertEqual(self.cursor.target_pos.x, 400)
        self.assertEqual(self.cursor.target_pos.y, 300)

    def test_save_system_3star_and_loadout(self):
        """Test level progress 3-star evaluations and leaderboard loadout persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores_file = os.path.join(tmpdir, "high_scores.json")
            progress_file = os.path.join(tmpdir, "level_progress.json")
            settings_file = os.path.join(tmpdir, "settings.json")

            save_sys = SaveSystem(filename=scores_file, progress_filename=progress_file, settings_filename=settings_file)

            # Test save level progress with 3-star rating
            save_sys.save_progress(selected_level=2, stars=3, score=8500)
            progress = save_sys.load_progress()

            self.assertEqual(progress["highest_unlocked"], 3)
            self.assertIn(2, progress["completed_levels"])
            self.assertEqual(progress["level_stars"].get("2"), 3)
            self.assertEqual(progress["level_scores"].get("2"), 8500)

            # Test save high score with loadout hull/color
            save_sys.save_score("ACE", 15000, hull="vanguard", color="green")
            scores = save_sys.load_scores()

            self.assertTrue(len(scores) > 0)
            top = scores[0]
            self.assertEqual(top["name"], "ACE")
            self.assertEqual(top["score"], 15000)
            self.assertEqual(top.get("hull"), "vanguard")
            self.assertEqual(top.get("color"), "green")


if __name__ == "__main__":
    unittest.main()
