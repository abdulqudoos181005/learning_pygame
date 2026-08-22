# pyrefly: ignore [missing-import]
import os
import sys
import unittest
import pygame as pg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from audio.director import AudioDirector
from assets_loader import AssetsLoader


class TestSprint11Audio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        # Initialize mixer in headless / test-friendly mode
        try:
            pg.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.assets = AssetsLoader()
        self.audio = AudioDirector(assets=self.assets, screen_width=1280)

    def test_audio_director_initialization(self):
        self.assertEqual(self.audio.music_volume, 0.7)
        self.assertEqual(self.audio.sfx_volume, 0.8)
        self.assertEqual(self.audio.ui_volume, 0.8)

    def test_bus_volume_controls(self):
        self.audio.set_bus_volumes(music=0.5, sfx=0.6, ui=0.9)
        self.assertAlmostEqual(self.audio.music_volume, 0.5)
        self.assertAlmostEqual(self.audio.sfx_volume, 0.6)
        self.assertAlmostEqual(self.audio.ui_volume, 0.9)

        # Clamping
        self.audio.set_bus_volumes(music=1.5, sfx=-0.2)
        self.assertEqual(self.audio.music_volume, 1.0)
        self.assertEqual(self.audio.sfx_volume, 0.0)

    def test_ducking_mechanism(self):
        self.audio.trigger_ducking(duration=0.5, factor=0.4)
        self.assertTrue(self.audio.is_ducked)
        self.assertEqual(self.audio.duck_factor, 0.4)
        self.assertAlmostEqual(self.audio.duck_timer, 0.5)

        # Update should reduce duck timer and restore
        self.audio.update(0.6)
        self.assertFalse(self.audio.is_ducked)

    def test_sfx_spatial_pan_and_play(self):
        # Center pan
        ch_center = self.audio.play_sfx("laser", pos_x=640)
        # Left pan
        ch_left = self.audio.play_sfx("laser", pos_x=100)
        # Right pan
        ch_right = self.audio.play_sfx("laser", pos_x=1200)

    def test_laser_voice_limiting(self):
        # Firing multiple lasers should not exceed max voices
        for _ in range(10):
            self.audio.play_sfx("laser", pos_x=640)
        self.assertLessEqual(len(self.audio.active_laser_channels), AudioDirector.MAX_LASER_VOICES)

    def test_ui_grammar_calls(self):
        self.audio.play_ui("tick")
        self.audio.play_ui("confirm")
        self.audio.play_ui("danger")
        self.audio.play_ui("purchase")

    def test_procedural_menu_music(self):
        self.audio.play_music("menu", fade_ms=100)
        self.assertEqual(self.audio.current_music_track, "menu")


if __name__ == "__main__":
    unittest.main()
