"""
level_system.py — Space Shooters Sprint 2

Replaces the old open-ended wave counter with a structured 10-level system.
Each level has a fixed number of waves, and each wave has a config that drives
enemy type distribution, count, health/speed multipliers, and spawn timing.

Boss encounters are placed at Level 5 and Level 10 (the final boss).
"""

# ---------------------------------------------------------------------------
# Level Configuration Table
# ---------------------------------------------------------------------------

def _make_wave(count, types, weights, hp_mult=1.0, spd_mult=1.0, spawn_delay=1.5):
    """
    Helper to build a single wave configuration dict.
    
    Args:
        count       (int)   : Number of enemies to spawn this wave.
        types       (list)  : Enemy type strings (e.g. ['scout', 'stinger']).
        weights     (list)  : Relative probability weights matching `types`.
        hp_mult     (float) : Health point multiplier applied to each enemy this wave.
        spd_mult    (float) : Speed multiplier applied to each enemy this wave.
        spawn_delay (float) : Seconds between successive enemy spawns.
    """
    return {
        "count": count,
        "types": types,
        "weights": weights,
        "hp_mult": hp_mult,
        "spd_mult": spd_mult,
        "spawn_delay": spawn_delay,
        "boss": False,
    }


def _make_boss_wave(hp_mult=1.0, spd_mult=1.0):
    """Boss wave config - skips regular spawning and triggers the Boss sprite."""
    return {
        "count": 1,
        "types": [],
        "weights": [],
        "hp_mult": hp_mult,
        "spd_mult": spd_mult,
        "spawn_delay": 0,
        "boss": True,
    }


# 10 levels, progressively harder.
LEVEL_CONFIGS = [
    # Level 1
    {
        "waves": [
            _make_wave(5, ["scout"], [1.0], hp_mult=1.0, spd_mult=1.0, spawn_delay=1.6),
            _make_wave(6, ["scout"], [1.0], hp_mult=1.0, spd_mult=1.0, spawn_delay=1.4),
        ],
        "boss_wave": False,
    },
    # Level 2
    {
        "waves": [
            _make_wave(6, ["scout", "stinger"], [0.7, 0.3], hp_mult=1.1, spd_mult=1.05, spawn_delay=1.5),
            _make_wave(8, ["scout", "stinger"], [0.6, 0.4], hp_mult=1.1, spd_mult=1.05, spawn_delay=1.3),
        ],
        "boss_wave": False,
    },
    # Level 3
    {
        "waves": [
            _make_wave(7, ["scout", "stinger", "cruiser"], [0.5, 0.35, 0.15], hp_mult=1.2, spd_mult=1.1, spawn_delay=1.4),
            _make_wave(9, ["scout", "stinger", "cruiser"], [0.45, 0.35, 0.2], hp_mult=1.2, spd_mult=1.1, spawn_delay=1.2),
        ],
        "boss_wave": False,
    },
    # Level 4
    {
        "waves": [
            _make_wave(8, ["scout", "stinger", "cruiser"], [0.4, 0.4, 0.2], hp_mult=1.3, spd_mult=1.15, spawn_delay=1.3),
            _make_wave(10, ["scout", "stinger", "cruiser"], [0.35, 0.4, 0.25], hp_mult=1.3, spd_mult=1.15, spawn_delay=1.1),
        ],
        "boss_wave": False,
    },
    # Level 5 - BOSS
    {
        "waves": [
            _make_wave(6, ["scout", "stinger"], [0.5, 0.5], hp_mult=1.3, spd_mult=1.2, spawn_delay=1.2),
            _make_boss_wave(hp_mult=1.0, spd_mult=1.0),
        ],
        "boss_wave": True,
    },
    # Level 6
    {
        "waves": [
            _make_wave(10, ["scout", "stinger", "cruiser"], [0.35, 0.4, 0.25], hp_mult=1.4, spd_mult=1.2, spawn_delay=1.2),
            _make_wave(12, ["stinger", "cruiser"], [0.5, 0.5], hp_mult=1.4, spd_mult=1.2, spawn_delay=1.0),
        ],
        "boss_wave": False,
    },
    # Level 7
    {
        "waves": [
            _make_wave(10, ["scout", "stinger", "cruiser"], [0.3, 0.4, 0.3], hp_mult=1.5, spd_mult=1.25, spawn_delay=1.1),
            _make_wave(12, ["stinger", "cruiser"], [0.45, 0.55], hp_mult=1.5, spd_mult=1.25, spawn_delay=0.9),
        ],
        "boss_wave": False,
    },
    # Level 8
    {
        "waves": [
            _make_wave(12, ["scout", "stinger", "cruiser"], [0.25, 0.4, 0.35], hp_mult=1.7, spd_mult=1.3, spawn_delay=1.0),
            _make_wave(14, ["stinger", "cruiser"], [0.4, 0.6], hp_mult=1.7, spd_mult=1.3, spawn_delay=0.85),
        ],
        "boss_wave": False,
    },
    # Level 9
    {
        "waves": [
            _make_wave(12, ["stinger", "cruiser"], [0.45, 0.55], hp_mult=1.9, spd_mult=1.35, spawn_delay=0.95),
            _make_wave(15, ["stinger", "cruiser"], [0.4, 0.6], hp_mult=1.9, spd_mult=1.35, spawn_delay=0.75),
        ],
        "boss_wave": False,
    },
    # Level 10 - FINAL BOSS
    {
        "waves": [
            _make_wave(10, ["stinger", "cruiser"], [0.4, 0.6], hp_mult=2.0, spd_mult=1.4, spawn_delay=0.9),
            _make_boss_wave(hp_mult=2.0, spd_mult=1.3),
        ],
        "boss_wave": True,
    },
]


class LevelSystem:
    """
    Manages the current level, wave-within-level, and enemy spawn scheduling.
    
    The PlayState delegates all 'what to spawn next?' questions to this class,
    keeping the state itself clean and free of hardcoded level logic.
    """

    def __init__(self, starting_level=1):
        self.level_index = max(0, min(starting_level - 1, len(LEVEL_CONFIGS) - 1))
        self.wave_index  = 0         # 0-based index into current level's waves list
        self.spawned     = 0         # Enemies spawned in the current wave so far
        self.spawn_timer = 0.0       # Countdown until next spawn
        self.spawn_queue = []        # Queue of enemy types for smoother, data-structure-based spawning
        self.complete    = False     # True after Level 10 boss is defeated
        self._load_wave()

    def start_level(self, level_number):
        """Reset the system so a selected level becomes the new campaign entry point."""
        level_number = max(1, min(int(level_number), len(LEVEL_CONFIGS)))
        self.level_index = level_number - 1
        self.wave_index = 0
        self.complete = False
        self._load_wave()

    @property
    def level_number(self):
        """1-based level number for display."""
        return self.level_index + 1

    @property
    def wave_number(self):
        """1-based wave number within the current level for display."""
        return self.wave_index + 1

    @property
    def total_levels(self):
        return len(LEVEL_CONFIGS)

    @property
    def current_wave_cfg(self):
        """The active wave configuration dict."""
        return LEVEL_CONFIGS[self.level_index]["waves"][self.wave_index]

    @property
    def is_boss_wave(self):
        return self.current_wave_cfg["boss"]

    @property
    def wave_enemy_count(self):
        return self.current_wave_cfg["count"]

    @property
    def hp_mult(self):
        return self.current_wave_cfg["hp_mult"]

    @property
    def spd_mult(self):
        return self.current_wave_cfg["spd_mult"]

    @property
    def spawn_delay(self):
        return self.current_wave_cfg["spawn_delay"]

    def _load_wave(self):
        """Reset per-wave counters for the current wave."""
        self.spawned     = 0
        self.spawn_timer = 0.0
        self.spawn_queue = []
        if not self.current_wave_cfg["boss"]:
            import random
            self.spawn_queue = [
                random.choices(self.current_wave_cfg["types"], weights=self.current_wave_cfg["weights"])[0]
                for _ in range(self.current_wave_cfg["count"])
            ]

    def tick_spawn(self, dt):
        """
        Called every frame (after the intro banner clears).

        Returns:
            str or None: enemy type to spawn ('scout','stinger','cruiser','boss'),
                         or None if no spawn this frame.
        """
        cfg = self.current_wave_cfg

        # Boss wave: spawn once and stop
        if cfg["boss"]:
            if self.spawned == 0:
                self.spawned = 1
                return "boss"
            return None

        # Regular wave: spawn until count reached
        if self.spawned >= cfg["count"]:
            return None

        if not self.spawn_queue:
            import random
            self.spawn_queue = [
                random.choices(cfg["types"], weights=cfg["weights"])[0]
                for _ in range(cfg["count"])
            ]

        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return None

        self.spawn_timer = cfg["spawn_delay"]
        self.spawned += 1
        return self.spawn_queue.pop(0)

    def wave_finished_spawning(self):
        """True when all enemies for this wave have been queued."""
        return self.spawned >= self.current_wave_cfg["count"]

    def advance_wave(self):
        """
        Move to the next wave in the current level, or the next level.
        
        Returns:
            'wave'     - moved to next wave in same level
            'level'    - moved to next level
            'complete' - all 10 levels done
        """
        level_cfg = LEVEL_CONFIGS[self.level_index]
        next_wave = self.wave_index + 1

        if next_wave < len(level_cfg["waves"]):
            self.wave_index = next_wave
            self._load_wave()
            return "wave"
        else:
            next_level = self.level_index + 1
            if next_level >= len(LEVEL_CONFIGS):
                self.complete = True
                return "complete"
            self.level_index = next_level
            self.wave_index  = 0
            self._load_wave()
            return "level"

    def banner_text(self):
        """Returns the string to show on the wave-intro banner."""
        if self.is_boss_wave:
            if self.level_number == 10:
                return "FINAL BOSS - ANNIHILATOR"
            return "BOSS INCOMING"
        return f"LEVEL {self.level_number}  -  WAVE {self.wave_number}"

    def banner_color(self):
        """Returns the RGB color for the intro banner."""
        if self.is_boss_wave:
            return (255, 0, 50)
        if self.wave_index == 0:
            return (0, 255, 200)   # Teal for new level
        return (255, 200, 0)       # Gold for subsequent waves
