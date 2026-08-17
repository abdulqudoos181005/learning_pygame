import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from assets_loader import AssetsLoader
from states import (
    MenuState,
    InstructionsState,
    ShopState,
    LevelSelectState,
    PauseState,
    GameOverState,
    HighScoresState,
)


class DummyGame:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.assets = AssetsLoader()
        self.state = None
        self.target = None
        self.upgrades = {}
        self.is_running = True

    def change_state(self, state):
        self.target = state
        self.state = state

    def quit(self):
        self.is_running = False


class Sprint10FontsTest(unittest.TestCase):
    def setUp(self):
        self.game = DummyGame()
        self.screen = pygame.Surface((1280, 720))

    def test_each_role_loads_its_own_ttf(self):
        assets = self.game.assets
        self.assertEqual(assets.font_sources["title"], "audiowide_cyber_display.ttf")
        self.assertEqual(assets.font_sources["ui"], "vector_future_bold.ttf")
        self.assertEqual(assets.font_sources["hud"], "vector_future_thin.ttf")
        self.assertIsNotNone(assets.title_font)
        self.assertIsNotNone(assets.font)
        self.assertIsNotNone(assets.hud_font)
        self.assertGreater(assets.title_font.get_height(), assets.font.get_height())
        self.assertGreaterEqual(assets.font.get_height(), assets.hud_font.get_height())

    def test_missing_ttf_falls_back_per_role_only(self):
        assets = AssetsLoader()
        original_loader = assets._load_role_font

        def fake_loader(filename, size, fallback_size):
            if filename == "audiowide_cyber_display.ttf":
                return pygame.font.SysFont("Trebuchet MS", fallback_size), None
            return original_loader(filename, size, fallback_size)

        assets._load_role_font = fake_loader
        assets.title_font, assets.font_sources["title"] = assets._load_role_font(
            "audiowide_cyber_display.ttf", size=42, fallback_size=48
        )
        assets.font, assets.font_sources["ui"] = assets._load_role_font(
            "vector_future_bold.ttf", size=22, fallback_size=24
        )
        assets.hud_font, assets.font_sources["hud"] = assets._load_role_font(
            "vector_future_thin.ttf", size=18, fallback_size=20
        )

        self.assertIsNone(assets.font_sources["title"])
        self.assertEqual(assets.font_sources["ui"], "vector_future_bold.ttf")
        self.assertEqual(assets.font_sources["hud"], "vector_future_thin.ttf")

    def test_screens_render_with_new_hierarchy(self):
        MenuState(self.game).draw(self.screen)
        InstructionsState(self.game).draw(self.screen)
        LevelSelectState(self.game).draw(self.screen)
        PauseState(self.game, MenuState(self.game)).draw(self.screen)
        GameOverState(self.game, 1234).draw(self.screen)
        HighScoresState(self.game).draw(self.screen)
        ShopState(self.game, score=900, cleared_level=1).draw(self.screen)


if __name__ == "__main__":
    unittest.main()
