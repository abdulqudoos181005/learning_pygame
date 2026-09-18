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

def _make_wave(count, types, weights, hp_mult=1.0, spd_mult=1.0, spawn_delay=1.5, formation="v_shape"):
    """
    Helper to build a single wave configuration dict.
    """
    return {
        "count": count,
        "types": types,
        "weights": weights,
        "hp_mult": hp_mult,
        "spd_mult": spd_mult,
        "spawn_delay": spawn_delay,
        "formation": formation,
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
    # Level 3 - Crimson raid begins (Snipers & Shield walls)
    {
        "waves": [
            _make_wave(7, ["scout", "stinger", "sniper_skiff"], [0.5, 0.3, 0.2], hp_mult=1.2, spd_mult=1.1, spawn_delay=1.4, formation="line"),
            _make_wave(9, ["aegis_defender", "scout", "sniper_skiff"], [0.25, 0.5, 0.25], hp_mult=1.2, spd_mult=1.1, spawn_delay=1.2, formation="shield_wall"),
        ],
        "boss_wave": False,
    },
    # Level 4 - Crimson raid climax (Shield wall & Ambush waves)
    {
        "waves": [
            _make_wave(8, ["aegis_defender", "stinger", "sniper_skiff"], [0.35, 0.4, 0.25], hp_mult=1.3, spd_mult=1.15, spawn_delay=1.3, formation="shield_wall"),
            _make_wave(10, ["phase_phantom", "cruiser", "stinger"], [0.35, 0.35, 0.3], hp_mult=1.3, spd_mult=1.15, spawn_delay=1.1, formation="ambush_wave"),
        ],
        "boss_wave": False,
    },
    # Level 5 - BOSS (Goliath Dreadnought)
    {
        "waves": [
            _make_wave(7, ["aegis_defender", "sniper_skiff", "stinger", "phase_phantom"], [0.3, 0.25, 0.25, 0.2], hp_mult=1.3, spd_mult=1.2, spawn_delay=1.2, formation="shield_wall"),
            _make_boss_wave(hp_mult=1.0, spd_mult=1.0),
        ],
        "boss_wave": True,
    },
    # Level 6 - Cryo blockade (Ambush wave & Carrier assault)
    {
        "waves": [
            _make_wave(10, ["phase_phantom", "sniper_skiff", "stinger"], [0.4, 0.3, 0.3], hp_mult=1.4, spd_mult=1.2, spawn_delay=1.2, formation="ambush_wave"),
            _make_wave(12, ["hive_carrier", "aegis_defender", "stinger"], [0.25, 0.3, 0.45], hp_mult=1.4, spd_mult=1.2, spawn_delay=1.0, formation="carrier_assault"),
        ],
        "boss_wave": False,
    },
    # Level 7 - Cryo blockade heavy (Shield walls & Carrier assaults)
    {
        "waves": [
            _make_wave(11, ["aegis_defender", "sniper_skiff", "cruiser"], [0.4, 0.35, 0.25], hp_mult=1.5, spd_mult=1.25, spawn_delay=1.1, formation="shield_wall"),
            _make_wave(13, ["hive_carrier", "phase_phantom", "sniper_skiff", "stinger"], [0.25, 0.35, 0.2, 0.2], hp_mult=1.5, spd_mult=1.25, spawn_delay=0.9, formation="carrier_assault"),
        ],
        "boss_wave": False,
    },
    # Level 8 - Shadow corps (Stealth ambush & Combined arms)
    {
        "waves": [
            _make_wave(12, ["phase_phantom", "sniper_skiff", "aegis_defender"], [0.45, 0.3, 0.25], hp_mult=1.7, spd_mult=1.3, spawn_delay=1.0, formation="ambush_wave"),
            _make_wave(14, ["hive_carrier", "aegis_defender", "phase_phantom", "cruiser"], [0.25, 0.3, 0.25, 0.2], hp_mult=1.7, spd_mult=1.3, spawn_delay=0.85, formation="carrier_assault"),
        ],
        "boss_wave": False,
    },
    # Level 9 - Shadow corps dread (Double carrier assault & Fortress wave)
    {
        "waves": [
            _make_wave(13, ["hive_carrier", "sniper_skiff", "phase_phantom"], [0.3, 0.35, 0.35], hp_mult=1.9, spd_mult=1.35, spawn_delay=0.95, formation="carrier_assault"),
            _make_wave(15, ["aegis_defender", "hive_carrier", "phase_phantom", "cruiser"], [0.3, 0.25, 0.25, 0.2], hp_mult=1.9, spd_mult=1.35, spawn_delay=0.75, formation="shield_wall"),
        ],
        "boss_wave": False,
    },
    # Level 10 - FINAL BOSS (Grand Armada Vanguard & Apex Void Leviathan)
    {
        "waves": [
            _make_wave(12, ["aegis_defender", "sniper_skiff", "phase_phantom", "hive_carrier", "cruiser"], [0.25, 0.2, 0.25, 0.15, 0.15], hp_mult=2.0, spd_mult=1.4, spawn_delay=0.9, formation="shield_wall"),
            _make_boss_wave(hp_mult=2.0, spd_mult=1.3),
        ],
        "boss_wave": True,
    },
]


# ---------------------------------------------------------------------------
# Sprint 11 / Pillar B — Faction theaters
#
# Maps each level range onto the armada folder(s), nebula, boss mothership,
# and projectile palette that should skin that mission, per the campaign
# table in implementation_plan.md. Only 3 projectile-color folders exist
# (blue_photon_beams / green_plasma_beams / red_crimson_beams), so theaters
# without a matching hue reuse the closest available color.
# ---------------------------------------------------------------------------

ARMADA_PREFIX = {
    "bio_swarm": "bio",
    "crimson_raiders": "crimson",
    "cryo_legion": "cryo",
    "shadow_corps": "shadow",
}

# Generic enemy type -> shared per-faction ship-role suffix (each armada
# folder mirrors the same 5-ship naming pattern).
ENEMY_ROLE_SUFFIX = {
    "scout": "scout_dart",
    "stinger": "wasp_stinger",
    "cruiser": "heavy_cruiser",
    "aegis_defender": "dreadnought",
    "sniper_skiff": "blade_interceptor",
    "phase_phantom": "blade_interceptor",
    "hive_carrier": "heavy_cruiser",
    "swarmer": "scout_dart",
}


def armada_image_key(armada_folder, enemy_type):
    """Builds the theater-specific sprite filename for an enemy role (e.g. 'crimson_wasp_stinger')."""
    prefix = ARMADA_PREFIX.get(armada_folder, "bio")
    suffix = ENEMY_ROLE_SUFFIX.get(enemy_type, "scout_dart")
    return f"{prefix}_{suffix}"


THEATERS = [
    {   # Levels 1-2 - Bio nursery
        "name": "Bio Nursery",
        "armadas": ["bio_swarm"],
        "nebula": "nebula_sapphire_drift",
        "nebula_secondary": None,
        "grade": None,
        "accent_color": (110, 170, 255),
        "boss_key": None,
        "laser_key": "laser_blue_beam_stream_long",
    },
    {   # Levels 3-4 - Crimson raid
        "name": "Crimson Raid",
        "armadas": ["crimson_raiders"],
        "nebula": "nebula_cosmic_magenta",
        "nebula_secondary": None,
        "grade": None,
        "accent_color": (255, 110, 150),
        "boss_key": None,
        "laser_key": "laser_red_beam_stream_long",
    },
    {   # Level 5 - First mothership (mix of the two prior factions, red-graded magenta nebula)
        "name": "First Mothership",
        "armadas": ["bio_swarm", "crimson_raiders"],
        "nebula": "nebula_cosmic_magenta",
        "nebula_secondary": None,
        "grade": ((200, 40, 40), 60),
        "accent_color": (255, 90, 90),
        "boss_key": "mothership_saucer_crimson_red",
        "laser_key": "laser_red_beam_stream_long",
    },
    {   # Levels 6-7 - Cryo blockade
        "name": "Cryo Blockade",
        "armadas": ["cryo_legion"],
        "nebula": "nebula_abyss_violet",
        "nebula_secondary": None,
        "grade": None,
        "accent_color": (160, 130, 255),
        "boss_key": None,
        "laser_key": "laser_blue_beam_stream_long",
    },
    {   # Levels 8-9 - Shadow corps (same violet nebula, desaturated grade)
        "name": "Shadow Corps",
        "armadas": ["shadow_corps"],
        "nebula": "nebula_abyss_violet",
        "nebula_secondary": None,
        "grade": ((100, 95, 110), 90),
        "accent_color": (120, 110, 140),
        "boss_key": None,
        "laser_key": "laser_green_beam_stream_long",
    },
    {   # Level 10 - Solar throne (all factions remnant + final saucer, magenta/violet pulse)
        "name": "Solar Throne",
        "armadas": ["bio_swarm", "crimson_raiders", "cryo_legion", "shadow_corps"],
        "nebula": "nebula_cosmic_magenta",
        "nebula_secondary": "nebula_abyss_violet",
        "grade": None,
        "accent_color": (255, 140, 190),
        "boss_key": "mothership_saucer_solar_gold",
        "laser_key": "laser_red_beam_stream_long",
    },
]


def get_theater(level_number):
    """Returns the faction-theater config dict for a given 1-based level number."""
    level_number = max(1, min(int(level_number), 10))
    if level_number <= 2:
        return THEATERS[0]
    if level_number <= 4:
        return THEATERS[1]
    if level_number == 5:
        return THEATERS[2]
    if level_number <= 7:
        return THEATERS[3]
    if level_number <= 9:
        return THEATERS[4]
    return THEATERS[5]


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
            cfg = self.current_wave_cfg
            types = cfg["types"]
            weights = cfg["weights"]
            count = cfg["count"]
            formation = cfg.get("formation", "v_shape")

            chosen = [random.choices(types, weights=weights)[0] for _ in range(count)]

            # Apply tactical formation ordering
            if formation == "shield_wall":
                # Frontline: Aegis defenders lead the charge, followed by standard craft, then Snipers in the rear
                def order_key(t):
                    if t == "aegis_defender":
                        return 0
                    elif t in ("scout", "stinger", "cruiser"):
                        return 1
                    elif t == "sniper_skiff":
                        return 2
                    return 1
                chosen.sort(key=order_key)
            elif formation == "carrier_assault":
                # Hive carriers appear early to deploy swarms
                def order_key(t):
                    if t == "hive_carrier":
                        return 0
                    return 1
                chosen.sort(key=order_key)
            elif formation == "ambush_wave":
                # Ambush wave: Phase Phantoms appear deeper into the wave
                def order_key(t):
                    if t != "phase_phantom":
                        return 0
                    return 1
                chosen.sort(key=order_key)

            self.spawn_queue = chosen

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

        # Allow a manually prepared queue or zero-time checks to consume immediately.
        # In normal gameplay a timer gate still controls cadence.
        if self.spawn_queue and self.spawned > 0 and dt <= 0:
            self.spawn_timer = 0.0
            self.spawned += 1
            return self.spawn_queue.pop(0)

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
