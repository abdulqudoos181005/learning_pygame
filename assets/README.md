# 🚀 Game Assets Directory & Thematic Catalog

Welcome to the organized **Space Shooter Game Assets Catalog**. All 318 assets have been sorted into **12 distinct thematic vibe folders** with semantic, expressive naming for rapid discovery and modular game development.

---

## 📁 Directory Structure Overview

```text
assets/
├── alien_armada/          # Alien invaders grouped by faction vibe & size
│   ├── bio_swarm/         # Green bio-mechanical swarm ships
│   ├── boss_motherships/  # Massive UFO mothership saucers
│   ├── crimson_raiders/   # Aggressive crimson-red strike fleet
│   ├── cryo_legion/       # High-tech icy-blue tactical ships
│   └── shadow_corps/      # Stealth obsidian/black dreadnoughts & fighters
├── audio/                 # Background music & crisp sound effects
│   ├── music/             # Atmospheric battle themes & tracks
│   └── sfx/               # Lasers, shields, powerups, alarms, EMPs
├── fonts/                 # Retro-futuristic TTF vector fonts
├── modular_shipyard/      # Custom ship builder modules & parts
│   ├── cannons_turrets/   # Heavy cannons, dual blasters & turret mounts
│   ├── cockpits/          # Colored canopy modules (Blue, Green, Red, Yellow)
│   ├── engines/           # Sub-light ion & plasma thruster units
│   ├── hull_scratches/    # Battle-damage hull scratch decals
│   ├── structural_beams/  # Modular ship girders & beam struts
│   └── wings/             # Aerodynamic & space-flight wing assemblies
├── player_fleet/          # Starfighter craft & hull damage overlays
│   └── damage_overlays/   # Light, moderate, and critical battle damage FX
├── powerups_pickups/      # In-game collectibles & tier upgrades
│   ├── ancient_relics/    # Bronze, Silver, and Gold score artifacts
│   ├── medical_capsules/  # Health, Energy, Overcharge, and Velocity pills
│   ├── powerup_orbs/      # Tactical floating orbs (Shield, Bolt, Star)
│   └── tier_badges/       # Rank medals & achievement tokens
├── raw_sheets_source/     # Master spritesheets, XML maps, SVG vectors & license
├── space_environments/    # Parallax background nebula & void textures
├── space_hazards/         # Deep-space asteroid fields & debris
│   ├── carbon_meteors/    # Brown carbonaceous asteroids (Titan to tiny)
│   └── iron_meteors/      # Grey metallic iron asteroids (Titan to tiny)
├── ui_hud/                # Glassmorphic cyber UI & HUD elements
│   ├── cyber_buttons/     # Glowing neon glass action buttons
│   ├── cyber_numerals/    # Digital font numerals & multiplier glyphs
│   ├── life_counters/     # HUD mini player ship life icons
│   └── reticle_cursor/    # Tactical crosshair aiming reticle
├── vfx_effects/           # Visual effects, forcefields & trails
│   ├── energy_shields/    # Forcefield bubble layers & shields
│   ├── sparkles/          # Stardust flares & cosmic glimmers
│   ├── speed_trails/      # Hyperspeed warp blur lines
│   └── thruster_plumes/   # Dynamic afterburner & engine exhaust flares
└── weapons_projectiles/   # High-energy laser bolts & plasma beams
    ├── blue_photon_beams/ # 16 photon laser variants (bolts, streams, waves)
    ├── green_plasma_beams/# 16 plasma laser variants (bolts, lances, bursts)
    └── red_crimson_beams/ # 16 crimson thermal laser variants
```

---

## 🎨 Theme & Vibe Breakdown

### 1. 🌌 Space Environments (`space_environments/`)
* **Vibe**: Vast cosmic expanse, glowing nebulae, deep void.
* **Files**:
  - `void_black_stars.png`: Deep dark space backdrop with faint distant stars.
  - `nebula_sapphire_drift.png`: Vibrant cyan/blue stellar dust cloud.
  - `nebula_abyss_violet.png`: Dark purple mysterious cosmic void.
  - `nebula_cosmic_magenta.png`: High-energy violet-magenta nebula.

### 2. 🛸 Player Fleet (`player_fleet/`)
* **Vibe**: Sleek, heroic, high-tech human vanguard starfighters.
* **Hull Archetypes** (available in **Blue, Green, Orange, Red**):
  - `interceptor_strike_<color>.png`: Balanced strike fighter with dual wing mounts.
  - `heavy_cruiser_assault_<color>.png`: Armored assault gunship with broad hull.
  - `stealth_vanguard_bomber_<color>.png`: Forward-swept wing stealth craft.
* **Damage Overlays** (`damage_overlays/`):
  - `<archetype>_damage_light.png`
  - `<archetype>_damage_moderate.png`
  - `<archetype>_damage_critical.png`

### 3. 👾 Alien Armada (`alien_armada/`)
* **Vibe**: Menacing, diverse extraterrestrial factions.
* **Faction Corps**:
  - **`shadow_corps/`**: Obsidian stealth raiders (`shadow_dreadnought`, `shadow_heavy_cruiser`, `shadow_wasp_stinger`, `shadow_scout_dart`, `shadow_blade_interceptor`).
  - **`cryo_legion/`**: Advanced icy blue tactical fleet.
  - **`bio_swarm/`**: Venomous green bio-mechanical insectoid ships.
  - **`crimson_raiders/`**: Aggressive high-damage crimson dreadnoughts.
  - **`boss_motherships/`**: Heavy UFO saucer motherships (`mothership_saucer_cryo_blue`, `bio_green`, `crimson_red`, `solar_gold`).

### 4. ⚡ Weapons & Projectiles (`weapons_projectiles/`)
* **Vibe**: High-energy sci-fi ordnance, crisp lasers, heavy plasma rods.
* **Categories**:
  - `blue_photon_beams/`: 16 variations (`laser_blue_bolt_standard`, `laser_blue_stream_long`, `laser_blue_wide_wave`, `laser_blue_heavy_slug`, etc.)
  - `green_plasma_beams/`: 16 variations (`laser_green_bolt_standard`, `laser_green_plasma_burst`, `laser_green_focus_lance`, etc.)
  - `red_crimson_beams/`: 16 variations (`laser_red_stream_long`, `laser_red_charge_flare`, `laser_red_heavy_slug`, etc.)

### 5. 🪨 Space Hazards (`space_hazards/`)
* **Vibe**: Drifting asteroid belts, explosive cosmic rocks, hazardous mineral fields.
* **Mineral Types**:
  - **`carbon_meteors/`**: Brown carbonaceous rocks (`meteor_carbon_titan_01..04`, `medium_01..02`, `small_01..02`, `tiny_debris_01..02`).
  - **`iron_meteors/`**: Heavy grey ferrous asteroid chunks (`meteor_iron_titan_01..04`, `medium_01..02`, `small_01..02`, `tiny_debris_01..02`).

### 6. 💊 Power-ups & Pickups (`powerups_pickups/`)
* **Vibe**: Rewarding glowing loot drops and tactical combat buffs.
* **Subcategories**:
  - **`medical_capsules/`**: `capsule_health_green`, `capsule_energy_blue`, `capsule_overcharge_red`, `capsule_velocity_yellow`.
  - **`powerup_orbs/`**: Floating tactical shields (`orb_shield_*`), hyper stars (`orb_star_*`), speed bolts (`orb_bolt_*`).
  - **`tier_badges/`**: Bronze, Silver, and Gold badges for shields, bolts, and stars.
  - **`ancient_relics/`**: High-value score artifacts (`relic_artifact_bronze`, `silver`, `gold`).

### 7. 🔥 VFX & Thrusters (`vfx_effects/`)
* **Vibe**: Dynamic particle energy, thruster flames, forcefield bubbles.
* **Elements**:
  - `thruster_plumes/`: 20 progressive flame sizes/shapes (`thruster_flame_00` to `19`).
  - `energy_shields/`: `forcefield_bubble_outer`, `forcefield_bubble_core`, `forcefield_bubble_dense`.
  - `speed_trails/`: `hyperspace_warp_lines`.
  - `sparkles/`: `sparkle_stardust_small`, `sparkle_stardust_medium`, `sparkle_stardust_flare`.

### 8. 🎛️ UI & HUD Elements (`ui_hud/`)
* **Vibe**: Sleek cyberpunk neon arcade interface.
* **Elements**:
  - `cyber_buttons/`: Glass action buttons (`btn_glass_cyan`, `btn_glass_emerald`, `btn_glass_ruby`, `btn_glass_amber`).
  - `reticle_cursor/`: `crosshair_tactical_cursor.png`.
  - `cyber_numerals/`: Digital score digits (`digit_0` to `digit_9`, `digit_multiplier_x`).
  - `life_counters/`: Mini HUD icons for every player ship color & class.

### 9. 🛠️ Modular Shipyard (`modular_shipyard/`)
* **Vibe**: Deep modular spaceship construction kit.
* **Parts**:
  - `cockpits/`: 32 cockpit modules across 4 color palettes.
  - `wings/`: 32 wing styles across 4 color palettes.
  - `engines/`: 5 heavy engine and thruster modules.
  - `cannons_turrets/`: 11 weapon barrels and heavy/light turret mounts.
  - `structural_beams/`: 7 connector joints and long structural girders.
  - `hull_scratches/`: Battle-wear weathering textures.

### 10. 🔊 Audio & Soundscapes (`audio/`)
* **Vibe**: High-energy 8-bit/16-bit arcade synth soundscape.
* **Tracks & SFX**:
  - `music/theme_boss_arcade_battle.wav`: Fast-paced boss encounter music.
  - `sfx/laser_blaster_crisp.wav`: Sharp player blaster fire.
  - `sfx/laser_retro_pew_01.ogg` / `02.ogg`: Retro synth projectile blasts.
  - `sfx/player_death_alarm.wav`: Player destruction warning sequence.
  - `sfx/shield_activate.ogg` & `shield_depleted.ogg`: Forcefield state transitions.
  - `sfx/powerup_bonus_chime.ogg`: Harmonic buff pickup sound.
  - `sfx/alien_emp_zap.ogg`: Alien electrical discharge.

### 11. 🔤 Fonts (`fonts/`)
* **Vibe**: Cyber-tactical vector typography.
* **Files**:
  - `vector_future_bold.ttf`: Heavy geometric display typeface.
  - `vector_future_thin.ttf`: Clean high-tech UI sub-font.
  - `audiowide_cyber_display.ttf`: Modern sci-fi display font.

---

## 💻 Programmatic Usage (`AssetsLoader`)

The `AssetsLoader` class automatically indexes all subdirectories and provides O(1) cached access with fallback art:

```python
# 1. Load by thematic path
img = assets.get_image("player_fleet/interceptor_strike_blue", width=60, height=60)
bg  = assets.get_image("space_environments/nebula_sapphire_drift")
snd = assets.get_sound("audio/sfx/laser_blaster_crisp")

# 2. Load by unique base name
boss_ship = assets.get_image("mothership_saucer_crimson_red", 150, 100)

# 3. Load via semantic aliases (automatic mapping)
player = assets.get_image("player", 60, 60)               # Maps to interceptor_strike_blue
enemy  = assets.get_image("enemy_scout", 45, 45)          # Maps to bio_scout_dart
rock   = assets.get_image("asteroid_large_brown", 70, 70) # Maps to meteor_carbon_titan_01
laser  = assets.get_sound("laser")                        # Maps to laser_blaster_crisp
```

---
*Created and organized for the Pygame Space Shooter project. Graphics & SFX credit: Kenney.nl (CC0) & Mixkit.*
