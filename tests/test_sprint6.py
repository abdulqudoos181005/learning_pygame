import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pygame

pygame.init()
pygame.font.init()
pygame.display.set_mode((1280, 720))

from level_system import LevelSystem
from sprites import Asteroid
from states import LevelCompleteState


class DummyAssets:
    def __init__(self):
        if not pygame.font.get_init():
            pygame.font.init()
        self.font = pygame.font.SysFont('arial', 24)
        self.title_font = pygame.font.SysFont('arial', 48)
        self.hud_font = pygame.font.SysFont('arial', 18)


class DummyGame:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.assets = DummyAssets()
        self.state = None
        self.target = None

    def change_state(self, state):
        self.target = state
        self.state = state


class Sprint6FeaturesTest(unittest.TestCase):
    def test_level_system_uses_spawn_queue(self):
        system = LevelSystem(starting_level=1)
        self.assertTrue(hasattr(system, 'spawn_queue'))
        self.assertTrue(hasattr(system, 'tick_spawn'))
        system.spawn_queue.clear()
        system.spawn_queue.extend(['scout', 'stinger'])
        self.assertEqual(system.tick_spawn(0.0), 'scout')
        self.assertEqual(system.tick_spawn(0.0), 'stinger')

    def test_asteroid_types_exist(self):
        self.assertTrue(hasattr(Asteroid, 'SIZES'))
        self.assertTrue(hasattr(Asteroid, 'COLORS'))
        self.assertIn('small', Asteroid.SIZES)
        self.assertIn('large', Asteroid.SIZES)
        self.assertIn('brown', Asteroid.COLORS)
        self.assertIn('grey', Asteroid.COLORS)

    def test_level_complete_state_ignores_keyboard_continue(self):
        game = DummyGame()
        state = LevelCompleteState(game, 500, 2)

        state.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)])
        self.assertFalse(getattr(state, 'transition_locked', False))
        self.assertIsNone(game.target)

        state.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(state.continue_rect.centerx, state.continue_rect.centery))])
        self.assertTrue(state.transition_locked)
        self.assertIsNotNone(game.target)


if __name__ == '__main__':
    unittest.main()
