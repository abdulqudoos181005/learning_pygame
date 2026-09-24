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

        # Load ship class & color identity from game loadout
        loadout = getattr(self.game, 'loadout', {"hull": "interceptor", "color": "blue"})
        self.hull_type = loadout.get("hull", "interceptor").lower()
        self.color_name = loadout.get("color", "blue").lower()

        # Hull identity presets (Interceptor: balanced, Cruiser: heavy/tanky/wide, Vanguard: fast/stealth/missile)
        hull_asset_keys = {
            "interceptor": f"player_fleet/interceptor_strike_{self.color_name}",
            "cruiser": f"player_fleet/heavy_cruiser_assault_{self.color_name}",
            "vanguard": f"player_fleet/stealth_vanguard_bomber_{self.color_name}",
        }
        self.sprite_key = hull_asset_keys.get(self.hull_type, f"player_fleet/interceptor_strike_{self.color_name}")
        self.base_image = self.game.assets.get_image(self.sprite_key, 60, 60)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.velocity = pg.Vector2(0, 0)

        # Baseline stats by Hull Class
        if self.hull_type == "cruiser":
            self.max_speed = 340.0
            self.acceleration = 1500.0
            self.max_health = 140
            self.health = 140
            self.max_shield = 120
            self.shoot_cooldown = 0.28
            self.starting_missiles = 3
        elif self.hull_type == "vanguard":
            self.max_speed = 460.0
            self.acceleration = 2100.0
            self.max_health = 80
            self.health = 80
            self.max_shield = 80
            self.shoot_cooldown = 0.22
            self.starting_missiles = 4
        else:  # interceptor
            self.max_speed = 400.0
            self.acceleration = 1800.0
            self.max_health = 100
            self.health = 100
            self.max_shield = 100
            self.shoot_cooldown = 0.25
            self.starting_missiles = 3

        self.drag = 8.0
        self.bank_angle = 0.0
        self.recoil_timer = 0.0
        self.hit_stutter = 0.0
        self.muzzle_timer = 0.0
        self.missile_hold_timer = 0.0
        self.presentation = PlayerPresentation(self)

        # Stats
        self.speed = self.max_speed
        self.shield = 0  # Starts at 0, goes up with Shield PowerUp
        self.lives = 3
        self.invincible_timer = 0.0
        self.flash_timer = 0.0

        # Weapon properties
        self.shoot_timer = 0.0
        self.base_laser_tier = 1

        # Power-up states (Sprint 2: triple-shot & speed timers increased to 12s)
        self.triple_shot_timer = 0.0
        self.speed_boost_timer = 0.0
        self.shield_active = False
        self.laser_power_timer = 0.0   # Power laser: next-tier boost for 10s

        # Sprint 15: Tech Tree Upgrades & Secondary Ordnance Loadout
        self.ordnance_type = loadout.get("ordnance", "missile").lower()
        upgrades = {}
        if hasattr(self.game, 'save_system') and self.game.save_system:
            curr_user = getattr(self.game, 'current_user', None)
            user_id = curr_user["id"] if curr_user and isinstance(curr_user, dict) and "id" in curr_user else None
            hangar_data = self.game.save_system.load_hangar(user_id)
            upgrades = hangar_data.get("upgrades", {})
        elif hasattr(self.game, 'upgrades'):
            upgrades = getattr(self.game, 'upgrades', {})

        armor_tier = upgrades.get("armor", 0)
        shield_tier = upgrades.get("shield", 0)
        magnet_tier = upgrades.get("magnet", 0)
        graze_tier = upgrades.get("graze", 0)
        ordnance_tier = upgrades.get("ordnance_bay", 0)

        self.max_health += armor_tier * 15
        self.health = self.max_health
        self.max_shield += shield_tier * 15
        self.shield_reboot_bonus = 1.0 + shield_tier * 0.1
        self.magnet_radius = 80.0 + magnet_tier * 45.0
        self.starting_missiles += ordnance_tier
        self.missile_cooldown_base = max(0.2, 0.5 - ordnance_tier * 0.05)

        self.missile_count = self.starting_missiles  # Stored homing missiles (activated by M key)
        self.missile_cooldown = 0.0    # Prevent spamming missiles

        # Sprint 14 Phase 3: Adrenaline / Overdrive Gauge & Graze Mechanics
        self.overdrive = 0.0
        self.max_overdrive = 100.0
        self.overdrive_active = False
        self.overdrive_timer = 0.0
        self.OVERDRIVE_DURATION = 4.0
        self.graze_radius = 42 + graze_tier * 6
        self.graze_score_bonus = 50 + graze_tier * 15
        self.graze_charge_amount = 12.0 + graze_tier * 2.5
        self.graze_count = 0

    def add_overdrive(self, amount):
        """Adds charge to the Overdrive gauge when not actively in Overdrive."""
        if not self.overdrive_active:
            self.overdrive = min(self.max_overdrive, self.overdrive + amount)

    def activate_overdrive(self):
        """Activates Overdrive mode if gauge is 100% full."""
        if self.overdrive >= self.max_overdrive and not self.overdrive_active:
            self.overdrive_active = True
            self.overdrive_timer = self.OVERDRIVE_DURATION
            self.overdrive = 0.0
            return True
        return False

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
            if shield_broke:
                if hasattr(self.game, 'audio') and self.game.audio:
                    self.game.audio.play_sfx("shield_down", pos_x=self.pos_x)
                elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
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
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.trigger_ducking(duration=0.5, factor=0.35)
                self.game.audio.play_sfx("player_death", pos_x=self.pos_x)
            elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
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
        if self.overdrive_active:
            self.overdrive_timer -= dt
            if self.overdrive_timer <= 0:
                self.overdrive_active = False
                self.overdrive_timer = 0.0
        self.recoil_timer = max(0.0, self.recoil_timer - dt)
        self.hit_stutter = max(0.0, self.hit_stutter - dt)
        self.muzzle_timer = max(0.0, self.muzzle_timer - dt)
        self.presentation.update(dt)

        # Track invincibility blink state — alpha is applied AFTER self.image is set below
        _blink_alpha = None
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            self.flash_timer += dt
            if self.flash_timer >= 0.12:
                self.flash_timer = 0.0
            # Alternate between dim (90) and full (255) every blink half-cycle
            _blink_alpha = 90 if (self.flash_timer < 0.06) else 255
        else:
            self.flash_timer = 0.0

        self.shield_active = self.shield > 0

        # Sprint 11 / Pillar G: Action Graph Input Routing
        # The player sprite reads action states from game.input instead of raw keycodes directly
        inp = getattr(self.game, 'input', None)
        dx, dy = 0.0, 0.0
        
        if inp:
            if inp.is_held("up"): dy -= 1
            if inp.is_held("down"): dy += 1
            if inp.is_held("left"): dx -= 1
            if inp.is_held("right"): dx += 1
        else:
            keys = pg.key.get_pressed()
            if keys[pg.K_w] or keys[pg.K_UP]: dy -= 1
            if keys[pg.K_s] or keys[pg.K_DOWN]: dy += 1
            if keys[pg.K_a] or keys[pg.K_LEFT]: dx -= 1
            if keys[pg.K_d] or keys[pg.K_RIGHT]: dx += 1

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
        # Assign image FIRST, then apply blink alpha so it lands on the correct Surface object.
        self.image = rotated
        if _blink_alpha is not None:
            self.image.set_alpha(_blink_alpha)
        else:
            self.image.set_alpha(255)
        self.rect = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

        # Fire regular weapons via InputMap action
        is_firing = inp.is_held("fire") if inp else (pg.key.get_pressed()[pg.K_SPACE] or pg.key.get_pressed()[pg.K_j])
        if is_firing:
            self.shoot()
        
        # Launch missile via InputMap action
        is_missile = inp.is_held("missile") if inp else pg.key.get_pressed()[pg.K_m]
        if is_missile and self.missile_count > 0 and self.missile_cooldown <= 0:
            self.missile_hold_timer += dt
            self._launch_missile()
            self.missile_cooldown = 0.5  # Half-second cooldown between launches
        elif not is_missile:
            self.missile_hold_timer = 0.0

        # Sprint 14 Phase 3: Trigger Overdrive via InputMap or keyboard shortcut (F or SPACE+M)
        is_overdrive = False
        if inp:
            is_overdrive = inp.is_pressed("overdrive")
        else:
            keys = pg.key.get_pressed()
            is_overdrive = keys[pg.K_f] or (keys[pg.K_SPACE] and keys[pg.K_m])

        if is_overdrive and self.overdrive >= self.max_overdrive and not self.overdrive_active:
            state = getattr(self.game, 'state', None)
            if state and hasattr(state, 'activate_player_overdrive'):
                state.activate_player_overdrive()
            else:
                self.activate_overdrive()

    def shoot(self):
        if self.shoot_timer <= 0:
            # Overdrive grants 2x supercharged firing rate
            effective_cooldown = self.shoot_cooldown * 0.5 if self.overdrive_active else self.shoot_cooldown
            self.shoot_timer = effective_cooldown
            self.recoil_timer = 0.06
            self.muzzle_timer = 0.07
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_sfx("laser", pos_x=self.pos_x, pitch_variance=True)
            elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
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
                spread_angle = 20 if self.hull_type == "cruiser" else (12 if self.hull_type == "vanguard" else 15)
                laser_center = Laser(self.game, self.rect.centerx, self.rect.top, speed_y=-600, angle=0,   damage=laser_dmg, img_name=img_name)
                laser_left   = Laser(self.game, self.rect.left,   self.rect.top, speed_y=-550, angle=-spread_angle, damage=laser_dmg, img_name=img_name)
                laser_right  = Laser(self.game, self.rect.right,  self.rect.top, speed_y=-550, angle=spread_angle,  damage=laser_dmg, img_name=img_name)
                state.player_lasers.add(laser_center, laser_left, laser_right)
                state.all_sprites.add(laser_center, laser_left, laser_right)
            elif self.hull_type == "cruiser":
                # Heavy Cruiser: Dual-barrel wide volley
                left_x = self.rect.centerx - 16
                right_x = self.rect.centerx + 16
                laser_l = Laser(self.game, left_x, self.rect.top, speed_y=-600, damage=int(laser_dmg * 0.7), img_name=img_name)
                laser_r = Laser(self.game, right_x, self.rect.top, speed_y=-600, damage=int(laser_dmg * 0.7), img_name=img_name)
                state.player_lasers.add(laser_l, laser_r)
                state.all_sprites.add(laser_l, laser_r)
            else:
                # Single center shot (Interceptor / Vanguard standard)
                laser = Laser(self.game, self.rect.centerx, self.rect.top, speed_y=-600, damage=laser_dmg, img_name=img_name)
                state.player_lasers.add(laser)
                state.all_sprites.add(laser)

    def _missile_target(self):
        state = self.game.state
        enemies = getattr(state, "enemies", ())
        targetable = [e for e in enemies if not getattr(e, "is_cloaked", False)]
        return max(targetable, key=lambda enemy: enemy.health, default=None)

    def draw_presentation_back(self, surface):
        self.presentation.draw_back(surface)

    def draw_presentation_front(self, surface):
        self.presentation.draw_front(surface)

    def _launch_missile(self):
        """Spawns equipped Secondary Ordnance (Missile, Cluster Bomb, or Ion EMP)."""
        state = self.game.state
        if not hasattr(state, 'enemies') or not hasattr(state, 'missiles'):
            return
        
        self.missile_count -= 1
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_sfx("laser_pew", pos_x=self.pos_x)
        elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
            self.game.assets.get_sound("laser_pew").play()

        if self.ordnance_type == "cluster":
            ordnance = ClusterMissile(self.game, self.rect.centerx, self.rect.top, state.enemies)
        elif self.ordnance_type == "ion_emp":
            ordnance = IonEMPOrb(self.game, self.rect.centerx, self.rect.top, state.enemies)
        else:
            ordnance = Missile(self.game, self.rect.centerx, self.rect.top, state.enemies)

        state.missiles.add(ordnance)
        state.all_sprites.add(ordnance)


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
        self.grazed = False  # Sprint 14 Phase 3: Tracks near-miss bullet grazing
        
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
        elif self.type == "aegis_defender":
            self.image = self.game.assets.get_image(_sprite_key("aegis_defender", "enemy_cruiser"), 64, 64)
            self.speed_y = random.randint(45, 70) * spd_mult
            self.speed_x = 0
            self.max_health = int(85 * hp_mult)
            self.shoot_delay = 2.5
            self.score_value = 600
            self.shield_active = True
        elif self.type == "sniper_skiff":
            self.image = self.game.assets.get_image(_sprite_key("sniper_skiff", "enemy_stinger"), 48, 48)
            self.speed_y = 120 * spd_mult
            self.speed_x = random.choice([-70, 70]) * spd_mult
            self.max_health = int(35 * hp_mult)
            self.shoot_delay = 2.0
            self.score_value = 450
        elif self.type == "phase_phantom":
            self.image = self.game.assets.get_image(_sprite_key("phase_phantom", "enemy_scout"), 46, 46)
            self.speed_y = 160 * spd_mult
            self.speed_x = 0
            self.max_health = int(45 * hp_mult)
            self.shoot_delay = 2.5
            self.score_value = 500
            self.is_cloaked = True
        elif self.type == "hive_carrier":
            self.image = self.game.assets.get_image(_sprite_key("hive_carrier", "enemy_cruiser"), 84, 84)
            self.speed_y = 60 * spd_mult
            self.speed_x = 0
            self.max_health = int(180 * hp_mult)
            self.shoot_delay = 2.8
            self.score_value = 800
        elif self.type == "swarmer":
            self.image = self.game.assets.get_image(_sprite_key("swarmer", "enemy_scout"), 22, 22)
            self.speed_y = 250 * spd_mult
            self.speed_x = 0
            self.max_health = 10
            self.shoot_delay = 9999.0
            self.score_value = 80
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
        
        # Sprint 11 / Pillar I: Telegraph & Elite Enemy attributes
        self.is_elite = (self.type == "cruiser" and random.random() < 0.25)
        if self.is_elite:
            self.max_health = int(self.max_health * 1.5)
            self.health = self.max_health
            self.score_value = int(self.score_value * 2)
            self.nameplate = "SHADOW ELITE"

        self.telegraph_timer = 0.0

        # Sine wave horizontal movement configuration (only for certain enemies)
        self.wave_timer = random.uniform(0, 2 * math.pi)
        
    def get_hit(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.kill()
            return True # Destroyed
        return False

    def update(self, dt):
        if self.telegraph_timer > 0:
            self.telegraph_timer -= dt

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
            
        # Shooting logic with 400ms telegraph warning
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
            if self.shoot_timer <= 0.4 and self.telegraph_timer <= 0 and self.type == "cruiser":
                self.telegraph_timer = 0.4
        else:
            self.shoot()
            self.shoot_timer = self.shoot_delay

    def shoot(self):
        state = self.game.state
        if not hasattr(state, 'enemy_lasers'):
            return
            
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.65)
        elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
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


# Boss Archetypes & Minions imported from modular boss package
from boss import (
    Boss,
    GoliathDreadnought,
    ApexVoidLeviathan,
    OrbitalShieldBit,
    EscortDrone,
    ProximityMine,
)

# Sprint 14 Phase 2: Elite Enemy Archetypes imported from modular enemies package
from enemies import (
    AegisDefender,
    SniperSkiff,
    RailgunSlug,
    PhasePhantom,
    HiveCarrier,
    Swarmer,
)


def create_enemy(game, x, y, enemy_type="scout", hp_mult=1.0, spd_mult=1.0, armada_folder=None, laser_key=None):
    """Factory helper to instantiate specialized enemy classes by type."""
    if enemy_type == "aegis_defender":
        return AegisDefender(game, x, y, hp_mult=hp_mult, spd_mult=spd_mult, armada_folder=armada_folder, laser_key=laser_key)
    elif enemy_type == "sniper_skiff":
        return SniperSkiff(game, x, y, hp_mult=hp_mult, spd_mult=spd_mult, armada_folder=armada_folder, laser_key=laser_key)
    elif enemy_type == "phase_phantom":
        return PhasePhantom(game, x, y, hp_mult=hp_mult, spd_mult=spd_mult, armada_folder=armada_folder, laser_key=laser_key)
    elif enemy_type == "hive_carrier":
        return HiveCarrier(game, x, y, hp_mult=hp_mult, spd_mult=spd_mult, armada_folder=armada_folder, laser_key=laser_key)
    elif enemy_type == "swarmer":
        return Swarmer(game, x, y, spd_mult=spd_mult, armada_folder=armada_folder)
    else:
        return Enemy(game, x, y, enemy_type=enemy_type, hp_mult=hp_mult, spd_mult=spd_mult, armada_folder=armada_folder, laser_key=laser_key)




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
        """Returns the enemy sprite with the highest current health, or None. Skips cloaked enemies."""
        best    = None
        best_hp = -1
        for e in self.enemy_group:
            if getattr(e, "is_cloaked", False):
                continue
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


class ClusterMissile(pg.sprite.Sprite):
    """
    Sprint 15 Secondary Ordnance: Cluster Bomb Pod.
    Seeks enemies, deals direct damage and bursts into 6 explosive submunition fragments.
    """
    SPEED = 420.0
    TURN_RATE = 3.0
    DAMAGE = 25

    def __init__(self, game, x, y, enemy_group):
        super().__init__()
        self.game = game
        self.enemy_group = enemy_group
        self.damage = self.DAMAGE
        self.image = self.game.assets.get_image("cluster_missile", 18, 32)
        self.rect = self.image.get_rect(center=(x, y))
        self.angle_rad = 0.0
        self.fx = float(x)
        self.fy = float(y)
        self.trail = []
        self.lifetime = 3.0

    def _find_target(self):
        best = None
        best_hp = -1
        for e in self.enemy_group:
            if getattr(e, "is_cloaked", False):
                continue
            if e.health > best_hp:
                best_hp = e.health
                best = e
        return best

    def detonate(self):
        """Detonates warhead, spawning 6 radial cluster fragments and exploding."""
        state = getattr(self.game, 'state', None)
        if state and hasattr(state, 'missiles'):
            for i in range(6):
                ang = i * 60 + random.uniform(-10, 10)
                frag = ClusterFragment(self.game, self.rect.centerx, self.rect.centery, ang)
                state.missiles.add(frag)
                state.all_sprites.add(frag)
        self.kill()

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.detonate()
            return

        self.trail.append((self.fx, self.fy))
        if len(self.trail) > 12:
            self.trail.pop(0)

        target = self._find_target()
        if target:
            dx = target.rect.centerx - self.fx
            dy = target.rect.centery - self.fy
            desired_angle = math.atan2(dy, dx) + math.pi / 2
            diff = (desired_angle - self.angle_rad + math.pi) % (2 * math.pi) - math.pi
            max_turn = self.TURN_RATE * dt
            self.angle_rad += max(-max_turn, min(max_turn, diff))

        self.fx += math.sin(self.angle_rad) * self.SPEED * dt
        self.fy -= math.cos(self.angle_rad) * self.SPEED * dt
        self.rect.center = (int(self.fx), int(self.fy))

        degrees = math.degrees(self.angle_rad)
        base_img = self.game.assets.get_image("cluster_missile", 18, 32)
        self.image = pg.transform.rotate(base_img, -degrees)
        self.rect = self.image.get_rect(center=self.rect.center)

        if (self.rect.bottom < 0 or self.rect.top > self.game.height
                or self.rect.right < 0 or self.rect.left > self.game.width):
            self.kill()

    def draw_trail(self, surface):
        if len(self.trail) < 2:
            return
        for index in range(1, len(self.trail)):
            alpha = int(30 + index * 15)
            radius = max(2, int(index / 4))
            glow = pg.Surface((radius * 6, radius * 6), pg.SRCALPHA)
            pg.draw.circle(glow, (255, 100, 20, alpha), glow.get_rect().center, radius)
            surface.blit(glow, glow.get_rect(center=(round(self.trail[index - 1][0]), round(self.trail[index - 1][1]))), special_flags=pg.BLEND_ADD)


class ClusterFragment(pg.sprite.Sprite):
    """Explosive submunition fragment ejected from ClusterMissile."""
    SPEED = 480.0
    DAMAGE = 15

    def __init__(self, game, x, y, angle_deg):
        super().__init__()
        self.game = game
        self.damage = self.DAMAGE
        self.angle_deg = angle_deg
        self.rad = math.radians(angle_deg)
        self.image = self.game.assets.get_image("cluster_fragment", 12, 12)
        self.rect = self.image.get_rect(center=(x, y))
        self.fx = float(x)
        self.fy = float(y)
        self.speed_x = math.cos(self.rad) * self.SPEED
        self.speed_y = math.sin(self.rad) * self.SPEED
        self.lifetime = 0.7

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        self.fx += self.speed_x * dt
        self.fy += self.speed_y * dt
        self.rect.center = (int(self.fx), int(self.fy))
        if (self.rect.bottom < 0 or self.rect.top > self.game.height
                or self.rect.right < 0 or self.rect.left > self.game.width):
            self.kill()

    def draw_trail(self, surface):
        pass


class IonEMPOrb(pg.sprite.Sprite):
    """
    Sprint 15 Secondary Ordnance: Ion Pulse EMP.
    Slow-moving piercing energy sphere that absorbs enemy lasers and shocks targets.
    """
    SPEED_Y = -220.0
    DAMAGE = 12

    def __init__(self, game, x, y, enemy_group=None):
        super().__init__()
        self.game = game
        self.damage = self.DAMAGE
        self.image = self.game.assets.get_image("ion_emp_orb", 36, 36)
        self.rect = self.image.get_rect(center=(x, y))
        self.fx = float(x)
        self.fy = float(y)
        self.lifetime = 3.5
        self.aura_radius = 48

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0 or self.rect.bottom < 0:
            self.kill()
            return

        self.fy += self.SPEED_Y * dt
        self.rect.center = (int(self.fx), int(self.fy))

        # Dissolve nearby enemy lasers
        state = getattr(self.game, 'state', None)
        if state and hasattr(state, 'enemy_lasers'):
            for laser in list(state.enemy_lasers):
                dx = laser.rect.centerx - self.rect.centerx
                dy = laser.rect.centery - self.rect.centery
                if dx * dx + dy * dy <= self.aura_radius * self.aura_radius:
                    laser.kill()
                    if hasattr(state, 'particles'):
                        from fx import spawn_sparks
                        spawn_sparks(state.particles, laser.rect.centerx, laser.rect.centery, (0, 0), color=(0, 240, 255), count=4)

    def draw_trail(self, surface):
        pulse = 1.0 + 0.2 * math.sin(pg.time.get_ticks() * 0.015)
        r = int(self.aura_radius * pulse)
        aura = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
        pg.draw.circle(aura, (0, 220, 255, 60), (r, r), r)
        pg.draw.circle(aura, (180, 255, 255, 120), (r, r), max(1, r - 6), 2)
        surface.blit(aura, aura.get_rect(center=self.rect.center), special_flags=pg.BLEND_ADD)


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
        state = getattr(self.game, 'state', None)
        player = getattr(state, 'player', None)
        if player and hasattr(player, 'rect') and hasattr(player, 'magnet_radius') and player.magnet_radius > 0:
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist < player.magnet_radius and dist > 1.0:
                self.rect.x += int((dx / dist) * 160.0 * dt)
                self.rect.y += int((dy / dist) * 160.0 * dt)
            else:
                self.rect.y += self.speed_y * dt
        else:
            self.rect.y += self.speed_y * dt
        # Clean up if it falls off bottom screen
        if self.rect.top > self.game.height:
            self.kill()


class ScoreCrystal(pg.sprite.Sprite):
    """
    Score Crystal — Transmuted from enemy bullets by the Overdrive EMP burst.
    
    Magnetizes rapidly toward the player, awarding 150 bonus score and tactile feedback.
    """
    SPEED = 180.0
    MAX_SPEED = 650.0
    ACCELERATION = 900.0

    def __init__(self, game, x, y):
        super().__init__()
        self.game = game
        self.score_value = 150
        self.image = self.game.assets.get_image("score_crystal", 18, 18)
        self.rect = self.image.get_rect(center=(x, y))
        self.fx = float(x)
        self.fy = float(y)
        self.vx = random.uniform(-60.0, 60.0)
        self.vy = random.uniform(-80.0, -10.0)
        self.lifetime = 8.0
        self.magnet_radius = 550.0

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0 or self.rect.top > self.game.height + 40:
            self.kill()
            return

        state = getattr(self.game, 'state', None)
        player = getattr(state, 'player', None)
        if player and hasattr(player, 'rect'):
            dx = player.rect.centerx - self.fx
            dy = player.rect.centery - self.fy
            dist = math.hypot(dx, dy)
            if dist < self.magnet_radius and dist > 1.0:
                nx = dx / dist
                ny = dy / dist
                self.vx += nx * self.ACCELERATION * dt
                self.vy += ny * self.ACCELERATION * dt
                spd = math.hypot(self.vx, self.vy)
                if spd > self.MAX_SPEED:
                    self.vx = (self.vx / spd) * self.MAX_SPEED
                    self.vy = (self.vy / spd) * self.MAX_SPEED
            else:
                self.vy += 80.0 * dt
        else:
            self.vy += 80.0 * dt

        self.fx += self.vx * dt
        self.fy += self.vy * dt
        self.rect.center = (int(self.fx), int(self.fy))

