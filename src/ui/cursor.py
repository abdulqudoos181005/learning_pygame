# pyrefly: ignore [missing-import]
import math
import pygame as pg


class SoftwareCursor:
    """
    Sprint 11 / Pillar F — Tactical Software Reticle.

    Replaces standard OS mouse arrow with a crisp tactical crosshair:
    - Reticle asset: 'ui_hud/reticle_cursor/crosshair_tactical_cursor'
    - Smooth slight lerp in combat for dynamic aimed feel
    - Hides OS hardware cursor while window is focused
    """

    def __init__(self, assets, width=1280, height=720):
        self.assets = assets
        self.width = width
        self.height = height
        self.pos = pg.Vector2(width // 2, height // 2)
        self.target_pos = pg.Vector2(width // 2, height // 2)
        self.cursor_img = assets.get_image("ui_hud/reticle_cursor/crosshair_tactical_cursor", 32, 32)
        self.visible = True

        # Hide hardware OS cursor
        try:
            pg.mouse.set_visible(False)
        except Exception:
            pass

    def update(self, dt, lerp_aim=False):
        """Updates software cursor position with optional slight aiming lerp."""
        raw_x, raw_y = pg.mouse.get_pos()
        self.target_pos.update(raw_x, raw_y)

        if lerp_aim:
            # Smooth aim lerp for tactical weapon feel
            diff = self.target_pos - self.pos
            self.pos += diff * min(1.0, 24.0 * dt)
        else:
            self.pos.update(self.target_pos)

    def draw(self, surface):
        """Renders the crosshair software cursor."""
        if not self.visible:
            return
        if self.cursor_img:
            rect = self.cursor_img.get_rect(center=(round(self.pos.x), round(self.pos.y)))
            surface.blit(self.cursor_img, rect)
        else:
            # Vector fallback reticle
            cx, cy = round(self.pos.x), round(self.pos.y)
            pg.draw.circle(surface, (0, 240, 255), (cx, cy), 10, width=1)
            pg.draw.line(surface, (0, 240, 255), (cx - 14, cy), (cx + 14, cy), width=1)
            pg.draw.line(surface, (0, 240, 255), (cx, cy - 14), (cx, cy + 14), width=1)
