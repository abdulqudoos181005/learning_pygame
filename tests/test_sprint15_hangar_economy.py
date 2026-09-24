# pyrefly: ignore [missing-import]
import os
import sys
import unittest
import pygame as pg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db.manager import DatabaseManager
from db.auth_service import AuthService
from db.hangar_repository import HangarRepository
from save_system import SaveSystem
from assets_loader import AssetsLoader
from sprites import Player, Laser, Missile, ClusterMissile, ClusterFragment, IonEMPOrb, PowerUp, ScoreCrystal
from states import HangarState, PlayState


class MockGame:
    def __init__(self, db=None):
        self.width = 1280
        self.height = 720
        self.assets = AssetsLoader()
        self.db = db or DatabaseManager(db_path=":memory:")
        self.auth_service = AuthService(self.db)
        self.hangar_repo = HangarRepository(self.db)
        self.save_system = SaveSystem(
            db_manager=self.db,
            hangar_repo=self.hangar_repo,
            settings_filename="test_hangar_settings.json",
        )
        self.current_user = None
        self.loadout = {"hull": "interceptor", "color": "blue", "ordnance": "missile"}
        self.state = None

        from input_map import InputMap
        self.input = InputMap()
        from ui.cursor import SoftwareCursor
        self.cursor = SoftwareCursor(self.assets, self.width, self.height)
        from audio.director import AudioDirector
        self.audio = AudioDirector(assets=self.assets, screen_width=self.width)

    def is_logged_in(self):
        return bool(self.current_user and "id" in self.current_user)

    def change_state(self, new_state):
        self.state = new_state


class TestSprint15HangarEconomy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        pg.display.set_mode((1280, 720))

    def setUp(self):
        self.db = DatabaseManager(db_path=":memory:")
        self.game = MockGame(db=self.db)
        self.repo = self.game.hangar_repo

        # Register two test users
        self.u1, _ = self.game.auth_service.register_user("CommanderAlpha", "SecurePass123")
        self.u2, _ = self.game.auth_service.register_user("PilotBravo", "SecurePass456")

    def tearDown(self):
        if os.path.exists(self.game.save_system.settings_filepath):
            os.remove(self.game.save_system.settings_filepath)
        self.db.close()

    def test_hangar_repository_credit_transactions(self):
        u1_id = self.u1["id"]
        data = self.repo.get_hangar_data(u1_id)
        self.assertEqual(data["credits"], 0)

        # Add credits
        bal = self.repo.add_credits(u1_id, 500)
        self.assertEqual(bal, 500)

        data = self.repo.get_hangar_data(u1_id)
        self.assertEqual(data["credits"], 500)
        self.assertEqual(data["lifetime_credits"], 500)

        # Spend credits
        success = self.repo.spend_credits(u1_id, 200)
        self.assertTrue(success)
        self.assertEqual(self.repo.get_hangar_data(u1_id)["credits"], 300)

        # Overspend fails
        fail = self.repo.spend_credits(u1_id, 9999)
        self.assertFalse(fail)
        self.assertEqual(self.repo.get_hangar_data(u1_id)["credits"], 300)

    def test_upgrade_tier_progression_and_caps(self):
        u1_id = self.u1["id"]
        self.repo.add_credits(u1_id, 3000)

        # Tier 0 -> Tier 1 (Armor cost = 100)
        res1 = self.repo.purchase_upgrade(u1_id, "armor")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["new_tier"], 1)
        self.assertEqual(res1["credits_left"], 2900)

        # Tier 1 -> Tier 2 (Armor cost = 250)
        res2 = self.repo.purchase_upgrade(u1_id, "armor")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["new_tier"], 2)
        self.assertEqual(res2["credits_left"], 2650)

        # Progress to Tier 5
        self.repo.purchase_upgrade(u1_id, "armor") # 3
        self.repo.purchase_upgrade(u1_id, "armor") # 4
        self.repo.purchase_upgrade(u1_id, "armor") # 5
        data = self.repo.get_hangar_data(u1_id)
        self.assertEqual(data["upgrades"]["armor"], 5)

        # Max tier cap reached
        cap_res = self.repo.purchase_upgrade(u1_id, "armor")
        self.assertFalse(cap_res["success"])
        self.assertIn("maximum", cap_res["error"].lower())

    def test_hull_unlock_criteria_and_purchasing(self):
        u1_id = self.u1["id"]
        # Interceptor unlocked by default
        data = self.repo.get_hangar_data(u1_id)
        self.assertIn("interceptor", data["unlocked_hulls"])

        # Try to unlock cruiser without funds or stars
        fail = self.repo.unlock_hull(u1_id, "cruiser", total_stars=0)
        self.assertFalse(fail["success"])

        # Unlock cruiser with credits
        self.repo.add_credits(u1_id, 600)
        succ = self.repo.unlock_hull(u1_id, "cruiser", total_stars=0)
        self.assertTrue(succ["success"])
        self.assertIn("cruiser", self.repo.get_hangar_data(u1_id)["unlocked_hulls"])

        # Unlock vanguard with star requirement
        v_succ = self.repo.unlock_hull(u1_id, "vanguard", total_stars=15)
        self.assertTrue(v_succ["success"])
        self.assertIn("vanguard", self.repo.get_hangar_data(u1_id)["unlocked_hulls"])

    def test_player_stat_scaling_with_upgrades(self):
        u1_id = self.u1["id"]
        self.game.current_user = self.u1
        self.repo.add_credits(u1_id, 5000)

        # Buy 2 tiers armor, 2 tiers shield, 1 tier magnet, 1 tier graze, 2 tiers ordnance bay
        self.repo.purchase_upgrade(u1_id, "armor")        # +15 HP
        self.repo.purchase_upgrade(u1_id, "armor")        # +15 HP -> Total +30 HP
        self.repo.purchase_upgrade(u1_id, "shield")       # +15 SH
        self.repo.purchase_upgrade(u1_id, "shield")       # +15 SH -> Total +30 SH
        self.repo.purchase_upgrade(u1_id, "magnet")       # +45px Magnet
        self.repo.purchase_upgrade(u1_id, "graze")        # +15% Graze bonus
        self.repo.purchase_upgrade(u1_id, "ordnance_bay") # +1 Missile
        self.repo.purchase_upgrade(u1_id, "ordnance_bay") # +1 Missile -> Total +2 Missiles

        player = Player(self.game, 640, 600)
        # Interceptor base HP is 100, so 100 + 30 = 130
        self.assertEqual(player.max_health, 130)
        self.assertEqual(player.health, 130)
        # Interceptor base Shield is 100, so 100 + 30 = 130
        self.assertEqual(player.max_shield, 130)
        # Magnet radius = 80 + 45 = 125
        self.assertEqual(player.magnet_radius, 125.0)
        # Starting missiles = 3 + 2 = 5
        self.assertEqual(player.missile_count, 5)
        self.assertEqual(player.graze_score_bonus, 65)

    def test_cluster_missile_submunition_detonation(self):
        self.game.state = PlayState(self.game, selected_level=1)
        cluster = ClusterMissile(self.game, 640, 400, self.game.state.enemies)
        self.game.state.missiles.add(cluster)

        initial_count = len(self.game.state.missiles)
        cluster.detonate()

        # Detonate should have removed the main cluster and spawned 6 ClusterFragments
        self.assertNotIn(cluster, self.game.state.missiles)
        fragments = [m for m in self.game.state.missiles if isinstance(m, ClusterFragment)]
        self.assertEqual(len(fragments), 6)

    def test_ion_emp_orb_projectile_absorption(self):
        self.game.state = PlayState(self.game, selected_level=1)
        laser1 = Laser(self.game, 640, 390, speed_y=400)
        laser2 = Laser(self.game, 640, 600, speed_y=400) # Out of radius
        self.game.state.enemy_lasers.add(laser1, laser2)

        orb = IonEMPOrb(self.game, 640, 400)
        self.game.state.missiles.add(orb)

        orb.update(0.016)
        # laser1 should be absorbed and killed, laser2 survives
        self.assertNotIn(laser1, self.game.state.enemy_lasers)
        self.assertIn(laser2, self.game.state.enemy_lasers)

    def test_graviton_magnet_suction_physics(self):
        self.game.state = PlayState(self.game, selected_level=1)
        self.game.state.player.rect.center = (640, 400)
        self.game.state.player.magnet_radius = 200.0

        crystal = ScoreCrystal(self.game, 640, 500)
        crystal.magnet_radius = 200.0
        self.game.state.crystals.add(crystal)

        init_y = crystal.fy
        crystal.update(0.1)
        # Crystal should accelerate upward toward player (fy decreases)
        self.assertLess(crystal.fy, init_y)

    def test_multi_user_hangar_progression_isolation(self):
        u1_id = self.u1["id"]
        u2_id = self.u2["id"]

        # Give User 1 1000 credits and buy armor
        self.repo.add_credits(u1_id, 1000)
        self.repo.purchase_upgrade(u1_id, "armor")

        data_u1 = self.repo.get_hangar_data(u1_id)
        data_u2 = self.repo.get_hangar_data(u2_id)

        self.assertEqual(data_u1["upgrades"]["armor"], 1)
        self.assertEqual(data_u2["upgrades"]["armor"], 0)
        self.assertEqual(data_u1["credits"], 900)
        self.assertEqual(data_u2["credits"], 0)

    def test_hangar_state_tabs_and_rendering(self):
        hangar = HangarState(self.game, return_state="level_select")
        self.assertEqual(hangar.active_tab, 0)

        # Switch to Tech Tree tab
        hangar.active_tab = 1
        surf = pg.Surface((1280, 720))
        hangar.draw(surf)

        # Switch to Ordnance tab
        hangar.active_tab = 2
        hangar.draw(surf)
        self.assertEqual(len(hangar.ORDNANCE_CATALOG), 3)


if __name__ == "__main__":
    unittest.main()
