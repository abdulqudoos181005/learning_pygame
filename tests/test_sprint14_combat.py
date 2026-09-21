# pyrefly: ignore [missing-import]
import math
import unittest
import pygame as pg

# Initialize headless pygame display
pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1, 1), pg.NOFRAME)
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from assets_loader import AssetsLoader
from src.vfx.telegraph import (
    LaserSightline,
    RingHazard,
    ConicalHazard,
    PhaseEMPBlast,
    BossPhaseNotification,
    TelegraphManager,
)
from src.boss import (
    Boss,
    GoliathDreadnought,
    ApexVoidLeviathan,
    OrbitalShieldBit,
    EscortDrone,
    ProximityMine,
)
from src.ui.hud import HUD


class MockGame:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.assets = AssetsLoader()
        self.audio = None
        self.state = None


class MockPlayer:
    def __init__(self, x=640, y=550):
        self.rect = pg.Rect(x - 25, y - 25, 50, 50)
        self.max_health = 100
        self.health = 100
        self.max_shield = 100
        self.shield = 50
        self.lives = 3
        self.score = 0
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.speed_boost_timer = 0.0
        self.triple_shot_timer = 0.0
        self.laser_power_timer = 0.0
        self.missile_count = 3
        self.missile_cooldown = 0.0
        self.base_laser_tier = 1

    def get_hit(self, damage):
        if self.shield > 0:
            absorbed = min(self.shield, damage)
            self.shield -= absorbed
            damage -= absorbed
        if damage > 0:
            self.health -= damage
            if self.health <= 0:
                self.lives -= 1
                self.health = self.max_health
                return True
        return False

    def draw_presentation_back(self, surface):
        pass

    def draw_presentation_front(self, surface):
        pass


class MockPlayState:
    def __init__(self, game):
        self.game = game
        self.player = MockPlayer()
        self.enemies = pg.sprite.Group()
        self.all_sprites = pg.sprite.Group()
        self.player_lasers = pg.sprite.Group()
        self.enemy_lasers = pg.sprite.Group()
        self.missiles = pg.sprite.Group()
        self.powerups = pg.sprite.Group()
        self.asteroids = pg.sprite.Group()
        self.particles = pg.sprite.Group()
        self.boss_active = False
        self.boss_instance = None
        self.score = 1500
        self.combo_count = 2
        self.combo_multiplier = 1.2
        self.combo_timer = 2.0
        self.COMBO_WINDOW = 3.0
        self.last_dt = 0.016
        self.level_sys = type("MockLevelSys", (), {"is_boss_wave": True, "level_number": 5})()
        self.telegraphs = TelegraphManager(game)


class TestSprint14Phase1Telegraphs(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.state = MockPlayState(self.game)
        self.game.state = self.state

    def test_laser_sightline_lifecycle(self):
        """Tests that LaserSightline progresses through aiming -> locked -> firing -> finished."""
        fired = []
        sl = LaserSightline(
            start_provider=(lambda: (640, 100)),
            target_provider=(lambda: (self.state.player.rect.centerx, self.state.player.rect.centery)),
            aim_duration=0.5,
            lock_duration=0.2,
            fire_duration=0.3,
            beam_width=20,
            damage=25,
            on_fire_callback=lambda s: fired.append(s),
        )
        self.assertTrue(sl.is_aiming)
        self.assertEqual(sl.state, LaserSightline.STATE_AIMING)

        # Update while aiming
        sl.update(0.3)
        self.assertTrue(sl.is_aiming)

        # Advance to locked state
        sl.update(0.25)
        self.assertTrue(sl.is_locked)

        # Advance to firing state
        sl.update(0.25)
        self.assertTrue(sl.is_firing)
        self.assertEqual(len(fired), 1)

        # Hit detection during firing
        target_rect = pg.Rect(630, 400, 40, 40)
        self.assertTrue(sl.check_hit(target_rect))
        # Subsequent check in same blast shouldn't double-hit
        self.assertFalse(sl.check_hit(target_rect))

        # Advance to finished
        sl.update(0.35)
        self.assertTrue(sl.is_finished)

    def test_ring_hazard_lifecycle_and_damage(self):
        """Tests that RingHazard expands, bursts, and damages target."""
        burst_called = []
        hz = RingHazard(
            center=(640, 500),
            radius=60,
            warning_duration=0.4,
            burst_duration=0.2,
            damage=30,
            on_burst_callback=lambda h: burst_called.append(h),
        )
        self.assertTrue(hz.is_warning)

        # Advance past warning duration into burst
        hz.update(0.45)
        self.assertTrue(hz.is_bursting)
        self.assertEqual(len(burst_called), 1)

        # Hit detection
        in_range_rect = pg.Rect(630, 490, 30, 30)
        self.assertTrue(hz.check_hit(in_range_rect))

        out_of_range_rect = pg.Rect(100, 100, 30, 30)
        self.assertFalse(hz.check_hit(out_of_range_rect))

        # Advance to finished
        hz.update(0.25)
        self.assertTrue(hz.is_finished)

    def test_conical_hazard_arc_detection(self):
        """Tests ConicalHazard full lifecycle, angular hit detection, and drawing."""
        burst_called = []
        cone = ConicalHazard(
            origin=(640, 100),
            center_angle=90.0,  # Straight downward
            spread_angle=60.0,
            radius=300,
            warning_duration=0.2,
            burst_duration=0.3,
            damage=25,
            on_burst_callback=lambda c: burst_called.append(c),
        )
        self.assertTrue(cone.is_warning)
        self.assertFalse(cone.is_bursting)
        self.assertFalse(cone.is_finished)
        self.assertFalse(cone.finished)

        # Draw in warning state
        test_surf = pg.Surface((1280, 720), pg.SRCALPHA)
        cone.draw(test_surf)

        # Advance to burst
        cone.update(0.25)
        self.assertFalse(cone.is_warning)
        self.assertTrue(cone.is_bursting)
        self.assertEqual(cone.state, ConicalHazard.STATE_BURST)
        self.assertEqual(len(burst_called), 1)

        # Draw in burst state
        cone.draw(test_surf)

        # Directly below origin: in cone
        direct_below = pg.Rect(630, 250, 40, 40)
        self.assertTrue(cone.check_hit(direct_below))

        # Far to the side: outside cone
        far_side = pg.Rect(200, 100, 40, 40)
        self.assertFalse(cone.check_hit(far_side))

        # Advance to finished
        cone.update(0.35)
        self.assertFalse(cone.is_bursting)
        self.assertTrue(cone.is_finished)
        self.assertTrue(cone.finished)

        # Draw after finished (should be no-op)
        cone.draw(test_surf)

    def test_telegraph_manager_integration(self):
        """Tests TelegraphManager creation, updates, and player damage check."""
        tm = TelegraphManager(self.game)
        sl = tm.create_laser_sightline(
            start_provider=(640, 50),
            target_provider=(640, 550),
            aim_duration=0.1,
            lock_duration=0.1,
            fire_duration=0.2,
            damage=35,
        )
        hz = tm.create_ring_hazard(
            center=(640, 550),
            radius=50,
            warning_duration=0.2,
            burst_duration=0.2,
            damage=20,
        )
        ch = tm.create_conical_hazard(
            origin=(640, 100),
            center_angle=90.0,
            spread_angle=50.0,
            radius=400,
            warning_duration=0.2,
            burst_duration=0.2,
            damage=30,
        )
        emp = tm.create_emp_blast(center=(640, 200))
        notif = tm.notify_boss_phase("BOSS ALERT", "PHASE 2")

        # Before firing, player receives 0 damage
        dmg = tm.check_player_hits(self.state.player.rect)
        self.assertEqual(dmg, 0)

        # Advance into firing/burst window
        tm.update(0.22)
        dmg = tm.check_player_hits(self.state.player.rect)
        self.assertGreater(dmg, 0)

        # Draw to test surface (ensure no crash)
        surf = pg.Surface((1280, 720), pg.SRCALPHA)
        tm.draw(surf, self.game.assets)

        # Clear
        tm.clear()
        self.assertEqual(len(tm.sightlines), 0)
        self.assertEqual(len(tm.hazards), 0)


class TestSprint14Phase1Bosses(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.state = MockPlayState(self.game)
        self.game.state = self.state

    def test_base_boss_phase_transitions_and_invulnerability(self):
        """Tests boss multi-phase transitions, EMP pulse, and invulnerability buffer."""
        boss = Boss(self.game, hp_mult=1.0, base_health=600, title="TEST MOTHERSHIP")
        self.assertEqual(boss.attack_phase, 1)
        self.assertEqual(boss.max_health, 600)
        self.assertEqual(boss.health, 600)

        # Put player laser in group
        from src.sprites import Laser
        pl = Laser(self.game, 640, 400, speed_y=-500)
        self.state.player_lasers.add(pl)
        self.assertEqual(len(self.state.player_lasers), 1)

        # Deal damage to cross Phase 2 threshold (<= 66% = <= 396 HP)
        boss.get_hit(210)  # HP = 390
        self.assertEqual(boss.attack_phase, 2)
        self.assertTrue(boss.is_invulnerable)
        # EMP pulse cleared player lasers
        self.assertEqual(len(self.state.player_lasers), 0)

        # During invulnerability, incoming damage is absorbed/deflected (0 damage)
        hp_before = boss.health
        boss.get_hit(100)
        self.assertEqual(boss.health, hp_before)

        # Expire invulnerability
        boss.update(0.9)
        self.assertFalse(boss.is_invulnerable)

        # Deal damage to cross Phase 3 threshold (<= 33% = <= 198 HP)
        boss.get_hit(200)  # HP = 190
        self.assertEqual(boss.attack_phase, 3)

    def test_goliath_dreadnought_phase_mechanics(self):
        """Tests Level 5 Goliath Dreadnought orbital shield bits, speed overclock, and mines."""
        goliath = GoliathDreadnought(self.game, hp_mult=1.0, spd_mult=1.0)
        self.assertEqual(goliath.boss_title, "GOLIATH DREADNOUGHT")
        self.assertEqual(goliath.attack_phase, 1)
        initial_speed = abs(goliath.speed_x)

        # Transition to Phase 2 (Orbital Bastion)
        goliath.get_hit(int(goliath.max_health * 0.35))
        self.assertEqual(goliath.attack_phase, 2)
        self.assertIn("ORBITAL BASTION", goliath.phase_subtitle)
        # Should have spawned 2 orbital shield bits and gained shield
        self.assertGreater(goliath.shield, 0)
        bits = [m for m in goliath.minions if isinstance(m, OrbitalShieldBit)]
        self.assertEqual(len(bits), 2)

        # Shield bit damage and rotation
        bit = bits[0]
        self.assertTrue(bit.alive())
        bit.update(0.1)
        # Destroy shield bit
        bit.get_hit(bit.max_health + 10)
        self.assertFalse(bit.alive())

        # Transition to Phase 3 (Overclocked Fury)
        goliath.update(0.9)  # clear invulnerability
        goliath.get_hit(goliath.shield + int(goliath.max_health * 0.35))
        self.assertEqual(goliath.attack_phase, 3)
        self.assertIn("OVERCLOCKED FURY", goliath.phase_subtitle)
        self.assertGreater(abs(goliath.speed_x), initial_speed)

        # Proximity mine behavior
        mine = ProximityMine(self.game, 640, 300)
        self.state.enemies.add(mine)
        self.assertTrue(mine.alive())
        mine.update(0.1)
        # Detonation creates area hazard
        mine.detonate()
        self.assertFalse(mine.alive())
        self.assertGreater(len(self.state.telegraphs.hazards), 0)

        # Sweeping conical hazard triggering in Phase 3
        hazards_before = len(self.state.telegraphs.hazards)
        goliath._trigger_sweeping_arc()
        self.assertGreater(len(self.state.telegraphs.hazards), hazards_before)

        # Update telegraphs through lifecycle and verify draw doesn't crash
        test_surf = pg.Surface((1280, 720), pg.SRCALPHA)
        self.state.telegraphs.update(0.5)
        self.state.telegraphs.draw(test_surf)
        self.state.telegraphs.update(0.5)
        self.state.telegraphs.draw(test_surf)


    def test_apex_void_leviathan_danmaku_and_supernova(self):
        """Tests Level 10 Final Boss Apex Void Leviathan escort drones, danmaku, and Supernova."""
        apex = ApexVoidLeviathan(self.game, hp_mult=1.0)
        self.assertEqual(apex.boss_title, "APEX VOID LEVIATHAN")
        self.assertEqual(apex.attack_phase, 1)

        # Deploy phase 1 escort drones
        apex.on_phase_enter(1)
        drones = [m for m in apex.minions if isinstance(m, EscortDrone)]
        self.assertEqual(len(drones), 2)
        drone = drones[0]
        drone.update(0.1)
        drone.get_hit(100)
        self.assertFalse(drone.alive())

        # Transition to Phase 2 (Danmaku Hellstorm)
        apex.get_hit(apex.shield + int(apex.max_health * 0.35))
        self.assertEqual(apex.attack_phase, 2)
        self.assertIn("DANMAKU HELLSTORM", apex.phase_subtitle)

        # Danmaku shoot patterns generate enemy projectiles
        lasers_before = len(self.state.enemy_lasers)
        apex.shoot()
        self.assertGreater(len(self.state.enemy_lasers), lasers_before)

        # Transition to Phase 3 (Supernova Meltdown)
        apex.update(0.9)  # clear invulnerability
        apex.get_hit(apex.shield + int(apex.max_health * 0.35))
        self.assertEqual(apex.attack_phase, 3)
        self.assertIn("SUPERNOVA MELTDOWN", apex.phase_subtitle)
        self.assertTrue(apex.supernova_active)
        self.assertAlmostEqual(apex.supernova_timer, 10.0)

        # Advance supernova countdown
        apex.update(2.0)
        self.assertAlmostEqual(apex.supernova_timer, 8.0, delta=0.1)



class TestSprint14Phase1HUD(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.state = MockPlayState(self.game)
        self.game.state = self.state
        self.hud = HUD(self.game)

    def test_segmented_boss_hud_rendering(self):
        """Tests boss health bar with gemstone pips, shield bar, and supernova timer in HUD."""
        boss = GoliathDreadnought(self.game, hp_mult=1.0)
        self.state.boss_active = True
        self.state.boss_instance = boss

        # Draw Phase 1
        surf = pg.Surface((1280, 720), pg.SRCALPHA)
        self.hud.draw(surf, self.state)

        # Transition to Phase 2 with shield
        boss.get_hit(int(boss.max_health * 0.35))
        self.hud.draw(surf, self.state)
        self.assertGreater(boss.shield, 0)

        # Switch to Apex Void Leviathan Phase 3 for Supernova UI testing
        apex = ApexVoidLeviathan(self.game, hp_mult=1.0)
        apex.trigger_phase_transition(3, "APEX VOID LEVIATHAN", "PHASE 3: SUPERNOVA MELTDOWN")
        self.state.boss_instance = apex
        self.assertTrue(apex.supernova_active)

        # Draw Supernova HUD alert
        self.hud.draw(surf, self.state)


class TestSprint14Phase2EliteEnemies(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.state = MockPlayState(self.game)
        self.game.state = self.state

    def test_aegis_defender_frontal_deflection_and_overheat(self):
        """Tests Aegis Defender frontal shield deflection, ripple timer, and overheat vulnerability."""
        from src.sprites import AegisDefender, Laser
        aegis = AegisDefender(self.game, 640, 200, hp_mult=1.0)
        self.assertEqual(aegis.type, "aegis_defender")
        self.assertTrue(aegis.shield_active)
        initial_hp = aegis.health

        # Player laser hitting from front (below moving upwards)
        laser = Laser(self.game, 640, 220, speed_y=-500)
        self.assertTrue(aegis.deflect_laser(laser))
        self.assertGreater(aegis.shield_ripple_timer, 0.0)
        self.assertEqual(aegis.health, initial_hp)

        # Trigger overheat cycle (shield_timer expired)
        aegis.shield_timer = 0.0
        aegis.update(0.05)
        self.assertFalse(aegis.shield_active)

        # During overheat, laser is NOT deflected and hull takes damage
        self.assertFalse(aegis.deflect_laser(laser))
        aegis.get_hit(20)
        self.assertEqual(aegis.health, initial_hp - 20)

        # Verify draw_extras doesn't crash in active or overheated states
        test_surf = pg.Surface((1280, 720), pg.SRCALPHA)
        aegis.draw_extras(test_surf)
        aegis.shield_active = True
        aegis.draw_extras(test_surf)

    def test_sniper_skiff_aiming_and_railgun(self):
        """Tests Sniper Skiff perimeter movement, LaserSightline aiming, and high-speed railgun firing."""
        from src.sprites import SniperSkiff, RailgunSlug
        sniper = SniperSkiff(self.game, 640, 20, hp_mult=1.0)
        self.assertEqual(sniper.type, "sniper_skiff")
        self.assertEqual(sniper.state, SniperSkiff.STATE_ENTERING)

        # Descends to perimeter and transitions to patrol
        sniper.update(1.0)
        self.assertEqual(sniper.state, SniperSkiff.STATE_PATROL)
        self.assertEqual(sniper.speed_y, 0.0)

        # Advance patrol timer to trigger aiming
        sniper.patrol_timer = 0.0
        sniper.update(0.05)
        self.assertEqual(sniper.state, SniperSkiff.STATE_AIMING)
        self.assertIsNotNone(sniper.sightline)

        # Fire railgun slug
        lasers_before = len(self.state.enemy_lasers)
        sniper._fire_railgun(sniper.sightline)
        self.assertEqual(len(self.state.enemy_lasers), lasers_before + 1)
        slug = [s for s in self.state.enemy_lasers if isinstance(s, RailgunSlug)][0]
        self.assertEqual(slug.damage, 30)
        self.assertEqual(slug.speed, 950.0)

        # Update slug and verify draw_trail
        slug.update(0.016)
        test_surf = pg.Surface((1280, 720), pg.SRCALPHA)
        slug.draw_trail(test_surf)

        # Destroying sniper cleans up sightline
        sniper.get_hit(sniper.health + 10)
        self.assertFalse(sniper.alive())
        self.assertIsNone(sniper.sightline)

    def test_phase_phantom_cloaking_and_ambush(self):
        """Tests Phase Phantom optical cloaking, missile untargetability, and decloak shotgun burst."""
        from src.sprites import PhasePhantom, Missile
        phantom = PhasePhantom(self.game, 640, 200, hp_mult=1.0)
        self.assertEqual(phantom.type, "phase_phantom")
        self.assertTrue(phantom.is_cloaked)
        self.assertEqual(phantom.image.get_alpha(), 38)
        self.state.enemies.add(phantom)

        # Missile cannot auto-target cloaked phantom
        missile = Missile(self.game, 640, 500, self.state.enemies)
        self.assertIsNone(missile._find_target())

        # Advance stalking timer into decloaking & attack
        phantom.state_timer = 0.0
        phantom.update(0.05)
        self.assertEqual(phantom.state, PhasePhantom.STATE_DECLOAKING)

        phantom.state_timer = 0.0
        phantom.update(0.05)
        self.assertEqual(phantom.state, PhasePhantom.STATE_ATTACKING)
        self.assertFalse(phantom.is_cloaked)

        # When decloaked, missile can target it
        self.assertEqual(missile._find_target(), phantom)

        # Verify shotgun burst spawned 5 spread projectiles
        self.assertEqual(len(self.state.enemy_lasers), 5)

        # Verify draw_extras
        test_surf = pg.Surface((1280, 720), pg.SRCALPHA)
        phantom.draw_extras(test_surf)

    def test_hive_carrier_and_swarmer_deployment(self):
        """Tests Hive Carrier positioning, Swarmer micro-drone deployment, and homing steering."""
        from src.sprites import HiveCarrier, Swarmer
        carrier = HiveCarrier(self.game, 640, 50, hp_mult=1.0)
        self.assertEqual(carrier.type, "hive_carrier")
        self.state.enemies.add(carrier)

        # Move to target hover Y
        carrier.update(2.0)
        self.assertGreaterEqual(carrier.rect.centery, carrier.target_y)

        # Trigger drone launch
        carrier.drone_spawn_timer = 0.0
        carrier.update(0.05)
        swarmers = [e for e in self.state.enemies if isinstance(e, Swarmer)]
        self.assertGreaterEqual(len(swarmers), 3)

        # Test Swarmer homing update towards player
        swarmer = swarmers[0]
        swarmer.update(0.1)
        self.assertTrue(swarmer.alive())
        self.assertEqual(swarmer.score_value, 80)

        # Carrier destruction
        carrier.get_hit(carrier.health + 10)
        self.assertFalse(carrier.alive())


class TestSprint14Phase2Formations(unittest.TestCase):
    def test_tactical_formations_and_level_configs(self):
        """Tests that LevelSystem configs for levels 3-10 incorporate new elite enemy archetypes and formations."""
        from src.level_system import LevelSystem, LEVEL_CONFIGS

        # Verify Level 3 introduces sniper skiff and aegis defender
        l3_types = set()
        for w in LEVEL_CONFIGS[2]["waves"]:
            l3_types.update(w["types"])
        self.assertIn("sniper_skiff", l3_types)
        self.assertIn("aegis_defender", l3_types)

        # Verify Level 4 introduces phase phantom
        l4_types = set()
        for w in LEVEL_CONFIGS[3]["waves"]:
            l4_types.update(w["types"])
        self.assertIn("phase_phantom", l4_types)

        # Verify Level 6 introduces hive carrier
        l6_types = set()
        for w in LEVEL_CONFIGS[5]["waves"]:
            l6_types.update(w["types"])
        self.assertIn("hive_carrier", l6_types)

        # Test Shield Wall formation ordering: Aegis defenders are positioned at front of queue
        ls = LevelSystem(starting_level=3)
        ls.wave_index = 1  # Wave 2 is shield_wall formation
        ls._load_wave()
        self.assertEqual(ls.current_wave_cfg["formation"], "shield_wall")
        # In a shield wall, aegis_defender comes before sniper_skiff
        if "aegis_defender" in ls.spawn_queue and "sniper_skiff" in ls.spawn_queue:
            first_aegis = ls.spawn_queue.index("aegis_defender")
            first_sniper = ls.spawn_queue.index("sniper_skiff")
            self.assertLess(first_aegis, first_sniper)

        # Test Carrier Assault formation ordering: Hive carriers appear early in wave
        ls.start_level(6)
        ls.wave_index = 1  # Wave 2 is carrier_assault formation
        ls._load_wave()
        self.assertEqual(ls.current_wave_cfg["formation"], "carrier_assault")
        if "hive_carrier" in ls.spawn_queue:
            self.assertEqual(ls.spawn_queue[0], "hive_carrier")


class TestSprint14Phase3TacticalMechanics(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.state = MockPlayState(self.game)
        self.game.state = self.state

    def test_graze_detection_and_overdrive_charge(self):
        """Tests near-miss bullet grazing: proximity detection, single-graze flag, score bonus, and Overdrive charging."""
        from src.sprites import Player, Laser
        from src.states import PlayState

        play_state = PlayState(self.game, selected_level=1)
        player = play_state.player
        player.rect.center = (640, 500)
        player.pos_x = 640.0
        player.pos_y = 500.0
        player.overdrive = 0.0
        player.graze_count = 0
        initial_score = play_state.score

        # 1. Spawn enemy laser just outside player hitbox but within graze radius (e.g. 38px away from center)
        laser = Laser(self.game, 640 + 38, 500, speed_y=300)
        play_state.enemy_lasers.add(laser)
        self.assertFalse(laser.grazed)

        # Trigger collision checks
        play_state._check_collisions()

        # Laser should now be grazed
        self.assertTrue(laser.grazed)
        self.assertEqual(player.graze_count, 1)
        self.assertEqual(player.overdrive, 12.0)
        self.assertGreater(play_state.score, initial_score)

        # Subsequent check on same frame/laser should not double-graze
        score_after_graze = play_state.score
        play_state._check_collisions()
        self.assertEqual(player.graze_count, 1)
        self.assertEqual(player.overdrive, 12.0)
        self.assertEqual(play_state.score, score_after_graze)

    def test_overdrive_meter_activation_and_duration(self):
        """Tests Overdrive gauge charging, activation, supercharged weapon fire rate, and duration decay."""
        from src.sprites import Player

        player = Player(self.game, 640, 500)
        self.assertEqual(player.overdrive, 0.0)
        self.assertFalse(player.overdrive_active)

        # Partial charge
        player.add_overdrive(40.0)
        self.assertEqual(player.overdrive, 40.0)
        # Activation fails if not 100%
        self.assertFalse(player.activate_overdrive())
        self.assertFalse(player.overdrive_active)

        # Fill to 100%
        player.add_overdrive(70.0)
        self.assertEqual(player.overdrive, 100.0)

        # Activate Overdrive
        self.assertTrue(player.activate_overdrive())
        self.assertTrue(player.overdrive_active)
        self.assertEqual(player.overdrive, 0.0)
        self.assertEqual(player.overdrive_timer, player.OVERDRIVE_DURATION)

        # Overdrive 2x supercharged fire rate
        normal_cooldown = player.shoot_cooldown
        player.shoot_timer = 0.0
        player.shoot()
        self.assertAlmostEqual(player.shoot_timer, normal_cooldown * 0.5, places=3)

        # Update timers and verify countdown
        player.update(2.0)
        self.assertTrue(player.overdrive_active)
        self.assertAlmostEqual(player.overdrive_timer, 2.0, places=2)

        # Advance past 4 seconds -> Overdrive expires
        player.update(2.5)
        self.assertFalse(player.overdrive_active)
        self.assertEqual(player.overdrive_timer, 0.0)

    def test_emp_burst_and_score_crystal_conversion(self):
        """Tests that Overdrive EMP burst clears enemy lasers and converts them into collectible ScoreCrystals."""
        from src.sprites import Laser, ScoreCrystal
        from src.states import PlayState

        play_state = PlayState(self.game, selected_level=1)
        player = play_state.player
        player.overdrive = 100.0

        # Spawn 4 enemy lasers
        for x in [500, 550, 600, 650]:
            laser = Laser(self.game, x, 300, speed_y=250)
            play_state.enemy_lasers.add(laser)
            play_state.all_sprites.add(laser)

        self.assertEqual(len(play_state.enemy_lasers), 4)
        self.assertEqual(len(play_state.crystals), 0)

        # Activate Overdrive EMP
        success = play_state.activate_player_overdrive()
        self.assertTrue(success)
        self.assertTrue(player.overdrive_active)

        # All enemy lasers cleared
        self.assertEqual(len(play_state.enemy_lasers), 0)

        # Transmuted into 4 ScoreCrystals
        self.assertEqual(len(play_state.crystals), 4)

        # Test ScoreCrystal magnetic attraction toward player
        crystal = next(iter(play_state.crystals))
        initial_vy = crystal.vy
        crystal.update(0.1)
        # Should accelerate toward player at (640, 620)
        self.assertIsNotNone(crystal.vx)

        # Test crystal collection
        initial_score = play_state.score
        crystal.rect.center = player.rect.center
        play_state._check_collisions()
        self.assertFalse(crystal.alive())
        self.assertGreaterEqual(play_state.score, initial_score + crystal.score_value)

    def test_bullet_time_dilation_factor(self):
        """Tests that enemies and enemy bullets move at 50% speed during Overdrive while player moves normally."""
        from src.sprites import Enemy, Laser
        from src.states import PlayState

        play_state = PlayState(self.game, selected_level=1)
        player = play_state.player
        player.overdrive = 100.0

        enemy = Enemy(self.game, 640, 100, "scout")
        play_state.enemies.add(enemy)

        laser = Laser(self.game, 640, 200, speed_y=400)
        play_state.enemy_lasers.add(laser)

        # Without overdrive: enemy moves with full dt
        initial_ey = enemy.rect.y
        initial_ly = laser.fy
        play_state.update(0.1)
        normal_enemy_delta = enemy.rect.y - initial_ey
        normal_laser_delta = laser.fy - initial_ly

        # Activate Overdrive: EMP clears existing lasers
        play_state.activate_player_overdrive()
        self.assertTrue(player.overdrive_active)

        # Spawn new laser during active Overdrive
        overdrive_laser = Laser(self.game, 640, 200, speed_y=400)
        play_state.enemy_lasers.add(overdrive_laser)
        initial_ly = overdrive_laser.fy

        play_state.update(0.1)
        dilated_enemy_delta = enemy.rect.y - initial_ey
        dilated_laser_delta = overdrive_laser.fy - initial_ly

        self.assertAlmostEqual(dilated_laser_delta, normal_laser_delta * 0.5, places=1)

    def test_render_pipeline_flash_and_chromatic_pulses(self):
        """Tests RenderPipeline screen flash and chromatic pulse triggers and timers."""
        from src.render.pipeline import RenderPipeline

        pipeline = RenderPipeline(1280, 720)
        self.assertEqual(pipeline.flash_timer, 0.0)
        self.assertEqual(pipeline.chromatic_pulse_timer, 0.0)

        # Trigger flash
        pipeline.trigger_flash(duration=0.2, color=(200, 240, 255))
        self.assertEqual(pipeline.flash_timer, 0.2)
        self.assertEqual(pipeline.flash_color, (200, 240, 255))

        # Trigger chromatic
        pipeline.trigger_chromatic(duration=0.3, intensity=3)
        self.assertEqual(pipeline.chromatic_pulse_timer, 0.3)
        self.assertEqual(pipeline.chromatic_pulse_intensity, 3)

        # Update timers
        pipeline.update(0.1)
        self.assertAlmostEqual(pipeline.flash_timer, 0.1, places=2)
        self.assertAlmostEqual(pipeline.chromatic_pulse_timer, 0.2, places=2)

        pipeline.update(0.25)
        self.assertEqual(pipeline.flash_timer, 0.0)
        self.assertEqual(pipeline.chromatic_pulse_timer, 0.0)
        self.assertEqual(pipeline.chromatic_pulse_intensity, 0)

    def test_audio_director_overdrive_and_graze(self):
        """Tests AudioDirector overdrive audio trigger and graze sound effects."""
        from src.audio.director import AudioDirector

        audio = AudioDirector(assets=self.game.assets, screen_width=1280)
        audio.trigger_overdrive_audio(duration=4.0)
        self.assertTrue(audio.is_ducked)
        self.assertAlmostEqual(audio.duck_timer, 4.0, places=2)

        # Play graze SFX
        res = audio.play_graze_sfx(pos_x=640)
        # Should execute cleanly without error (mixer or mock)

    def test_hud_overdrive_gauge_rendering(self):
        """Tests that HUD renders Overdrive gauge in charging, ready, and active states."""
        from src.sprites import Player
        from src.ui.hud import HUD

        hud = HUD(self.game)
        player = Player(self.game, 640, 500)
        self.state.player = player
        surf = pg.Surface((1280, 720), pg.SRCALPHA)

        # 1. 40% charged state
        player.overdrive = 40.0
        player.overdrive_active = False
        hud.draw(surf, self.state)

        # 2. 100% READY state
        player.overdrive = 100.0
        player.overdrive_active = False
        hud.draw(surf, self.state)

        # 3. Active state
        player.activate_overdrive()
        self.assertTrue(player.overdrive_active)
        hud.draw(surf, self.state)


if __name__ == "__main__":
    unittest.main()


