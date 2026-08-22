# pyrefly: ignore [missing-import]
import pygame as pg


class RenderPipeline:
    """
    Sprint 11 / Pillar D — Unified 2D Render Pipeline & Post-Processing Stack.
    
    Draws to an offscreen world canvas, then processes:
    - Camera transform (shake, offset, zoom)
    - Additive Bloom (quarter-res downsample -> blur -> additive blend)
    - Damage & Shield Vignette
    - Dynamic Chromatic Aberration (R/B split on heavy impacts)
    - Cinematic Letterbox bars
    - Hyperspace Speed Lines
    - Clean presentation to screen buffer
    """

    def __init__(self, width=1280, height=720, assets=None):
        self.width = width
        self.height = height
        self.assets = assets

        # Offscreen canvas
        self.world_canvas = pg.Surface((width, height))

        # Quarter-resolution bloom surface for fast high-performance glow
        self.bloom_w = width // 4
        self.bloom_h = height // 4
        self.bloom_buffer = pg.Surface((self.bloom_w, self.bloom_h))

        # Pre-baked vignette surfaces for high FPS rendering
        self._vignette_red = self._create_vignette((220, 20, 20))
        self._vignette_cyan = self._create_vignette((20, 180, 240))

        # Letterbox animation
        self.letterbox_target = 0.0
        self.letterbox_height = 0.0
        self.LETTERBOX_MAX = 28.0

        # Quality settings
        self.quality = "high"  # "high" or "low"
        self.bloom_enabled = True
        self.vignette_enabled = True
        self.chromatic_enabled = True
        self.letterbox_enabled = True

    def _create_vignette(self, color):
        """Creates a smooth radial border gradient surface."""
        surf = pg.Surface((self.width, self.height), pg.SRCALPHA)
        # Draw outer borders with smooth gradient steps
        steps = 18
        for i in range(steps):
            alpha = int(140 * ((steps - i) / steps) ** 1.8)
            border_rect = pg.Rect(i * 3, i * 2, self.width - i * 6, self.height - i * 4)
            pg.draw.rect(surf, (*color, alpha), border_rect, width=3)
        return surf

    def set_letterbox(self, enabled=True):
        """Toggles cinematic letterbox bars."""
        self.letterbox_target = self.LETTERBOX_MAX if enabled else 0.0

    def update(self, dt):
        """Updates animated post-effects like letterbox transitions."""
        if abs(self.letterbox_height - self.letterbox_target) > 0.1:
            diff = self.letterbox_target - self.letterbox_height
            self.letterbox_height += diff * min(1.0, 8.0 * dt)
        else:
            self.letterbox_height = self.letterbox_target

    def apply_bloom(self, source_surf):
        """Performs fast additive bloom by quarter-res downsampling and upscaling."""
        if not self.bloom_enabled or self.quality == "low":
            return

        # 1. Downscale onto quarter-res buffer (acts as a low-pass filter)
        pg.transform.smoothscale(source_surf, (self.bloom_w, self.bloom_h), self.bloom_buffer)
        # 2. Upscale back smoothly and additively blend
        upscaled_bloom = pg.transform.smoothscale(self.bloom_buffer, (self.width, self.height))
        upscaled_bloom.set_alpha(110)
        source_surf.blit(upscaled_bloom, (0, 0), special_flags=pg.BLEND_ADD)

    def apply_chromatic_aberration(self, source_surf, target_surf, intensity=2):
        """Applies a subtle 1-2px red/blue horizontal split during heavy impact frames."""
        if not self.chromatic_enabled or intensity <= 0 or self.quality == "low":
            target_surf.blit(source_surf, (0, 0))
            return

        # Red channel shifted left, blue channel shifted right
        r_surf = source_surf.copy()
        r_surf.fill((255, 0, 0), special_flags=pg.BLEND_MULT)
        r_surf.set_alpha(160)

        b_surf = source_surf.copy()
        b_surf.fill((0, 160, 255), special_flags=pg.BLEND_MULT)
        b_surf.set_alpha(160)

        target_surf.blit(source_surf, (0, 0))
        target_surf.blit(r_surf, (-intensity, 0), special_flags=pg.BLEND_ADD)
        target_surf.blit(b_surf, (intensity, 0), special_flags=pg.BLEND_ADD)

    def draw_vignette(self, target_surf, health_ratio=1.0, shield_active=False):
        """Draws reactive damage edge glow and shield ring."""
        if not self.vignette_enabled:
            return

        # Red damage vignette when hull is damaged
        if health_ratio < 0.75:
            damage_factor = (0.75 - max(0.0, health_ratio)) / 0.75
            alpha = int(220 * (damage_factor ** 1.3))
            if alpha > 5:
                overlay = self._vignette_red.copy()
                overlay.set_alpha(alpha)
                target_surf.blit(overlay, (0, 0))

        # Cyan shield edge pulse when active
        if shield_active:
            overlay = self._vignette_cyan.copy()
            overlay.set_alpha(65)
            target_surf.blit(overlay, (0, 0), special_flags=pg.BLEND_ADD)

    def draw_letterbox(self, target_surf):
        """Renders top and bottom cinematic black bars."""
        h = int(self.letterbox_height)
        if h > 0:
            pg.draw.rect(target_surf, (0, 0, 0), (0, 0, self.width, h))
            pg.draw.rect(target_surf, (0, 0, 0), (0, self.height - h, self.width, h))

    def draw_speed_lines(self, target_surf, alpha=90):
        """Draws subtle speed lines across screen when speed boost is engaged."""
        if self.assets:
            lines_img = self.assets.get_image("speed_trails/hyperspace_warp_lines", self.width, self.height)
            if lines_img:
                lines = lines_img.copy()
                lines.set_alpha(alpha)
                target_surf.blit(lines, (0, 0), special_flags=pg.BLEND_ADD)

    def present(self, screen, camera=None, health_ratio=1.0, shield_active=False, speed_boost=False, is_boss_alert=False):
        """
        Final composite pass: Takes the world canvas, applies post-processing,
        transforms by camera zoom & shake offset, and blits to the destination screen.
        """
        # 1. Additive bloom on world canvas
        if self.bloom_enabled and self.quality != "low":
            self.apply_bloom(self.world_canvas)

        # 2. Camera zoom & offset
        offset_x, offset_y = (0, 0)
        zoom = 1.0
        shake_mag = 0.0

        if camera:
            offset_x, offset_y = camera.total_offset
            zoom = camera.zoom
            shake_mag = camera.shake_magnitude

        if abs(zoom - 1.0) > 0.005:
            new_w = int(self.width * zoom)
            new_h = int(self.height * zoom)
            scaled = pg.transform.smoothscale(self.world_canvas, (new_w, new_h))
            crop_x = (new_w - self.width) // 2
            crop_y = (new_h - self.height) // 2
            transformed = scaled.subsurface(pg.Rect(crop_x, crop_y, self.width, self.height))
        else:
            transformed = self.world_canvas

        # 3. Chromatic aberration during heavy shake or boss alert
        chroma_intensity = 0
        if is_boss_alert:
            chroma_intensity = 2
        elif shake_mag > 4.0:
            chroma_intensity = 1

        if chroma_intensity > 0:
            temp_surf = pg.Surface((self.width, self.height))
            self.apply_chromatic_aberration(transformed, temp_surf, intensity=chroma_intensity)
            screen.blit(temp_surf, (int(offset_x), int(offset_y)))
        else:
            screen.blit(transformed, (int(offset_x), int(offset_y)))

        # 4. Damage / shield vignette
        self.draw_vignette(screen, health_ratio=health_ratio, shield_active=shield_active)

        # 5. Speed lines if speed boost
        if speed_boost:
            self.draw_speed_lines(screen, alpha=85)

        # 6. Letterbox on top of everything
        self.draw_letterbox(screen)
