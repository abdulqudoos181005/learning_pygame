import sqlite3
from typing import Dict, List, Optional, Any
from db.manager import DatabaseManager


class HangarRepository:
    """
    Hangar and Armory progression repository for Space Shooters.
    
    Handles persistent pilot wallets (Nanite Credits), 5-track tech tree upgrade
    tiers, unlockable ship hulls, and equipped secondary ordnance.
    """

    UPGRADE_DEFAULTS = {
        "armor": 0,
        "shield": 0,
        "magnet": 0,
        "graze": 0,
        "ordnance_bay": 0,
    }

    UPGRADE_MAX_TIERS = {
        "armor": 5,
        "shield": 5,
        "magnet": 5,
        "graze": 5,
        "ordnance_bay": 5,
    }

    UPGRADE_COSTS = {
        "armor": [100, 250, 450, 750, 1200],
        "shield": [120, 280, 500, 800, 1300],
        "magnet": [80, 200, 380, 650, 1000],
        "graze": [150, 320, 580, 900, 1500],
        "ordnance_bay": [140, 300, 550, 850, 1400],
    }

    HULL_REQUIREMENTS = {
        "interceptor": {"cost": 0, "stars": 0},
        "cruiser": {"cost": 500, "stars": 6},
        "vanguard": {"cost": 1200, "stars": 15},
    }

    ORDNANCE_REQUIREMENTS = {
        "missile": {"cost": 0, "name": "Homing Missiles"},
        "cluster": {"cost": 400, "name": "Cluster Bomb Pod"},
        "ion_emp": {"cost": 800, "name": "Ion Pulse EMP"},
    }

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def get_hangar_data(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieves complete hangar and armory state for a user.
        If user_id is None (guest), returns baseline default dictionary.
        """
        default_data = {
            "credits": 0,
            "lifetime_credits": 0,
            "equipped_hull": "interceptor",
            "equipped_color": "blue",
            "equipped_ordnance": "missile",
            "upgrades": dict(self.UPGRADE_DEFAULTS),
            "unlocked_hulls": ["interceptor"],
            "unlocked_ordnance": ["missile"],
        }

        if user_id is None:
            return default_data

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Ensure user_hangar record exists
            cursor.execute(
                """
                INSERT INTO user_hangar (user_id, credits, lifetime_credits, equipped_hull, equipped_color, equipped_ordnance)
                VALUES (?, 0, 0, 'interceptor', 'blue', 'missile')
                ON CONFLICT(user_id) DO NOTHING;
                """,
                (user_id,),
            )

            # Ensure default hull is unlocked
            cursor.execute(
                """
                INSERT INTO user_unlocked_hulls (user_id, hull_id)
                VALUES (?, 'interceptor')
                ON CONFLICT(user_id, hull_id) DO NOTHING;
                """,
                (user_id,),
            )

            # Fetch wallet & equipped
            cursor.execute(
                "SELECT credits, lifetime_credits, equipped_hull, equipped_color, equipped_ordnance FROM user_hangar WHERE user_id = ?;",
                (user_id,),
            )
            hangar_row = cursor.fetchone()

            # Fetch upgrades
            cursor.execute("SELECT upgrade_id, tier FROM user_upgrades WHERE user_id = ?;", (user_id,))
            upgrade_rows = cursor.fetchall()
            upgrades = dict(self.UPGRADE_DEFAULTS)
            for row in upgrade_rows:
                upgrades[row["upgrade_id"]] = row["tier"]

            # Fetch unlocked hulls
            cursor.execute("SELECT hull_id FROM user_unlocked_hulls WHERE user_id = ?;", (user_id,))
            unlocked_hulls = [row["hull_id"] for row in cursor.fetchall()]
            if "interceptor" not in unlocked_hulls:
                unlocked_hulls.append("interceptor")

            unlocked_ordnance = ["missile"]
            if hangar_row and hangar_row["equipped_ordnance"] not in unlocked_ordnance:
                unlocked_ordnance.append(hangar_row["equipped_ordnance"])

            return {
                "credits": hangar_row["credits"] if hangar_row else 0,
                "lifetime_credits": hangar_row["lifetime_credits"] if hangar_row else 0,
                "equipped_hull": hangar_row["equipped_hull"] if hangar_row else "interceptor",
                "equipped_color": hangar_row["equipped_color"] if hangar_row else "blue",
                "equipped_ordnance": hangar_row["equipped_ordnance"] if hangar_row else "missile",
                "upgrades": upgrades,
                "unlocked_hulls": unlocked_hulls,
                "unlocked_ordnance": unlocked_ordnance,
            }

    def add_credits(self, user_id: Optional[int], amount: int) -> int:
        """Adds credits to a user's wallet. Returns updated balance."""
        if user_id is None or amount <= 0:
            return 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_hangar (user_id, credits, lifetime_credits)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    credits = credits + ?,
                    lifetime_credits = lifetime_credits + ?;
                """,
                (user_id, amount, amount, amount, amount),
            )
            cursor.execute("SELECT credits FROM user_hangar WHERE user_id = ?;", (user_id,))
            row = cursor.fetchone()
            return row["credits"] if row else amount

    def spend_credits(self, user_id: Optional[int], amount: int) -> bool:
        """Deducts credits if user has sufficient funds. Returns True if successful."""
        if user_id is None or amount <= 0:
            return False

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT credits FROM user_hangar WHERE user_id = ?;", (user_id,))
            row = cursor.fetchone()
            if not row or row["credits"] < amount:
                return False

            cursor.execute(
                "UPDATE user_hangar SET credits = credits - ? WHERE user_id = ?;",
                (amount, user_id),
            )
            return True

    def purchase_upgrade(self, user_id: Optional[int], upgrade_id: str) -> Dict[str, Any]:
        """
        Attempts to buy the next tier of an upgrade for user_id.
        Returns result dictionary: {"success": bool, "new_tier": int, "credits_left": int, "error": str}
        """
        if user_id is None:
            return {"success": False, "error": "Guest accounts cannot purchase persistent upgrades in DB."}

        if upgrade_id not in self.UPGRADE_COSTS:
            return {"success": False, "error": f"Invalid upgrade '{upgrade_id}'"}

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Get current tier
            cursor.execute("SELECT tier FROM user_upgrades WHERE user_id = ? AND upgrade_id = ?;", (user_id, upgrade_id))
            tier_row = cursor.fetchone()
            current_tier = tier_row["tier"] if tier_row else 0

            max_tier = self.UPGRADE_MAX_TIERS.get(upgrade_id, 5)
            if current_tier >= max_tier:
                return {"success": False, "error": "Upgrade already at maximum tier."}

            cost = self.UPGRADE_COSTS[upgrade_id][current_tier]

            # Check wallet
            cursor.execute("SELECT credits FROM user_hangar WHERE user_id = ?;", (user_id,))
            hangar_row = cursor.fetchone()
            balance = hangar_row["credits"] if hangar_row else 0

            if balance < cost:
                return {"success": False, "error": f"Insufficient credits ({balance}/{cost})."}

            # Deduct and upgrade
            cursor.execute(
                "UPDATE user_hangar SET credits = credits - ? WHERE user_id = ?;",
                (cost, user_id),
            )
            new_tier = current_tier + 1
            cursor.execute(
                """
                INSERT INTO user_upgrades (user_id, upgrade_id, tier)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, upgrade_id) DO UPDATE SET tier = ?;
                """,
                (user_id, upgrade_id, new_tier, new_tier),
            )

            cursor.execute("SELECT credits FROM user_hangar WHERE user_id = ?;", (user_id,))
            updated_balance = cursor.fetchone()["credits"]

            return {
                "success": True,
                "new_tier": new_tier,
                "credits_left": updated_balance,
                "cost": cost,
            }

    def unlock_hull(self, user_id: Optional[int], hull_id: str, total_stars: int = 0) -> Dict[str, Any]:
        """
        Unlocks a ship hull using credits or star requirements.
        """
        if user_id is None:
            return {"success": False, "error": "Guest account."}

        req = self.HULL_REQUIREMENTS.get(hull_id)
        if not req:
            return {"success": False, "error": f"Unknown hull '{hull_id}'"}

        cost = req["cost"]
        required_stars = req["stars"]

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_unlocked_hulls WHERE user_id = ? AND hull_id = ?;", (user_id, hull_id))
            if cursor.fetchone():
                return {"success": True, "already_unlocked": True}

            can_unlock_via_stars = total_stars >= required_stars and required_stars > 0

            if not can_unlock_via_stars and cost > 0:
                cursor.execute("SELECT credits FROM user_hangar WHERE user_id = ?;", (user_id,))
                row = cursor.fetchone()
                balance = row["credits"] if row else 0
                if balance < cost:
                    return {"success": False, "error": f"Requires {cost} credits or {required_stars} campaign stars."}
                cursor.execute("UPDATE user_hangar SET credits = credits - ? WHERE user_id = ?;", (cost, user_id))

            cursor.execute(
                """
                INSERT INTO user_unlocked_hulls (user_id, hull_id)
                VALUES (?, ?)
                ON CONFLICT(user_id, hull_id) DO NOTHING;
                """,
                (user_id, hull_id),
            )

            return {"success": True, "hull_id": hull_id}

    def set_loadout(self, user_id: Optional[int], hull: str, color: str, ordnance: Optional[str] = None):
        """Saves active equipped loadout for user."""
        if user_id is None:
            return

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if ordnance:
                cursor.execute(
                    """
                    INSERT INTO user_hangar (user_id, equipped_hull, equipped_color, equipped_ordnance)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        equipped_hull = ?,
                        equipped_color = ?,
                        equipped_ordnance = ?;
                    """,
                    (user_id, hull, color, ordnance, hull, color, ordnance),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_hangar (user_id, equipped_hull, equipped_color)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        equipped_hull = ?,
                        equipped_color = ?;
                    """,
                    (user_id, hull, color, hull, color),
                )
