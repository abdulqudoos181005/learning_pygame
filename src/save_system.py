import json
import os

class SaveSystem:
    """
    Handles persistence of player high scores, level progression, and settings.
    
    Provides SQLite database storage for registered pilot accounts via
    ScoreRepository and ProgressRepository, with automatic fallback to local
    JSON files for guest pilots and offline gameplay.
    """
    def __init__(
        self,
        filename="high_scores.json",
        progress_filename="level_progress.json",
        settings_filename="settings.json",
        db_manager=None,
        score_repo=None,
        progress_repo=None,
        hangar_repo=None,
    ):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.filepath = os.path.join(project_root, filename)
        self.progress_filepath = os.path.join(project_root, progress_filename)
        self.settings_filepath = os.path.join(project_root, settings_filename)

        # SQLite database bridge and repositories
        self.db = db_manager
        self.score_repo = score_repo
        self.progress_repo = progress_repo
        self.hangar_repo = hangar_repo

        # Lazy initialize repositories if db_manager is supplied without repos
        if self.db and not self.score_repo:
            try:
                from db.score_repository import ScoreRepository
                self.score_repo = ScoreRepository(self.db)
            except Exception as e:
                print(f"[SaveSystem] Warning initializing ScoreRepository: {e}")

        if self.db and not self.progress_repo:
            try:
                from db.progress_repository import ProgressRepository
                self.progress_repo = ProgressRepository(self.db)
            except Exception as e:
                print(f"[SaveSystem] Warning initializing ProgressRepository: {e}")

        if self.db and not self.hangar_repo:
            try:
                from db.hangar_repository import HangarRepository
                self.hangar_repo = HangarRepository(self.db)
            except Exception as e:
                print(f"[SaveSystem] Warning initializing HangarRepository: {e}")

    def load_settings(self):
        """Loads complete user settings dict (volumes, visuals, controls, accessibility, loadout)."""
        defaults = {
            "music_volume": 0.7,
            "sfx_volume": 0.8,
            "ui_volume": 0.8,
            "shake_intensity": 1.0,
            "bloom": False,
            "hitmarkers": True,
            "fullscreen": False,
            "screen_flash": True,
            "hull": "interceptor",
            "color": "blue",
            "ordnance": "missile",
            "credits": 0,
            "unlocked_hulls": ["interceptor"],
            "unlocked_ordnance": ["missile"],
            "upgrades": {
                "armor": 0,
                "shield": 0,
                "magnet": 0,
                "graze": 0,
                "ordnance_bay": 0,
            },
            "keybinds": {
                "up": "w",
                "down": "s",
                "left": "a",
                "right": "d",
                "fire": "space",
                "missile": "m",
                "pause": "p"
            }
        }
        if not os.path.exists(self.settings_filepath):
            return defaults

        try:
            with open(self.settings_filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Merge loaded keys over defaults
                    for k, v in data.items():
                        if k == "keybinds" and isinstance(v, dict):
                            defaults["keybinds"].update(v)
                        else:
                            defaults[k] = v
                    return defaults
        except Exception as e:
            print(f"Warning: Failed to load settings JSON: {e}")

        return defaults

    def save_settings(self, settings_dict):
        """Saves entire settings dictionary to settings.json."""
        try:
            with open(self.settings_filepath, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            return True
        except Exception as e:
            print(f"Warning: Failed to save settings JSON: {e}")
            return False

    def load_loadout(self, user_id=None):
        """Loads ship loadout configuration (hull, color, ordnance) from DB or settings.json."""
        if user_id is not None and self.hangar_repo:
            try:
                hangar_data = self.hangar_repo.get_hangar_data(user_id)
                if hangar_data:
                    return {
                        "hull": hangar_data.get("equipped_hull", "interceptor"),
                        "color": hangar_data.get("equipped_color", "blue"),
                        "ordnance": hangar_data.get("equipped_ordnance", "missile"),
                    }
            except Exception as e:
                print(f"[SaveSystem] Warning loading loadout from database: {e}")

        settings = self.load_settings()
        hull = str(settings.get("hull", "interceptor")).lower()
        color = str(settings.get("color", "blue")).lower()
        ordnance = str(settings.get("ordnance", "missile")).lower()
        if hull not in ("interceptor", "cruiser", "vanguard"):
            hull = "interceptor"
        if color not in ("blue", "green", "orange", "red"):
            color = "blue"
        if ordnance not in ("missile", "cluster", "ion_emp"):
            ordnance = "missile"
        return {"hull": hull, "color": color, "ordnance": ordnance}

    def save_loadout(self, hull, color, ordnance="missile", user_id=None):
        """Saves chosen ship hull, color, and ordnance to database and settings.json."""
        clean_hull = str(hull).lower() if str(hull).lower() in ("interceptor", "cruiser", "vanguard") else "interceptor"
        clean_color = str(color).lower() if str(color).lower() in ("blue", "green", "orange", "red") else "blue"
        clean_ordnance = str(ordnance).lower() if str(ordnance).lower() in ("missile", "cluster", "ion_emp") else "missile"

        if user_id is not None and self.hangar_repo:
            try:
                self.hangar_repo.set_loadout(user_id, clean_hull, clean_color, clean_ordnance)
            except Exception as e:
                print(f"[SaveSystem] Warning saving loadout to database: {e}")

        settings = self.load_settings()
        settings["hull"] = clean_hull
        settings["color"] = clean_color
        settings["ordnance"] = clean_ordnance
        return self.save_settings(settings)

    def load_hangar(self, user_id=None):
        """Loads complete hangar data (wallet, upgrades, hull unlocks, equipped loadout)."""
        if user_id is not None and self.hangar_repo:
            try:
                return self.hangar_repo.get_hangar_data(user_id)
            except Exception as e:
                print(f"[SaveSystem] Warning loading hangar from database: {e}")

        # JSON Guest fallback
        settings = self.load_settings()
        upgrades = settings.get("upgrades", {
            "armor": 0,
            "shield": 0,
            "magnet": 0,
            "graze": 0,
            "ordnance_bay": 0,
        })
        return {
            "credits": settings.get("credits", 0),
            "lifetime_credits": settings.get("credits", 0),
            "equipped_hull": settings.get("hull", "interceptor"),
            "equipped_color": settings.get("color", "blue"),
            "equipped_ordnance": settings.get("ordnance", "missile"),
            "upgrades": upgrades,
            "unlocked_hulls": settings.get("unlocked_hulls", ["interceptor"]),
            "unlocked_ordnance": settings.get("unlocked_ordnance", ["missile"]),
        }

    def add_credits(self, amount, user_id=None):
        """Adds credits to active profile."""
        if amount <= 0:
            return 0
        if user_id is not None and self.hangar_repo:
            try:
                return self.hangar_repo.add_credits(user_id, amount)
            except Exception as e:
                print(f"[SaveSystem] Warning adding credits to DB: {e}")

        settings = self.load_settings()
        current = settings.get("credits", 0)
        new_total = current + amount
        settings["credits"] = new_total
        self.save_settings(settings)
        return new_total

    def purchase_upgrade(self, upgrade_id, user_id=None):
        """Buys next tier of upgrade for user or guest."""
        from db.hangar_repository import HangarRepository
        if user_id is not None and self.hangar_repo:
            return self.hangar_repo.purchase_upgrade(user_id, upgrade_id)

        # Guest mode JSON purchase
        settings = self.load_settings()
        upgrades = settings.get("upgrades", {
            "armor": 0, "shield": 0, "magnet": 0, "graze": 0, "ordnance_bay": 0
        })
        current_tier = upgrades.get(upgrade_id, 0)
        costs = HangarRepository.UPGRADE_COSTS.get(upgrade_id, [100, 200, 300, 400, 500])
        if current_tier >= len(costs):
            return {"success": False, "error": "Max tier reached."}

        cost = costs[current_tier]
        credits = settings.get("credits", 0)
        if credits < cost:
            return {"success": False, "error": f"Insufficient credits ({credits}/{cost})."}

        settings["credits"] = credits - cost
        upgrades[upgrade_id] = current_tier + 1
        settings["upgrades"] = upgrades
        self.save_settings(settings)
        return {
            "success": True,
            "new_tier": current_tier + 1,
            "credits_left": settings["credits"],
            "cost": cost,
        }

    def unlock_hull(self, hull_id, total_stars=0, user_id=None):
        """Unlocks a hull via DB or JSON."""
        from db.hangar_repository import HangarRepository
        if user_id is not None and self.hangar_repo:
            return self.hangar_repo.unlock_hull(user_id, hull_id, total_stars)

        settings = self.load_settings()
        unlocked = set(settings.get("unlocked_hulls", ["interceptor"]))
        if hull_id in unlocked:
            return {"success": True, "already_unlocked": True}

        req = HangarRepository.HULL_REQUIREMENTS.get(hull_id, {"cost": 500, "stars": 0})
        cost = req["cost"]
        required_stars = req["stars"]

        can_unlock = (total_stars >= required_stars and required_stars > 0)
        if not can_unlock and cost > 0:
            credits = settings.get("credits", 0)
            if credits < cost:
                return {"success": False, "error": f"Requires {cost} credits or {required_stars} stars."}
            settings["credits"] = credits - cost

        unlocked.add(hull_id)
        settings["unlocked_hulls"] = list(unlocked)
        self.save_settings(settings)
        return {"success": True, "hull_id": hull_id}
        
    def load_scores(self, user_id=None):
        """
        Loads and returns sorted high scores list.
        
        If user_id is provided and database repository is available, retrieves
        that user's top scores.
        If user_id is None and database repository is available, retrieves
        global top 10 scores from the database.
        Falls back to JSON file / defaults if database is empty or unavailable.
        """
        if self.score_repo:
            try:
                if user_id is not None:
                    user_scores = self.score_repo.get_user_top_scores(user_id, limit=10)
                    if user_scores:
                        return user_scores
                    return []
                else:
                    db_scores = self.score_repo.get_top_scores(limit=10)
                    if db_scores:
                        return db_scores
            except Exception as e:
                print(f"[SaveSystem] Warning: Database score retrieval failed: {e}")

        # JSON Fallback for global / guest scores
        if not os.path.exists(self.filepath):
            return self._get_default_scores()
            
        try:
            with open(self.filepath, 'r') as f:
                scores = json.load(f)
                if isinstance(scores, list):
                    scores = sorted(scores, key=lambda x: x.get("score", 0), reverse=True)
                    return scores
        except Exception as e:
            print(f"Warning: Failed to load high scores JSON: {e}")
            
        return self._get_default_scores()

    def load_user_scores(self, user_id, limit=10):
        """Retrieves top scores achieved by a specific user from DB."""
        if not user_id:
            return []
        if self.score_repo:
            try:
                return self.score_repo.get_user_top_scores(user_id, limit=limit)
            except Exception as e:
                print(f"[SaveSystem] Error loading user scores: {e}")
        return []

    def save_score(self, name, score, hull="interceptor", color="blue", user_id=None):
        """
        Adds a new score entry with player hull/color loadout.
        Persists to SQLite database if score repository is available,
        and synchronizes with local JSON leaderboard.
        """
        clean_name = str(name).strip().upper()[:20] or "UNKNOWN"
        clean_hull = str(hull).lower() if str(hull).lower() in ("interceptor", "cruiser", "vanguard") else "interceptor"
        clean_color = str(color).lower() if str(color).lower() in ("blue", "green", "orange", "red") else "blue"
        clean_score = max(0, int(score))

        # 1. Save to SQLite database if available
        if self.score_repo:
            try:
                self.score_repo.record_score(
                    name=clean_name,
                    score=clean_score,
                    hull=clean_hull,
                    color=clean_color,
                    user_id=user_id,
                )
            except Exception as e:
                print(f"[SaveSystem] Warning saving score to database: {e}")

        # 2. Synchronize to local JSON file
        scores = []
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        scores = data
            except Exception:
                scores = []

        scores.append({
            "name": clean_name[:8],
            "score": clean_score,
            "hull": clean_hull,
            "color": clean_color
        })
        scores = sorted(scores, key=lambda x: x.get("score", 0), reverse=True)[:10]

        try:
            with open(self.filepath, 'w') as f:
                json.dump(scores, f, indent=4)
            return True
        except Exception as e:
            print(f"Warning: Failed to save high scores JSON: {e}")
            return False

    def load_progress(self, user_id=None):
        """
        Loads campaign progression, 3-star ratings, and level high scores.
        If user_id is provided and progress_repo is available, loads user-scoped data.
        Otherwise falls back to level_progress.json.
        """
        if user_id is not None and self.progress_repo:
            try:
                db_progress = self.progress_repo.get_progress(user_id)
                if db_progress:
                    return db_progress
            except Exception as e:
                print(f"[SaveSystem] Warning loading progress from database: {e}")

        if not os.path.exists(self.progress_filepath):
            return self._get_default_progress()

        try:
            with open(self.progress_filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    highest = int(data.get("highest_unlocked", 1))
                    completed = data.get("completed_levels", [])
                    level_stars = data.get("level_stars", {})
                    level_scores = data.get("level_scores", {})

                    if not isinstance(completed, list):
                        completed = []
                    if not isinstance(level_stars, dict):
                        level_stars = {}
                    if not isinstance(level_scores, dict):
                        level_scores = {}

                    highest = max(1, min(highest, 10))
                    return {
                        "highest_unlocked": highest,
                        "completed_levels": [int(l) for l in completed if isinstance(l, (int, str)) and str(l).isdigit()],
                        "level_stars": {str(k): int(v) for k, v in level_stars.items()},
                        "level_scores": {str(k): int(v) for k, v in level_scores.items()}
                    }
        except Exception as e:
            print(f"Warning: Failed to load level progress JSON: {e}")

        return self._get_default_progress()

    def save_progress(self, selected_level, completed_levels=None, stars=0, score=0, user_id=None):
        """
        Save or update level progression, 3-star ratings, and per-level high score.
        If user_id is provided, commits to database for the specific pilot account.
        Also syncs local JSON file for guests and offline availability.
        """
        lvl_num = max(1, min(int(selected_level), 10))
        star_num = max(0, min(int(stars), 3))
        score_num = max(0, int(score))

        # 1. Save to SQLite database if user is authenticated
        if user_id is not None and self.progress_repo:
            try:
                self.progress_repo.save_level_progress(
                    user_id=user_id,
                    level=lvl_num,
                    stars=star_num,
                    score=score_num,
                    completed=True,
                )
            except Exception as e:
                print(f"[SaveSystem] Warning saving progress to database: {e}")

        # 2. Sync to local JSON file
        progress = self.load_progress()
        lvl_key = str(lvl_num)

        highest_unlocked = max(progress.get("highest_unlocked", 1), min(lvl_num + 1, 10))
        completed = set(progress.get("completed_levels", []))
        if completed_levels is not None:
            completed.update([int(l) for l in completed_levels])
        completed.add(lvl_num)

        stars_dict = progress.get("level_stars", {})
        existing_stars = int(stars_dict.get(lvl_key, 0))
        stars_dict[lvl_key] = max(existing_stars, star_num)

        scores_dict = progress.get("level_scores", {})
        existing_score = int(scores_dict.get(lvl_key, 0))
        scores_dict[lvl_key] = max(existing_score, score_num)

        payload = {
            "highest_unlocked": int(highest_unlocked),
            "completed_levels": sorted(completed),
            "level_stars": stars_dict,
            "level_scores": scores_dict
        }

        try:
            with open(self.progress_filepath, 'w') as f:
                json.dump(payload, f, indent=4)
            return True
        except Exception as e:
            print(f"Warning: Failed to save level progress JSON: {e}")
            return False

    def _get_default_scores(self):
        """Predefined default scores list when no high score file is found."""
        return [
            {"name": "COMMANDER", "score": 10000, "hull": "interceptor", "color": "blue"},
            {"name": "PILOT", "score": 5000, "hull": "cruiser", "color": "orange"},
            {"name": "RECRUIT", "score": 1000, "hull": "vanguard", "color": "green"}
        ]

    def _get_default_progress(self):
        """Default progression record for a fresh player profile."""
        return {
            "highest_unlocked": 1,
            "completed_levels": [],
            "level_stars": {},
            "level_scores": {}
        }


