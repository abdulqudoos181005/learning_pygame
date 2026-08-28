# pyrefly: ignore [missing-import]
import math
import pygame as pg


class SoftwareCursor:
    """
    Sprint 11 & 12 — Context-Aware Tactical Software Reticle.

    Replaces standard OS mouse arrow with a crisp tactical crosshair:
    - Reticle asset: 'ui_hud/reticle_cursor/crosshair_tactical_cursor'
    - Smooth slight lerp in combat for dynamic aimed feel
    - Interactive hover expansion (1.0 -> 1.3x scale) & glow pulse over UI controls
    - Snaps softly to active keyboard/gamepad focus targets
    - Hides OS hardware cursor while window is focused
    """

    def __init__(self, assets, width=1280, height=720):
        self.assets = assets
        self.width = width
        self.height = height
        self.pos = pg.Vector2(width // 2, height // 2)
        self.target_pos = pg.Vector2(width // 2, height // 2)
        self.base_cursor_img = assets.get_image("ui_hud/reticle_cursor/crosshair_tactical_cursor", 32, 32)
        self.visible = True
        
        self.hovered_control = False
        self.hover_scale = 1.0
        self.anim_timer = 0.0

        # Hide hardware OS cursor
        try:
            pg.mouse.set_visible(False)
        except Exception:
            pass

    def snap_to(self, x, y):
        """Snaps software cursor position to a keyboard/gamepad focused control."""
        self.target_pos.update(x, y)

    def set_hover_state(self, is_hovered):
        """Sets whether cursor is currently hovering an interactive element."""
        self.hovered_control = is_hovered

    def update(self, dt, lerp_aim=False):
        """Updates software cursor position and dynamic hover scale."""
        self.anim_timer += dt
        
        if not self.hovered_control:
            raw_x, raw_y = pg.mouse.get_pos()
            self.target_pos.update(raw_x, raw_y)

        # Smooth scale interpolation
        target_scale = 1.28 if self.hovered_control else 1.0
        self.hover_scale += (target_scale - self.hover_scale) * min(1.0, 16.0 * dt)

        if lerp_aim:
            # Smooth aim lerp for tactical weapon feel
            diff = self.target_pos - self.pos
            self.pos += diff * min(1.0, 24.0 * dt)
        else:
            diff = self.target_pos - self.pos
            if diff.length_squared() > 1.0:
                self.pos += diff * min(1.0, 20.0 * dt)
            else:
                self.pos.update(self.target_pos)

    def draw(self, surface):
        """Renders the crosshair software cursor."""
        if not self.visible:
            return
        
        cx, cy = round(self.pos.x), round(self.pos.y)
        pulse = 1.0 + 0.08 * math.sin(self.anim_timer * 10.0) if self.hovered_control else 1.0
        final_scale = self.hover_scale * pulse

        if self.base_cursor_img:
            size = max(16, int(32 * final_scale))
            scaled_img = pg.transform.smoothscale(self.base_cursor_img, (size, size)) if size != 32 else self.base_cursor_img
            rect = scaled_img.get_rect(center=(cx, cy))
            surface.blit(scaled_img, rect)
            if self.hovered_control:
                # Add cyan glow circle behind cursor when hovering UI controls
                pg.draw.circle(surface, (0, 255, 220), (cx, cy), int(16 * final_scale), 1)
        else:
            # Vector fallback reticle
            color = (0, 255, 220) if self.hovered_control else (0, 240, 255)
            rad = int(10 * final_scale)
            pg.draw.circle(surface, color, (cx, cy), rad, width=1)
            pg.draw.line(surface, color, (cx - rad - 4, cy), (cx + rad + 4, cy), width=1)
            pg.draw.line(surface, color, (cx, cy - rad - 4), (cx, cy + rad + 4), width=1)

