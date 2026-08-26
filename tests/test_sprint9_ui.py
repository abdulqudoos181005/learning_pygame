import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from states import (
    MenuState,
    InstructionsState,
    ShopState,
    LevelSelectState,
    PauseState,
    GameOverState,
    _draw_ui_button,
    _UPGRADE_POOL,
)
from assets_loader import AssetsLoader


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


class Sprint9UITest(unittest.TestCase):
    def setUp(self):
        self.game = DummyGame()
        self.screen = pygame.Surface((1280, 720))

    def test_menu_state_has_flight_manual_and_quit(self):
        menu = MenuState(self.game)
        self.assertIn("Play Game", menu.options)
        self.assertIn("Hangar / Ships", menu.options)
        self.assertIn("Flight Manual", menu.options)
        self.assertIn("High Scores", menu.options)
        self.assertIn("Quit", menu.options)
        self.assertEqual(len(menu.buttons), 5)

        # Select Flight Manual
        flight_idx = menu.options.index("Flight Manual")
        menu.selected_index = flight_idx
        menu._select_option(flight_idx)
        self.assertIsInstance(self.game.target, InstructionsState)

        # Select Quit
        quit_idx = menu.options.index("Quit")
        menu.selected_index = quit_idx
        menu._select_option(quit_idx)
        self.assertFalse(self.game.is_running)

    def test_instructions_state_cards_and_navigation(self):
        inst = InstructionsState(self.game)
        self.assertEqual(len(inst.cards), 6)
        self.assertEqual(len(inst.mechanics), 6)

        # Check mechanics card contents
        titles = [m["title"] for m in inst.mechanics]
        self.assertIn("FLIGHT CONTROLS", titles)
        self.assertIn("PRIMARY PHOTON BLASTER", titles)
        self.assertIn("HOMING MISSILES", titles)
        self.assertIn("KINETIC SHIELD BARRIER", titles)
        self.assertIn("COMBO MULTIPLIER", titles)
        self.assertIn("HAZARDS & MOTHERSHIPS", titles)

        # Render test
        inst.update(0.016)
        inst.draw(self.screen)

        # Navigation back via ESC key
        inst.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)])
        self.assertIsInstance(self.game.target, MenuState)

        # Navigation back via mouse click on back button
        inst.handle_events([
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=(inst.back_rect.centerx, inst.back_rect.centery)
            )
        ])
        self.assertIsInstance(self.game.target, MenuState)

    def test_shop_state_overhaul(self):
        shop = ShopState(self.game, score=1000, cleared_level=1)
        self.assertEqual(len(shop.card_rects), 3)
        self.assertEqual(len(shop.offers), 3)

        # Verify upgrade pool has sprite aliases and valid attributes
        for item in _UPGRADE_POOL:
            self.assertIn("sprite_alias", item)
            self.assertIn("name", item)
            self.assertIn("desc", item)
            self.assertIn("cost", item)
            self.assertIn("step", item)

        # Purchase transaction test
        first_cost = shop.offers[0]["cost"]
        shop._buy(0)
        self.assertIn(0, shop.purchased)
        self.assertEqual(shop.score, 1000 - first_cost)
        self.assertGreater(len(self.game.upgrades), 0)

        # Particle update and draw test
        shop.update(0.016)
        shop.draw(self.screen)

    def test_draw_ui_button_danger_styling(self):
        surf = pygame.Surface((200, 50))
        font = self.game.assets.font
        rect = pygame.Rect(10, 10, 180, 40)

        # Standard button draw
        _draw_ui_button(surf, rect, "NORMAL", font, hovered=True, danger=False)

        # Danger button draw (ruby red styling)
        _draw_ui_button(surf, rect, "QUIT", font, hovered=True, danger=True)
        _draw_ui_button(surf, rect, "QUIT", font, pressed=True, danger=True)

    def test_declutter_screens_render_cleanly(self):
        # LevelSelectState
        lvl_sel = LevelSelectState(self.game)
        lvl_sel.draw(self.screen)

        # PauseState
        pause = PauseState(self.game, lvl_sel)
        pause.draw(self.screen)

        # GameOverState
        game_over = GameOverState(self.game, 1500)
        game_over.draw(self.screen)


if __name__ == '__main__':
    unittest.main()
