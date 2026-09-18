# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg

try:
    from vfx.telegraph import LaserSightline
    from fx import spawn_sparks, spawn_explosion
except ModuleNotFoundError:
    from ..vfx.telegraph import LaserSightline
    from ..fx import spawn_sparks, spawn_explosion

from level_system import armada_image_key


class RailgunSlug(pg.sprite.Sprite):
    """
    Ultra-fast high-damage railgun projectile fired by Sniper Skiffs.
    Speeds at ~950 px/s and deals 30 damage on hit.
    """

    def __init__(self, game, x, y, target_x, target_y, damage=30, img_name="laser_red_beam_stream_long"):
        super().__init__()
        self.game = game
        self.damage = damage
        self.fx = float(x)
        self.fy = float(y)
        self.speed = 950.0
        self.trail = []

        # Direction vector towards target
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy)
        if dist > 0.001:
            self.dir_x = dx / dist
            self.dir_y = dy / dist
        else:
            self.dir_x = 0.0
            self.dir_y = 1.0

        self.angle_deg = math.degrees(math.atan2(-self.dir_y, self.dir_x)) - 90.0

        # Load and rotate beam asset
        base_img = self.game.assets.get_image(img_name, 12, 36)
        self.image = pg.transform.rotate(base_img, self.angle_deg)
        self.rect = self.image.get_rect(center=(int(self.fx), int(self.fy)))

    def update(self, dt):
        self.trail.append((self.fx, self.fy))
        if len(self.trail) > 8:
            self.trail.pop(0)

        self.fx += self.dir_x * self.speed * dt
        self.fy += self.dir_y * self.speed * dt
        self.rect.center = (int(self.fx), int(self.fy))

        if (
            self.rect.bottom < -20
            or self.rect.top > self.game.height + 20
            or self.rect.right < -20
            or self.rect.left > self.game.width + 20
        ):
            self.kill()

    def draw_trail(self, surface):
        if len(self.trail) < 2:
            return
        for idx in range(1, len(self.trail)):
            alpha = int(40 + idx * 25)
            color = (255, 60, 60, alpha)
            pos_a = (round(self.trail[idx - 1][0]), round(self.trail[idx - 1][1]))
            pos_b = (round(self.trail[idx][0]), round(self.trail[idx][1]))
            pg.draw.line(surface, color, pos_a, pos_b, 3)


class SniperSkiff(pg.sprite.Sprite):
    """
    Sniper Skiff — Long-Range Railgun.
    
    Stays at the top perimeter, aims a visible targeting laser at the player
    for 1.2s, locks trajectory, then discharges an ultra-fast high-damage railgun slug.
    """

    STATE_ENTERING = "entering"
    STATE_PATROL = "patrol"
    STATE_AIMING = "aiming"

    def __init__(self, game, x, y, hp_mult=1.0, spd_mult=1.0, armada_folder=None, laser_key=None):
        super().__init__()
        self.game = game
        self.armada_folder = armada_folder
        self.laser_key = laser_key or "laser_red_beam_stream_long"
        self.type = "sniper_skiff"

        sprite_key = armada_image_key(armada_folder, "sniper_skiff") if armada_folder else "enemy_stinger"
        self.raw_image = self.game.assets.get_image(sprite_key, 48, 48)
        self.image = self.raw_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

        # Stats
        self.hp_mult = hp_mult
        self.spd_mult = spd_mult
        self.max_health = int(35 * hp_mult)
        self.health = self.max_health
        self.score_value = 450

        # Movement: descends to top perimeter then stops vertical movement
        self.target_y = random.randint(70, 115)
        self.speed_y = 120.0 * spd_mult
        self.speed_x = random.choice([-70.0, 70.0]) * spd_mult
        self.state = self.STATE_ENTERING

        # Sniping & Telegraph variables
        self.patrol_timer = random.uniform(1.2, 2.0)
        self.sightline = None
        self.locked_target_pos = (x, self.game.height - 80)

    def _get_player_pos(self):
        state = self.game.state
        if hasattr(state, "player") and state.player and hasattr(state.player, "rect"):
            return (state.player.rect.centerx, state.player.rect.centery)
        return (self.rect.centerx, self.game.height - 80)

    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            if self.sightline:
                self.sightline.state = LaserSightline.STATE_FINISHED
                self.sightline = None
            self.kill()
            return True
        return False

    def update(self, dt):
        # 1. State machine for movement & aiming
        if self.state == self.STATE_ENTERING:
            self.rect.y += int(self.speed_y * dt)
            if self.rect.centery >= self.target_y:
                self.rect.centery = self.target_y
                self.speed_y = 0.0
                self.state = self.STATE_PATROL
        elif self.state == self.STATE_PATROL:
            # Patrol horizontally along top edge
            self.rect.x += int(self.speed_x * dt)
            if self.rect.left < 50:
                self.rect.left = 50
                self.speed_x = abs(self.speed_x)
            elif self.rect.right > self.game.width - 50:
                self.rect.right = self.game.width - 50
                self.speed_x = -abs(self.speed_x)

            self.patrol_timer -= dt
            if self.patrol_timer <= 0:
                self._start_aiming()

        elif self.state == self.STATE_AIMING:
            # Slow down horizontal speed while aiming
            self.rect.x += int(self.speed_x * 0.25 * dt)
            if self.rect.left < 50:
                self.rect.left = 50
                self.speed_x = abs(self.speed_x)
            elif self.rect.right > self.game.width - 50:
                self.rect.right = self.game.width - 50
                self.speed_x = -abs(self.speed_x)

            if self.sightline:
                self.sightline.update(dt)
                if self.sightline.is_locked:
                    self.locked_target_pos = (self.sightline.locked_end_pos.x, self.sightline.locked_end_pos.y)
                if self.sightline.is_finished:
                    self.sightline = None
                    self.state = self.STATE_PATROL
                    self.patrol_timer = random.uniform(1.8, 2.6)

    def _start_aiming(self):
        self.state = self.STATE_AIMING
        self.sightline = LaserSightline(
            start_provider=(lambda: (self.rect.centerx, self.rect.bottom)),
            target_provider=(lambda: self._get_player_pos()),
            aim_duration=1.2,
            lock_duration=0.25,
            fire_duration=0.2,
            beam_width=14,
            damage=30,
            beam_color=(255, 40, 40),
            core_color=(255, 220, 220),
            on_fire_callback=self._fire_railgun,
        )
        # Register in TelegraphManager if available
        state = self.game.state
        if hasattr(state, "telegraphs") and state.telegraphs:
            state.telegraphs.sightlines.append(self.sightline)

    def _fire_railgun(self, sightline):
        state = self.game.state
        if not hasattr(state, "enemy_lasers"):
            return

        tx, ty = self.locked_target_pos
        slug = RailgunSlug(
            self.game,
            self.rect.centerx,
            self.rect.bottom,
            tx,
            ty,
            damage=30,
            img_name=self.laser_key,
        )
        state.enemy_lasers.add(slug)
        state.all_sprites.add(slug)

        if hasattr(self.game, "audio") and self.game.audio:
            self.game.audio.play_sfx("zap", pos_x=self.rect.centerx, volume_mult=0.9)
        elif hasattr(self.game.assets, "get_sound"):
            self.game.assets.get_sound("zap").play()

    def draw_extras(self, surface):
        """Renders the targeting sightline if not managed globally."""
        state = self.game.state
        if not (hasattr(state, "telegraphs") and state.telegraphs):
            if self.sightline and not self.sightline.is_finished:
                self.sightline.draw(surface)
