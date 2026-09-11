# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg
try:
    from fx import spawn_sparks, spawn_explosion
except ModuleNotFoundError:
    from ..fx import spawn_sparks, spawn_explosion



class Boss(pg.sprite.Sprite):
    """
    Base multi-phase boss entity with segmented health, directional shields,
    invulnerability windows, EMP phase shifts, and telegraph integration.
    """

    def __init__(
        self,
        game,
        hp_mult=1.0,
        spd_mult=1.0,
        boss_key=None,
        laser_key=None,
        title="CRIMSON MOTHERSHIP",
        base_health=600,
        base_shield=0,
    ):
        super().__init__()
        self.game = game
        self.boss_key = boss_key or "boss"
        self.laser_key = laser_key or "laser_enemy"
        self.boss_title = title
        
        self.image = self.game.assets.get_image(self.boss_key, 160, 110)
        self.rect = self.image.get_rect(center=(self.game.width // 2, -120))

        # Multipliers and Stats
        self.hp_mult = hp_mult
        self.spd_mult = spd_mult
        self.max_health = int(base_health * hp_mult)
        self.health = self.max_health

        self.max_shield = int(base_shield * hp_mult)
        self.shield = self.max_shield

        self.speed_x = 110 * spd_mult
        self.target_y = 120
        self.score_value = int(6000 * hp_mult)

        # Multi-Phase System
        self.attack_phase = 1
        self.max_phases = 3
        self.phase_thresholds = [0.66, 0.33]  # Triggers Phase 2 at <=66%, Phase 3 at <=33%
        self.phase_subtitle = "PHASE 1"

        # Invulnerability & Phase Transition Effects
        self.invulnerable_timer = 0.0
        self.phase_notification_text = ""
        self.phase_notification_timer = 0.0

        # Movement & Attack Timers
        self.shoot_timer = 2.0
        self.minions = []
        self.supernova_active = False
        self.supernova_timer = 0.0
        self.supernova_max = 10.0

    @property
    def boss_name(self):
        return f"{self.boss_title} — {self.phase_subtitle.upper()}"

    @property
    def is_invulnerable(self):
        return self.invulnerable_timer > 0

    def trigger_phase_transition(self, new_phase, title, subtitle):
        """Executes a dramatic EMP phase shift, clearing player projectiles and notifying HUD."""
        self.attack_phase = new_phase
        self.phase_subtitle = subtitle
        self.invulnerable_timer = 0.8
        self.phase_notification_text = f"{title}: {subtitle}"
        self.phase_notification_timer = 2.5

        state = getattr(self.game, "state", None)
        if state:
            # 1. Clear player lasers via EMP pulse
            if hasattr(state, "player_lasers"):
                state.player_lasers.empty()

            # 2. Spawn visual EMP shockwave ring
            if hasattr(state, "telegraphs") and state.telegraphs:
                state.telegraphs.create_emp_blast(self.rect.centerx, self.rect.centery)
                state.telegraphs.notify_boss_phase(title, subtitle)

            # 3. Camera effects (hit stop + screen shake)
            if hasattr(state, "camera") and state.camera:
                state.camera.trigger_hit_stop(0.06)
                state.camera.add_shake(0.45, 10.0)
            elif hasattr(state, "trigger_shake"):
                state.trigger_shake(0.45, 10)

            # 4. Audio cues
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.trigger_ducking(0.8, 0.4)
                self.game.audio.play_sfx("zap", pos_x=self.rect.centerx, volume_mult=1.0)
                self.game.audio.play_sfx("shield_up", pos_x=self.rect.centerx, volume_mult=0.9)

        self.on_phase_enter(new_phase)

    def on_phase_enter(self, new_phase):
        """Override in subclasses to initialize phase-specific minions or behaviors."""
        pass

    def get_hit(self, damage):
        """Processes incoming damage with invulnerability check and shield absorption."""
        state = getattr(self.game, "state", None)

        if self.invulnerable_timer > 0:
            if state and hasattr(state, "particles"):
                spawn_sparks(state.particles, self.rect.centerx, self.rect.bottom, (0, 1), color=(0, 255, 255), count=6)
            return False

        # Shield absorption
        if self.shield > 0:
            absorbed = min(self.shield, damage)
            self.shield -= absorbed
            damage -= absorbed
            if state and hasattr(state, "particles"):
                spawn_sparks(state.particles, self.rect.centerx, self.rect.centery, (0, 1), color=(80, 200, 255), count=10)
            if damage <= 0:
                return False

        self.health -= damage

        # Check phase transitions
        hp_ratio = self.health / max(1, self.max_health)
        if self.attack_phase == 1 and hp_ratio <= self.phase_thresholds[0]:
            self.trigger_phase_transition(2, f"{self.boss_title}", "PHASE 2: COMBAT ESCALATION")
        elif self.attack_phase == 2 and hp_ratio <= self.phase_thresholds[1]:
            self.trigger_phase_transition(3, f"{self.boss_title}", "PHASE 3: CORE OVERCLOCK")

        if self.health <= 0:
            self.health = 0
            self.on_defeat()
            self.kill()
            return True
        return False

    def on_defeat(self):
        """Clean up any active minions or hazards upon boss destruction."""
        for minion in list(self.minions):
            if minion.alive():
                minion.kill()
        self.minions.clear()

    def update(self, dt):
        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)

        if self.phase_notification_timer > 0:
            self.phase_notification_timer = max(0.0, self.phase_notification_timer - dt)

        # Entrance movement
        if self.rect.centery < self.target_y:
            self.rect.y += 85 * dt
        else:
            # Sweeping patrol
            self.rect.x += self.speed_x * dt
            if self.rect.left < 50:
                self.rect.left = 50
                self.speed_x = abs(self.speed_x)
            elif self.rect.right > self.game.width - 50:
                self.rect.right = self.game.width - 50
                self.speed_x = -abs(self.speed_x)

        # Update firing timer & logic
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
        else:
            self.shoot()
            self.reset_shoot_timer()

    def reset_shoot_timer(self):
        if self.attack_phase == 1:
            self.shoot_timer = 1.4
        elif self.attack_phase == 2:
            self.shoot_timer = 0.85
        else:
            self.shoot_timer = 0.45

    def shoot(self):
        """Default base boss shooting behavior."""
        state = getattr(self.game, "state", None)
        if not state or not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser
        if self.attack_phase == 1:
            l1 = Laser(self.game, self.rect.centerx - 35, self.rect.bottom, speed_y=380, img_name=self.laser_key)
            l2 = Laser(self.game, self.rect.centerx + 35, self.rect.bottom, speed_y=380, img_name=self.laser_key)
            state.enemy_lasers.add(l1, l2)
            state.all_sprites.add(l1, l2)
        elif self.attack_phase == 2:
            l1 = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=420, angle=0)
            l2 = Laser(self.game, self.rect.centerx - 30, self.rect.bottom, speed_y=400, angle=-18)
            l3 = Laser(self.game, self.rect.centerx + 30, self.rect.bottom, speed_y=400, angle=18)
            for l in (l1, l2, l3):
                l.raw_image = self.game.assets.get_image("laser_boss", 16, 40)
                l.image = pg.transform.rotate(l.raw_image, -l.angle) if l.angle != 0 else l.raw_image
            state.enemy_lasers.add(l1, l2, l3)
            state.all_sprites.add(l1, l2, l3)
        else:
            angle = random.uniform(-40, 40)
            l = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=480, angle=angle, img_name=self.laser_key)
            state.enemy_lasers.add(l)
            state.all_sprites.add(l)

    def draw_extras(self, surface):
        """Renders extra visuals like invulnerability bubble or active shields."""
        if self.invulnerable_timer > 0:
            pulse = int(140 + 80 * math.sin(pg.time.get_ticks() * 0.03))
            inv_surf = pg.Surface(self.rect.size, pg.SRCALPHA)
            pg.draw.ellipse(inv_surf, (0, 220, 255, pulse), inv_surf.get_rect(), 3)
            surface.blit(inv_surf, self.rect.topleft, special_flags=pg.BLEND_ADD)
        elif self.shield > 0:
            pulse = int(90 + 40 * math.sin(pg.time.get_ticks() * 0.015))
            sh_surf = pg.Surface(self.rect.size, pg.SRCALPHA)
            pg.draw.ellipse(sh_surf, (80, 160, 255, pulse), sh_surf.get_rect(), 2)
            surface.blit(sh_surf, self.rect.topleft, special_flags=pg.BLEND_ADD)
