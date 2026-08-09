import os
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from level_system import LevelSystem
from sprites import Asteroid


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


if __name__ == '__main__':
    unittest.main()
