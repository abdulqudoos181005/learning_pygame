# Space Shooters Game - Development Plan

This plan details the design, architecture, and step-by-step roadmap to build a fully polished, production-ready, and shippable **Space Shooters** game using Pygame.

---

## User Review Required

> [!IMPORTANT]
> **Resolution & Aspect Ratio**: We propose a default virtual resolution of **1280x720 (16:9 HD)**, which is standard for modern desktop indie games. Let us know if you prefer a different resolution or want full-screen toggle support.
>
> **Asset Style**: A shippable game requires clean assets. We can generate placeholder or custom art/sprites if needed, or we can use stylized procedural shapes/vector graphics to keep the game code self-contained and modern.

---

## Open Questions

> [!IMPORTANT]
> 1. **Control Scheme**: Should the player move with standard WASD/Arrow keys and fire with the `Spacebar`, or would you like to support mouse steering/aiming as well?
> 2. **Game Loop Style**: Do you want an endless shooter with increasing difficulty (waves) and high scores, or a level-based shooter with a distinct ending and a final Boss?
> 3. **Assets**: Do you have custom graphics/audio files you want to use, or should we write code that works with procedurally generated textures and royalty-free sounds?

---

## Proposed Changes

We will build the game modularly inside the [src](file:///d:/projects/learning_pygame/src) directory.

### 1. Game Architecture & Manager
A state-machine pattern to handle screen transitions (Main Menu, Gameplay, Pause, Game Over, Leaderboard).

#### [NEW] [game.py](file:///d:/projects/learning_pygame/src/game.py)
The central manager class containing the game loop, state controller, event dispatcher, and common services (asset loading, audio manager).

#### [NEW] [states.py](file:///d:/projects/learning_pygame/src/states.py)
Definitions of all game states: `MenuState`, `PlayState`, `PauseState`, `GameOverState`, `HighScoresState`.

---

### 2. Entities & Physics
Using Pygame's Sprite groups for collisions, updating, and drawing.

#### [NEW] [sprites.py](file:///d:/projects/learning_pygame/src/sprites.py)
- `Player`: Player ship with health, lives, weapon state, and engine trail.
- `Laser`: Projectiles fired by Player/Enemies with direction and speed.
- `Enemy`: Standard enemy class with subclass variants:
  - `Scout`: Fast, low health.
  - `Stinger`: Fires targeted lasers.
  - `Cruiser`: High health, slow.
  - `Boss`: Multiple phases, health bar, special attack patterns.
- `PowerUp`: Drops (Shield, Triple Shot, Speed Boost) that spawn from destroyed enemies.

---

### 3. FX & UI Systems
Visual polish and HUD.

#### [NEW] [fx.py](file:///d:/projects/learning_pygame/src/fx.py)
- Particle effects for engine thrusters, laser impacts, and explosions.
- Screen shake helper for heavy damage/explosions.
- Scrolling parallax starfield background.

#### [NEW] [ui.py](file:///d:/projects/learning_pygame/src/ui.py)
HUD rendering (health bar, lives icon, score, power-up timers) and main menu buttons with hover effects.

---

### 4. Data & Packaging
Persisting scores and bundling.

#### [NEW] [save_system.py](file:///d:/projects/learning_pygame/src/save_system.py)
Handles loading and saving high scores locally using JSON format.

#### [NEW] [assets_loader.py](file:///d:/projects/learning_pygame/src/assets_loader.py)
A centralized loader that automatically falls back to procedural drawing (circles, rectangles, basic shapes) if asset files (PNGs, WAVs) are missing, preventing crashes.

---

## Sprint 1 — Completed ✅

All core files have been created:
- [game.py](file:///d:/projects/learning_pygame/src/game.py) — Game loop & state machine
- [states.py](file:///d:/projects/learning_pygame/src/states.py) — All game states
- [sprites.py](file:///d:/projects/learning_pygame/src/sprites.py) — Player, enemies, lasers, powerups
- [fx.py](file:///d:/projects/learning_pygame/src/fx.py) — Particles, screen shake, starfield
- [save_system.py](file:///d:/projects/learning_pygame/src/save_system.py) — High score persistence
- [assets_loader.py](file:///d:/projects/learning_pygame/src/assets_loader.py) — Asset loading with procedural fallback

---

## Sprint 2 — Upcoming

> [!NOTE]
> This section will be filled in as we plan the next phase of development. Possible areas include:
> - Boss battle implementation & phase transitions
> - Audio system integration (sound effects + background music)
> - Full UI polish (animated menus, transitions)
> - Level/wave progression system
> - PyInstaller packaging for Windows distribution

---

## Verification Plan

### Automated Tests
- Scripted tests to verify collision math and screen boundary logic.
- JSON save system unit tests for read/write integrity.

### Manual Verification
- Playtest controls, enemy movement patterns, boss battles, and frame rate stability.
- Verify resolution scaling, screen-shake duration, and audio playback.
- Package using `PyInstaller` and run on Windows.
