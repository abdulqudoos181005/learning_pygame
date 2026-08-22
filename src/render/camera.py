# pyrefly: ignore [missing-import]
import random
import math
import pygame as pg


class Camera:
    """
    Sprint 11 / Pillar D — Dynamic 2D Camera with Dead-Zone Follow,
    Directional Impulse, Hit-Stop, and Zoom Pulse.
    """

    def __init__(self, screen_width=1280, screen_height=720):
        self.width = screen_width
        self.height = screen_height

        # Position tracking and follow
        self.pos = pg.Vector2(0, 0)
        self.target_pos = pg.Vector2(0, 0)
        self.follow_deadzone = pg.Rect(-60, -40, 120, 80)
        self.follow_speed = 3.5
        self.vertical_bias = -24.0  # Keeps fight framed above player

        # Zoom
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.zoom_speed = 4.0

        # Screen shake & directional impulse
        self.shake_timer = 0.0
        self.shake_magnitude = 0.0
        self.shake_offset = pg.Vector2(0, 0)
        self.impulse = pg.Vector2(0, 0)
        self.impulse_decay = 8.0

        # Hit-stop (micro time-freeze for impact weight)
        self.hit_stop_timer = 0.0
        self.time_scale = 1.0

    def add_shake(self, duration=0.2, magnitude=5.0):
        """Triggers screen vibration over a duration."""
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_magnitude = max(self.shake_magnitude, magnitude)

    def add_impulse(self, dir_x, dir_y, magnitude=12.0):
        """Kicks the camera along an impact direction vector."""
        vec = pg.Vector2(dir_x, dir_y)
        if vec.length_squared() > 0:
            vec = vec.normalize() * magnitude
            self.impulse += vec

    def trigger_hit_stop(self, duration=0.04):
        """Freezes/slows simulation time briefly for impact feel."""
        self.hit_stop_timer = max(self.hit_stop_timer, duration)

    def set_target_zoom(self, zoom, speed=4.0):
        """Sets target camera zoom level (e.g. 1.04 on boss intro, 1.02 on combo)."""
        self.target_zoom = zoom
        self.zoom_speed = speed

    def get_effective_dt(self, dt):
        """Returns delta time adjusted by hit-stop state."""
        if self.hit_stop_timer > 0:
            return dt * 0.05
        return dt * self.time_scale

    def update(self, dt, target_x=None, target_y=None):
        # 1. Hit-stop timer
        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= dt

        # 2. Camera dead-zone follow
        if target_x is not None and target_y is not None:
            center_x = self.width / 2.0
            center_y = self.height / 2.0
            diff_x = (target_x - center_x) * 0.12
            diff_y = (target_y - center_y) * 0.08 + self.vertical_bias
            self.target_pos.x = max(-35.0, min(35.0, diff_x))
            self.target_pos.y = max(-25.0, min(25.0, diff_y))
            self.pos += (self.target_pos - self.pos) * min(1.0, self.follow_speed * dt)
        else:
            self.pos *= max(0.0, 1.0 - 5.0 * dt)

        # 3. Zoom interpolation
        if abs(self.zoom - self.target_zoom) > 0.001:
            diff = self.target_zoom - self.zoom
            self.zoom += diff * min(1.0, self.zoom_speed * dt)
        else:
            self.zoom = self.target_zoom

        # 4. Shake decay & offset calculation
        if self.shake_timer > 0:
            self.shake_timer -= dt
            fade = self.shake_timer / max(0.001, self.shake_timer + dt)
            self.shake_offset.x = random.uniform(-self.shake_magnitude, self.shake_magnitude) * fade
            self.shake_offset.y = random.uniform(-self.shake_magnitude, self.shake_magnitude) * fade
        else:
            self.shake_offset.update(0, 0)
            self.shake_magnitude = 0.0

        # 5. Impulse damping
        self.impulse *= max(0.0, 1.0 - self.impulse_decay * dt)

    @property
    def total_offset(self):
        """Returns the final offset (X, Y) to displace rendering."""
        return (
            self.pos.x + self.shake_offset.x + self.impulse.x,
            self.pos.y + self.shake_offset.y + self.impulse.y,
        )
