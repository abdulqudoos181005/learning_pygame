# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg

try:
    from fx import spawn_sparks, spawn_explosion
except ModuleNotFoundError:
    from ..fx import spawn_sparks, spawn_explosion

from level_system import armada_image_key


class AegisDefender(pg.sprite.Sprite):
    """
    Aegis Defender — Frontline Barrier Ship.
    
    Features a 120-degree frontal energy shield that deflects player lasers
    from the front. Overheats periodically (5s active, 2.5s overheat),
    forcing the player to flank, use homing missiles, or time attacks.
    """

    def __init__(self, game, x, y, hp_mult=1.0, spd_mult=1.0, armada_folder=None, laser_key=None):
        super().__init__()
        self.game = game
        self.armada_folder = armada_folder
        self.laser_key = laser_key or "laser_enemy"
        self.type = "aegis_defender"

        # Resolve asset from armada folder
        sprite_key = armada_image_key(armada_folder, "aegis_defender") if armada_folder else "enemy_cruiser"
        self.raw_image = self.game.assets.get_image(sprite_key, 64, 64)
        self.image = self.raw_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

        # Stats
        self.hp_mult = hp_mult
        self.spd_mult = spd_mult
        self.max_health = int(85 * hp_mult)
        self.health = self.max_health
        self.score_value = 600

        # Movement
        self.speed_y = random.randint(45, 70) * spd_mult
        self.speed_x = 0.0
        self.wave_timer = random.uniform(0, math.tau)

        # Shield & Overheat mechanics
        self.shield_active = True
        self.shield_max_time = 5.0
        self.overheat_duration = 2.5
        self.shield_timer = self.shield_max_time
        self.shield_ripple_timer = 0.0

        # Defensive weapons
        self.shoot_delay = 2.5
        self.shoot_timer = random.uniform(1.0, 2.0)

    def deflect_laser(self, laser):
        """
        Checks if an incoming player laser is blocked by the 120-degree frontal shield.
        Returns True if deflected (no damage to hull), False otherwise.
        """
        if not self.shield_active:
            return False

        # Shield covers the front (downward direction).
        # Player lasers travel upward (speed_y < 0) from below.
        # Deflect if laser hits the front half of the ship.
        if laser.rect.bottom >= self.rect.centery - 8:
            self.shield_ripple_timer = 0.22
            # Spawn deflection sparks
            if hasattr(self.game.state, "particles"):
                spawn_sparks(
                    self.game.state.particles,
                    laser.rect.centerx,
                    laser.rect.top,
                    (0, 1),
                    color=(0, 230, 255),
                    count=8,
                )
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("shield_down", pos_x=self.rect.centerx, volume_mult=0.55)
            elif hasattr(self.game.assets, "get_sound"):
                self.game.assets.get_sound("shield_down").play()
            return True

        return False

    def get_hit(self, damage, frontal=False):
        """Standard damage handler. Can be bypassed if frontal shield is active."""
        if frontal and self.shield_active:
            self.shield_ripple_timer = 0.2
            return False

        self.health -= damage
        if self.health <= 0:
            self.kill()
            return True
        return False

    def update(self, dt):
        # Shield overheat cycle
        if self.shield_active:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_timer = self.overheat_duration
                # Fizzle sparks on overheat
                if hasattr(self.game.state, "particles"):
                    spawn_sparks(
                        self.game.state.particles,
                        self.rect.centerx,
                        self.rect.bottom,
                        (0, 1),
                        color=(255, 140, 40),
                        count=10,
                    )
        else:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield_active = True
                self.shield_timer = self.shield_max_time
                if hasattr(self.game, "audio") and self.game.audio:
                    self.game.audio.play_sfx("powerup", pos_x=self.rect.centerx, volume_mult=0.5)

        if self.shield_ripple_timer > 0:
            self.shield_ripple_timer = max(0.0, self.shield_ripple_timer - dt)

        # Movement: slow downward advance + subtle sway
        self.wave_timer += dt * 1.5
        self.rect.x += int(math.sin(self.wave_timer) * 1.2)
        self.rect.y += int(self.speed_y * dt)

        # Boundary checks
        if self.rect.left < 20:
            self.rect.left = 20
        elif self.rect.right > self.game.width - 20:
            self.rect.right = self.game.width - 20

        if self.rect.top > self.game.height:
            self.kill()

        # Firing logic
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot()
            self.shoot_timer = self.shoot_delay

    def shoot(self):
        state = self.game.state
        if not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser
        l1 = Laser(self.game, self.rect.left + 12, self.rect.bottom, speed_y=320, img_name=self.laser_key)
        l2 = Laser(self.game, self.rect.right - 12, self.rect.bottom, speed_y=320, img_name=self.laser_key)
        state.enemy_lasers.add(l1, l2)
        state.all_sprites.add(l1, l2)

        if hasattr(self.game, "audio") and self.game.audio:
            self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.55)

    def draw_extras(self, surface):
        """Draws the 120-degree frontal energy shield arc or overheat venting."""
        center_x = self.rect.centerx
        center_y = self.rect.centery + 8
        radius = 38

        if self.shield_active:
            # Active shield: glowing cyan/teal 120-degree arc facing downward
            # In pygame arc: 0 rad = 3 o'clock. Downward 120-deg arc is from 30 deg to 150 deg (in math angle: -30 to -150)
            # Standard screen coords: bottom is +Y.
            arc_surf = pg.Surface((radius * 2 + 16, radius * 2 + 16), pg.SRCALPHA)
            arc_rect = pg.Rect(8, 8, radius * 2, radius * 2)

            alpha = 240 if self.shield_ripple_timer > 0 else 180
            glow_color = (180, 255, 255, alpha) if self.shield_ripple_timer > 0 else (0, 220, 255, alpha)

            # Draw outer glow arc and main arc (angles in radians: downward arc spans from ~3.66 rad to ~5.76 rad)
            # Pygame arc angles: 0 rad is 3 o'clock (right), angle goes counter-clockwise.
            # Downward: between 210° (7pi/6) and 330° (11pi/6).
            pg.draw.arc(arc_surf, (0, 160, 220, 90), arc_rect.inflate(4, 4), math.radians(210), math.radians(330), 6)
            pg.draw.arc(arc_surf, glow_color, arc_rect, math.radians(210), math.radians(330), 3)

            # Cap pips
            surface.blit(arc_surf, (center_x - radius - 8, center_y - radius - 8), special_flags=pg.BLEND_ADD)
        else:
            # Overheat state: faint orange flickering fumes
            if random.random() < 0.35:
                fume_x = center_x + random.randint(-20, 20)
                fume_y = self.rect.bottom + random.randint(-4, 6)
                pg.draw.circle(surface, (255, 120, 30, 120), (fume_x, fume_y), random.randint(2, 4))
