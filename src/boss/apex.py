# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg
try:
    from boss.boss_base import Boss
    from boss.minions import EscortDrone
except ModuleNotFoundError:
    from .boss_base import Boss
    from .minions import EscortDrone



class ApexVoidLeviathan(Boss):
    """
    Level 10 Final Campaign Boss: Apex Void Leviathan.
    
    Phase 1 (Void Swarm): Dual heavy beam sweepers with telegraphing + escort support drones.
    Phase 2 (Danmaku Hellstorm): Complex geometric bullet hell patterns (spiral blossoms, ring pulses).
    Phase 3 (Supernova Meltdown): 10-second DPS check countdown + radial homing pulses & core explosion.
    """

    def __init__(self, game, hp_mult=1.0, spd_mult=1.0, boss_key=None, laser_key=None):
        super().__init__(
            game,
            hp_mult=hp_mult,
            spd_mult=spd_mult,
            boss_key=boss_key or "mothership_saucer_solar_gold",
            laser_key=laser_key or "laser_green_beam_stream_long",
            title="APEX VOID LEVIATHAN",
            base_health=1200,
            base_shield=100,
        )
        self.phase_subtitle = "PHASE 1: VOID SWARM"
        self.score_value = int(12000 * hp_mult)

        # Attack Pattern Counters
        self.beam_cooldown = 4.0
        self.spiral_angle = 0.0
        self.danmaku_mode = 0  # 0: Spiral, 1: Ring pulse, 2: Criss-cross
        self.danmaku_switch_timer = 3.5

        # Phase 3 Supernova State
        self.supernova_active = False
        self.supernova_timer = 10.0
        self.supernova_max = 10.0
        self.supernova_discharged = False

    def on_phase_enter(self, new_phase):
        state = getattr(self.game, "state", None)

        if new_phase == 1:
            # Spawn 2 Escort Drones
            if state:
                d1 = EscortDrone(self.game, self, side_offset=-130)
                d2 = EscortDrone(self.game, self, side_offset=130)
                self.minions.extend([d1, d2])
                if hasattr(state, "enemies"):
                    state.enemies.add(d1, d2)
                if hasattr(state, "all_sprites"):
                    state.all_sprites.add(d1, d2)

        elif new_phase == 2:
            self.phase_subtitle = "PHASE 2: DANMAKU HELLSTORM"
            self.shoot_timer = 0.25

        elif new_phase == 3:
            self.phase_subtitle = "PHASE 3: SUPERNOVA MELTDOWN"
            self.supernova_active = True
            self.supernova_timer = 10.0
            self.shoot_timer = 0.35
            # Slow side-to-side sweeping to focus on core meltdown
            self.speed_x = 40.0

    def update(self, dt):
        super().update(dt)

        state = getattr(self.game, "state", None)
        if not state:
            return

        # Phase 1: Heavy telegraphed laser beam sweepers
        if self.attack_phase == 1:
            if not self.minions and self.rect.centery >= self.target_y - 10:
                self.on_phase_enter(1)

            self.beam_cooldown -= dt
            if self.beam_cooldown <= 0:
                self.beam_cooldown = 4.5
                self._trigger_telegraphed_beam()

        # Phase 2: Rotating Danmaku mode switch
        elif self.attack_phase == 2:
            self.spiral_angle += dt * 110.0
            self.danmaku_switch_timer -= dt
            if self.danmaku_switch_timer <= 0:
                self.danmaku_switch_timer = 4.0
                self.danmaku_mode = (self.danmaku_mode + 1) % 3

        # Phase 3: Supernova Countdown
        elif self.attack_phase == 3 and self.supernova_active and not self.supernova_discharged:
            self.supernova_timer -= dt
            # Screen shake intensification as timer reaches 0
            if self.supernova_timer <= 3.0:
                if hasattr(state, "camera") and state.camera:
                    state.camera.add_shake(0.1, 4.0)

            if self.supernova_timer <= 0:
                self.supernova_timer = 0.0
                self._discharge_supernova()

    def _trigger_telegraphed_beam(self):
        state = getattr(self.game, "state", None)
        if not state or not hasattr(state, "telegraphs") or not state.telegraphs:
            return

        player = getattr(state, "player", None)
        target_cb = (lambda: player.rect.center) if player else (lambda: (self.rect.centerx, self.game.height - 100))

        # Left and right cannon beams
        state.telegraphs.create_laser_sightline(
            start_provider=(lambda: (self.rect.centerx - 45, self.rect.bottom)),
            target_provider=target_cb,
            aim_duration=1.1,
            lock_duration=0.35,
            fire_duration=0.45,
            beam_width=20,
            damage=30,
            beam_color=(0, 240, 160),
            core_color=(230, 255, 240),
            on_fire_callback=lambda sl: self._on_beam_fire(sl),
        )
        state.telegraphs.create_laser_sightline(
            start_provider=(lambda: (self.rect.centerx + 45, self.rect.bottom)),
            target_provider=target_cb,
            aim_duration=1.1,
            lock_duration=0.35,
            fire_duration=0.45,
            beam_width=20,
            damage=30,
            beam_color=(0, 240, 160),
            core_color=(230, 255, 240),
            on_fire_callback=lambda sl: self._on_beam_fire(sl),
        )

    def _on_beam_fire(self, sightline):
        if hasattr(self.game, "audio") and self.game.audio:
            self.game.audio.play_sfx("zap", pos_x=self.rect.centerx, volume_mult=1.0)
        state = getattr(self.game, "state", None)
        if state and hasattr(state, "camera") and state.camera:
            state.camera.add_shake(0.2, 5.0)

    def _discharge_supernova(self):
        """Discharges apocalyptic supernova blast if player fails 10s DPS check."""
        self.supernova_discharged = True
        state = getattr(self.game, "state", None)
        if not state:
            return

        # Massive EMP blast & camera shake
        if hasattr(state, "telegraphs") and state.telegraphs:
            state.telegraphs.create_emp_blast(self.rect.center, max_radius=1200, duration=1.2, color=(255, 60, 40))
        if hasattr(state, "camera") and state.camera:
            state.camera.add_shake(0.8, 16.0)
        if hasattr(self.game, "audio") and self.game.audio:
            self.game.audio.play_sfx("zap", pos_x=self.rect.centerx, volume_mult=1.0)
            self.game.audio.play_sfx("player_death", pos_x=self.rect.centerx, volume_mult=1.0)

        # Inflict heavy damage on player
        player = getattr(state, "player", None)
        if player:
            died = player.get_hit(80)
            if hasattr(state, "trigger_damage_flash"):
                state.trigger_damage_flash(0.6 if died else 0.35)
            if hasattr(state, "spawn_floating_text"):
                state.spawn_floating_text(player.rect.centerx, player.rect.top, "-80 HP", color=(255, 80, 80))

    def shoot(self):
        state = getattr(self.game, "state", None)
        if not state or not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser

        if self.attack_phase == 1:
            # Dual pulse lasers from flanking pods
            l1 = Laser(self.game, self.rect.centerx - 45, self.rect.bottom, speed_y=390, damage=14, img_name="laser_boss")
            l2 = Laser(self.game, self.rect.centerx + 45, self.rect.bottom, speed_y=390, damage=14, img_name="laser_boss")
            state.enemy_lasers.add(l1, l2)
            state.all_sprites.add(l1, l2)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("laser", pos_x=self.rect.centerx, volume_mult=0.7)

        elif self.attack_phase == 2:
            if self.danmaku_mode == 0:
                # 8-way rotating spiral blossom
                for i in range(8):
                    ang = self.spiral_angle + (i * 45.0)
                    rad = math.radians(ang)
                    speed = 320
                    l = Laser(self.game, self.rect.centerx, self.rect.centery, speed_y=speed, angle=ang, damage=12, img_name="laser_tier3")
                    l.speed_x = speed * math.sin(rad)
                    l.speed_y = speed * math.cos(rad)
                    state.enemy_lasers.add(l)
                    state.all_sprites.add(l)
                if hasattr(self.game, "audio") and self.game.audio:
                    self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.5)

            elif self.danmaku_mode == 1:
                # Ring pulse expanding barrage (12 bullets)
                for ang in range(0, 360, 30):
                    rad = math.radians(ang)
                    speed = 290
                    l = Laser(self.game, self.rect.centerx, self.rect.centery, speed_y=speed, angle=ang, damage=12, img_name="laser_boss")
                    l.speed_x = speed * math.sin(rad)
                    l.speed_y = speed * math.cos(rad)
                    state.enemy_lasers.add(l)
                    state.all_sprites.add(l)
                if hasattr(self.game, "audio") and self.game.audio:
                    self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.7)

            else:
                # Criss-cross wave pattern
                for ang in (-35, -18, 0, 18, 35):
                    l = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=410, angle=ang, damage=14, img_name="laser_boss")
                    state.enemy_lasers.add(l)
                    state.all_sprites.add(l)
                if hasattr(self.game, "audio") and self.game.audio:
                    self.game.audio.play_sfx("laser", pos_x=self.rect.centerx, volume_mult=0.7)

        elif self.attack_phase == 3:
            # Radial homing sparks & rapid pulse bursts
            for ang in range(0, 360, 45):
                jitter = random.uniform(-10, 10)
                rad = math.radians(ang + jitter)
                speed = 340
                l = Laser(self.game, self.rect.centerx, self.rect.centery, speed_y=speed, angle=ang + jitter, damage=15, img_name="laser_power")
                l.speed_x = speed * math.sin(rad)
                l.speed_y = speed * math.cos(rad)
                state.enemy_lasers.add(l)
                state.all_sprites.add(l)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.6)
