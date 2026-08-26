import json
import os

class SaveSystem:
    """
    Handles local persistence of player high scores and level progression.
    
    This system reads, writes, and maintains a sorted leaderboard, capping it
    to the top 10 scores to keep things clean.
    """
    def __init__(self, filename="high_scores.json", progress_filename="level_progress.json", settings_filename="settings.json"):
        # We calculate the absolute path to the high_scores.json file.
        # os.path.abspath(__file__) gets the full path of 'save_system.py'.
        # os.path.dirname(...) climbs up one folder to 'src/'.
        # The outer os.path.dirname(...) climbs up again to the project root directory.
        # This ensures the high score file is always created in the project root,
        # regardless of which folder the user launches the game script from.
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.filepath = os.path.join(project_root, filename)
        self.progress_filepath = os.path.join(project_root, progress_filename)
        self.settings_filepath = os.path.join(project_root, settings_filename)

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

    def load_loadout(self):
        """Loads ship loadout configuration (hull, color) from settings.json."""
        settings = self.load_settings()
        hull = str(settings.get("hull", "interceptor")).lower()
        color = str(settings.get("color", "blue")).lower()
        if hull not in ("interceptor", "cruiser", "vanguard"):
            hull = "interceptor"
        if color not in ("blue", "green", "orange", "red"):
            color = "blue"
        return {"hull": hull, "color": color}

    def save_loadout(self, hull, color):
        """Saves chosen ship hull and color to settings.json."""
        settings = self.load_settings()
        settings["hull"] = str(hull).lower() if str(hull).lower() in ("interceptor", "cruiser", "vanguard") else "interceptor"
        settings["color"] = str(color).lower() if str(color).lower() in ("blue", "green", "orange", "red") else "blue"
        return self.save_settings(settings)
        
    def load_scores(self):
        """
        Loads and returns the sorted high scores list from the JSON file.
        
        If the file doesn't exist or is corrupted, it safely catches the error
        and returns a predefined list of default scores so the game doesn't crash.
        """
        # If the high score file doesn't exist yet (e.g., first launch), load defaults
        if not os.path.exists(self.filepath):
            return self._get_default_scores()
            
        try:
            with open(self.filepath, 'r') as f:
                scores = json.load(f)
                # Ensure the loaded data is a list of dictionaries as expected
                if isinstance(scores, list):
                    # Sort the list of dictionaries in-place by the 'score' key in descending order.
                    # lambda x: x.get("score", 0) extracts the score value for comparison.
                    scores = sorted(scores, key=lambda x: x.get("score", 0), reverse=True)
                    return scores
        except Exception as e:
            # Catch file read or JSON decoding errors gracefully
            print(f"Warning: Failed to load high scores JSON: {e}")
            
        return self._get_default_scores()

    def save_score(self, name, score):
        """
        Adds a new score entry, sorts the leaderboard, limits it to the top 10,
        and saves it back to the JSON file.
        """
        # Load the existing list of high scores
        scores = self.load_scores()
        
        # Sanitize the input name:
        # Strip trailing/leading spaces, convert to uppercase, and restrict to 8 characters
        # for clean UI rendering in the HighScores table. If name is empty, default to "UNKNOWN".
        clean_name = str(name).strip().upper()[:8] or "UNKNOWN"
        
        # Append the new score entry
        scores.append({"name": clean_name, "score": int(score)})
        
        # Sort again to ensure the newly added score goes to its correct rank position
        scores = sorted(scores, key=lambda x: x["score"], reverse=True)
        
        # Slice the list to retain only the top 10 scores
        scores = scores[:10]
        
        try:
            # Open file in write mode ('w') and save the updated list as formatted JSON
            with open(self.filepath, 'w') as f:
                # indent=4 formats the JSON file with 4-space indentation, making it human-readable
                json.dump(scores, f, indent=4)
            return True
        except Exception as e:
            print(f"Warning: Failed to save high scores JSON: {e}")
            return False

    def load_progress(self):
        """Loads the player's level unlock/progression data from disk."""
        if not os.path.exists(self.progress_filepath):
            return self._get_default_progress()

        try:
            with open(self.progress_filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    highest = int(data.get("highest_unlocked", 1))
                    completed = data.get("completed_levels", [])
                    if not isinstance(completed, list):
                        completed = []
                    highest = max(1, min(highest, 10))
                    return {
                        "highest_unlocked": highest,
                        "completed_levels": [int(level) for level in completed if isinstance(level, int)]
                    }
        except Exception as e:
            print(f"Warning: Failed to load level progress JSON: {e}")

        return self._get_default_progress()

    def save_progress(self, selected_level, completed_levels=None):
        """Save or update level progression for the unlocked campaign."""
        progress = self.load_progress()
        highest_unlocked = max(progress.get("highest_unlocked", 1), min(selected_level + 1, 10))
        completed = set(progress.get("completed_levels", []))
        if completed_levels is not None:
            completed.update(completed_levels)
        completed.add(int(selected_level))

        payload = {
            "highest_unlocked": int(highest_unlocked),
            "completed_levels": sorted(completed)
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
            {"name": "COMMANDER", "score": 10000},
            {"name": "PILOT", "score": 5000},
            {"name": "RECRUIT", "score": 1000}
        ]

    def _get_default_progress(self):
        """Default progression record for a fresh player profile."""
        return {
            "highest_unlocked": 1,
            "completed_levels": []
        }

