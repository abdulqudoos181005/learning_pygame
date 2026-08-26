# pyrefly: ignore [missing-import]
import os
import sys
import unittest
import pygame as pg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from save_system import SaveSystem
from assets_loader import AssetsLoader
from states import HangarState, LevelSelectState, PlayState
from sprites import Player
from level_system import THEATERS, get_theater


class MockGame:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.assets = AssetsLoader()
        self.save_system = SaveSystem(settings_filename="test_settings.json")
        self.loadout = self.save_system.load_loadout()
        self.state = None
        self.upgrades = {}

    def change_state(self, new_state):
        self.state = new_state


class TestSprint11Hangar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        pg.display.set_mode((1280, 720))

    def setUp(self):
        self.game = MockGame()
        if os.path.exists(self.game.save_system.settings_filepath):
            os.remove(self.game.save_system.settings_filepath)

    def tearDown(self):
        if os.path.exists(self.game.save_system.settings_filepath):
            os.remove(self.game.save_system.settings_filepath)

    def test_hangar_hulls_and_colors_resolve_to_assets(self):
        # Verify all 3 hulls x 4 colors resolve to existing textures in AssetsLoader
        for hull in ("interceptor", "cruiser", "vanguard"):
            for color in ("blue", "green", "orange", "red"):
                if hull == "interceptor":
                    key = f"player_fleet/interceptor_strike_{color}"
                elif hull == "cruiser":
                    key = f"player_fleet/heavy_cruiser_assault_{color}"
                else:
                    key = f"player_fleet/stealth_vanguard_bomber_{color}"

                img = self.game.assets.get_image(key, 60, 60)
                self.assertIsNotNone(img)
                self.assertEqual(img.get_width(), 60)
                self.assertEqual(img.get_height(), 60)

                # Life counter icons
                life_key = f"ui_hud/life_counters/hud_life_{hull}_{color}"
                life_img = self.game.assets.get_image(life_key, 24, 24)
                self.assertIsNotNone(life_img)

    def test_hangar_state_selection_and_persistence(self):
        hangar = HangarState(self.game, return_state="level_select")
        # Change hull to Cruiser (index 1) and color to Red (index 3)
        hangar.selected_hull_idx = 1
        hangar.selected_color_idx = 3
        hangar._save_and_sync()

        self.assertEqual(self.game.loadout["hull"], "cruiser")
        self.assertEqual(self.game.loadout["color"], "red")

        # Verify persisted in test_settings.json
        reloaded = self.game.save_system.load_loadout()
        self.assertEqual(reloaded["hull"], "cruiser")
        self.assertEqual(reloaded["color"], "red")

    def test_player_stats_and_sprite_follow_loadout(self):
        # Test Cruiser
        self.game.loadout = {"hull": "cruiser", "color": "green"}
        player_cruiser = Player(self.game, 640, 600)
        self.assertEqual(player_cruiser.hull_type, "cruiser")
        self.assertEqual(player_cruiser.color_name, "green")
        self.assertEqual(player_cruiser.max_health, 140)
        self.assertEqual(player_cruiser.max_shield, 120)
        self.assertEqual(player_cruiser.max_speed, 340.0)

        # Test Vanguard
        self.game.loadout = {"hull": "vanguard", "color": "orange"}
        player_vanguard = Player(self.game, 640, 600)
        self.assertEqual(player_vanguard.hull_type, "vanguard")
        self.assertEqual(player_vanguard.color_name, "orange")
        self.assertEqual(player_vanguard.max_health, 80)
        self.assertEqual(player_vanguard.max_shield, 80)
        self.assertEqual(player_vanguard.max_speed, 460.0)
        self.assertEqual(player_vanguard.missile_count, 4)

    def test_hangar_state_draws_without_exception(self):
        hangar = HangarState(self.game, return_state="menu")
        screen = pg.Surface((1280, 720))
        hangar.update(0.016)
        hangar.draw(screen)


class TestSprint11Theaters(unittest.TestCase):
    def test_levels_map_to_distinct_theaters(self):
        theater_l1 = get_theater(1)
        theater_l5 = get_theater(5)
        theater_l8 = get_theater(8)
        theater_l10 = get_theater(10)

        self.assertEqual(theater_l1["name"], "Bio Nursery")
        self.assertEqual(theater_l5["name"], "First Mothership")
        self.assertEqual(theater_l8["name"], "Shadow Corps")
        self.assertEqual(theater_l10["name"], "Solar Throne")

        # Distinct accent colors & nebulae
        self.assertNotEqual(theater_l1["accent_color"], theater_l5["accent_color"])
        self.assertIsNotNone(theater_l1["nebula"])
        self.assertIsNotNone(theater_l8["nebula"])


if __name__ == "__main__":
    unittest.main()
