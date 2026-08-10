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


---

## Verification Plan

### Automated Tests ✅
- `level_system.py` — advance through all 10 levels, verify `"complete"` signal and boss wave detection.
- `sprites.py` — import check, `PowerUp.BASE_TYPES`, `PowerUp.EXTRA_TYPES`, `Missile.DAMAGE` constants.
- `states.py` — `PlayState` instantiation and `update(dt)` with headless display.
- All 7 source files — AST syntax parse with zero errors.

### Manual Verification (To Do)
- [done] Playtest Level 1–2: scouts and stingers spawn correctly.
- [done] Playtest Level 3+: cruisers appear, new powerups drop.
- [done] Verify health boost pickup doesn't exceed 100 HP.
- [done] Verify power laser fires red and deals 2× damage.
- [done] Verify missile homes on highest-HP enemy and explodes on hit.
- [done] Verify boss appears at Level 5 and Level 10 with correct HP scaling.
- [done] Verify `GameCompleteState` displays after Level 10 boss defeat.
- [done] Verify triple-shot timer shows 12s bar (not 8s).
- [done] Verify speed boost timer shows 12s bar (not 8s).
