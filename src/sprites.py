import pygame as pg
import random
import math

class Player(pg.sprite.Sprite):
    def __init__(self, game, x, y):
        super().__init__()
        self.game = game
        self.image = self.game.assets.get_image("player", 60, 60)
        self.rect = self.image.get_rect(center=(x, y))
        
        # Stats
        self.speed = 400.0  # Pixels per second
        self.max_health = 100
        self.health = 100
        self.max_shield = 100
        self.shield = 0  # Starts at 0, goes up with Shield PowerUp
        self.lives = 3
        
        # Weapon properties
        self.shoot_cooldown = 0.25 # seconds
        self.shoot_timer = 0.0
        
        # Power-up states
        self.triple_shot_timer = 0.0
        self.speed_boost_timer = 0.0
        self.shield_active = False

    def get_hit(self, damage):
        """Handle damage to player ship, affecting shield first then health."""
        if self.shield > 0:
            self.shield -= damage
            if self.shield < 0:
                self.health += self.shield # Apply remaining damage to health
                self.shield = 0
        else:
            self.health -= damage
            
        # Trigger screen shake on taking damage
        if hasattr(self.game.state, 'trigger_shake'):
            self.game.state.trigger_shake(duration=0.2, magnitude=5)
            
        if self.health <= 0:
            self.lives -= 1
            self.health = self.max_health
            self.shield = 0
            # Reset position
            self.rect.center = (self.game.width // 2, self.game.height - 80)
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
            
        self.shield_active = self.shield > 0

        # Movement keys
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
            
            # Apply speed boost power-up if active
            current_speed = self.speed * 1.5 if self.speed_boost_timer > 0 else self.speed
            
            self.rect.x += dx * current_speed * dt
            self.rect.y += dy * current_speed * dt

        # Screen boundaries check
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > self.game.width:
            self.rect.right = self.game.width
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > self.game.height:
            self.rect.bottom = self.game.height

        # Fire weapons
        if keys[pg.K_SPACE] or keys[pg.K_j]:
            self.shoot()

    def shoot(self):
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_cooldown
            
            # Retrieve laser groups from active state
            state = self.game.state
            if not hasattr(state, 'player_lasers'):
                return
                
            if self.triple_shot_timer > 0:
                # Fire 3 lasers (center, diagonal-left, diagonal-right)
                laser_center = Laser(self.game, self.rect.centerx, self.rect.top, speed_y=-600, angle=0)
                laser_left = Laser(self.game, self.rect.left, self.rect.top, speed_y=-550, angle=-15)
                laser_right = Laser(self.game, self.rect.right, self.rect.top, speed_y=-550, angle=15)
                state.player_lasers.add(laser_center, laser_left, laser_right)
                state.all_sprites.add(laser_center, laser_left, laser_right)
            else:
                # Single center shot
                laser = Laser(self.game, self.rect.centerx, self.rect.top, speed_y=-600)
                state.player_lasers.add(laser)
                state.all_sprites.add(laser)


class Laser(pg.sprite.Sprite):
    def __init__(self, game, x, y, speed_y, angle=0):
        super().__init__()
        self.game = game
        self.angle = angle
        
        # Select appropriate image based on direction (player moves up/negative, enemy moves down/positive)
        is_player = speed_y < 0
        img_name = "laser_player" if is_player else "laser_enemy"
        
        self.raw_image = self.game.assets.get_image(img_name, 12, 32)
        if self.angle != 0:
            self.image = pg.transform.rotate(self.raw_image, -self.angle)
        else:
            self.image = self.raw_image
            
        self.rect = self.image.get_rect(center=(x, y))
        
        # Speeds
        self.speed_y = speed_y
        self.speed_x = speed_y * math.sin(math.radians(self.angle)) if self.angle != 0 else 0
        if is_player:
            # Adjust horizontal speed correctly for shooting angle
            self.speed_x = -abs(speed_y) * math.sin(math.radians(self.angle))
            self.speed_y = -abs(speed_y) * math.cos(math.radians(self.angle))
        else:
            self.speed_x = abs(speed_y) * math.sin(math.radians(self.angle))
            self.speed_y = abs(speed_y) * math.cos(math.radians(self.angle))

    def update(self, dt):
        self.rect.x += self.speed_x * dt
        self.rect.y += self.speed_y * dt
        
        # Kill if it leaves screen boundaries
        if self.rect.bottom < 0 or self.rect.top > self.game.height or self.rect.right < 0 or self.rect.left > self.game.width:
            self.kill()


class Enemy(pg.sprite.Sprite):
    def __init__(self, game, x, y, enemy_type="scout"):
        super().__init__()
        self.game = game
        self.type = enemy_type
        
        # Configure variables based on enemy type
        if self.type == "scout":
            self.image = self.game.assets.get_image("enemy_scout", 45, 45)
            self.speed_y = random.randint(180, 240)
            self.speed_x = 0
            self.max_health = 10
            self.shoot_delay = 9999.0 # Scouts don't shoot
            self.score_value = 100
        elif self.type == "stinger":
            self.image = self.game.assets.get_image("enemy_stinger", 48, 48)
            self.speed_y = random.randint(100, 150)
            # Gentle side-to-side sweeping motion
            self.speed_x = random.choice([-80, 80])
            self.max_health = 20
            self.shoot_delay = random.uniform(1.5, 2.5)
            self.score_value = 250
        elif self.type == "cruiser":
            self.image = self.game.assets.get_image("enemy_cruiser", 70, 70)
            self.speed_y = random.randint(50, 80)
            self.speed_x = 0
            self.max_health = 60
            self.shoot_delay = random.uniform(2.0, 3.5)
            self.score_value = 500
        else: # default placeholder
            self.image = self.game.assets.get_image("enemy_scout", 45, 45)
            self.speed_y = 150
            self.speed_x = 0
            self.max_health = 10
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
            
        if self.type == "stinger":
            # Shoot standard red laser down
            laser = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=400)
            state.enemy_lasers.add(laser)
            state.all_sprites.add(laser)
        elif self.type == "cruiser":
            # Shoot double lasers
            l1 = Laser(self.game, self.rect.left + 15, self.rect.bottom, speed_y=350)
            l2 = Laser(self.game, self.rect.right - 15, self.rect.bottom, speed_y=350)
            state.enemy_lasers.add(l1, l2)
            state.all_sprites.add(l1, l2)


class Boss(pg.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.image = self.game.assets.get_image("boss", 150, 100)
        self.rect = self.image.get_rect(center=(self.game.width // 2, -100))
        
        # Stats
        self.max_health = 500
        self.health = 500
        self.speed_x = 100
        self.target_y = 120
        self.score_value = 5000
        
        # Attack intervals
        self.shoot_timer = 2.0
        self.attack_phase = 1

    def get_hit(self, damage):
        self.health -= damage
        # Phase transitions
        if self.health <= 150:
            self.attack_phase = 3
        elif self.health <= 350:
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

        if self.attack_phase == 1:
            # Fire standard red lasers from left and right gun pods
            l1 = Laser(self.game, self.rect.centerx - 40, self.rect.bottom, speed_y=380)
            l2 = Laser(self.game, self.rect.centerx + 40, self.rect.bottom, speed_y=380)
            state.enemy_lasers.add(l1, l2)
            state.all_sprites.add(l1, l2)
            
        elif self.attack_phase == 2:
            # Fire heavy green plasma beams down-left, down, down-right
            l1 = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=420, angle=0)
            l2 = Laser(self.game, self.rect.centerx - 30, self.rect.bottom, speed_y=400, angle=-15)
            l3 = Laser(self.game, self.rect.centerx + 30, self.rect.bottom, speed_y=400, angle=15)
            
            # Re-key them as boss lasers (heavy plasma green texture)
            for l in (l1, l2, l3):
                l.raw_image = self.game.assets.get_image("laser_boss", 16, 40)
                l.image = pg.transform.rotate(l.raw_image, -l.angle) if l.angle != 0 else l.raw_image
                
            state.enemy_lasers.add(l1, l2, l3)
            state.all_sprites.add(l1, l2, l3)
            
        elif self.attack_phase == 3:
            # Rapid fire sweeping single lasers
            angle = random.uniform(-40, 40)
            l = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=480, angle=angle)
            state.enemy_lasers.add(l)
            state.all_sprites.add(l)


class PowerUp(pg.sprite.Sprite):
    def __init__(self, game, x, y, ptype=None):
        super().__init__()
        self.game = game
        self.type = ptype or random.choice(["shield", "triple", "speed"])
        
        # Load asset based on type
        self.image = self.game.assets.get_image(f"powerup_{self.type}", 32, 32)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed_y = 120.0

    def update(self, dt):
        self.rect.y += self.speed_y * dt
        # Clean up if it falls off bottom screen
        if self.rect.top > self.game.height:
            self.kill()

