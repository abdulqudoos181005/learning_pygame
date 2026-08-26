# pyrefly: ignore [missing-import]
import os
import sys
import unittest
import pygame as pg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from input_map import InputMap
from save_system import SaveSystem


class TestSprint11Input(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        pg.display.set_mode((1280, 720))

    def setUp(self):
        self.save_system = SaveSystem(settings_filename="test_input_settings.json")
        if os.path.exists(self.save_system.settings_filepath):
            os.remove(self.save_system.settings_filepath)

    def tearDown(self):
        if os.path.exists(self.save_system.settings_filepath):
            os.remove(self.save_system.settings_filepath)

    def test_input_map_action_graph(self):
        inp = InputMap()
        # Initial state should be clean/false
        self.assertFalse(inp.is_held("fire"))
        self.assertFalse(inp.is_pressed("fire"))
        self.assertFalse(inp.is_released("fire"))

        # Manual state test: simulating rising edge
        inp.actions_held["fire"] = True
        inp.actions_pressed["fire"] = True
        self.assertTrue(inp.is_held("fire"))
        self.assertTrue(inp.is_pressed("fire"))

    def test_settings_persistence_roundtrip(self):
        settings = self.save_system.load_settings()
        self.assertIn("music_volume", settings)
        self.assertIn("keybinds", settings)

        # Modify and save
        settings["music_volume"] = 0.42
        settings["keybinds"]["fire"] = "k"
        self.save_system.save_settings(settings)

        # Reload
        reloaded = self.save_system.load_settings()
        self.assertAlmostEqual(reloaded["music_volume"], 0.42, delta=0.01)
        self.assertEqual(reloaded["keybinds"]["fire"], "k")


if __name__ == "__main__":
    unittest.main()
