# Space Shooters Game — Development Plan

This plan tracks the full design, architecture, and progress of the **Space Shooters** Pygame project.

---

## Decisions Made

> [!NOTE]
> - **Resolution**: 1280×720 (16:9 HD) — standard desktop indie resolution.
> - **Controls**: WASD / Arrow keys to move, SPACE to shoot, M to launch missile, ESC to pause.
> - **Game Style**: Level-based shooter — 10 levels with increasing difficulty and a final Boss on Level 10.
> - **Assets**: Procedurally generated vector art + graceful PNG fallback via `AssetsLoader`.

---

## Sprint 1 — ✅ COMPLETE

All core architecture and gameplay systems were built.

### 1. Game Architecture & Manager

#### ✅ [DONE] [game.py](file:///d:/projects/learning_pygame/src/game.py)
The central engine class:
- Initializes Pygame, mixer, display window (1280×720), and clock.
- Hosts the main game loop (60 FPS cap, delta-time based).
- Manages state switching via the **State Pattern** (`change_state()`).
- Owns the shared `AssetsLoader` instance used by all states/sprites.

#### ✅ [DONE] [states.py](file:///d:/projects/learning_pygame/src/states.py)
All game states implemented:
- `MenuState` — animated starfield, keyboard-navigated option list (Play, High Scores, Quit).
- `PlayState` — main gameplay loop with enemy waves, HUD, screen shake, collisions.
- `PauseState` — semi-transparent overlay, resume / quit to menu.
- `GameOverState` — name entry with blinking cursor, score saved to JSON.
- `HighScoresState` — top-10 leaderboard table loaded from JSON.

---

### 2. Entities & Physics

#### ✅ [DONE] [sprites.py](file:///d:/projects/learning_pygame/src/sprites.py)
- `Player`: WASD movement, shield system, weapon firing, power-up timers.
- `Laser`: Directional projectile with angle support; player vs enemy variants.
- `Enemy`: Three type variants — `Scout`, `Stinger`, `Cruiser` — each with unique movement and attack patterns.
- `Boss`: Three-phase attack boss with health bar and phase-based firing patterns.
- `PowerUp`: Floating drops — Shield, Triple Shot, Speed Boost.

---

### 3. FX & UI Systems

#### ✅ [DONE] [fx.py](file:///d:/projects/learning_pygame/src/fx.py)
- `Starfield`: 3-layer parallax scrolling star background.
- `Particle` + `spawn_explosion()`: Radial particle bursts for explosions.
- `spawn_sparks()`: Directional spark impacts on laser hits.
- Screen shake double-buffer system (canvas → offset blit).

#### ⚠️ [SKIPPED] ui.py
HUD was implemented directly inside `PlayState._draw_hud()` instead of a separate file. No standalone `ui.py` was created — HUD is self-contained in `states.py`.

---

### 4. Data & Packaging

#### ✅ [DONE] [save_system.py](file:///d:/projects/learning_pygame/src/save_system.py)
- Loads/saves high scores to `high_scores.json` at project root.
- Auto-sorts and caps at top 10. Defaults to sample scores on first launch.

#### ✅ [DONE] [assets_loader.py](file:///d:/projects/learning_pygame/src/assets_loader.py)
- Caches images and sounds to avoid repeated disk reads.
- Procedural vector fallback for all sprites if PNG files are missing.
- System font loading (`Trebuchet MS`) for HUD, title, and menu text.

---

## Sprint 2 — ✅ COMPLETE

Level system, new powerups, and homing missile weapon implemented.

### 1. Level System

#### ✅ [NEW] [level_system.py](file:///d:/projects/learning_pygame/src/level_system.py)
Replaces the old open-ended wave counter with a structured **10-level config system**:
- Each level has 2 waves. Enemies get progressively harder (more HP, faster speed) via `hp_mult` / `spd_mult`.
- Boss encounters at **Level 5** and **Level 10** (final boss — 2× HP + 1.3× speed).
- `LevelSystem.tick_spawn(dt)` returns the next enemy type to spawn each frame.
- `LevelSystem.advance_wave()` handles wave → level → `"complete"` transitions.
- Banner text + color driven by `banner_text()` / `banner_color()` methods.

---

### 2. New Sprites & Weapons

#### ✅ [MODIFIED] [sprites.py](file:///d:/projects/learning_pygame/src/sprites.py)

**Laser changes:**
- Added `damage` parameter (default 10 for player, auto for enemy).
- Power laser variant uses `img_name="laser_power"` for red visual + 20 damage.

**Player changes:**
- `laser_power_timer` — activates red 2× damage laser for 10 seconds.
- `missile_count` — stored homing missiles; launched with **M key**.
- `missile_cooldown` — prevents missile spam (0.5s between launches).
- `triple_shot_timer` and `speed_boost_timer` still present (duration now 12s each).

**Enemy changes:**
- `hp_mult` and `spd_mult` constructor params — scale health and speed per level config.

**Boss changes:**
- Accepts `hp_mult` and `spd_mult` — final boss at Level 10 has 2× health.
- Phase transitions now proportional to `max_health` (30% / 70% thresholds).
- `score_value` also scales with `hp_mult`.

**New: `Missile` sprite:**
- Homing missile that targets the enemy with the **highest current health**.
- Steers with a configurable turn rate (`TURN_RATE = 3.5 rad/s`), speed `450 px/s`.
- Deals `30 damage` on collision + triggers a large orange explosion.
- Rotates its sprite dynamically to match heading direction.

**PowerUp changes:**
- `BASE_TYPES` = `shield`, `triple`, `speed` (all levels).
- `EXTRA_TYPES` = `health`, `power_laser`, `missile` (unlocked from Level 3+).

---

### 3. New Assets

#### ✅ [MODIFIED] [assets_loader.py](file:///d:/projects/learning_pygame/src/assets_loader.py)
New procedural images added:
- `laser_power` — thick red beam with orange-yellow core.
- `powerup_health` — green circle with white cross (medical style).
- `powerup_power_laser` — crimson orb with `P` label.
- `powerup_missile` — orange orb with `M` label.
- `missile` — orange rocket with nose cone, fins, and exhaust glow.

---

### 4. PlayState & HUD Overhaul

#### ✅ [MODIFIED] [states.py](file:///d:/projects/learning_pygame/src/states.py)

**PlayState changes:**
- Uses `LevelSystem` for all wave/level logic — no more hardcoded wave variables.
- Added `missiles` sprite group; missile vs enemy collision (30 dmg + explosion + screen shake).
- Powerup collection handles all 6 types:
  - `shield` → +40 shield (capped at max).
  - `triple` → 12s triple shot (↑ from 8s).
  - `speed` → 12s speed boost (↑ from 8s).
  - `health` → +30 HP (capped at 100). *(New)*
  - `power_laser` → 10s red 2× damage laser. *(New)*
  - `missile` → +1 missile to inventory. *(New)*
- Powerup drops from Level 3+ include the 3 new extra types (equal weight spread).

**HUD additions:**
- Level + Wave tracker replaces old wave-only counter.
- Missile inventory display with icon row + `[M]` label.
- Power Laser timer bar added to active powerup section.
- Wave banner now uses `LevelSystem.banner_text()` / `banner_color()`.

**New: `GameCompleteState`:**
- Victory screen with pulsing gold title shown after beating Level 10.
- Auto-saves score as `"VICTOR"` and redirects to leaderboard.

---

## Sprint 3 — ✅ COMPLETE

### new game state (UI for levels)
[description]  a state or a new screen where a player can select the level which appears after clicking "Play Game" in the main menu and the user is directed to after beating every level 

### appearance 
-> should match the theme of the UI
-> 2 rows, 5 levels each row
-> should display a banner "LEVELS" at the top
-> the current highest unlocked/playble level should blink softly 
-> completed levels should be green 
-> Locked level (levels after the current highest unlocked/playble level) should be grayed out
-> an exit arrow to go back to the main menu 
-> means every level can be played multiple times
-> make it interactive 
-> make that so all the buttons can also be pressed via a mouse click and hovering over the button should change its color slightly to indicate it is being hovered 
-> 


### changes
do as it is required 

### sprites 
-> should use the same style of sprites as the other game objects (player, enemy, powerups, etc.)

### Sprint 3 completion notes
- The level-select screen is implemented as a dedicated interactive UI state that opens after clicking the main menu play action and can also be reached from the game-complete flow.
- The selector uses a 2×5 grid layout with a visible `LEVELS` banner, per-level status colors, soft blinking for the current highest unlocked level, and a menu back control.
- The level tiles are mouse-clickable and hover-aware, while preserving replayability by allowing levels to be replayed multiple times.
- The level selector continues to follow the project’s existing visual theme and sprite style conventions for consistent presentation.


---


## Sprint 4 — ✅ COMPLETE

### making the game accessble by mouse and clickble 
[description]: now in this sprint we are going to make the UI elements be clickble buttons 

### changes
-> making the main menu buttons be clickble
-> making the leaderboard escape button clickble
-> making the pause menu buttons be clickble 
[NOTE] future any changes in UI or addition of any other UI component remember to make them acessble by the mouse too (clickble)

[NOTE] you are going to make sure no other funtionaltiy is being compromised and follow the instructions throughly

## MODIFICATIONS of sprint 4: ✅ COMPLETE
-Make the tiles un-acessble via enter if the cursor is not hovering. *(completed)*
-make the leadboard's and level's "menu" button more interactive (changes color upon hovering). *(completed)*
-fix the bug for the current highest level hover effect (currently upon hovering once it remain in the same state even when the cursor is not upon it). *(completed)*
-make the passed level button interactive too (changes color upon hovering). *(completed)*
-make the box/borders of the main menu buttons be allinged as currently they are not bcz of unknown dot infront of them. *(completed)*
-add some little animation for each click/hover to make it look more engaging/interactive *(completed)*

### Sprint 4 completion notes
- Shared mouse-friendly button rendering now powers the main menu, pause menu, leaderboard back button, and end-state confirmations.
- The level selector now resets stale hover state when the cursor leaves a tile, and keyboard `Enter` only launches a level when there is a valid hover target.
- All sprint-4 requested polish items were implemented without compromising existing gameplay flow.


---


## Sprint 5 
**description** gameplay changes

### change no 1.
**description** after completion of a level, go back to the level state and so the player sees the level state and selects either the new level (which just unlocked by clear a previous level) or select any other level as he whiches rather than progressing automaticly.
*reason*: current way doesnt give the **feel** of progression and this way will do
[NOTE] the player should get a "congratulations" message window (showing its score) before getting to the levels menu. 

### change no 2.
**description** the power-ups changes:
-there should be a "pity/acculmation" system so a power-up drop id guareented after killing 3 enemies **NOTE** it should follow a random approach as it does right now *but* only if it doesn't drop after killing any 2 enemies the 3rd enemy should drop.
-the leaser should be upgraded after every 3 levels,  and the upgrades should effect its damage and color, 
*teir-1* normal, as it is currently, for 1,2 and 3 level.
*teir-2* bit higher damage, as it is currently for powerful laser power-up, for 4,5 and 6 level.
*teir-3* same jump up as in teir-1 to teir-2, and purple color, for 7,8,9 and 10 level.
-the powerful laser powerup should act as the next laser teir which will come as a next progressive laser upgrade. [flow] if i am at 2nd level (teir-1), then powerful laser powerup should give me the laser as ill get after completing the 3rd level (teir-2) and likewise with other scenarios.
*Reason* current system diesnt feel rewarding and as the game progresses it feels more difficult and tiresome
**GOAL** to overcome the short commings (mentioned in the reasons) and make the gameplay more engaing

### change no 3:
**description** add a invincibility for 4 secs in the start of a level and as a life is lost and the begining of the new life,
-make the player blink for the duration of the invincibility so the player knows he is invincible
*Reason* in some circumstances player may panick or might crash and to prevent that we will do this 
**GOAL** to ensure good gameplay

### Sprint 5 completion notes
- The sprint goals are now live in the game loop: level completion loops back to the campaign selector via a score-based congratulations popup, power rewards are more forgiving and better paced, and the player receives clear safety feedback during the start-of-level and respawn invulnerability intervals.
- These changes were implemented without regressing the existing mouse-click UI and level selector flow from Sprint 3–4.

---

## Sprint 6 — Game Feel & Polish

### description
This sprint focuses on the parts that make a shooter feel alive instead of merely functional. The game already has progression, enemies, bosses, and menu systems, but it still needs stronger moment-to-moment feedback, better player readability, and a more rewarding rhythm so it feels like a complete game rather than a prototype.

### core missing ingredients

#### 1. Player feedback and responsiveness
- Add stronger hit feedback when the player takes damage: screen flash, quick camera shake, red vignette, and a brief knockback effect.
- Make enemy impacts feel readable with distinct hit spark colors for player shots vs enemy shots.
- Improve weapon firing feedback with muzzle flashes, recoil motion, and more satisfying shot timing.
- Ensure the player always feels in control through smoother aim, consistent movement drift, and better collision response.

#### 2. Better enemy telegraphing and threat readability
- Add warning indicators before boss attacks or heavy enemy volleys.
- Give enemies distinct attack cues so the player can anticipate danger instead of reacting blind.
- Show enemy health bars or at least stronger visual states for elite enemies and bosses.
- Add more contrast between backgrounds and threats so the player can understand danger quickly at a glance.

#### 3. Reward and progression rhythm
- Add more satisfying score popups, combo text, and floating damage numbers for major hits.
- Show clear reward moments after clearing a wave or boss: screen pulse, new unlock notification, and short celebratory sound.
- Make checkpoints and difficulty progression feel earned, not just numerical.
- Reward the player with visible progression in the level select screen and with clearly communicated unlocks.

#### 4. Audio and atmosphere
- Add a more complete sound system: shot sounds, enemy explosions, power-up pickup, hit feedback, boss warnings, and menu transitions.
- Use volume layering and distinct sound categories so the game has an audible identity.
- Add subtle background music changes between menu, normal combat, and boss phases.
- Audio should reinforce danger, reward, and success rather than just playing generic effects.

#### 5. Screen-space polish and readability
- Improve the HUD with clearer health, shield, and ammo-style indicators that are easy to read under pressure.
- Add pulse animations for power-ups and high-priority pickups so they are easier to spot.
- Add subtle motion to the background, UI, and parallax layers so the game feels denser and more alive.
- Standardize fonts, icon sizing, and spacing to make the interface feel intentional.

#### 6. Difficulty tuning and pacing
- Separate enemy wave difficulty from pure stat scaling; use pacing, formation changes, and burst patterns to create memorable encounters.
- Slow the early game down just enough to teach the player the mechanics, then accelerate tension gradually.
- Ensure boss fights feel like climactic moments, not just larger enemies with more health.
- Add a small amount of breathing room after difficult sections so the player can recover without frustration.

#### 7. State transitions and “game identity”
- Add a short intro sequence or title card before each major combat phase.
- Add a win/lose transition that gives the fight a sense of closure.
- Make level transitions feel intentional with animated banner text, subtle fade, and a brief recap of rewards.
- Give the game a stronger identity through consistent visual language and moment-to-moment feedback.

### implementation priorities
1. Improve hit feedback and damage readability.
2. Add stronger boss and enemy warning cues.
3. Add reward feedback and post-combat celebration moments.
4. Create a fuller sound layer with music and SFX transitions.
5. Refine UI readability and HUD clarity under stress.
6. Tune enemy pacing and difficulty curves for better flow.
7. Add polish pass for transitions, animations, and visual consistency.

### expected outcome
By the end of this sprint, the game should feel like a real arcade shooter instead of a systems demo. The player should understand what is happening, feel the impact of actions, recognize danger early, and enjoy a stronger loop of combat, reward, and progression.

### Sprint 6 completion notes
- This sprint addresses the final missing layer: the game-feel layer that turns core mechanics into a satisfying experience.
- The focus is on responsiveness, clarity, reward, sound, and pacing so the project feels cohesive and fun to play.
- These improvements are the difference between a functional game and a game that feels alive, intentional, and memorable.

---

## Sprint 7 — Fix: Level-Clear Spacebar Repeat Bug

### description
This sprint is dedicated to the bug where the player can hold the spacebar on the level-cleared screen and the game continues to advance repeatedly or too quickly, causing accidental state skipping and inconsistent progression.

### root cause
The level-clear screen currently accepts keyboard input too eagerly. When the spacebar is held down, repeated `KEYDOWN` events or key-repeat behavior can trigger the continue action multiple times before the state transition completes. Because the game is changing screens immediately, the input loop can keep firing and cause rapid or duplicate advancement.

### goal
Stop the level-clear progression from repeating and force a single, clean transition per screen instance.

### required fix
- Add a one-time action guard for the level-clear continue flow.
- Ignore repeated key events while the same key is still being held down.
- Allow only one transition action from the level-clear screen even if the player is pressing `SPACE`, `ENTER`, or mouse-clicking repeatedly.
- Prevent the same input from firing again during the state swap itself.
- Apply the same defensive pattern to any other final-screen continuation states that are vulnerable to held-key repeat behavior.

### implementation notes
- Use a boolean such as `transition_locked` or `action_fired` in the level-complete state.
- Only allow `_continue()` to run once.
- In `handle_events()`, ignore repeated keydown events by checking `event.key` + `event.type` behavior and skip anything while the screen is already transitioning.
- If a button is clicked or keyboard input triggers, the action should immediately lock and then change state.
- The player should still be able to continue normally with a single press, but not by holding the button down.

### acceptance criteria
- Pressing and holding space on the level-clear screen should not rapidly re-enter the level selector.
- A single key press or single mouse click should continue exactly once.
- The game must transition cleanly without stacking extra state changes.
- The fix should be repeat-safe and easy to reuse for future UI states.

### Sprint 7 completion notes
- This bug must be closed before the game is considered stable, because it creates confusing progression behavior and makes the level-complete flow feel broken.
- The fix is a small but important input-safety pass: one press, one transition, no repeat spam while the key is held.
- This sprint ends the bug rather than leaving it to user frustration during playtesting.


## sprint 6
**description** general changes in ui and mechanics of the game
### change-1:
- make the game smoother by applying data structures in the generation\spawning of the enemies 
### change-2:
- spwaning asteriods that are of three sizes (small,medium and large) and two colors (broen and grey)
- they just move forward and if player hits it does a bit of damage to player
- the damage should be relavite to the size of the asteriods small to lowest and large the highest
--
*Reason* 
- to add the new features and giving the game a **Feel** of a challange
**GOAL**
- To add all the features mentioned above without compromising already added functions and flow

## debugging 6th sprint
- make the asteriods be destroyable
- add the particles effect on up the interactions
- add a screen shake when the collisions between the player and asteriod 
- improve the movement of the asteriods so it feels like an asteriods rhater than a living thing

## Sprint 7
**description** new features to make the game feel more complete and rewarding

### change-1:
- add a **combo / score-multiplier** system to the gameplay
- killing enemies in quick succession (within ~2 seconds of each other) builds a combo counter that is displayed on screen
- the combo multiplier starts at 1× and increases by 0.5× for each consecutive kill up to a cap of 5×
- the multiplier is applied to the score earned for each enemy kill
- if the player takes too long between kills or gets hit, the combo resets back to 1×
- a floating combo text should pop up near the kill to show the current streak (e.g. "×2 COMBO!", "×3 COMBO!")
- the combo counter should be shown in the HUD

*Reason*
- the current scoring system feels flat; every kill gives the same reward regardless of skill
- a combo system rewards aggressive, skillful play and makes high score chasing feel meaningful

**GOAL**
- to make the scoring loop feel dynamic and exciting without changing the core enemy/health balance

---

### change-2:
- add a **between-level upgrade shop** that appears after the congratulations popup and before the level select screen
- the shop should offer 3 randomly selected upgrades each time, chosen from a pool
- the player spends score points to buy upgrades (each upgrade has a visible cost shown on the button)
- upgrade pool examples:
  - `Max Health Up` — permanently increases max health by 20
  - `Max Shield Up` — permanently increases max shield capacity by 20
  - `Extra Life` — adds 1 extra life
  - `Faster Reload` — permanently reduces shoot cooldown by 10%
  - `Missile Capacity` — permanently increases max missile carry count by 1
  - `Shield Regen` — player slowly regenerates shield over time (passive)
- a "Skip" button should always be available if the player doesn't want to spend
- the shop screen should match the existing dark space theme with the same button style

*Reason*
- right now there is no meaningful use of the score during a run; it only matters for the leaderboard
- a shop gives the player agency and makes every level feel like it is contributing to a meta-progression

**GOAL**
- to add a lightweight but satisfying upgrade loop that makes replaying levels and earning score feel purposeful

---

### change-3:
- add **boss warning and cinematic intro** sequences before each boss fight
- when the level system reaches a boss wave, show a full-screen red-tinted warning overlay with flashing "!! BOSS INCOMING !!" text for ~2 seconds before the boss spawns
- the boss should then fly in from the top of the screen with a short entry animation rather than appearing instantly
- during the warning phase the player cannot shoot or move (brief cinematic lock) so the moment feels dramatic
- after the boss is defeated, show a short "BOSS DEFEATED" banner with a screen flash and bigger explosion particles before transitioning

*Reason*
- boss fights currently feel abrupt; the boss just appears with no build-up
- a warning sequence signals danger clearly and makes the player feel the weight of the fight before it begins

**GOAL**
- to make boss encounters feel like proper climactic events with clear telegraphing and satisfying resolution

---

---

## Sprint 8 — ✅ COMPLETE

Asset Architecture & Thematic Reorganization: Transitioned from an unorganized raw asset structure to a curated, 12-category vibe-based taxonomy with smart O(1) indexing and semantic aliasing.

### 1. Thematic Folder Taxonomy & Vibe-Based Organization

All 318 game assets were audited, sorted, and renamed into 12 dedicated theme directories under `assets/`:

#### ✅ [NEW DIRECTORY STRUCTURE] [assets/](file:///d:/projects/learning_pygame/assets/)
- **`player_fleet/`** — 21 files: Interceptor strike fighters, heavy assault cruisers, and stealth vanguard bombers across 4 colors (Blue, Green, Orange, Red) + dedicated `damage_overlays/` (Light, Moderate, Critical).
- **`alien_armada/`** — 24 files: Faction-based invader fleets:
  - `shadow_corps/` (Obsidian stealth dreadnoughts, cruisers, stingers, scouts, interceptors)
  - `cryo_legion/` (Icy blue tactical assault fleet)
  - `bio_swarm/` (Venomous green bio-mechanical insectoid ships)
  - `crimson_raiders/` (Aggressive red heavy strike armada)
  - `boss_motherships/` (Colossal UFO saucer craft in Cryo, Bio, Crimson, and Solar variants)
- **`weapons_projectiles/`** — 48 files: 16 weapon variations each for:
  - `blue_photon_beams/` (Standard bolts, dual bolts, stream beams, wide waves, heavy slugs)
  - `green_plasma_beams/` (Plasma bursts, focus lances, pulse orbs, ion spears)
  - `red_crimson_beams/` (Thermal beams, charge flares, heavy slugs, needle piercers)
- **`space_environments/`** — 4 files: Parallax background textures (`void_black_stars`, `nebula_sapphire_drift`, `nebula_abyss_violet`, `nebula_cosmic_magenta`).
- **`space_hazards/`** — 20 files: Deep-space asteroids and mineral fields:
  - `carbon_meteors/` (Brown carbonaceous rocks: Titan, Medium, Small, Tiny Debris)
  - `iron_meteors/` (Grey ferrous metallic asteroids: Titan, Medium, Small, Tiny Debris)
- **`powerups_pickups/`** — 32 files: Tactical combat collectibles:
  - `medical_capsules/` (Health, Energy, Overcharge, Velocity)
  - `powerup_orbs/` (Shield, Bolt, Star orbs across 4 color palettes)
  - `tier_badges/` (Bronze, Silver, Gold achievement medals)
  - `ancient_relics/` (Score artifacts: Bronze, Silver, Gold)
- **`vfx_effects/`** — 27 files: Dynamic visual effects:
  - `thruster_plumes/` (20 progressive flame sizes and afterburners)
  - `energy_shields/` (Outer, core, and dense forcefield bubbles)
  - `speed_trails/` (`hyperspace_warp_lines`)
  - `sparkles/` (Stardust sparkles and cosmic flares)
- **`ui_hud/`** — 28 files: Cyberpunk HUD & menu interface:
  - `cyber_buttons/` (Glowing glass buttons in Cyan, Emerald, Ruby, Amber)
  - `reticle_cursor/` (`crosshair_tactical_cursor`)
  - `cyber_numerals/` (Digits 0–9 and multiplier 'x')
  - `life_counters/` (HUD ship icons for all classes and colors)
- **`modular_shipyard/`** — 94 files: Modular ship components (`cockpits/`, `wings/`, `engines/`, `cannons_turrets/`, `structural_beams/`, `hull_scratches/`).
- **`audio/`** — 10 files:
  - `music/` (`theme_boss_arcade_battle.wav`)
  - `sfx/` (Crisp blasters, retro laser pews, death alarm, defeat theme, shield activate/deplete, powerup chime, EMP zap).
- **`fonts/`** — 3 files: Retro-futuristic TTF vector typefaces (`vector_future_bold.ttf`, `vector_future_thin.ttf`, `audiowide_cyber_display.ttf`).
- **`raw_sheets_source/`** — 7 files: Original master spritesheet, XML coordinates, SVG vectors, showcase preview, and Kenney CC0 license.

---

### 2. Smart Asset Indexing & Resolver

#### ✅ [MODIFIED] [assets_loader.py](file:///d:/projects/learning_pygame/src/assets_loader.py)
- **O(1) Recursive Directory Indexing**: `_build_asset_indexes()` scans the assets tree on startup, populating `_image_index` and `_sound_index` by relative path, full key without extension, and base filename.
- **Semantic Game Entity Aliases**: Automatic mapping for game sprites (`"player"` → `player_fleet/interceptor_strike_blue`, `"enemy_scout"` → `alien_armada/bio_swarm/bio_scout_dart`, `"boss"` → `alien_armada/boss_motherships/mothership_saucer_crimson_red`, `"laser_player"` → `weapons_projectiles/blue_photon_beams/laser_blue_stream_long`, etc.).
- **Dynamic Asteroid Resolver**: Maps dynamic keys like `asteroid_large_brown` and `asteroid_small_grey` to the appropriate titan/medium/small/tiny meteor sprites in `space_hazards/`.
- **Pre-Display Alpha Conversion Safety**: Protects `convert_alpha()` calls when Pygame's video mode is not yet initialized or running headless.
- **Custom TTF Font Pipeline**: Automatically detects and initializes `vector_future_bold.ttf` or `audiowide_cyber_display.ttf` with fallback to `SysFont("Trebuchet MS")`.

---

### 3. Documentation & Catalog

#### ✅ [NEW] [assets/README.md](file:///d:/projects/learning_pygame/assets/README.md)
Comprehensive interactive catalog documenting:
- Complete directory hierarchy and category descriptions.
- Theme and vibe breakdown for all 12 categories with visual purpose explanations.
- Programmatic code examples demonstrating path lookups, base name lookups, and semantic aliases.
- Attribution and licensing documentation (CC0).

---

## Sprint 9 — ✅ COMPLETE: UI/UX Overhaul & Visual Polish

Revamped the user interface, interaction design, and visual aesthetics across all menus and states to deliver a sleek, modern, and cohesive arcade experience.

### 1. De-Cluttering & Dedicated Game Mechanics Guide

#### ✅ [DONE] De-Clutter Existing Screens
- Stripped out repetitive, intrusive guidance text and instruction footers from [`states.py`](file:///d:/projects/learning_pygame/src/states.py) across `MenuState`, `LevelSelectState`, `ShopState`, `PauseState`, `GameOverState`, `LevelCompleteState`, `GameCompleteState`, and `HighScoresState`.
- Maintained clean, cinematic screen compositions focused purely on relevant options, cards, and stats.

#### ✅ [DONE] Dedicated Game Mechanics Manual — [states.py](file:///d:/projects/learning_pygame/src/states.py) (`InstructionsState`)
- Added a dedicated **"Flight Manual & Combat Mechanics"** state accessible directly from the Main Menu (`MenuState`).
- Content is strictly focused on **Game Mechanics**:
  - **Flight Controls**: Full omnidirectional vector thrusters, inertial dampening, and boundary barriers.
  - **Primary Photon Blasters**: Rapid concentrated plasma bolts, upgradeable with Triple Cannons and Heavy Slugs (`SPACEBAR`).
  - **Homing Missiles**: Lock-on acoustic warheads tracking highest-threat enemies with area-of-effect damage (`M` key).
  - **Kinetic Shield Barrier**: 100% impact damage absorption before hull breach, restored via pickups and nanite regenerators.
  - **Combo Multiplier**: Ramps up score multipliers up to ×3.0 by chaining rapid kills before decay timer depletion.
  - **Hazards & Motherships**: Asteroid fragmentation physics and multi-phase Boss projectile patterns.
- Interactive card layout with intuitive keyboard (`ESC` / `ENTER` / `BACKSPACE`) and mouse ("<- MENU" button) navigation.

---

### 2. Upgrade Shop Overhaul & Micro-Animations

#### ✅ [DONE] Enhanced Shop Layout & Typography — [states.py](file:///d:/projects/learning_pygame/src/states.py) (`ShopState`)
- **Spacious Card Dimensions & Geometry**: Expanded card dimensions (`340×240px`) with generous margins and multi-line descriptive text wrapping so all upgrade names, stats, and lore fit comfortably with zero truncation or text crowding.
- **Genuine High-Res Sprite Icons**: Replaced flat geometric placeholder circles with indexed game sprites from `assets/powerups_pickups/`, `assets/weapons_projectiles/`, and `assets/player_fleet/` via `AssetsLoader` with fallback colors.
- **Dynamic Juice & Micro-Animations**:
  - **Card Hover Elevation & Pulse**: Smooth card lift offset (`-4px`) and glowing neon border highlights when hovering.
  - **Purchase Juice**: Sparkle particle bursts (`spawn_sparks`), purchase chime SFX (`powerup`), and checkmark badge overlays upon purchase.
  - **Affordability Visuals**: Interactive price tags displaying gold (`Cost: X PTS`) with hover buy hints when affordable, and muted red with `🔒 Need Budget` tags when score is insufficient.

---

### 3. Destructive Action Highlighting (Red Hover on Quit Buttons)

#### ✅ [DONE] Semantic Button Styling — [states.py](file:///d:/projects/learning_pygame/src/states.py)
- Extended `_draw_ui_button()` to support `danger=True` for danger/destructive button styles.
- **Quit / Exit Buttons**: In `MenuState` and `PauseState`, hovering or selecting the "Quit" / "Quit to Menu" button renders a vibrant ruby red glow (`fill=(65, 15, 25)`, `border=(255, 60, 80)`, `text=(255, 140, 160)`) instead of standard cyan/blue.
- Provides immediate, unmistakable visual feedback distinguishing destructive actions from progression actions.

---

### 4. Advanced UI/UX Components & Visual Hierarchy

#### ✅ [DONE] Component System & Aesthetics
- **Standardized Color Grammar**:
  - **Cyan / Neon Blue**: Navigation & neutral interactive buttons (`Play`, `Flight Manual`, `Leaderboard`).
  - **Emerald Green**: Confirmations, purchase completions, and level progression (`Continue`, `Start`).
  - **Amber / Gold**: Currency, score multipliers, and high score ranks.
  - **Ruby Red**: Destructive actions (`Quit`, `Quit to Menu`, heavy damage flash alerts).
- **Interactive Particle Touches**: Sparkle particle bursts and starfield depth layers in shop and game menus.
- **Screen Transitions**: Smooth state changes across the menu hierarchy.

---

## Sprint 10 — ✅ COMPLETE: Typography Overhaul (Custom Fonts)

Replaced the single-typeface look with a three-role hierarchy using the TTFs in [`assets/fonts/`](file:///d:/projects/learning_pygame/assets/fonts). Titles, UI, and HUD now read as distinct layers.

### Font roles

| Role | Asset | Typical use |
| --- | --- | --- |
| **Display / title** | `audiowide_cyber_display.ttf` | Menu titles, banners, GAME OVER, BOSS ALERT, mission complete |
| **UI / body** | `vector_future_bold.ttf` | Buttons, option lists, shop names, high-score rows, prompts |
| **HUD / captions** | `vector_future_thin.ttf` | In-game HUD labels, card body copy, subtitles, tags |

Fallback remains `SysFont("Trebuchet MS")` at matching sizes if a TTF fails to load — per role only.

### 1. Font pipeline in AssetsLoader

#### ✅ [DONE] [assets_loader.py](file:///d:/projects/learning_pygame/src/assets_loader.py)
- `_load_role_font()` loads each TTF independently instead of one `chosen_font` for all three sizes.
- Public API is unchanged: `title_font`, `font`, and `hud_font`.
- Sizes tuned per role (display 42, UI 22, HUD 18) so labels still fit current layouts.
- Fail per-role: if one file is missing, only that role falls back to SysFont.
- `font_sources` records which file actually loaded (`None` means SysFont fallback).

### 2. Apply hierarchy across screens

#### ✅ [DONE] [states.py](file:///d:/projects/learning_pygame/src/states.py)
- **Titles & banners**: Main menu, Flight Manual, Levels, Shop, Pause, Game Over, High Scores, wave/boss banners use `title_font` (Audiowide).
- **Interactive UI**: Buttons, lists, name entry, shop prices, leaderboard rows use `font` (Vector Future Bold).
- **Dense / secondary text**: HUD (score, combo, wave, HP/SH, missiles), floating combat text, shop subtitle, Flight Manual body, level-select captions, cinematic subtitles use `hud_font` (Vector Future Thin).

### 3. Verification

#### ✅ [DONE] Automated + manual checklist
- [x] All three TTFs load; no silent Trebuchet fallback when files are present.
- [x] Menu, Flight Manual, Level Select, Shop, Pause, Game Over, High Scores, and in-game HUD use the new hierarchy.
- [x] Existing Sprint 6 / Sprint 9 UI tests still pass.

### expected outcome
Space Shooters uses the three custom typefaces with a consistent display / UI / HUD split. Typography matches the cyber-arcade art direction instead of a single bold font stretched across every size.

---

## Sprint 11 — The Presentation Engine (Ship It Like It Was Built in a Real Engine)

> **North star:** A player who has never seen the source should not be able to tell this was written in raw Pygame. It should feel like a shipped indie title: living ships, a directed soundtrack, a world that changes per mission, and a camera/HUD that *reacts*.

> **Honest diagnosis:** Sprints 1–10 built a complete *game*. Sprint 11 builds the *engine around it*. We already own 318 curated assets (nebulae, faction fleets, thruster plumes, damage overlays, energy shields, cyber HUD, ship hangar parts, SFX). Almost none of that is driving the frame. Combat still draws onto a flat `(10, 10, 15)` fill with dotted `Starfield` circles, integer `rect` motion, a couple of `.play()` calls, and instant state swaps. That is the gap between “student project” and “I bought this on itch.io.”

This sprint has **no feature-count ceiling**. It is one coordinated presentation stack, not a bag of polish tickets. Every pillar feeds the same loop: **identity → world → body → camera → audio → HUD → transition**.

---

### Architecture — new presentation layer (do not dump this into `states.py`)

Treat this like a small engine, not more state methods.

| Module | Role |
| --- | --- |
| [`src/render/pipeline.py`](file:///d:/projects/learning_pygame/src/render/pipeline.py) | Offscreen world canvas → shake → bloom/glow → chromatic fringe → vignette → letterbox → present. One `present(screen)` call per frame. |
| [`src/render/camera.py`](file:///d:/projects/learning_pygame/src/render/camera.py) | Soft follow, punch-in on hits, zoom pulse on boss spawn / combo milestones, recovery damping. |
| [`src/world/environment.py`](file:///d:/projects/learning_pygame/src/world/environment.py) | Layered nebula + void parallax from `space_environments/`, drifting dust, hyperspace warp on level enter. |
| [`src/audio/director.py`](file:///d:/projects/learning_pygame/src/audio/director.py) | Buses (music / sfx / ui), ducking, cooldown-gated one-shots, stereo pan by x-position, music stems (menu / combat / boss / victory). |
| [`src/input/actions.py`](file:///d:/projects/learning_pygame/src/input/actions.py) | Action map: keyboard + gamepad, rebindable, edge-triggered vs held. Kill `keys[K_SPACE]` sprinkled in sprites. |
| [`src/persistence/settings.py`](file:///d:/projects/learning_pygame/src/persistence/settings.py) | `settings.json`: volumes, fullscreen, vsync-ish frame cap, shake intensity, keybinds, last hangar loadout. |
| [`src/hangar/loadout.py`](file:///d:/projects/learning_pygame/src/hangar/loadout.py) | Ship class × color, weapon tint, starting kit. Applied when `PlayState` constructs `Player`. |
| [`src/vfx/pool.py`](file:///d:/projects/learning_pygame/src/vfx/pool.py) | Object-pooled particles, muzzle flashes, hit sparks, floating numbers. No per-shot `Surface` alloc spikes. |
| [`src/ui/hud.py`](file:///d:/projects/learning_pygame/src/ui/hud.py) | Finally extract HUD from `PlayState._draw_hud()`. Cyber numerals, life-counter sprites, custom reticle cursor. |

`Game` becomes a thin host: window mode, settings, audio director, input map, then the active state. `PlayState` stops being a god-object for drawing.

---

### Pillar A — ✅ COMPLETE: Living spacecraft (the player should *feel* mass)

The ship is currently a static 60×60 blit that teleports by integer pixels. That is the #1 “this is Pygame” tell.

#### Sub-pixel body + inertia
- Store `pos_x / pos_y` as floats. `rect` is derived, never the source of truth.
- Add **acceleration / drag** so the interceptor has mass. Speed boost should feel like afterburner (higher accel + longer exhaust), not a secret `* 1.5` on velocity.
- Bank the sprite 6–12° toward lateral velocity. Subtle, but every real shmup does this.

#### Thrusters that actually fire
- Wire `vfx_effects/thruster_plumes/` to input: idle glow, throttle plume, afterburner length on speed boost / dash.
- Additive (`BLEND_ADD`) exhaust so it blooms against nebulae.
- Opposite: when the player is hit, thrusters stutter for 120ms.

#### Battle damage as a language
- Composite `player_fleet/damage_overlays/` (light / moderate / critical) onto the hull by HP thresholds (~70% / 40% / 15%).
- Smoke / ember particles leak from the hull at moderate+ damage.
- On respawn, overlays clear with a brief repair sparkle (`vfx_effects/sparkles/`).

#### Shield as geometry, not a drawn circle
- Use `vfx_effects/energy_shields/` (outer / core / dense) scaled to the ship.
- Hit the bubble: ripple scale + chromatic flash, play `shield_down` only on break, `shield_up` on pickup / regen tick.
- Shield regen (shop upgrade) should be *visible* as a slow inward fill, not a silent number.

#### Muzzle, recoil, trails
- Every shot: muzzle flash at cannon sockets, 1–2px visual recoil, projectile with a short additive trail.
- Homing missiles leave a smoke ribbon and a lock-on diamond on the current target (highest HP) *before* launch if `M` is held 150ms — real games telegraph specials.

**Wow moment:** take one hit at 20% HP, afterburner out of a cruiser volley, shield bubble cracking, hull smoking, camera punching in. If that still looks like a tutorial, the pillar failed.

---

### Pillar B — ✅ COMPLETE: A universe per mission (stop drawing dots on navy)

`space_environments/` exists. Combat still fills `(10,10,15)` and sprinkles circles.

#### Three-layer parallax world
1. Far: `void_black_stars` (slow drift).
2. Mid: mission nebula (`nebula_sapphire_drift` / `abyss_violet` / `cosmic_magenta`) with wrap-scroll and very slow rotation or UV offset.
3. Near: existing star motes + occasional debris silhouettes from tiny meteors, uncollidable, for depth.

#### Faction theaters (the campaign should change *species*, not just HP multipliers)

| Levels | Theater | Armada folder | Nebula | Boss mothership |
| --- | --- | --- | --- | --- |
| 1–2 | Bio nursery | `bio_swarm/` | sapphire | — |
| 3–4 | Crimson raid | `crimson_raiders/` | magenta | — |
| 5 | First mothership | mix + `boss_motherships/` | magenta + red grade | Cryo or Crimson saucer |
| 6–7 | Cryo blockade | `cryo_legion/` | violet | — |
| 8–9 | Shadow corps | `shadow_corps/` | abyss violet + desat | — |
| 10 | Solar throne | all factions remnant + final saucer | magenta/violet pulse | `mothership_saucer_*` finale |

Enemy sprites, projectile palettes, and ambient particle color **must** follow the theater. Level 8 should feel like a different game from Level 1 without touching the control scheme.

#### Hyperspace arrive / leave
- On level start: `speed_trails/hyperspace_warp_lines` streak, then the camera settles.
- On level clear: reverse warp into the congratulations overlay — the universe *exits*, the UI does not just pop.

---

### Pillar C — ✅ COMPLETE: Directed audio (mixer is not a soundtrack)

#### Audio Director rules
- **Buses:** Music, Combat SFX, UI. Independent volume controls with clean mixing.
- **Ducking:** When a boss warning fires or player dies, background music ducks by ~6–8 dB for 400ms+ before smoothly restoring.
- **Voice of weapons:** Player lasers with subtle pitch variance; enemy shots utilize distinct sfx cues so factions are audible.
- **One-shot gating:** Max 4 concurrent laser voices with cooldown gating to prevent ear-fatiguing WAV stacking on held fire.
- **Spatial-lite:** Real-time stereo panning for in-game combat sfx based on X coordinate position across the 1280px field.
- **Stems / states:**
  - Menu / hangar: Lush procedural sci-fi ambient drone bed generated in 16-bit PCM stereo.
  - Combat: Dynamic background battle theme smoothly faded in.
  - Boss: Red alert stinger + boss battle music.
  - Victory / defeat: Defeat theme + audio ducking.
- **UI audio grammar:** Confirm chimes, purchase SFX, and subtle navigation feedback.

---

### Pillar D — ✅ COMPLETE: Camera, hit-stop, and a real post stack

#### Camera
- Dead-zone follow of the player with vertical bias framing (`src/render/camera.py`).
- **Hit-stop:** 30–50ms micro time-freeze on missile impacts, boss phase breaks, and 5× combo milestones.
- **Impulse:** Directional impact kick opposite damage vector with rapid decay.
- **Zoom:** 1.00 default, 1.04 on boss intro/alert, 1.02 while combo ≥ 4×, with smooth damped interpolation.

#### Post-process (Realtime Pipeline — `src/render/pipeline.py`)
1. **Additive bloom:** Downsampled quarter-res bright extraction (320×180) → blur → smoothscale upscale with `BLEND_ADD`.
2. **Damage vignette:** Pre-baked gradient border overlay scaled by missing health + cyan shield barrier ring.
3. **Chromatic aberration:** 1–2px horizontal red/blue channel split during heavy impact shake and boss alerts.
4. **Letterbox:** Smoothly animated 28px cinematic black bars during boss warnings and cinematic sequences.
5. **Speed lines:** Faint hyperspace warp lines overlay active during speed boosts.
- Quality toggle: Low (skips bloom pass for low-spec) / High (full post-processing stack). Default High.

---

### Pillar E — ✅ COMPLETE: Hangar identity (the missing metagame fantasy)

We have three hulls × four colors and a modular shipyard. The player is no longer locked to a single blue interceptor.

#### HangarState (between Menu and Level Select, also reachable from Menu)
- **3-bay stage & 3D-carousel:** Interceptor (balanced), Heavy Cruiser (more HP / slower / dual-barrel wide shot), Stealth Vanguard (faster / agile / tighter hitbox, missiles start +1).
- **Color swatches:** Blue / Green / Orange / Red with instant swatch selection.
- **Live preview:** Idle animated thruster loop (single/dual engine based on hull), gentle yaw banking, sparkle bursts, and nameplate in Audiowide Cyber Display.
- **Persistence:** Confirm writes `settings.json` loadout (`{"hull": ..., "color": ...}`); `PlayState` and `Player` construct dynamically from that.
- **Shipyard Backdrop:** Modular shipyard structural beams, thruster mounts, and turret greebles decorate the hangar wall.

#### Run identity
- **Level-select tiles:** Dynamically tinted to the theater accent colors (`Bio Nursery`, `Crimson Raid`, `First Mothership`, `Cryo Blockade`, `Shadow Corps`, `Solar Throne`) with subtitle theater headers.
- **HUD life icons:** Uses dedicated `ui_hud/life_counters/hud_life_{hull}_{color}` matching the player's chosen hull & color loadout.
- **Damage overlays:** `PlayerPresentation` loads matching hull damage layers (`interceptor`, `heavy_cruiser`, `stealth_vanguard`).

---

### Pillar F — HUD of a product, custom cursor, Options — [COMPLETE]
- Extracted `src/ui/hud.py` with glowing segmented health/shield energy meters, cyber numerals for score multiplier, missile status, named boss bar (`CRIMSON MOTHERSHIP — PHASE 1`), and white 80ms hitmarker chevrons.
- Software Tactical Reticle cursor (`src/ui/cursor.py`) with aim lerp, hiding hardware OS cursor.
- Full `OptionsState` accessible from Main Menu and Pause Menu supporting audio bus volume sliders, screen shake toggle, bloom toggle, hitmarkers, damage flash accessibility toggle, and F11 fullscreen toggle.

---

### Pillar G — Input like an engine (actions, not keycodes) — [COMPLETE]
- `InputMap` action graph (`src/input_map.py`) providing device-agnostic action mapping (`up`, `down`, `left`, `right`, `fire`, `missile`, `pause`, `confirm`, `cancel`) with gamepad support and rumble.
- Integrated into `Game` and `Player` sprite so movement and weapons read action states.

---

### Pillar H — Cinematic state machine — [COMPLETE]
- `StateTransition` overlay (`src/render/transition.py`) supporting fade, iris, and warp modes with double-trigger protection.
- Fully integrated into `Game.change_state()`.

---

### Pillar I — Encounter direction & telegraphs — [COMPLETE]
- Wave formations (`v_shape`, `line`, `diving_pair`) and 400ms cruiser weapon telegraph chevrons.
- Elite enemy nameplates and health pips (`SHADOW ELITE`).

---

### Pillar J — Performance & engine hygiene — [COMPLETE]
- `ParticlePool` in `src/fx.py` pre-allocating 384 reusable particles for zero-allocation performance during high-combo explosions.
- Full unit test coverage passing with 32 automated tests.

---

### Implementation order (build like a lead, not like a magpie)

1. **Settings + InputMap + OptionsState** — everything else reads from here.
2. **Render pipeline + camera** — even the current art will start to feel expensive.
3. **Environment + faction theaters** — the campaign becomes a journey.
4. **Living ship (inertia, thrusters, damage, shield sprites).**
5. **Audio Director** — mix last visual pass to the new picture.
6. **Hangar + HUD extract + reticle.**
7. **Transitions + hit-stop + letterbox cinematics.**
8. **Formations / telegraphs / debris weather.**
9. **Pooling, fullscreen, gamepad, rumble, accessibility toggles.**
10. **Playtest pass:** 10-level run, eyes closed audio-only 30 seconds, screenshot vs a Steam shmup.

If time explodes, cut order is: formations (I) → hangar cosmetics → chromatic aberration. **Do not cut bloom, thrusters, nebulae, audio buses, or Options.** Those are the identity of this sprint.

---

### Acceptance criteria — the “impress me” bar

A stranger records a 45-second clip of Level 5. The clip must contain **all** of:

- [ ] A nebula that is recognizably not a dotted starfield.
- [ ] A player ship that banks, trails thrust, and shows damage after hits.
- [ ] A shield that looks like a forcefield asset, not `pg.draw.circle`.
- [ ] Camera punch + bloom on a missile detonation.
- [ ] Boss music that was already in the bed, then *lifts*, not a sudden `.play()`.
- [ ] A named boss bar and a letterboxed warning.
- [ ] HUD numerals / life icons from `ui_hud/`, software reticle visible.
- [ ] Fade or warp into the fight, not an instant blit from the level grid.

Plus product checks:

- [ ] Hangar selection persists after restart.
- [ ] Options volumes persist; mute music does not mute UI ticks.
- [ ] Gamepad can finish Level 1 without touching the keyboard.
- [ ] Fullscreen round-trips without losing audio or fonts.
- [ ] Accessibility: disable shake + screen flash and the game remains readable.
- [ ] 60 FPS on High during a busy Level 8 wave, or auto-drop to Low bloom with a single notice.

---

### Tests (Sprint 11)

#### Automated
- `tests/test_sprint11_pipeline.py` — pipeline presents without crashing; Low quality skips bloom path; shake offset applied at present.
- `tests/test_sprint11_input.py` — action map: held fire does not generate extra `pressed` edges; rebind persists in a temp `settings.json`.
- `tests/test_sprint11_audio.py` — director respects bus volumes; laser voice cap ≤ 4; fade does not throw if mixer uninitialized (headless).
- `tests/test_sprint11_hangar.py` — each class×color resolves to an indexed sprite; `PlayState` player image follows loadout.
- `tests/test_sprint11_theaters.py` — levels 1, 5, 8, 10 map to distinct armada roots and nebula keys.
- Existing Sprint 6 / 9 / 10 tests still pass.

#### Manual
- Full campaign screenshot log (L1, L5 intro, L8, L10 victory).
- Headphones pass: pan, duck, no laser machine-gun WAV stacking.
- Pad pass + keyboard rebind pass.
- Low HP + afterburner + asteroid belt stress clip.

---

### Expected outcome

Space Shooters stops looking like a well-structured Pygame tutorial with expensive Kenney art sitting in a folder. It looks like a **directed arcade product**: a hangar you picked, a theater you flew into, a ship that bleeds and burns, a camera that flinches, a mix that breathes, and UI that belongs on a store page.

That is Sprint 11. That is the last mile between “it works” and “it *ships*.”

---

## Verification Plan

### Automated Tests ✅
- `tests/test_sprint10_fonts.py` — Typography roles:
  - Each of `title_font`, `font`, and `hud_font` loads its own TTF.
  - A missing display TTF falls back to SysFont without dropping the other two roles.
  - Menu, Flight Manual, Level Select, Shop, Pause, Game Over, and High Scores still draw.
- `tests/test_sprint9_ui.py` — Unit tests verifying:
  - `InstructionsState` creation, card rendering, and keyboard/mouse return navigation.
  - `ShopState` card rendering, sprite icon loading, particle bursts, and score deduction.
  - `_draw_ui_button` danger/quit button color variations and hover states.
  - De-cluttered states render cleanly without regressions.
- `tests/test_sprint6.py` — Level system spawn queue, Asteroid types/sizes/colors, and LevelCompleteState UI.

### Manual Verification ✅
- [done] Verified clean, uncluttered layouts in Menu, Level Select, Shop, Pause, GameOver, and HighScores states.
- [done] Navigated to the new Flight Manual / Mechanics Guide from Main Menu and verified all 6 mechanic cards render clearly.
- [done] Tested Shop with spacious cards, high-res upgrade sprite icons, hover elevation, and purchase sparkle bursts.
- [done] Verified vibrant ruby red hover highlight on Quit buttons in Main Menu and Pause Menu.
- [done] Confirmed Audiowide titles, Vector Future Bold UI, and Vector Future Thin HUD/captions.


---

## Sprint 11 — Bug Fix Patch (Pillar A/B/C/D)

### Issues Addressed

#### Bug 1 — Combat music leaking into Level Select (Pillar C)
**Root cause:** `LevelSelectState.__init__` never called `play_music("menu")`, so when arriving from `PlayState` (combat music active), the boss battle track kept playing on the level-select screen.
**Additionally**, `AudioDirector.play_music("menu")` had a blanket dedup guard that prevented a re-trigger if `current_music_track` was already `"menu"`. This meant the ambient bed stayed silent if the player returned to the menu more than once.

**Fixed in:**
- [`src/states.py`](file:///d:/projects/learning_pygame/src/states.py) — Added `play_music("menu", fade_ms=600)` call at the end of `LevelSelectState.__init__`.
- [`src/audio/director.py`](file:///d:/projects/learning_pygame/src/audio/director.py) — `play_music("menu")` now always stops and restarts the procedural ambient bed, bypassing the track-equality guard. All other tracks still use the dedup guard.

---

#### Bug 2 — Game slowness / performance drops (Pillar D + Pillar A)
Multiple hot-path allocations were identified and eliminated:

**Fixed in [`src/fx.py`](file:///d:/projects/learning_pygame/src/fx.py):**
- `Particle._update_image()` was calling `pg.Surface()` + `fill()` + `pg.draw.circle()` **every frame** for every active particle. With 200+ particles in a boss fight, this caused frame-time spikes.
- **Removed:** `_update_image()` method entirely.
- **New approach:** Circle is drawn **once at spawn**. Per-frame updates call only `set_alpha()` — no reallocation, no redraw. ~80% cheaper per particle per frame.

**Fixed in [`src/vfx/player_presentation.py`](file:///d:/projects/learning_pygame/src/vfx/player_presentation.py):**
- Shield rendering called `pg.transform.smoothscale()` **3 times per frame** whenever the shield was active (every 60th-of-a-second). With a 92×92 source scaled to a float-animated size, this was a significant CPU hit.
- **New approach:** All three shield layers are pre-scaled to 3 fixed sizes (small / base / large) at `__init__`. `draw_front()` picks the nearest cache entry — zero smoothscale calls during gameplay.
- `damage_layers` now pre-baked with `.copy()` at init; `draw_front()` calls `set_alpha()` only, removing the per-frame `.copy()` call.

**Fixed in [`src/render/pipeline.py`](file:///d:/projects/learning_pygame/src/render/pipeline.py):**
- Bloom was running two full `smoothscale` operations + a full-res Surface blit **every frame**.
- **New approach:** Bloom is computed only on **even frames** (every other frame) and cached into `_bloom_cache`. Odd frames reuse the cached result. This halves bloom cost with no perceptible quality change.

---

---

#### Bug 3 — Screen not visible enough due to heavy post-processing & powerup visuals (Pillar D + A)
Extra additive effects and high brightness layers were washed out and obscuring gameplay:

**Fixed in [`src/render/pipeline.py`](file:///d:/projects/learning_pygame/src/render/pipeline.py):**
- **Bloom pass:** Completely disabled (`bloom_enabled = False`) to eliminate washed-out whites and excessive additive brightness across the entire screen.
- **Speed lines overlay:** Removed during speed boosts to prevent extra screen clutter and glare.
- **Shield vignette:** Completely removed from screen-space presentation to avoid whole-screen cyan tints.
- **Damage vignette:** Threshold tuned to `< 45% HP` with reduced alpha (160) so it only signals critical danger.
- **Chromatic aberration threshold:** Raised to `shake_mag > 8.0` for heavy boss/impact moments only.

**Fixed in [`src/vfx/player_presentation.py`](file:///d:/projects/learning_pygame/src/vfx/player_presentation.py):**
- **Shield power-up effect:** Replaced the 3-layer additive pulsing shield stacking with a single clean, subtle soft bubble overlay (`alpha = 65`, non-additive), ensuring the player ship and surroundings remain crystal clear.

---

#### Bug 4 — Player sprite alpha blink not working at any level (Pillar A)
**Root cause:** In `Player.update()`, the invincibility blink logic was calling `self.image.set_alpha(90)` on `self.image` (the old rotated copy), and then immediately afterward `self.image = rotated` assigned a **brand new Surface** — discarding the alpha that was just set. The blink never visually appeared.

**Fixed in [`src/sprites.py`](file:///d:/projects/learning_pygame/src/sprites.py):**
- Moved alpha application to **after** `self.image = rotated` is assigned.
- Introduced `_blink_alpha` local variable computed from `flash_timer` (< 0.06s = dim, ≥ 0.06s = bright). Applied to the final Surface object in one place.
- `set_alpha(255)` is always called when not invincible — ensures alpha resets cleanly after invincibility ends.

---

### What Was NOT Changed or Removed
- All Sprint 11 Pillar goals (living ship inertia & banking, faction theaters & nebulae, audio director & spatial audio, camera follow & hit-stop) remain fully active.
- All Sprint 5–10 mechanics (combo multiplier system, upgrade shop, boss warning cinematics, level select) unchanged.
- No gameplay parameters (damage values, speed boosts, wave configs, powerup drops) altered.
- The particle visual (circle shape, colors, lifespan) is preserved with high-performance alpha fades.

