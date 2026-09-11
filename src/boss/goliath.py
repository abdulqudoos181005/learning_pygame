# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg
from boss.boss_base import Boss
from boss.minions import OrbitalShieldBit, ProximityMine


class GoliathDreadnought(Boss):
    """
    Level 5 Campaign Boss: Goliath Dreadnought.
    
    Phase 1 (Broadside Barrage): Heavy alternating dual vulcan cannons + twin missile pods.
    Phase 2 (Orbital Bastion): 2 rotating energy shield bits deflecting front fire + shield overlay.
    Phase 3 (Overclocked Fury): 40% speed boost + sweeping conical laser arcs + proximity fragmentation mines.
    """

    def __init__(self, game, hp_mult=1.0, spd_mult=1.0, boss_key=None, laser_key=None):
        super().__init__(
            game,
            hp_mult=hp_mult,
            spd_mult=spd_mult,
            boss_key=boss_key or "mothership_saucer_crimson_red",
            laser_key=laser_key or "laser_red_beam_stream_long",
            title="GOLIATH DREADNOUGHT",
            base_health=700,
            base_shield=0,
        )
        self.phase_subtitle = "PHASE 1: BROADSIDE BARRAGE"
        self.missile_timer = 3.5
        self.mine_timer = 3.2
        self.sweep_timer = 2.4
        self.sweep_angle = 90.0
        self.vulcan_side = 0

    def on_phase_enter(self, new_phase):
        state = getattr(self.game, "state", None)

        if new_phase == 2:
            self.phase_subtitle = "PHASE 2: ORBITAL BASTION"
            # Grant active shield barrier
            self.max_shield = int(220 * self.hp_mult)
            self.shield = self.max_shield

            # Spawn 2 rotating OrbitalShieldBits
            if state:
                bit1 = OrbitalShieldBit(self.game, self, initial_angle=0.0, radius=125, orbit_speed=1.8)
                bit2 = OrbitalShieldBit(self.game, self, initial_angle=math.pi, radius=125, orbit_speed=1.8)
                self.minions.extend([bit1, bit2])
                if hasattr(state, "enemies"):
                    state.enemies.add(bit1, bit2)
                if hasattr(state, "all_sprites"):
                    state.all_sprites.add(bit1, bit2)

        elif new_phase == 3:
            self.phase_subtitle = "PHASE 3: OVERCLOCKED FURY"
            self.speed_x = abs(self.speed_x) * 1.45
            self.shoot_timer = 0.4

    def update(self, dt):
        super().update(dt)

        state = getattr(self.game, "state", None)
        if not state:
            return

        # Phase 1: Periodic homing missile barrages
        if self.attack_phase == 1:
            self.missile_timer -= dt
            if self.missile_timer <= 0:
                self.missile_timer = 3.8
                self._launch_missile_pod()

        # Phase 3: Sweeping conical arcs and proximity mines
        elif self.attack_phase == 3:
            # Drop proximity mines
            self.mine_timer -= dt
            if self.mine_timer <= 0:
                self.mine_timer = 3.2
                mine = ProximityMine(self.game, self.rect.centerx + random.randint(-40, 40), self.rect.bottom + 10)
                self.minions.append(mine)
                if hasattr(state, "enemies"):
                    state.enemies.add(mine)
                if hasattr(state, "all_sprites"):
                    state.all_sprites.add(mine)

            # Sweeping conical hazard
            self.sweep_timer -= dt
            if self.sweep_timer <= 0:
                self.sweep_timer = 2.8
                self._trigger_sweeping_arc()

    def _launch_missile_pod(self):
        state = getattr(self.game, "state", None)
        if not state or not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser
        # Left and right missile pod launch
        for offset_x in (-50, 50):
            m = Laser(self.game, self.rect.centerx + offset_x, self.rect.bottom, speed_y=280, damage=16, img_name="powerup_missile")
            state.enemy_lasers.add(m)
            state.all_sprites.add(m)
        if hasattr(self.game, "audio") and self.game.audio:
            self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.8)

    def _trigger_sweeping_arc(self):
        state = getattr(self.game, "state", None)
        if not state or not hasattr(state, "telegraphs") or not state.telegraphs:
            return

        # Create conical hazard towards player
        target_center = self.rect.centerx
        player = getattr(state, "player", None)
        if player:
            angle_to_player = math.degrees(math.atan2(player.rect.centery - self.rect.centery, player.rect.centerx - self.rect.centerx))
        else:
            angle_to_player = 90.0

        state.telegraphs.create_conical_hazard(
            origin=(self.rect.centerx, self.rect.bottom),
            center_angle=angle_to_player,
            spread_angle=55.0,
            radius=320,
            warning_duration=0.9,
            burst_duration=0.45,
            damage=28,
            color=(255, 60, 40),
        )

    def shoot(self):
        state = getattr(self.game, "state", None)
        if not state or not hasattr(state, "enemy_lasers"):
            return

        from sprites import Laser

        if self.attack_phase == 1:
            # Alternating dual vulcan cannon
            self.vulcan_side = 1 - self.vulcan_side
            pod_x = self.rect.centerx - 38 if self.vulcan_side == 0 else self.rect.centerx + 38
            l = Laser(self.game, pod_x, self.rect.bottom, speed_y=420, damage=12, img_name=self.laser_key)
            state.enemy_lasers.add(l)
            state.all_sprites.add(l)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("laser", pos_x=pod_x, volume_mult=0.6)

        elif self.attack_phase == 2:
            # Heavy 3-way plasma barrage
            angles = (-22, 0, 22)
            for ang in angles:
                l = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=380, angle=ang, damage=14)
                l.raw_image = self.game.assets.get_image("laser_boss", 16, 38)
                l.image = pg.transform.rotate(l.raw_image, -l.angle) if l.angle != 0 else l.raw_image
                state.enemy_lasers.add(l)
                state.all_sprites.add(l)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("laser_pew", pos_x=self.rect.centerx, volume_mult=0.85)

        elif self.attack_phase == 3:
            # Rapid sweeping vulcan streams
            ang = random.uniform(-35, 35)
            l = Laser(self.game, self.rect.centerx, self.rect.bottom, speed_y=460, angle=ang, damage=15, img_name=self.laser_key)
            state.enemy_lasers.add(l)
            state.all_sprites.add(l)
            if hasattr(self.game, "audio") and self.game.audio:
                self.game.audio.play_sfx("laser", pos_x=self.rect.centerx, volume_mult=0.6)
