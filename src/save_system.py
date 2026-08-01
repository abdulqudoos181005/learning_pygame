import json
import os

class SaveSystem:
    def __init__(self, filename="high_scores.json"):
        # Put high_scores.json in the project root directory
        self.filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
        
    def load_scores(self):
        """Loads and returns sorted high scores list from file. Returns a default list if file doesn't exist."""
        if not os.path.exists(self.filepath):
            return self._get_default_scores()
            
        try:
            with open(self.filepath, 'r') as f:
                scores = json.load(f)
                # Ensure it's a list and sorted
                if isinstance(scores, list):
                    scores = sorted(scores, key=lambda x: x.get("score", 0), reverse=True)
                    return scores
        except Exception as e:
            print(f"Warning: Failed to load high scores JSON: {e}")
            
        return self._get_default_scores()

    def save_score(self, name, score):
        """Adds a score, sorts the leaderboard, trims it to top 10, and writes to file."""
        scores = self.load_scores()
        
        # Strip name or set default
        clean_name = str(name).strip().upper()[:8] or "UNKNOWN"
        
        scores.append({"name": clean_name, "score": int(score)})
        # Sort descending
        scores = sorted(scores, key=lambda x: x["score"], reverse=True)
        # Limit to top 10
        scores = scores[:10]
        
        try:
            with open(self.filepath, 'w') as f:
                json.dump(scores, f, indent=4)
            return True
        except Exception as e:
            print(f"Warning: Failed to save high scores JSON: {e}")
            return False

    def _get_default_scores(self):
        return [
            {"name": "COMMANDER", "score": 10000},
            {"name": "PILOT", "score": 5000},
            {"name": "RECRUIT", "score": 1000}
        ]
