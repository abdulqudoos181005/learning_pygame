# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg
try:
    from fx import spawn_sparks, spawn_explosion
except ModuleNotFoundError:
    from ..fx import spawn_sparks, spawn_explosion



class OrbitalShieldBit(pg.sprite.Sprite):
    """
    Rotating energy shield drone orbiting the Goliath Dreadnought during Phase 2.
    Deflects front player projectiles until bypassed or destroyed.
    """

    def __init__(self, game, boss, initial_angle=0.0, radius=125, orbit_speed=1.6):
        super().__init__()
        self.game = game
        self.boss = boss
        self.angle = initial_angle
        self.radius = radius
        self.orbit_speed = orbit_speed

        self.max_health = 120
        self.health = self.max_health
        self.score_value = 800

        self.image = pg.Surface((44, 44), pg.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.boss.rect.centerx), int(self.boss.rect.centery)))
        self._render_drone_surface()

    def _render_drone_surface(self):
        self.image.fill((0, 0, 0, 0))
        # Core generator pod
        pg.draw.circle(self.image, (40, 70, 110), (22, 22), 12)
        pg.draw.circle(self.image, (80, 200, 255), (22, 22), 8)
        pg.draw.circle(self.image, (220, 255, 255), (22, 22), 4)
        # Energy barrier arc
        pg.draw.circle(self.image, (0, 240, 255, 200), (22, 22), 18, 2)

    def update(self, dt):
        if not self.boss.alive():
            self.kill()
            return

        self.angle += self.orbit_speed * dt
        cx = self.boss.rect.centerx + self.radius * math.cos(self.angle)
        cy = self.boss.rect.centery + self.radius * 0.75 * math.sin(self.angle)
        self.rect.center = (int(cx), int(cy))

    def get_hit(self, damage):
        self.health -= damage
        state = getattr(self.game, "state", None)
        if state and hasattr(state, "particles"):
            spawn_sparks(state.particles, self.rect.centerx, self.rect.centery, (0, 1), color=(0, 220, 255), count=10)
        
        if self.health <= 0:
            if state and hasattr(state, "particles"):
                spawn_explosion(state.particles, self.rect.centerx, self.rect.centery, color=(0, 200, 255), count=20)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("zap", pos_x=self.rect.centerx, volume_mult=0.7)
            self.kill()
            return True
        return False

    def draw_shield_arc(self, surface):
        if not self.alive():
            return
        # Pulsing shield bubble
        pulse = int(120 + 70 * math.sin(pg.time.get_ticks() * 0.02 + self.angle))
        sh_surf = pg.Surface((56, 56), pg.SRCALPHA)
        pg.draw.circle(sh_surf, (0, 220, 255, pulse), (28, 28), 24, 2)
        surface.blit(sh_surf, (self.rect.centerx - 28, self.rect.centery - 28), special_flags=pg.BLEND_ADD)


class EscortDrone(pg.sprite.Sprite):
    """
    Agile support escort drone deployed by Apex Void Leviathan during Phase 1.
    """

    def __init__(self, game, boss, side_offset=-140):
        super().__init__()
        self.game = game
        self.boss = boss
        self.side_offset = side_offset
        self.max_health = 90
        self.health = self.max_health
        self.score_value = 600

        self.image = self.game.assets.get_image("enemy_stinger", 36, 36)
        self.rect = self.image.get_rect(center=(self.boss.rect.centerx + self.side_offset, self.boss.rect.centery + 40))
        self.shoot_timer = random.uniform(1.0, 2.0)
        self.hover_timer = random.uniform(0, math.pi * 2)

    def update(self, dt):
        if not self.boss.alive():
            self.kill()
            return

        self.hover_timer += dt * 2.5
        target_x = self.boss.rect.centerx + self.side_offset + math.sin(self.hover_timer) * 25
        target_y = self.boss.rect.centery + 45 + math.cos(self.hover_timer * 1.5) * 15
        self.rect.center = (int(target_x), int(target_y))

        # Shooting
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot()
            self.shoot_timer = random.uniform(1.8, 2.8)

    def shoot(self):
        state = getattr(self.game, "state", None)
        if not state or not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser
        laser = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=360, damage=12, img_name="laser_enemy")
        state.enemy_lasers.add(laser)
        state.all_sprites.add(laser)
        if hasattr(self.game, "audio") and self.game.audio:
            self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.6)

    def get_hit(self, damage):
        self.health -= damage
        state = getattr(self.game, "state", None)
        if state and hasattr(state, "particles"):
            spawn_sparks(state.particles, self.rect.centerx, self.rect.top, (0, -1), color=(255, 180, 50), count=6)

        if self.health <= 0:
            if state and hasattr(state, "particles"):
                spawn_explosion(state.particles, self.rect.centerx, self.rect.centery, color=(255, 120, 0), count=20)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("zap", pos_x=self.rect.centerx, volume_mult=0.8)
            self.kill()
            return True
        return False


class ProximityMine(pg.sprite.Sprite):
    """
    Fragmentation proximity mine launched by Goliath Dreadnought in Phase 3.
    Drifts downward, detonating on player proximity or 4.0s timer into radial shrapnel.
    """

    def __init__(self, game, x, y):
        super().__init__()
        self.game = game
        self.image = pg.Surface((28, 28), pg.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.fx = float(x)
        self.fy = float(y)
        self.speed_y = 65.0
        self.timer = 4.0
        self.blink_timer = 0.0

        self.max_health = 35
        self.health = self.max_health
        self.score_value = 250
        self._render_mine_surface(is_bright=False)

    def _render_mine_surface(self, is_bright=False):
        self.image.fill((0, 0, 0, 0))
        # Spiked mine body
        body_color = (60, 40, 50)
        core_color = (255, 40, 60) if is_bright else (140, 20, 30)
        pg.draw.circle(self.image, body_color, (14, 14), 11)
        # Spikes
        for angle_deg in (0, 45, 90, 135, 180, 225, 270, 315):
            rad = math.radians(angle_deg)
            sx = int(14 + 13 * math.cos(rad))
            sy = int(14 + 13 * math.sin(rad))
            pg.draw.line(self.image, (180, 120, 140), (14, 14), (sx, sy), 2)
        # Pulsing center warning light
        pg.draw.circle(self.image, core_color, (14, 14), 5)

    def update(self, dt):
        self.fy += self.speed_y * dt
        self.rect.center = (int(self.fx), int(self.fy))

        self.timer -= dt
        self.blink_timer += dt
        
        # Flashing speed increases as timer ticks down
        blink_rate = 0.3 if self.timer > 2.0 else 0.12
        if self.blink_timer >= blink_rate:
            self.blink_timer = 0.0
            self._render_mine_surface(is_bright=True)
        else:
            self._render_mine_surface(is_bright=False)

        state = getattr(self.game, "state", None)
        if state and hasattr(state, "player"):
            player = state.player
            dist = math.hypot(player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery)
            if dist < 85:
                self.detonate()
                return

        if self.timer <= 0 or self.rect.top > self.game.height + 20:
            self.detonate()

    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.detonate(destroyed_by_player=True)
            return True
        return False

    def detonate(self, destroyed_by_player=False):
        if not self.alive():
            return

        state = getattr(self.game, "state", None)
        if state:
            # Area hazard ring
            if hasattr(state, "telegraphs") and state.telegraphs:
                state.telegraphs.create_ring_hazard(
                    center=self.rect.center,
                    radius=55,
                    warning_duration=0.05,
                    burst_duration=0.3,
                    damage=18,
                    color=(255, 80, 40),
                )

            # Particles & Sound
            if hasattr(state, "particles"):
                spawn_explosion(state.particles, self.rect.centerx, self.rect.centery, color=(255, 80, 30), count=25)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("zap", pos_x=self.rect.centerx, volume_mult=0.75)

            # Spawn 8 radial shrapnel lasers if not destroyed from afar by player
            if not destroyed_by_player and hasattr(state, "enemy_lasers"):
                from sprites import Laser
                for angle in range(0, 360, 45):
                    rad = math.radians(angle)
                    speed = 280
                    # Create custom directional shrapnel
                    l = Laser(self.game, self.rect.centerx, self.rect.centery, speed_y=speed, angle=angle, damage=10, img_name="laser_enemy")
                    # Explicit speed components
                    l.speed_x = speed * math.sin(rad)
                    l.speed_y = speed * math.cos(rad)
                    state.enemy_lasers.add(l)
                    state.all_sprites.add(l)

        self.kill()
