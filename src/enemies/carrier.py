# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg

try:
    from fx import spawn_sparks, spawn_explosion
except ModuleNotFoundError:
    from ..fx import spawn_sparks, spawn_explosion

from level_system import armada_image_key


class Swarmer(pg.sprite.Sprite):
    """
    Swarmer — Agile Micro-Drone launched by Hive Carriers.
    
    Homing drone that steers toward the player's position, dealing collision
    damage and detonating on impact. Offers quick kill chain rewards.
    """

    def __init__(self, game, x, y, spd_mult=1.0, armada_folder=None):
        super().__init__()
        self.game = game
        self.type = "swarmer"
        self.score_value = 80
        self.max_health = 10
        self.health = 10

        sprite_key = armada_image_key(armada_folder, "swarmer") if armada_folder else "enemy_scout"
        self.raw_image = self.game.assets.get_image(sprite_key, 22, 22)
        self.image = self.raw_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

        self.fx = float(x)
        self.fy = float(y)
        self.speed = 260.0 * spd_mult
        self.turn_rate = 3.2
        self.heading_rad = math.radians(random.uniform(70, 110))  # Initially downward

    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.kill()
            return True
        return False

    def update(self, dt):
        state = self.game.state
        player = getattr(state, "player", None)

        if player and hasattr(player, "rect"):
            dx = player.rect.centerx - self.fx
            dy = player.rect.centery - self.fy
            desired_angle = math.atan2(dy, dx)
            # Angular steering
            diff = (desired_angle - self.heading_rad + math.pi) % (2 * math.pi) - math.pi
            max_turn = self.turn_rate * dt
            self.heading_rad += max(-max_turn, min(max_turn, diff))

        # Forward movement along heading
        self.fx += math.cos(self.heading_rad) * self.speed * dt
        self.fy += math.sin(self.heading_rad) * self.speed * dt
        self.rect.center = (int(self.fx), int(self.fy))

        # Rotate visual to face heading
        degrees = -math.degrees(self.heading_rad) - 90.0
        self.image = pg.transform.rotate(self.raw_image, degrees)
        self.rect = self.image.get_rect(center=self.rect.center)

        if self.rect.top > self.game.height + 40:
            self.kill()


class HiveCarrier(pg.sprite.Sprite):
    """
    Hive Carrier — Swarm Mothership.
    
    Heavy armored carrier that periodically launches 3-4 agile micro-drones (Swarmer)
    from twin launch bays to overwhelm the player.
    """

    def __init__(self, game, x, y, hp_mult=1.0, spd_mult=1.0, armada_folder=None, laser_key=None):
        super().__init__()
        self.game = game
        self.armada_folder = armada_folder
        self.laser_key = laser_key or "laser_red_beam_stream_long"
        self.type = "hive_carrier"

        sprite_key = armada_image_key(armada_folder, "hive_carrier") if armada_folder else "enemy_cruiser"
        self.raw_image = self.game.assets.get_image(sprite_key, 84, 84)
        self.image = self.raw_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

        # Stats
        self.hp_mult = hp_mult
        self.spd_mult = spd_mult
        self.max_health = int(180 * hp_mult)
        self.health = self.max_health
        self.score_value = 800

        # Movement
        self.target_y = random.randint(110, 160)
        self.speed_y = 60.0 * spd_mult
        self.sway_timer = random.uniform(0, math.tau)

        # Spawning & Weapons
        self.drone_spawn_interval = 4.0
        self.drone_spawn_timer = 2.0
        self.shoot_timer = 2.5
        self.minions = []

    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            # Huge death explosion
            if hasattr(self.game.state, "particles"):
                spawn_explosion(
                    self.game.state.particles,
                    self.rect.centerx,
                    self.rect.centery,
                    color=(255, 120, 20),
                    count=45,
                )
            self.kill()
            return True
        return False

    def update(self, dt):
        # Move downward into position then hover
        if self.rect.centery < self.target_y:
            self.rect.y += int(self.speed_y * dt)
        else:
            self.sway_timer += dt * 1.2
            self.rect.x += int(math.sin(self.sway_timer) * 1.5)

        # Boundary checks
        if self.rect.left < 40:
            self.rect.left = 40
        elif self.rect.right > self.game.width - 40:
            self.rect.right = self.game.width - 40

        # Filter dead minions
        self.minions = [m for m in self.minions if m.alive()]

        # Drone spawn timer
        self.drone_spawn_timer -= dt
        if self.drone_spawn_timer <= 0:
            if len(self.minions) < 6:
                self._launch_swarm()
            self.drone_spawn_timer = self.drone_spawn_interval

        # Firing timer
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self._shoot_defensive_lasers()
            self.shoot_timer = 2.8

    def _launch_swarm(self):
        state = self.game.state
        if not hasattr(state, "enemies"):
            return

        drone_count = random.randint(3, 4)
        for i in range(drone_count):
            bay_x = self.rect.left + 16 if (i % 2 == 0) else self.rect.right - 16
            bay_y = self.rect.centery + random.randint(-5, 15)
            swarmer = Swarmer(
                self.game,
                bay_x,
                bay_y,
                spd_mult=self.spd_mult,
                armada_folder=self.armada_folder,
            )
            state.enemies.add(swarmer)
            state.all_sprites.add(swarmer)
            self.minions.append(swarmer)

            # Bay launch spark puff
            if hasattr(state, "particles"):
                spawn_sparks(state.particles, bay_x, bay_y, direction=(0, 1), color=(255, 200, 50), count=6)

        if hasattr(self.game, "audio") and self.game.audio:
            self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.6)

    def _shoot_defensive_lasers(self):
        state = self.game.state
        if not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser
        l1 = Laser(self.game, self.rect.left + 22, self.rect.bottom, speed_y=340, img_name=self.laser_key)
        l2 = Laser(self.game, self.rect.right - 22, self.rect.bottom, speed_y=340, img_name=self.laser_key)
        state.enemy_lasers.add(l1, l2)
        state.all_sprites.add(l1, l2)
