# pyrefly: ignore [missing-import]
import pygame as pg
import random
import math

from level_system import get_theater


class SpaceEnvironment:
    """
    Sprint 11 / Pillar B — layered parallax mission backdrop.

    Replaces the flat navy fill + dotted Starfield in combat with a three-layer
    world (far void, mid nebula, near motes/debris) that reskins itself to the
    level's faction theater, plus a hyperspace warp-in/out transition played
    on mission start and mission clear.
    """

    TILE = 256
    WARP_IN_DURATION = 0.9
    WARP_OUT_DURATION = 0.7

    def __init__(self, assets, width, height, level_number):
        self.assets = assets
        self.width = width
        self.height = height

        self.far_offset = pg.Vector2(0, 0)
        self.mid_offset = pg.Vector2(0, 0)

        self.motes = []
        self.debris = []
        self.warp_streaks = []

        self.warp_direction = None  # None, "in", or "out"
        self.warp_timer = 0.0
        self.warp_duration = 0.0

        self.theater = None
        self.level_number = None
        self.set_level(level_number)

    def set_level(self, level_number):
        """Reconfigures the theater (armada/nebula/boss/laser/accent) for a mission."""
        self.level_number = level_number
        self.theater = get_theater(level_number)
        self._build_motes()
        self._build_warp_streaks()

    def _build_motes(self):
        accent = self.theater["accent_color"]
        self.motes = []
        # (count, speed range, size range, brightness) - mirrors the old Starfield's 3-layer parallax
        layers = [
            (int(50), (20, 50), (1, 2), 0.55),
            (int(25), (60, 110), (2, 3), 0.80),
            (int(10), (140, 220), (3, 4), 1.00),
        ]
        for count, speed_range, size_range, brightness in layers:
            color = tuple(min(255, int(c * brightness)) for c in accent)
            for _ in range(count):
                self.motes.append({
                    "x": random.uniform(0, self.width),
                    "y": random.uniform(0, self.height),
                    "speed": random.uniform(*speed_range),
                    "size": random.randint(*size_range),
                    "color": color,
                })

        # Occasional uncollidable debris silhouettes drifting through the near layer, for depth.
        self.debris = []
        debris_names = [
            "meteor_carbon_tiny_debris_01", "meteor_carbon_tiny_debris_02",
            "meteor_iron_tiny_debris_01", "meteor_iron_tiny_debris_02",
        ]
        for _ in range(5):
            size = random.randint(14, 26)
            img = self.assets.get_image(random.choice(debris_names), size, size).copy()
            img.set_alpha(90)
            self.debris.append({
                "image": img,
                "x": random.uniform(0, self.width),
                "y": random.uniform(0, self.height),
                "speed": random.uniform(15, 35),
                "rotation": random.uniform(0, 360),
                "spin": random.uniform(-12, 12),
            })

    def _build_warp_streaks(self):
        self.warp_streaks = [{
            "x": random.uniform(0, self.width),
            "length": random.uniform(120, 420),
            "width": random.randint(2, 4),
        } for _ in range(40)]

    def start_warp_in(self):
        """Plays the hyperspace streak-in on mission start, then the camera settles."""
        self.warp_direction = "in"
        self.warp_timer = 0.0
        self.warp_duration = self.WARP_IN_DURATION

    def start_warp_out(self):
        """Plays the reverse hyperspace streak-out on mission clear."""
        self.warp_direction = "out"
        self.warp_timer = 0.0
        self.warp_duration = self.WARP_OUT_DURATION

    @property
    def warp_active(self):
        return self.warp_direction is not None

    @property
    def warp_progress(self):
        """0..1 progress through the active warp animation."""
        if self.warp_duration <= 0:
            return 1.0
        return min(1.0, self.warp_timer / self.warp_duration)

    def update(self, dt):
        # Far void drifts slowly; mid nebula wrap-scrolls faster for parallax depth.
        self.far_offset.x = (self.far_offset.x + 6 * dt) % self.TILE
        self.far_offset.y = (self.far_offset.y + 4 * dt) % self.TILE
        self.mid_offset.x = (self.mid_offset.x + 14 * dt) % self.TILE
        self.mid_offset.y = (self.mid_offset.y + 9 * dt) % self.TILE

        for mote in self.motes:
            mote["y"] += mote["speed"] * dt
            if mote["y"] > self.height:
                mote["y"] = 0
                mote["x"] = random.uniform(0, self.width)

        for chunk in self.debris:
            chunk["y"] += chunk["speed"] * dt
            chunk["rotation"] += chunk["spin"] * dt
            if chunk["y"] > self.height + 20:
                chunk["y"] = -20
                chunk["x"] = random.uniform(0, self.width)

        if self.warp_direction is not None:
            self.warp_timer += dt
            if self.warp_timer >= self.warp_duration:
                self.warp_direction = None

    def _draw_tiled(self, surface, image, offset, alpha):
        """Tiles a cached square image across the surface, wrap-scrolled by offset."""
        image.set_alpha(alpha)
        ox = int(offset.x) % self.TILE - self.TILE
        oy = int(offset.y) % self.TILE - self.TILE
        y = oy
        while y < self.height:
            x = ox
            while x < self.width:
                surface.blit(image, (x, y))
                x += self.TILE
            y += self.TILE

    def _draw_far(self, surface):
        img = self.assets.get_image("void_black_stars", self.TILE, self.TILE)
        self._draw_tiled(surface, img, self.far_offset, alpha=180)

    def _draw_mid(self, surface):
        theater = self.theater
        primary = self.assets.get_image(theater["nebula"], self.TILE, self.TILE)
        secondary_key = theater.get("nebula_secondary")

        if secondary_key:
            # Solar Throne finale: crossfade between the two prior nebula colors (magenta/violet pulse).
            pulse = 0.5 + 0.5 * math.sin(pg.time.get_ticks() * 0.0004)
            self._draw_tiled(surface, primary, self.mid_offset, alpha=int(150 * (1 - pulse)))
            secondary = self.assets.get_image(secondary_key, self.TILE, self.TILE)
            self._draw_tiled(surface, secondary, self.mid_offset, alpha=int(150 * pulse))
        else:
            self._draw_tiled(surface, primary, self.mid_offset, alpha=150)
            grade = theater.get("grade")
            if grade:
                color, grade_alpha = grade
                overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
                overlay.fill((*color, grade_alpha))
                surface.blit(overlay, (0, 0))

    def _draw_near(self, surface):
        for mote in self.motes:
            pg.draw.circle(surface, mote["color"], (int(mote["x"]), int(mote["y"])), mote["size"])
        for chunk in self.debris:
            rotated = pg.transform.rotate(chunk["image"], chunk["rotation"])
            rect = rotated.get_rect(center=(int(chunk["x"]), int(chunk["y"])))
            surface.blit(rotated, rect)

    def _draw_warp_overlay(self, surface):
        progress = self.warp_progress
        if self.warp_direction == "in":
            alpha_scale = 1.0 - progress
            stretch = 1.0 - progress
        else:
            alpha_scale = progress
            stretch = progress

        if alpha_scale <= 0.01:
            return

        for streak in self.warp_streaks:
            length = max(20, int(streak["length"] * (0.25 + 0.75 * stretch)))
            img = self.assets.get_image("hyperspace_warp_lines", streak["width"], length)
            img.set_alpha(int(220 * alpha_scale))
            y = self.height / 2 - length / 2
            surface.blit(img, (streak["x"], y))

    def draw(self, surface):
        self._draw_far(surface)
        self._draw_mid(surface)
        self._draw_near(surface)
        if self.warp_direction is not None:
            self._draw_warp_overlay(surface)
