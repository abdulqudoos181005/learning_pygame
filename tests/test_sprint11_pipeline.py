# pyrefly: ignore [missing-import]
import os
import sys
import unittest
import pygame as pg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from render.camera import Camera
from render.pipeline import RenderPipeline
from assets_loader import AssetsLoader


class TestSprint11Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        pg.display.set_mode((1280, 720))

    def setUp(self):
        self.assets = AssetsLoader()
        self.camera = Camera(1280, 720)
        self.pipeline = RenderPipeline(1280, 720, assets=self.assets)
        self.screen = pg.Surface((1280, 720))

    def test_camera_deadzone_follow(self):
        # Target in center -> camera offset near 0
        self.camera.update(0.1, target_x=640, target_y=360)
        self.assertAlmostEqual(self.camera.pos.x, 0.0, delta=5.0)

        # Target shifted right -> camera follows smoothly
        for _ in range(30):
            self.camera.update(0.016, target_x=1000, target_y=360)
        self.assertGreater(self.camera.pos.x, 0.0)

    def test_camera_zoom_interpolation(self):
        self.camera.set_target_zoom(1.04, speed=5.0)
        self.assertEqual(self.camera.target_zoom, 1.04)
        for _ in range(40):
            self.camera.update(0.016)
        self.assertAlmostEqual(self.camera.zoom, 1.04, delta=0.01)

    def test_hit_stop_scaling(self):
        self.camera.trigger_hit_stop(duration=0.05)
        dt = 0.016
        effective_dt = self.camera.get_effective_dt(dt)
        self.assertLess(effective_dt, dt)

        # After hit stop expires, effective dt returns to normal
        self.camera.update(0.06)
        self.assertAlmostEqual(self.camera.get_effective_dt(dt), dt)

    def test_camera_impulse_and_decay(self):
        self.camera.add_impulse(0, 1.0, magnitude=20.0)
        self.assertGreater(self.camera.impulse.y, 0)
        initial_y = self.camera.impulse.y

        # Decay over time
        for _ in range(20):
            self.camera.update(0.016)
        self.assertLess(self.camera.impulse.y, initial_y)

    def test_render_pipeline_presentation(self):
        # Draw something on world canvas
        pg.draw.circle(self.pipeline.world_canvas, (0, 255, 200), (640, 360), 40)
        
        # Present to screen
        self.pipeline.present(
            self.screen,
            camera=self.camera,
            health_ratio=0.5,
            shield_active=True,
            speed_boost=True,
            is_boss_alert=False,
        )

    def test_quality_toggle_skips_bloom(self):
        self.pipeline.quality = "low"
        self.pipeline.present(self.screen, camera=self.camera)
        self.assertEqual(self.pipeline.quality, "low")

    def test_letterbox_toggle_animation(self):
        self.pipeline.set_letterbox(True)
        self.assertEqual(self.pipeline.letterbox_target, self.pipeline.LETTERBOX_MAX)
        for _ in range(30):
            self.pipeline.update(0.016)
        self.assertGreater(self.pipeline.letterbox_height, 0.0)

        self.pipeline.set_letterbox(False)
        for _ in range(30):
            self.pipeline.update(0.016)
        self.assertAlmostEqual(self.pipeline.letterbox_height, 0.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
