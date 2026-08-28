# pyrefly: ignore [missing-import]
import pygame as pg


class UITooltipManager:
    """
    Sprint 12 / Pillar 3 — Centralized Floating Tooltip Manager.

    Provides context-aware help text cards across Hangar, Shop, Options, and Level Select:
    - Renders dark glassmorphism cards with glowing cyan borders.
    - Smooth alpha fade-in / fade-out animations.
    - Automatic screen boundary clamping so tooltips never overflow off-screen.
    """

    def __init__(self, font, title_font=None, screen_width=1280, screen_height=720):
        self.font = font
        self.title_font = title_font or font
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.title = ""
        self.body = ""
        self.pos = (0, 0)
        self.active = False
        self.alpha = 0.0
        self.target_alpha = 0.0
        self.fade_speed = 1200.0  # Alpha points per second

    def set_tooltip(self, title, body, pos):
        """Sets active tooltip content and target position."""
        if title or body:
            self.title = title or ""
            self.body = body or ""
            self.pos = pos
            self.active = True
            self.target_alpha = 240.0
        else:
            self.clear()

    def clear(self):
        """Clears active tooltip and triggers fade out."""
        self.active = False
        self.target_alpha = 0.0

    def update(self, dt):
        """Updates alpha fade transitions."""
        if self.alpha < self.target_alpha:
            self.alpha = min(self.target_alpha, self.alpha + self.fade_speed * dt)
        elif self.alpha > self.target_alpha:
            self.alpha = max(self.target_alpha, self.alpha - self.fade_speed * dt)

    def draw(self, surface):
        """Renders tooltip card if alpha > 0."""
        if self.alpha <= 5.0 or not (self.title or self.body):
            return

        curr_alpha = int(self.alpha)

        # Render text surfaces
        title_surf = self.title_font.render(self.title, True, (0, 255, 220)) if self.title else None
        
        # Word-wrap body text if needed
        body_surfs = []
        if self.body:
            words = self.body.split(" ")
            line = ""
            max_line_w = 260
            for word in words:
                test_line = line + (" " if line else "") + word
                if self.font.size(test_line)[0] > max_line_w and line:
                    body_surfs.append(self.font.render(line, True, (200, 230, 250)))
                    line = word
                else:
                    line = test_line
            if line:
                body_surfs.append(self.font.render(line, True, (200, 230, 250)))

        # Calculate dimensions
        padding = 12
        line_spacing = 4
        
        width = max(
            (title_surf.get_width() if title_surf else 0),
            max((s.get_width() for s in body_surfs), default=0)
        ) + padding * 2
        
        height = padding * 2
        if title_surf:
            height += title_surf.get_height() + (line_spacing if body_surfs else 0)
        for s in body_surfs:
            height += s.get_height() + line_spacing
        if body_surfs:
            height -= line_spacing  # Remove trailing spacing

        # Position clamping
        px, py = self.pos
        tx = px + 18
        ty = py + 18
        if tx + width > self.screen_width - 15:
            tx = px - width - 12
        if ty + height > self.screen_height - 15:
            ty = py - height - 12
        tx = max(15, tx)
        ty = max(15, ty)

        # Draw card panel
        panel = pg.Surface((width, height), pg.SRCALPHA)
        panel.fill((12, 18, 32, int(curr_alpha * 0.92)))
        pg.draw.rect(panel, (0, 220, 255, curr_alpha), panel.get_rect(), 2, border_radius=8)
        pg.draw.rect(panel, (0, 140, 180, int(curr_alpha * 0.4)), panel.get_rect().inflate(-4, -4), 1, border_radius=6)
        surface.blit(panel, (tx, ty))

        # Blit text
        curr_y = ty + padding
        if title_surf:
            t_copy = title_surf.copy()
            t_copy.set_alpha(curr_alpha)
            surface.blit(t_copy, (tx + padding, curr_y))
            curr_y += title_surf.get_height() + line_spacing

        for b_surf in body_surfs:
            b_copy = b_surf.copy()
            b_copy.set_alpha(curr_alpha)
            surface.blit(b_copy, (tx + padding, curr_y))
            curr_y += b_surf.get_height() + line_spacing
