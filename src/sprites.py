# pyrefly: ignore [missing-import]
import pygame as pg
import random
import math
from vfx.player_presentation import PlayerPresentation
from level_system import armada_image_key

class Player(pg.sprite.Sprite):
    def __init__(self, game, x, y):
        super().__init__()
        self.game = game
        self.base_image = self.game.assets.get_image("player", 60, 60)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.velocity = pg.Vector2(0, 0)
        self.max_speed = 400.0
        self.acceleration = 1800.0
        self.drag = 8.0
        self.bank_angle = 0.0
        self.recoil_timer = 0.0
        self.hit_stutter = 0.0
        self.muzzle_timer = 0.0
        self.missile_hold_timer = 0.0
        self.presentation = PlayerPresentation(self)
        
        # Stats
        self.speed = 400.0  # Pixels per second
        self.max_health = 100
        self.health = 100
        self.max_shield = 100
        self.shield = 0  # Starts at 0, goes up with Shield PowerUp
        self.lives = 3
        self.invincible_timer = 0.0
        self.flash_timer = 0.0
        
        # Weapon properties
        self.shoot_cooldown = 0.25 # seconds
        self.shoot_timer = 0.0
        self.base_laser_tier = 1
        
        # Power-up states (Sprint 2: triple-shot & speed timers increased to 12s)
        self.triple_shot_timer = 0.0
        self.speed_boost_timer = 0.0
        self.shield_active = False
        self.laser_power_timer = 0.0   # Power laser: next-tier boost for 10s
        self.missile_count = 0         # Stored homing missiles (activated by M key)
        self.missile_cooldown = 0.0    # Prevent spamming missiles

    def _effective_laser_tier(self):
        """Return the currently active weapon tier after applying any power-laser pickup bonus."""
        if self.laser_power_timer > 0:
            return min(3, max(self.base_laser_tier, self.base_laser_tier + 1))
        return self.base_laser_tier

    def activate_invincibility(self, duration=4.0):
        self.invincible_timer = max(self.invincible_timer, duration)
        self.flash_timer = 0.0

    def get_hit(self, damage):
        """Handle damage to player ship, affecting shield first then health."""
        if self.invincible_timer > 0:
            return False

        shield_broke = False
        if self.shield > 0:
            self.shield -= damage
            shield_broke = self.shield <= 0
            self.presentation.trigger_shield_ripple()
            if shield_broke and hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                self.game.assets.get_sound("shield_down").play()
            if self.shield < 0:
                self.health += self.shield # Apply remaining damage to health
                self.shield = 0
        else:
            self.health -= damage
            
        # Trigger screen shake on taking damage
        if hasattr(self.game.state, 'trigger_shake'):
            self.game.state.trigger_shake(duration=0.2, magnitude=5)
        self.hit_stutter = 0.12
            
        if self.health <= 0:
            self.lives -= 1
            self.health = self.max_health
            self.shield = 0
            self.activate_invincibility(4.0)
            self.presentation.trigger_repair()
            if hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                self.game.assets.get_sound("player_death").play()
            # Reset position
            self.pos_x = float(self.game.width // 2)
            self.pos_y = float(self.game.height - 80)
            self.velocity.update(0, 0)
            self.rect.center = (round(self.pos_x), round(self.pos_y))
            return True # Died
        return False

    def update(self, dt):
        # Update timers
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
        if self.triple_shot_timer > 0:
            self.triple_shot_timer -= dt
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt
        if self.laser_power_timer > 0:
            self.laser_power_timer -= dt
        if self.missile_cooldown > 0:
            self.missile_cooldown -= dt
        self.recoil_timer = max(0.0, self.recoil_timer - dt)
        self.hit_stutter = max(0.0, self.hit_stutter - dt)
        self.muzzle_timer = max(0.0, self.muzzle_timer - dt)
        self.presentation.update(dt)
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            self.flash_timer += dt
            if self.flash_timer >= 0.12:
                self.flash_timer = 0.0
                self.image.set_alpha(90 if self.image.get_alpha() > 120 else 255)
        else:
            self.image.set_alpha(255)
            
        self.shield_active = self.shield > 0

        # Movement keys feed an inertial body; the rect remains the collision view.
        keys = pg.key.get_pressed()
        dx, dy = 0.0, 0.0
        
        if keys[pg.K_w] or keys[pg.K_UP]:
            dy -= 1
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            dy += 1
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            dx -= 1
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            dx += 1

        # Normalize diagonal movement vector
        if dx != 0 or dy != 0:
            length = math.sqrt(dx*dx + dy*dy)
            dx /= length
            dy /= length
            
        desired = pg.Vector2(dx, dy)
        boost = 1.5 if self.speed_boost_timer > 0 else 1.0
        self.max_speed = self.speed * boost
        if desired.length_squared() > 0:
            desired.scale_to_length(self.max_speed)
            self.velocity += (desired - self.velocity) * min(1.0, self.acceleration * dt / max(1.0, self.max_speed))
        else:
            self.velocity *= max(0.0, 1.0 - self.drag * dt)
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)
        self.pos_x += self.velocity.x * dt
        self.pos_y += self.velocity.y * dt

        # Screen boundaries check
        half_w, half_h = self.rect.width / 2, self.rect.height / 2
        self.pos_x = max(half_w, min(self.game.width - half_w, self.pos_x))
        self.pos_y = max(half_h, min(self.game.height - half_h, self.pos_y))
        self.bank_angle = max(-12.0, min(12.0, self.velocity.x / max(1.0, self.max_speed) * 12.0))
        rotated = pg.transform.rotozoom(self.base_image, self.bank_angle, 1.0)
        if self.recoil_timer > 0:
            rotated = pg.transform.smoothscale(
                rotated,
                (rotated.get_width(), max(1, rotated.get_height() - 2)),
            )
        self.image = rotated
        self.rect = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

        # Fire regular weapons
        if keys[pg.K_SPACE] or keys[pg.K_j]:
            self.shoot()
        
        # Launch missile (M key) — homing special weapon
        if keys[pg.K_m] and self.missile_count > 0 and self.missile_cooldown <= 0:
            self.missile_hold_timer += dt
            self._launch_missile()
            self.missile_cooldown = 0.5  # Half-second cooldown between launches
        elif not keys[pg.K_m]:
            self.missile_hold_timer = 0.0

    def shoot(self):
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_cooldown
            self.recoil_timer = 0.06
            self.muzzle_timer = 0.07
            if hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                self.game.assets.get_sound("laser").play()
            
            # Retrieve laser groups from active state
            state = self.game.state
            if not hasattr(state, 'player_lasers'):
                return
            
            # Progressive laser tiers: level-based baseline plus pickup bonus
            tier = self._effective_laser_tier()
            laser_damage_by_tier = {1: 10, 2: 20, 3: 30}
            laser_image_by_tier = {1: "laser_player", 2: "laser_power", 3: "laser_tier3"}
            laser_dmg = laser_damage_by_tier[tier]
            img_name  = laser_image_by_tier[tier]
                
            if self.triple_shot_timer > 0:
                # Fire 3 lasers (center, diagonal-left, diagonal-right)
                laser_center = Laser(self.game, self.rect.centerx, self.rect.top, speed_y=-600, angle=0,   damage=laser_dmg, img_name=img_name)
                laser_left   = Laser(self.game, self.rect.left,   self.rect.top, speed_y=-550, angle=-15, damage=laser_dmg, img_name=img_name)
                laser_right  = Laser(self.game, self.rect.right,  self.rect.top, speed_y=-550, angle=15,  damage=laser_dmg, img_name=img_name)
                state.player_lasers.add(laser_center, laser_left, laser_right)
                state.all_sprites.add(laser_center, laser_left, laser_right)
            else:
                # Single center shot
                laser = Laser(self.game, self.rect.centerx, self.rect.top, speed_y=-600, damage=laser_dmg, img_name=img_name)
                state.player_lasers.add(laser)
                state.all_sprites.add(laser)

    def _missile_target(self):
        state = self.game.state
        enemies = getattr(state, "enemies", ())
        return max(enemies, key=lambda enemy: enemy.health, default=None)

    def draw_presentation_back(self, surface):
        self.presentation.draw_back(surface)

    def draw_presentation_front(self, surface):
        self.presentation.draw_front(surface)

    def _launch_missile(self):
        """Spawns a homing Missile targeting the highest-health enemy on screen."""
        state = self.game.state
        if not hasattr(state, 'enemies') or not hasattr(state, 'missiles'):
            return
        
        self.missile_count -= 1
        if hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
            self.game.assets.get_sound("laser_pew").play()
        missile = Missile(self.game, self.rect.centerx, self.rect.top, state.enemies)
        state.missiles.add(missile)
        state.all_sprites.add(missile)


class Laser(pg.sprite.Sprite):
    def __init__(self, game, x, y, speed_y, angle=0, damage=10, img_name=None):
        super().__init__()
        self.game = game
        self.angle = angle
        self.damage = damage
        
        # Select appropriate image based on direction unless overridden by caller
        is_player = speed_y < 0
        if img_name is None:
            img_name = "laser_player" if is_player else "laser_enemy"
        
        self.raw_image = self.game.assets.get_image(img_name, 12, 32)
        if self.angle != 0:
            self.image = pg.transform.rotate(self.raw_image, -self.angle)
        else:
            self.image = self.raw_image
            
        self.rect = self.image.get_rect(center=(x, y))
        self.fx = float(x)
        self.fy = float(y)
        self.trail = []
        
        # Resolve speed into X/Y components accounting for angle
        if is_player:
            self.speed_x = -abs(speed_y) * math.sin(math.radians(self.angle))
            self.speed_y = -abs(speed_y) * math.cos(math.radians(self.angle))
        else:
            self.speed_x = abs(speed_y) * math.sin(math.radians(self.angle))
            self.speed_y = abs(speed_y) * math.cos(math.radians(self.angle))

    def update(self, dt):
        self.trail.append((self.fx, self.fy))
        if len(self.trail) > 5:
            self.trail.pop(0)
        self.fx += self.speed_x * dt
        self.fy += self.speed_y * dt
        self.rect.center = (round(self.fx), round(self.fy))
        
        # Kill if it leaves screen boundaries
        if self.rect.bottom < 0 or self.rect.top > self.game.height or self.rect.right < 0 or self.rect.left > self.game.width:
            self.kill()

    def draw_trail(self, surface):
        if len(self.trail) < 2:
            return
        color = (80, 220, 255) if self.speed_y < 0 else (255, 80, 100)
        for index in range(1, len(self.trail)):
            alpha = int(35 + index * 30)
            layer = pg.Surface((max(2, self.rect.width), max(2, self.rect.height)), pg.SRCALPHA)
            pg.draw.line(layer, (*color, alpha), (layer.get_width() // 2, layer.get_height()), (layer.get_width() // 2, 0), 2)
            surface.blit(layer, layer.get_rect(center=(round(self.trail[index - 1][0]), round(self.trail[index - 1][1]))), special_flags=pg.BLEND_ADD)


class Enemy(pg.sprite.Sprite):
    def __init__(self, game, x, y, enemy_type="scout", hp_mult=1.0, spd_mult=1.0, armada_folder=None, laser_key=None):
        super().__init__()
        self.game = game
        self.type = enemy_type
        self.laser_key = laser_key or "laser_enemy"

        def _sprite_key(role, fallback_alias):
            # Sprint 11: theater-driven armada folder picks the faction skin; otherwise keep the old static alias.
            return armada_image_key(armada_folder, role) if armada_folder else fallback_alias

        # Configure variables based on enemy type
        if self.type == "scout":
            self.image = self.game.assets.get_image(_sprite_key("scout", "enemy_scout"), 45, 45)
            self.speed_y = random.randint(180, 240) * spd_mult
            self.speed_x = 0
            self.max_health = int(10 * hp_mult)
            self.shoot_delay = 9999.0 # Scouts don't shoot
            self.score_value = 100
        elif self.type == "stinger":
            self.image = self.game.assets.get_image(_sprite_key("stinger", "enemy_stinger"), 48, 48)
            self.speed_y = random.randint(100, 150) * spd_mult
            # Gentle side-to-side sweeping motion
            self.speed_x = random.choice([-80, 80]) * spd_mult
            self.max_health = int(20 * hp_mult)
            self.shoot_delay = random.uniform(1.5, 2.5)
            self.score_value = 250
        elif self.type == "cruiser":
            self.image = self.game.assets.get_image(_sprite_key("cruiser", "enemy_cruiser"), 70, 70)
            self.speed_y = random.randint(50, 80) * spd_mult
            self.speed_x = 0
            self.max_health = int(60 * hp_mult)
            self.shoot_delay = random.uniform(2.0, 3.5)
            self.score_value = 500
        else: # default placeholder
            self.image = self.game.assets.get_image(_sprite_key("scout", "enemy_scout"), 45, 45)
            self.speed_y = 150 * spd_mult
            self.speed_x = 0
            self.max_health = int(10 * hp_mult)
            self.shoot_delay = 3.0
            self.score_value = 100

        self.health = self.max_health
        self.rect = self.image.get_rect(center=(x, y))
        self.shoot_timer = random.uniform(0.5, self.shoot_delay)
        
        # Sine wave horizontal movement configuration (only for certain enemies)
        self.wave_timer = random.uniform(0, 2 * math.pi)
        
    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.kill()
            return True # Destroyed
        return False

    def update(self, dt):
        # Y movement (always move down)
        self.rect.y += self.speed_y * dt
        
        # X movement patterns
        if self.type == "stinger":
            # Bounce off walls
            self.rect.x += self.speed_x * dt
            if self.rect.left < 10:
                self.rect.left = 10
                self.speed_x = abs(self.speed_x)
            elif self.rect.right > self.game.width - 10:
                self.rect.right = self.game.width - 10
                self.speed_x = -abs(self.speed_x)
                
        elif self.type == "cruiser":
            # Slow waving pattern
            self.wave_timer += dt * 2
            self.rect.x += math.sin(self.wave_timer) * 1.5

        # Offscreen cleanup
        if self.rect.top > self.game.height:
            self.kill()
            
        # Shooting logic
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
        else:
            self.shoot()
            self.shoot_timer = self.shoot_delay

    def shoot(self):
        state = self.game.state
        if not hasattr(state, 'enemy_lasers'):
            return
            
        if hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
            self.game.assets.get_sound("laser_pew").play()

        if self.type == "stinger":
            # Shoot a laser down, colored to the mission's faction theater
            laser = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=400, img_name=self.laser_key)
            state.enemy_lasers.add(laser)
            state.all_sprites.add(laser)
        elif self.type == "cruiser":
            # Shoot double lasers, colored to the mission's faction theater
            l1 = Laser(self.game, self.rect.left + 15, self.rect.bottom, speed_y=350, img_name=self.laser_key)
            l2 = Laser(self.game, self.rect.right - 15, self.rect.bottom, speed_y=350, img_name=self.laser_key)
            state.enemy_lasers.add(l1, l2)
            state.all_sprites.add(l1, l2)


class Boss(pg.sprite.Sprite):
    def __init__(self, game, hp_mult=1.0, spd_mult=1.0, boss_key=None, laser_key=None):
        super().__init__()
        self.game = game
        self.image = self.game.assets.get_image(boss_key or "boss", 150, 100)
        self.laser_key = laser_key or "laser_enemy"
        self.rect = self.image.get_rect(center=(self.game.width // 2, -100))
        
        # Stats (scaled by level multipliers)
        base_health = 500
        self.max_health = int(base_health * hp_mult)
        self.health = self.max_health
        self.speed_x = 100 * spd_mult
        self.target_y = 120
        self.score_value = int(5000 * hp_mult)
        
        # Attack intervals
        self.shoot_timer = 2.0
        self.attack_phase = 1

    def get_hit(self, damage):
        self.health -= damage
        # Phase transitions (proportional to max health)
        if self.health <= self.max_health * 0.3:
            self.attack_phase = 3
        elif self.health <= self.max_health * 0.7:
            self.attack_phase = 2
            
        if self.health <= 0:
            self.kill()
            return True
        return False

    def update(self, dt):
        # Entry animation: move down into the screen
        if self.rect.centery < self.target_y:
            self.rect.y += 80 * dt
        else:
            # Side-to-side sweeping motion
            self.rect.x += self.speed_x * dt
            if self.rect.left < 50:
                self.rect.left = 50
                self.speed_x = abs(self.speed_x)
            elif self.rect.right > self.game.width - 50:
                self.rect.right = self.game.width - 50
                self.speed_x = -abs(self.speed_x)

        # Shooting logic
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
        else:
            self.shoot()
            # Firing rates vary by phase
            if self.attack_phase == 1:
                self.shoot_timer = 1.5
            elif self.attack_phase == 2:
                self.shoot_timer = 0.8
            else:
                self.shoot_timer = 0.4

    def shoot(self):
        state = self.game.state
        if not hasattr(state, 'enemy_lasers'):
            return

        if hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
            self.game.assets.get_sound("laser_pew").play()

        if self.attack_phase == 1:
            # Fire lasers from left and right gun pods, colored to the mission's faction theater
            l1 = Laser(self.game, self.rect.centerx - 40, self.rect.bottom, speed_y=380, img_name=self.laser_key)
            l2 = Laser(self.game, self.rect.centerx + 40, self.rect.bottom, speed_y=380, img_name=self.laser_key)
            state.enemy_lasers.add(l1, l2)
            state.all_sprites.add(l1, l2)
            
        elif self.attack_phase == 2:
            # Fire heavy green plasma beams down-left, down, down-right
            l1 = Laser(self.game, self.rect.centerx,      self.rect.bottom, speed_y=420, angle=0)
            l2 = Laser(self.game, self.rect.centerx - 30, self.rect.bottom, speed_y=400, angle=-15)
            l3 = Laser(self.game, self.rect.centerx + 30, self.rect.bottom, speed_y=400, angle=15)
            
            # Re-key them as boss lasers (heavy plasma green texture)
            for l in (l1, l2, l3):
                l.raw_image = self.game.assets.get_image("laser_boss", 16, 40)
                l.image = pg.transform.rotate(l.raw_image, -l.angle) if l.angle != 0 else l.raw_image
                
            state.enemy_lasers.add(l1, l2, l3)
            state.all_sprites.add(l1, l2, l3)
            
        elif self.attack_phase == 3:
            # Rapid fire sweeping single lasers, colored to the mission's faction theater
            angle = random.uniform(-40, 40)
            l = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=480, angle=angle, img_name=self.laser_key)
            state.enemy_lasers.add(l)
            state.all_sprites.add(l)


class Asteroid(pg.sprite.Sprite):
    """Hazard rock that drifts downward and damages the player on impact."""
    SIZES = ("small", "medium", "large")
    COLORS = ("brown", "grey")
    DAMAGE_BY_SIZE = {"small": 8, "medium": 15, "large": 25}
    HEALTH_BY_SIZE = {"small": 25, "medium": 45, "large": 70}
    SIZE_TO_SCALE = {"small": 32, "medium": 48, "large": 64}

    def __init__(self, game, x=None, y=None, size=None, color=None):
        super().__init__()
        self.game = game
        self.size = size or random.choice(self.SIZES)
        self.color = color or random.choice(self.COLORS)
        self.damage = self.DAMAGE_BY_SIZE[self.size]
        self.max_health = self.HEALTH_BY_SIZE[self.size]
        self.health = self.max_health

        scale = self.SIZE_TO_SCALE[self.size]
        self.image = self.game.assets.get_image(f"asteroid_{self.size}_{self.color}", scale, scale)
        self.rect = self.image.get_rect(center=(x or random.randint(40, self.game.width - 40), y or -40))

        self.speed_y = random.uniform(70, 120) * ({"small": 1.0, "medium": 1.2, "large": 1.4}[self.size])
        self.speed_x = random.uniform(-30, 30)
        self.spin = random.uniform(-35, 35)
        self.rotation = random.uniform(0, 360)
        self.wobble = random.uniform(0, math.tau)
        self.wobble_speed = random.uniform(0.7, 2.2)

    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.kill()
            return True
        return False

    def update(self, dt):
        drift = math.sin(self.wobble) * 10
        self.rect.x += (self.speed_x + drift) * dt
        self.rect.y += self.speed_y * dt
        self.wobble += self.wobble_speed * dt
        self.rotation += self.spin * dt

        base = self.game.assets.get_image(
            f"asteroid_{self.size}_{self.color}",
            self.SIZE_TO_SCALE[self.size],
            self.SIZE_TO_SCALE[self.size],
        )
        self.image = pg.transform.rotate(base, self.rotation)
        self.rect = self.image.get_rect(center=self.rect.center)

        if self.rect.top > self.game.height + 40 or self.rect.left > self.game.width + 50 or self.rect.right < -50:
            self.kill()


class Missile(pg.sprite.Sprite):
    """
    A homing missile that targets the highest-health enemy on screen.
    Deals 30 damage on impact and triggers a large explosion effect.
    Activated by pressing M key when the player has missile_count > 0.
    """
    SPEED     = 450.0  # Pixels per second
    TURN_RATE = 3.5    # Radians per second (homing steer strength)
    DAMAGE    = 30

    def __init__(self, game, x, y, enemy_group):
        super().__init__()
        self.game = game
        self.enemy_group = enemy_group
        self.image = self.game.assets.get_image("missile", 14, 28)
        self.rect = self.image.get_rect(center=(x, y))
        # Current heading in radians (0 = up / negative Y)
        self.angle_rad = 0.0
        # Float positions for sub-pixel precision
        self.fx = float(x)
        self.fy = float(y)
        self.trail = []

    def _find_target(self):
        """Returns the enemy sprite with the highest current health, or None."""
        best    = None
        best_hp = -1
        for e in self.enemy_group:
            if e.health > best_hp:
                best_hp = e.health
                best    = e
        return best

    def update(self, dt):
        self.trail.append((self.fx, self.fy))
        if len(self.trail) > 14:
            self.trail.pop(0)
        target = self._find_target()
        if target:
            # Vector from missile to target
            dx = target.rect.centerx - self.fx
            dy = target.rect.centery - self.fy
            # atan2 gives angle from positive-X; shift so 0 rad = up (negative Y)
            desired_angle = math.atan2(dy, dx) + math.pi / 2
            # Smallest angular difference in [-pi, pi]
            diff = (desired_angle - self.angle_rad + math.pi) % (2 * math.pi) - math.pi
            max_turn = self.TURN_RATE * dt
            self.angle_rad += max(-max_turn, min(max_turn, diff))

        # Move forward in current heading direction
        self.fx += math.sin(self.angle_rad) * self.SPEED * dt
        self.fy -= math.cos(self.angle_rad) * self.SPEED * dt
        self.rect.center = (int(self.fx), int(self.fy))

        # Rotate sprite to match heading
        degrees   = math.degrees(self.angle_rad)
        base_img  = self.game.assets.get_image("missile", 14, 28)
        self.image = pg.transform.rotate(base_img, -degrees)
        self.rect  = self.image.get_rect(center=self.rect.center)

        # Kill if it leaves the screen
        if (self.rect.bottom < 0 or self.rect.top > self.game.height
                or self.rect.right < 0 or self.rect.left > self.game.width):
            self.kill()

    def draw_trail(self, surface):
        if len(self.trail) < 2:
            return
        for index in range(1, len(self.trail)):
            alpha = int(20 + index * 10)
            radius = max(1, int(index / 5))
            glow = pg.Surface((radius * 6, radius * 6), pg.SRCALPHA)
            pg.draw.circle(glow, (255, 150, 45, alpha), glow.get_rect().center, radius)
            surface.blit(glow, glow.get_rect(center=(round(self.trail[index - 1][0]), round(self.trail[index - 1][1]))), special_flags=pg.BLEND_ADD)


class PowerUp(pg.sprite.Sprite):
    """
    Floating power-up drop from destroyed enemies.
    
    Base types (all levels):  shield, triple, speed
    Extra types (level 3+):   health, power_laser, missile
    """
    BASE_TYPES  = ["shield", "triple", "speed"]
    EXTRA_TYPES = ["health", "power_laser", "missile"]

    def __init__(self, game, x, y, ptype=None):
        super().__init__()
        self.game = game
        self.type = ptype or random.choice(self.BASE_TYPES)
        
        # Load asset based on type
        self.image = self.game.assets.get_image(f"powerup_{self.type}", 32, 32)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed_y = 120.0

    def update(self, dt):
        self.rect.y += self.speed_y * dt
        # Clean up if it falls off bottom screen
        if self.rect.top > self.game.height:
            self.kill()
