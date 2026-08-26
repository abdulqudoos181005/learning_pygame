# pyrefly: ignore [missing-import]
import pygame as pg


class StateTransition:
    """
    Sprint 11 / Pillar H — Cinematic State Transition Overlay.

    Manages seamless transitions between game states:
    - Types: 'fade' (220ms), 'iris' (260ms), 'warp' (280ms)
    - Draws transition overlay directly on top of the rendered frame
    - Prevents double-firing of state switches
    """

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.active = False
        self.transition_type = "fade"
        self.duration = 0.22
        self.timer = 0.0
        self.halfway_executed = False
        self.next_state_factory = None
        self.on_midpoint_callback = None

    def start(self, next_state_factory, transition_type="fade", duration=0.22, on_midpoint=None):
        """Starts a new cinematic state transition."""
        self.active = True
        self.transition_type = transition_type
        self.duration = max(0.08, duration)
        self.timer = 0.0
        self.halfway_executed = False
        self.next_state_factory = next_state_factory
        self.on_midpoint_callback = on_midpoint

    def update(self, dt, game):
        """Updates the transition timer and triggers the state swap at the midpoint."""
        if not self.active:
            return

        self.timer += dt
        halfway = self.duration * 0.5

        if self.timer >= halfway and not self.halfway_executed:
            self.halfway_executed = True
            if callable(self.next_state_factory):
                new_state = self.next_state_factory()
                game.state = new_state
            elif self.next_state_factory is not None:
                game.state = self.next_state_factory

            if callable(self.on_midpoint_callback):
                self.on_midpoint_callback()

        if self.timer >= self.duration:
            self.active = False
            self.next_state_factory = None
            self.on_midpoint_callback = None

    def draw(self, screen):
        """Draws the transition overlay to screen."""
        if not self.active:
            return

        halfway = self.duration * 0.5
        progress = self.timer / self.duration

        # Fade Transition
        if self.transition_type == "fade":
            if self.timer < halfway:
                alpha = int(255 * (self.timer / halfway))
            else:
                alpha = int(255 * (1.0 - (self.timer - halfway) / halfway))
            fade_surf = pg.Surface((self.width, self.height), pg.SRCALPHA)
            fade_surf.fill((8, 10, 18, min(255, max(0, alpha))))
            screen.blit(fade_surf, (0, 0))

        # Iris Circle Transition
        elif self.transition_type == "iris":
            max_radius = int(((self.width // 2) ** 2 + (self.height // 2) ** 2) ** 0.5) + 20
            if self.timer < halfway:
                radius = int(max_radius * (1.0 - (self.timer / halfway)))
            else:
                radius = int(max_radius * ((self.timer - halfway) / halfway))
            radius = max(0, radius)

            iris_surf = pg.Surface((self.width, self.height), pg.SRCALPHA)
            iris_surf.fill((8, 10, 18, 255))
            if radius > 0:
                pg.draw.circle(iris_surf, (0, 0, 0, 0), (self.width // 2, self.height // 2), radius)
                # Cyan rim on iris edge
                pg.draw.circle(iris_surf, (0, 240, 255, 180), (self.width // 2, self.height // 2), radius, width=2)
            screen.blit(iris_surf, (0, 0))

        # Warp / Flash Transition
        elif self.transition_type == "warp":
            if self.timer < halfway:
                alpha = int(220 * (self.timer / halfway))
                color = (0, 200, 255, min(255, max(0, alpha)))
            else:
                alpha = int(255 * (1.0 - (self.timer - halfway) / halfway))
                color = (255, 255, 255, min(255, max(0, alpha)))
            warp_surf = pg.Surface((self.width, self.height), pg.SRCALPHA)
            warp_surf.fill(color)
            screen.blit(warp_surf, (0, 0))
