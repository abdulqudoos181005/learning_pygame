# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg

try:
    from fx import spawn_sparks, spawn_explosion
except ModuleNotFoundError:
    from ..fx import spawn_sparks, spawn_explosion

from level_system import armada_image_key


class PhasePhantom(pg.sprite.Sprite):
    """
    Phase Phantom — Stealth Interceptor.
    
    Features optical cloaking (fades to 15% opacity and cannot be auto-targeted
    by missiles). Glides into ambush position beside/behind the player, decloaks
    suddenly to deliver a rapid shotgun volley, then recloaks and repositions.
    """

    STATE_STALKING = "stalking"
    STATE_DECLOAKING = "decloaking"
    STATE_ATTACKING = "attacking"
    STATE_RECLOAKING = "recloaking"

    def __init__(self, game, x, y, hp_mult=1.0, spd_mult=1.0, armada_folder=None, laser_key=None):
        super().__init__()
        self.game = game
        self.armada_folder = armada_folder
        self.laser_key = laser_key or "laser_green_beam_stream_long"
        self.type = "phase_phantom"

        sprite_key = armada_image_key(armada_folder, "phase_phantom") if armada_folder else "enemy_scout"
        self.raw_image = self.game.assets.get_image(sprite_key, 46, 46)
        self.image = self.raw_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

        # Stats
        self.hp_mult = hp_mult
        self.spd_mult = spd_mult
        self.max_health = int(45 * hp_mult)
        self.health = self.max_health
        self.score_value = 500

        # Cloaking & Optical properties
        self.is_cloaked = True
        self.current_alpha = 38.0  # ~15% opacity
        self.target_alpha = 38.0
        self.image.set_alpha(int(self.current_alpha))

        # Ambush coordinates & state
        self.state = self.STATE_STALKING
        self.state_timer = random.uniform(2.0, 3.2)
        self.speed = 180.0 * spd_mult
        self.target_pos = pg.Vector2(x, y)
        self._pick_ambush_target()

    def _get_player_pos(self):
        state = self.game.state
        if hasattr(state, "player") and state.player and hasattr(state.player, "rect"):
            return pg.Vector2(state.player.rect.centerx, state.player.rect.centery)
        return pg.Vector2(self.game.width // 2, self.game.height - 80)

    def _pick_ambush_target(self):
        player_pos = self._get_player_pos()
        offset_x = random.choice([-160, -120, 120, 160])
        offset_y = random.choice([-100, -70, 40])
        target_x = max(60, min(self.game.width - 60, player_pos.x + offset_x))
        target_y = max(60, min(self.game.height - 120, player_pos.y + offset_y))
        self.target_pos = pg.Vector2(target_x, target_y)

    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.kill()
            return True
        return False

    def update(self, dt):
        player_pos = self._get_player_pos()

        # Smooth alpha interpolation
        if self.current_alpha != self.target_alpha:
            step = 600.0 * dt
            if self.current_alpha < self.target_alpha:
                self.current_alpha = min(self.target_alpha, self.current_alpha + step)
            else:
                self.current_alpha = max(self.target_alpha, self.current_alpha - step)
            self.image.set_alpha(int(self.current_alpha))

        self.state_timer -= dt

        # State machine
        if self.state == self.STATE_STALKING:
            # Stealthily glide towards ambush flank position
            to_target = self.target_pos - pg.Vector2(self.rect.center)
            dist = to_target.length()
            if dist > 8:
                to_target.normalize_ip()
                move = to_target * self.speed * dt
                self.rect.x += int(move.x)
                self.rect.y += int(move.y)

            if self.state_timer <= 0:
                self.state = self.STATE_DECLOAKING
                self.target_alpha = 255.0
                self.state_timer = 0.25

        elif self.state == self.STATE_DECLOAKING:
            if self.state_timer <= 0:
                self.is_cloaked = False
                self.state = self.STATE_ATTACKING
                self.state_timer = 1.2  # Vulnerability window
                self._fire_shotgun_burst()

                # Phase decloak visual & audio
                if hasattr(self.game.state, "particles"):
                    spawn_sparks(
                        self.game.state.particles,
                        self.rect.centerx,
                        self.rect.centery,
                        direction=(0, 0),
                        color=(200, 60, 255),
                        count=16,
                    )
                if hasattr(self.game, "audio") and self.game.audio:
                    self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.7)

        elif self.state == self.STATE_ATTACKING:
            # Slight drift while firing / exposed
            self.rect.y += int(30 * dt)
            if self.state_timer <= 0:
                self.state = self.STATE_RECLOAKING
                self.target_alpha = 38.0
                self.is_cloaked = True
                self.state_timer = 0.3

        elif self.state == self.STATE_RECLOAKING:
            if self.state_timer <= 0:
                self.state = self.STATE_STALKING
                self.state_timer = random.uniform(2.2, 3.5)
                self._pick_ambush_target()

        # Offscreen bounds protection
        if self.rect.top > self.game.height + 20:
            self.rect.top = -40
            self._pick_ambush_target()

    def _fire_shotgun_burst(self):
        state = self.game.state
        if not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser
        # Fire 5 spread lasers towards player
        angles = [-24, -12, 0, 12, 24]
        for ang in angles:
            laser = Laser(
                self.game,
                self.rect.centerx,
                self.rect.centery,
                speed_y=360,
                angle=ang,
                damage=12,
                img_name=self.laser_key,
            )
            state.enemy_lasers.add(laser)
            state.all_sprites.add(laser)

    def draw_extras(self, surface):
        """Draws a subtle purple phase shimmer when cloaked."""
        if self.is_cloaked and self.current_alpha <= 60:
            shimmer_radius = self.rect.width // 2 + 4
            shimmer = pg.Surface((shimmer_radius * 2, shimmer_radius * 2), pg.SRCALPHA)
            pg.draw.circle(shimmer, (180, 70, 255, 30), (shimmer_radius, shimmer_radius), shimmer_radius, 2)
            surface.blit(
                shimmer,
                (self.rect.centerx - shimmer_radius, self.rect.centery - shimmer_radius),
                special_flags=pg.BLEND_ADD,
            )
