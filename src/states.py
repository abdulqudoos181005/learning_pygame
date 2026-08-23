# pyrefly: ignore [missing-import]
import pygame as pg
import random
import math
from sprites import Player, Enemy, Laser, Boss, PowerUp, Missile, Asteroid
from fx import Starfield, spawn_explosion, spawn_sparks
from save_system import SaveSystem
from level_system import LevelSystem
from world.environment import SpaceEnvironment
from render.camera import Camera
from render.pipeline import RenderPipeline


def _draw_ui_button(screen, rect, label, font, *, hovered=False, pressed=False,
                    fill=(22, 34, 56, 220), border=(90, 120, 150, 255),
                    text_color=(240, 240, 240), pulse=0.0, danger=False):
    """Shared helper for consistent, mouse-friendly arcade buttons.

    All future UI elements can reuse this helper so hover and click feedback
    stays visually uniform without duplicating the button drawing logic.
    Supports danger=True for crimson/ruby red highlight feedback on destructive actions.
    """
    panel = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
    panel.fill((0, 0, 0, 0))

    if danger and (hovered or pressed):
        fill = (65, 15, 25, 240)
        border = (255, 60, 80, 255)
        text_color = (255, 140, 160)
        if pressed:
            fill = (90, 20, 30, 255)
            border = (255, 100, 120, 255)
            text_color = (255, 180, 190)
    elif hovered:
        fill_r, fill_g, fill_b, fill_a = fill
        border_r, border_g, border_b, border_a = border
        fill_r = min(255, fill_r + 22)
        fill_g = min(255, fill_g + 36)
        fill_b = min(255, fill_b + 42)
        border_r = min(255, border_r + 20)
        border_g = min(255, border_g + 40)
        border_b = min(255, border_b + 60)
        fill = (fill_r, fill_g, fill_b, fill_a)
        border = (border_r, border_g, border_b, border_a)
    elif pressed:
        fill_r, fill_g, fill_b, fill_a = fill
        border_r, border_g, border_b, border_a = border
        fill_r = max(0, fill_r - 14)
        fill_g = max(0, fill_g - 12)
        fill_b = max(0, fill_b - 18)
        border_r = min(255, border_r + 24)
        border_g = min(255, border_g + 40)
        border_b = min(255, border_b + 50)
        fill = (fill_r, fill_g, fill_b, fill_a)
        border = (border_r, border_g, border_b, border_a)

    fill_r, fill_g, fill_b, fill_a = fill
    border_r, border_g, border_b, border_a = border
    pulse_alpha = int(fill_a + (24 * math.sin(pulse) if pulse else 0))
    panel.fill((fill_r, fill_g, fill_b, max(0, min(255, pulse_alpha))))
    pg.draw.rect(panel, (border_r, border_g, border_b, border_a), panel.get_rect(), 2, border_radius=10)
    screen.blit(panel, rect)

    label_surf = font.render(label, True, text_color)
    label_rect = label_surf.get_rect(center=rect.center)
    if pressed:
        label_rect.move_ip(1, 2)
    screen.blit(label_surf, label_rect)


class State:
    """
    The abstract base class representing a generic Game State (State Pattern).
    
    All states (MenuState, PlayState, etc.) inherit from this class and
    override its lifecycle methods: handle_events, update, and draw.
    """
    def __init__(self, game):
        # Reference to the main Game class to allow state switching and screen size checks
        self.game = game

    def handle_events(self, events):
        """Processes user input events (keyboard, mouse, window closures)."""
        pass

    def update(self, dt):
        """Executes physics, mechanics, and timer updates for the current frame."""
        pass

    def draw(self, screen):
        """Draws visual assets, sprites, and UI elements to the active display screen."""
        pass


class MenuState(State):
    """
    State representing the Main Menu screen.
    
    Provides option selection (Play, Flight Manual, High Scores, Quit) and animated starfield.
    """
    def __init__(self, game):
        super().__init__(game)
        # Parallax background with 80 stars for the menu
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=80)
        self.anim_timer = 0.0
        self.click_timer = 0.0
        self.click_index = None
        
        # Render the menu title with a nice neon-cyan color
        self.title_text = self.game.assets.title_font.render("SPACE SHOOTERS", True, (0, 255, 200))
        self.title_rect = self.title_text.get_rect(center=(self.game.width // 2, self.game.height // 3.4))
        
        # Available choices and navigation cursor index
        self.options = ["Play Game", "Flight Manual", "High Scores", "Quit"]
        self.selected_index = 0
        self.hovered_index = None
        self.buttons = []
        self._build_buttons()
        
        # Sprint 11: Play menu atmospheric bed through AudioDirector
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_music("menu", fade_ms=500)

    def _build_buttons(self):
        self.buttons = []
        for idx, option in enumerate(self.options):
            rect = pg.Rect(self.game.width // 2 - 170, int(self.game.height * 0.44) + idx * 56, 340, 46)
            self.buttons.append({"label": option, "rect": rect})

    def handle_events(self, events):
        """Navigates options using the keyboard or a mouse click."""
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.hovered_index = None
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        self.hovered_index = idx
                        self.selected_index = idx
                        break
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        self.selected_index = idx
                        self.click_index = idx
                        self.click_timer = 0.12
                        self._select_option(idx)
                        return
            elif event.type == pg.KEYDOWN:
                # W or UP arrow goes up
                if event.key == pg.K_UP or event.key == pg.K_w:
                    self.selected_index = (self.selected_index - 1) % len(self.options)
                    self.hovered_index = None
                # S or DOWN arrow goes down
                elif event.key == pg.K_DOWN or event.key == pg.K_s:
                    self.selected_index = (self.selected_index + 1) % len(self.options)
                    self.hovered_index = None
                # ENTER selects the currently highlighted option
                elif event.key == pg.K_RETURN:
                    self.click_index = self.selected_index
                    self.click_timer = 0.12
                    self._select_option(self.selected_index)

    def _select_option(self, idx=None):
        """Executes the action corresponding to the highlighted option."""
        idx = self.selected_index if idx is None else idx
        if idx == 0:
            # Transition to level-selection screen
            self.game.change_state(LevelSelectState(self.game))
        elif idx == 1:
            # Transition to dedicated Flight Manual / Mechanics guide
            self.game.change_state(InstructionsState(self.game))
        elif idx == 2:
            # Transition to high scores leaderboard
            self.game.change_state(HighScoresState(self.game))
        elif idx == 3:
            # Exit game
            self.game.quit()

    def update(self, dt):
        """Scroll the background stars and animate menu hover pulses."""
        self.starfield.update(dt)
        self.anim_timer += dt
        if self.click_timer > 0:
            self.click_timer -= dt
            if self.click_timer <= 0:
                self.click_index = None

    def draw(self, screen):
        # Clear screen with a very deep cosmic blue background
        screen.fill((10, 12, 22))
        
        # Draw background stars first
        self.starfield.draw(screen)
        
        # Draw Title with a offset dark green/teal shadow glow effect
        glow_surf = self.game.assets.title_font.render("SPACE SHOOTERS", True, (0, 100, 80))
        glow_rect = glow_surf.get_rect(center=(self.title_rect.centerx + 2, self.title_rect.centery + 2))
        screen.blit(glow_surf, glow_rect)
        screen.blit(self.title_text, self.title_rect)
        
        # Draw menu options list
        for idx, button in enumerate(self.buttons):
            option = button["label"]
            rect = button["rect"]
            is_sel = (idx == self.selected_index)
            is_hovered = (self.hovered_index == idx)
            is_pressed = (self.click_index == idx and self.click_timer > 0)
            is_danger = (option.lower() == "quit")

            if is_danger and (is_hovered or is_sel):
                fill = (65, 15, 25, 245)
                border = (255, 60, 80, 255)
                color = (255, 140, 160)
            elif is_danger:
                fill = (35, 18, 24, 210)
                border = (140, 60, 70, 255)
                color = (220, 170, 180)
            else:
                color = (0, 255, 255) if is_sel else (190, 220, 240)
                if is_hovered or is_sel:
                    color = (120, 255, 255)

                fill = (22, 34, 56, 220)
                border = (100, 130, 160, 255)
                if is_hovered:
                    fill = (24, 94, 116, 240)
                    border = (0, 255, 255, 255)
                if is_sel:
                    fill = (18, 86, 108, 250)
                    border = (0, 255, 255, 255)
                if is_pressed:
                    fill = (12, 40, 84, 255)
                    border = (180, 255, 255, 255)

            _draw_ui_button(
                screen,
                rect,
                option,
                self.game.assets.font,
                hovered=is_hovered,
                pressed=is_pressed,
                fill=fill,
                border=border,
                text_color=color,
                pulse=self.anim_timer * 8 + idx,
                danger=is_danger,
            )


class InstructionsState(State):
    """
    Sprint 9 — Dedicated Game Mechanics & Flight Manual.
    
    Provides a comprehensive, elegant breakdown of all 6 core combat systems:
    Flight, Weapons, Missiles, Shields, Combo Multiplier, and Space Hazards.
    """
    def __init__(self, game):
        super().__init__(game)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=90)
        self.anim_timer = 0.0
        self.back_rect = pg.Rect(40, 30, 130, 44)
        self.back_hovered = False
        
        self.mechanics = [
            {
                "title": "FLIGHT CONTROLS",
                "tag": "WASD / ARROWS",
                "color": (0, 230, 255),
                "desc": "Full omnidirectional vector thrusters with inertial dampening. Boundary barriers keep your fighter securely within combat theater.",
            },
            {
                "title": "PRIMARY PHOTON BLASTER",
                "tag": "SPACEBAR",
                "color": (100, 180, 255),
                "desc": "Rapid concentrated plasma bolts. Upgradeable with Triple Cannons, Faster Reload modules, and heavy piercing laser slugs.",
            },
            {
                "title": "HOMING MISSILES",
                "tag": "M KEY",
                "color": (255, 130, 40),
                "desc": "Lock-on acoustic warheads that seek out the highest-threat enemy on screen, dealing massive area-of-effect explosive damage.",
            },
            {
                "title": "KINETIC SHIELD BARRIER",
                "tag": "DEFENSE SYSTEM",
                "color": (0, 255, 200),
                "desc": "Absorbs 100% of projectile and collision impacts before hull breach. Restored via blue powerup orbs and persistent shop nanites.",
            },
            {
                "title": "COMBO MULTIPLIER",
                "tag": "SCORE BOOST",
                "color": (255, 220, 50),
                "desc": "Chain rapid enemy takedowns before the decay timer expires to ramp up score multipliers up to x3.0. Taking damage breaks the chain.",
            },
            {
                "title": "HAZARDS & MOTHERSHIPS",
                "tag": "COMBAT THREATS",
                "color": (255, 70, 90),
                "desc": "Asteroids fragment into dangerous shards upon impact. Boss motherships feature multiple phases and high-density projectile patterns.",
            },
        ]
        
        # 2 rows x 3 columns grid with spacious card dimensions
        card_w, card_h = 380, 245
        gap_x, gap_y = 30, 20
        start_x = (self.game.width - (3 * card_w + 2 * gap_x)) // 2
        start_y = 135
        
        self.cards = []
        for i, item in enumerate(self.mechanics):
            row = i // 3
            col = i % 3
            rect = pg.Rect(start_x + col * (card_w + gap_x), start_y + row * (card_h + gap_y), card_w, card_h)
            self.cards.append({"rect": rect, "data": item})

    def handle_events(self, events):
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.back_hovered = self.back_rect.collidepoint(event.pos)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_rect.collidepoint(event.pos):
                    self.game.change_state(MenuState(self.game))
                    return
            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_BACKSPACE):
                    self.game.change_state(MenuState(self.game))
                    return

    def update(self, dt):
        self.starfield.update(dt)
        self.anim_timer += dt

    def draw(self, screen):
        screen.fill((10, 12, 22))
        self.starfield.draw(screen)

        # Header
        title = self.game.assets.title_font.render("FLIGHT MANUAL & MECHANICS", True, (0, 240, 255))
        screen.blit(title, title.get_rect(center=(self.game.width // 2, 50)))

        sub = self.game.assets.hud_font.render("Essential starship flight systems, weapons operation, and tactical survival protocols", True, (160, 190, 220))
        screen.blit(sub, sub.get_rect(center=(self.game.width // 2, 92)))

        # Back button
        _draw_ui_button(
            screen,
            self.back_rect,
            "<- MENU",
            self.game.assets.font,
            hovered=self.back_hovered,
            fill=(25, 36, 54, 220),
            border=(0, 220, 255, 255) if self.back_hovered else (90, 120, 150, 255),
            text_color=(200, 230, 255),
            pulse=self.anim_timer * 8,
        )

        # Draw cards
        for card_item in self.cards:
            rect = card_item["rect"]
            data = card_item["data"]
            theme_color = data["color"]

            card_surf = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
            card_surf.fill((18, 26, 42, 215))
            pg.draw.rect(card_surf, (*theme_color, 180), card_surf.get_rect(), 2, border_radius=12)
            
            # Top accent bar
            pg.draw.rect(card_surf, (*theme_color, 240), pg.Rect(0, 0, rect.width, 4), border_top_left_radius=12, border_top_right_radius=12)
            screen.blit(card_surf, rect)

            # Title
            title_surf = self.game.assets.font.render(data["title"], True, (255, 255, 255))
            screen.blit(title_surf, (rect.x + 16, rect.y + 14))

            # Tag badge
            tag_surf = self.game.assets.hud_font.render(f" {data['tag']} ", True, theme_color)
            tag_rect = tag_surf.get_rect(topleft=(rect.x + 16, rect.y + 46))
            bg_tag = pg.Surface((tag_rect.width + 8, tag_rect.height + 4), pg.SRCALPHA)
            bg_tag.fill((*theme_color, 35))
            pg.draw.rect(bg_tag, (*theme_color, 120), bg_tag.get_rect(), 1, border_radius=4)
            screen.blit(bg_tag, (tag_rect.x - 4, tag_rect.y - 2))
            screen.blit(tag_surf, tag_rect)

            # Divider line
            pg.draw.line(screen, (*theme_color, 70), (rect.x + 16, rect.y + 78), (rect.x + rect.width - 16, rect.y + 78), 1)

            # Multi-line wrapped description
            words = data["desc"].split()
            lines = []
            curr_line = []
            for w in words:
                curr_line.append(w)
                rendered = self.game.assets.hud_font.render(" ".join(curr_line), True, (170, 190, 210))
                if rendered.get_width() > rect.width - 32:
                    curr_line.pop()
                    lines.append(" ".join(curr_line))
                    curr_line = [w]
            if curr_line:
                lines.append(" ".join(curr_line))

            for line_idx, line_str in enumerate(lines):
                line_surf = self.game.assets.hud_font.render(line_str, True, (170, 190, 210))
                screen.blit(line_surf, (rect.x + 16, rect.y + 90 + line_idx * 22))



class LevelSelectState(State):
    """Interactive campaign-level chooser with mouse + keyboard support."""
    def __init__(self, game):
        super().__init__(game)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=100)
        self.save_system = SaveSystem()
        self.progress = self.save_system.load_progress()
        self.hovered_index = None
        self.selected_index = 0
        self.buttons = []
        self.blink_timer = 0.0
        self.back_rect = pg.Rect(40, 40, 100, 48)
        self.back_hovered = False
        self._build_buttons()

        # Bug fix: Switch back to menu ambient bed whenever level select is entered.
        # This covers the case where we arrive from PlayState (combat music still active).
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_music("menu", fade_ms=600)

    def _build_buttons(self):
        self.buttons = []
        highest_unlocked = self.progress.get("highest_unlocked", 1)
        completed_levels = set(self.progress.get("completed_levels", []))

        for level_num in range(1, 11):
            row = (level_num - 1) // 5
            col = (level_num - 1) % 5
            x = 130 + col * 220
            y = 180 + row * 150
            rect = pg.Rect(x, y, 160, 90)
            is_unlocked = level_num <= highest_unlocked
            is_completed = level_num in completed_levels
            self.buttons.append({
                "level": level_num,
                "rect": rect,
                "unlocked": is_unlocked,
                "completed": is_completed,
            })

    def handle_events(self, events):
        for event in events:
            if event.type == pg.MOUSEMOTION:
                mouse_pos = event.pos
                self.back_hovered = self.back_rect.collidepoint(mouse_pos)
                self.hovered_index = None
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(mouse_pos):
                        self.hovered_index = idx
                        self.selected_index = idx
                        break
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if self.back_rect.collidepoint(mouse_pos):
                    self.game.change_state(MenuState(self.game))
                    return
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(mouse_pos):
                        self.selected_index = idx
                        self._launch_level(button["level"])
                        return
            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_BACKSPACE):
                    self.game.change_state(MenuState(self.game))
                elif event.key in (pg.K_UP, pg.K_w):
                    self._move_selection(-5)
                elif event.key in (pg.K_DOWN, pg.K_s):
                    self._move_selection(5)
                elif event.key in (pg.K_LEFT, pg.K_a):
                    self._move_selection(-1)
                elif event.key in (pg.K_RIGHT, pg.K_d):
                    self._move_selection(1)
                elif event.key == pg.K_RETURN:
                    # Keyboard Enter can only launch a level if the mouse is currently hovering a tile.
                    if self.hovered_index is not None:
                        level_num = self.buttons[self.hovered_index]["level"]
                        if self.buttons[self.hovered_index]["unlocked"]:
                            self._launch_level(level_num)

    def _move_selection(self, delta):
        next_idx = self.selected_index + delta
        if 0 <= next_idx < len(self.buttons):
            self.selected_index = next_idx
            self.hovered_index = None

    def _launch_level(self, level_num):
        if level_num <= self.progress.get("highest_unlocked", 1):
            self.game.change_state(PlayState(self.game, selected_level=level_num))

    def update(self, dt):
        self.starfield.update(dt)
        self.blink_timer += dt

    def draw(self, screen):
        screen.fill((8, 10, 24))
        self.starfield.draw(screen)

        title = self.game.assets.title_font.render("LEVELS", True, (0, 240, 255))
        title_rect = title.get_rect(center=(self.game.width // 2, 100))
        screen.blit(title, title_rect)

        # Exit arrow to return to the menu.
        _draw_ui_button(
            screen,
            self.back_rect,
            "← MENU",
            self.game.assets.font,
            hovered=self.back_hovered,
            fill=(30, 40, 58, 190),
            border=(90, 140, 180, 255) if self.back_hovered else (90, 120, 150, 255),
            text_color=(190, 210, 220),
            pulse=self.blink_timer * 8,
        )

        for idx, button in enumerate(self.buttons):
            rect = button["rect"]
            unlocked = button["unlocked"]
            completed = button["completed"]
            hovered = self.hovered_index == idx
            blink = idx == (self.progress.get("highest_unlocked", 1) - 1) and self.blink_timer % 1.0 < 0.5

            fill = (35, 70, 100)
            border = (70, 160, 210)
            if not unlocked:
                fill = (40, 42, 50)
                border = (90, 90, 100)
            elif completed:
                fill = (26, 86, 42)
                border = (80, 255, 140)
            if hovered:
                if unlocked:
                    fill = (20, 110, 130) if not completed else (40, 130, 70)
                    border = (0, 255, 255) if not completed else (180, 255, 180)
                else:
                    fill = (60, 60, 70)
                    border = (140, 140, 160)

            if unlocked and blink:
                fill = (20, 130, 120)
                border = (180, 255, 255)

            panel = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
            panel.fill((0, 0, 0, 0))
            pg.draw.rect(panel, fill, panel.get_rect(), border_radius=10)
            pg.draw.rect(panel, border, panel.get_rect(), 2, border_radius=10)
            screen.blit(panel, rect)

            label = self.game.assets.hud_font.render(f"LEVEL {button['level']}", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=rect.center))

            if completed:
                done_tag = self.game.assets.hud_font.render("CLEARED", True, (200, 255, 210))
                screen.blit(done_tag, done_tag.get_rect(center=(rect.centerx, rect.centery + 28)))
            elif not unlocked:
                lock_tag = self.game.assets.hud_font.render("LOCKED", True, (190, 190, 200))
                screen.blit(lock_tag, lock_tag.get_rect(center=(rect.centerx, rect.centery + 28)))
            else:
                status_tag = self.game.assets.hud_font.render("PLAY", True, (0, 240, 255))
                screen.blit(status_tag, status_tag.get_rect(center=(rect.centerx, rect.centery + 28)))


class PlayState(State):
    """
    The primary gameplay state — Sprint 2 level-system version.
    
    Manages the player, LevelSystem-driven enemy waves, power-ups (including
    new Sprint 2 types), homing missiles, particles, collisions,
    screen shaking, and the heads-up display (HUD).
    """
    def __init__(self, game, selected_level=1):
        super().__init__(game)
        self.selected_level = max(1, min(int(selected_level), 10))
        # Sprint 11: layered per-mission parallax world (far void / mid nebula / near motes+debris)
        # replaces the flat navy fill, and reskins to the level's faction theater.
        self.environment = SpaceEnvironment(self.game.assets, self.game.width, self.game.height, self.selected_level)
        self.environment.start_warp_in()
        self.save_system = SaveSystem()
        self.kills_since_powerup = 0

        # Sprint 7: Combo / score-multiplier system
        self.combo_count      = 0      # consecutive kills within the time window
        self.combo_timer      = 0.0    # seconds remaining before combo resets
        self.combo_multiplier = 1.0    # current score multiplier (1×, 1.5×, 2×, … up to 5×)
        self.COMBO_WINDOW     = 2.0    # seconds between kills to sustain the chain
        self.COMBO_CAP        = 5.0    # maximum multiplier
        self.COMBO_STEP       = 0.5    # multiplier increment per kill
        
        # Sprint 11 / Pillar D: Dynamic 2D Camera & Unified Render Pipeline
        self.camera = Camera(self.game.width, self.game.height)
        self.pipeline = RenderPipeline(self.game.width, self.game.height, assets=self.game.assets)
        self.canvas = self.pipeline.world_canvas
        
        # Pygame sprite groups for clean collision and batch updating
        self.all_sprites   = pg.sprite.Group()
        self.player_group  = pg.sprite.GroupSingle()
        self.enemies       = pg.sprite.Group()
        self.player_lasers = pg.sprite.Group()
        self.enemy_lasers  = pg.sprite.Group()
        self.powerups      = pg.sprite.Group()
        self.particles     = pg.sprite.Group()
        self.missiles      = pg.sprite.Group()   # Sprint 2: homing missiles group
        self.asteroids     = pg.sprite.Group()   # Sprint 6: hazard rocks
        self.asteroid_timer = 0.0

        # Initialize Player in the center-bottom of the viewport
        self.player = Player(self.game, self.game.width // 2, self.game.height - 100)
        self.player_group.add(self.player)
        self.all_sprites.add(self.player)
        self.player.base_laser_tier = self._laser_tier_for_level(self.selected_level)
        self.player.missile_count = 3
        self.player.activate_invincibility(4.0)
        self.asteroid_timer = 1.5

        # Sprint 7: Apply persistent upgrade bonuses purchased from the shop
        upgrades = getattr(self.game, "upgrades", {})
        if upgrades.get("max_health_bonus", 0):
            self.player.max_health += upgrades["max_health_bonus"]
            self.player.health = self.player.max_health
        if upgrades.get("max_shield_bonus", 0):
            self.player.max_shield += upgrades["max_shield_bonus"]
        if upgrades.get("extra_lives", 0):
            self.player.lives += upgrades["extra_lives"]
        if upgrades.get("reload_reduction", 0.0):
            self.player.shoot_cooldown *= max(0.3, 1.0 - upgrades["reload_reduction"])
        if upgrades.get("missile_capacity", 0):
            self.player.missile_count += upgrades["missile_capacity"]
        self.player.shield_regen_rate = upgrades.get("shield_regen_rate", 0.0)
        
        # Game stats
        self.score = 0
        
        # Sprint 2: LevelSystem drives all wave/level progression
        self.level_sys = LevelSystem(starting_level=self.selected_level)
        
        # Intro banner timing (shows "LEVEL X - WAVE Y" or "BOSS INCOMING")
        self.wave_intro_timer = 2.5
        
        # Boss tracking
        self.boss_active        = False
        self.boss_instance      = None
        self.boss_warning_shown = False  # Sprint 7: ensures warning cinematic plays only once

        # Sprint 6 game-feel feedback
        self.damage_flash = 0.0
        self.boss_warning_timer = 0.0
        self.float_texts = []

        # Screen shake status
        self.shake_duration  = 0.0
        self.shake_magnitude = 0
        self.shake_offset    = pg.Vector2(0, 0)

        # Sprint 11: Switch soundtrack to combat bed
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_music("combat", fade_ms=600)

    def trigger_shake(self, duration, magnitude):
        """Enables screen shake with a specific duration and strength."""
        self.shake_duration  = duration
        self.shake_magnitude = magnitude
        if hasattr(self, 'camera'):
            self.camera.add_shake(duration, magnitude)

    def trigger_impulse(self, dir_x, dir_y, magnitude=12.0):
        """Adds a directional impact impulse to the camera."""
        if hasattr(self, 'camera'):
            self.camera.add_impulse(dir_x, dir_y, magnitude)

    def trigger_damage_flash(self, amount=0.25):
        """Adds a brief red hit flash across the screen."""
        self.damage_flash = max(self.damage_flash, amount)

    def spawn_floating_text(self, x, y, text, color=(255, 255, 255), life=0.8, drift_y=-26):
        """Creates a floating combat label for score, damage, or pickup feedback."""
        self.float_texts.append({
            "x": float(x),
            "y": float(y),
            "text": text,
            "color": color,
            "life": float(life),
            "max_life": float(life),
            "drift_y": float(drift_y),
        })

    def _laser_tier_for_level(self, level_num):
        if level_num <= 3:
            return 1
        if level_num <= 6:
            return 2
        return 3

    def handle_events(self, events):
        """Checks for pause triggers (ESC key)."""
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    # Freeze the game by pushing the PauseState on top, passing self (PlayState) to resume later
                    self.game.change_state(PauseState(self.game, self))

    def update(self, dt):
        # Sprint 11 / Pillar D: Dynamic Camera, hit-stop, & render pipeline update
        if hasattr(self, 'camera'):
            if self.boss_warning_timer > 0 or self.level_sys.is_boss_wave:
                self.camera.set_target_zoom(1.04)
            elif self.combo_count >= 4:
                self.camera.set_target_zoom(1.02)
            else:
                self.camera.set_target_zoom(1.00)
            self.camera.update(dt, target_x=self.player.pos_x, target_y=self.player.pos_y)
            self.shake_offset = self.camera.shake_offset
        else:
            # Fallback screen shake math
            if self.shake_duration > 0:
                self.shake_duration -= dt
                self.shake_offset.x = random.randint(-self.shake_magnitude, self.shake_magnitude)
                self.shake_offset.y = random.randint(-self.shake_magnitude, self.shake_magnitude)
            else:
                self.shake_offset.update(0, 0)

        if hasattr(self, 'pipeline'):
            self.pipeline.update(dt)

        self.damage_flash = max(0.0, self.damage_flash - dt)
        if self.level_sys.is_boss_wave:
            self.boss_warning_timer = 1.5
        elif self.boss_warning_timer > 0:
            self.boss_warning_timer = max(0.0, self.boss_warning_timer - dt)

        for item in self.float_texts[:]:
            item["life"] -= dt
            item["y"] += item["drift_y"] * dt
            if item["life"] <= 0:
                self.float_texts.remove(item)

        # Sprint 7: Tick combo decay timer
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_count = 0
                self.combo_multiplier = 1.0

        # Sprint 7: Passive shield regen from upgrade shop
        regen = getattr(self.player, "shield_regen_rate", 0.0)
        if regen > 0:
            self.player.shield = min(self.player.max_shield, self.player.shield + regen * dt)

        # 2. BACKGROUND ANIMATION
        self.environment.update(dt)

        # 3. ASTEROID HAZARDS (Sprint 6)
        self.asteroid_timer -= dt
        if self.asteroid_timer <= 0:
            self._spawn_asteroid()
            self.asteroid_timer = random.uniform(2.2, 4.5)
        
        # 4. ENEMY SPAWNING via LevelSystem
        if self.wave_intro_timer > 0:
            # Freeze enemy spawning while the wave intro text is showing
            self.wave_intro_timer -= dt
        elif not self.level_sys.complete:
            # Ask LevelSystem what to spawn this frame
            spawn_type = self.level_sys.tick_spawn(dt)
            
            if spawn_type == "boss":
                # Sprint 7: Show boss warning cinematic before spawning if not yet shown
                if not self.boss_warning_shown:
                    self.boss_warning_shown = True
                    self.level_sys.spawned = 0  # allow boss tick to re-fire after warning
                    self.game.change_state(BossWarningState(self.game, self))
                    return
                # Spawn the Boss with level-scaled multipliers, skinned to the mission's faction theater
                cfg = self.level_sys.current_wave_cfg
                theater = self.environment.theater
                self.boss_instance = Boss(
                    self.game,
                    hp_mult=cfg["hp_mult"],
                    spd_mult=cfg["spd_mult"],
                    boss_key=theater["boss_key"],
                    laser_key=theater["laser_key"],
                )
                self.enemies.add(self.boss_instance)
                self.all_sprites.add(self.boss_instance)
                self.boss_active = True

            elif spawn_type is not None:
                # Regular enemy spawn with level multipliers, skinned to the mission's faction theater
                cfg = self.level_sys.current_wave_cfg
                theater = self.environment.theater
                enemy = Enemy(
                    self.game,
                    random.randint(60, self.game.width - 60),
                    -40,
                    enemy_type=spawn_type,
                    hp_mult=cfg["hp_mult"],
                    spd_mult=cfg["spd_mult"],
                    armada_folder=random.choice(theater["armadas"]),
                    laser_key=theater["laser_key"],
                )
                self.enemies.add(enemy)
                self.all_sprites.add(enemy)

            # Check if wave/level is done (all spawned + all killed)
            if self.level_sys.wave_finished_spawning() and len(self.enemies) == 0:
                cleared_level = self.level_sys.level_number

                # Sprint 7: Boss defeated — show celebratory banner before advancing
                if self.boss_active:
                    self.boss_active = False
                    self.boss_instance = None
                    self.game.change_state(
                        BossDefeatedState(self.game, self, cleared_level)
                    )
                    return

                result = self.level_sys.advance_wave()
                self.wave_intro_timer = 2.5
                self.boss_active = False
                self.player.base_laser_tier = self._laser_tier_for_level(self.level_sys.level_number)
                
                if result == "level":
                    # Persist any cleared intermediate level so the selector reflects progress.
                    self.save_system.save_progress(cleared_level)
                    self.game.change_state(HyperspaceExitState(
                        self.game, self, ShopState(self.game, self.score, cleared_level)
                    ))
                    return
                elif result == "complete":
                    self.save_system.save_progress(self.selected_level, completed_levels=list(range(1, 11)))
                    # All 10 levels beaten — show victory screen
                    self.game.change_state(HyperspaceExitState(
                        self.game, self, GameCompleteState(self.game, self.score)
                    ))
                    return

        # 5. SPRITE & PARTICLE PHYSICS
        self.all_sprites.update(dt)
        self.particles.update(dt)

        # 6. COLLISION CHECKS
        self._check_collisions()

    def _draw_float_text(self, canvas):
        """Renders floating battle feedback text for rewards and damage."""
        for item in self.float_texts:
            alpha = max(0, int((item["life"] / item["max_life"]) * 255))
            text = self.game.assets.hud_font.render(item["text"], True, (*item["color"], alpha))
            # pygame color tuples with alpha aren't supported by render; this uses a temporary surface.
            text.set_alpha(alpha)
            rect = text.get_rect(center=(int(item["x"]), int(item["y"])))
            canvas.blit(text, rect)

    def _spawn_asteroid(self, size=None, x=None, y=None, color=None):
        """Spawns a hazard asteroid from the top of the screen."""
        size = size or random.choices(["small", "medium", "large"], weights=[0.55, 0.30, 0.15])[0]
        asteroid = Asteroid(self.game, x=x or random.randint(40, self.game.width - 40), y=y or -60, size=size, color=color)
        self.asteroids.add(asteroid)
        self.all_sprites.add(asteroid)
        return asteroid

    def _break_asteroid(self, asteroid):
        """Break a larger asteroid into smaller, damaging chunks."""
        if asteroid.size == "small":
            return

        next_sizes = {"large": ["medium", "medium"], "medium": ["small", "small"]}
        for child_size in next_sizes[asteroid.size]:
            child = self._spawn_asteroid(
                size=child_size,
                x=asteroid.rect.centerx + random.randint(-12, 12),
                y=asteroid.rect.centery + random.randint(-12, 12),
                color=asteroid.color,
            )
            child.speed_x = asteroid.speed_x * 1.2 + random.uniform(-30, 30)
            child.speed_y = asteroid.speed_y * 0.9 + random.uniform(15, 45)
            child.rotation = random.uniform(0, 360)
            child.spin = random.uniform(-80, 80)

    def _check_collisions(self):
        """Handles hitbox intersections between game elements."""

        asteroid_hits = pg.sprite.groupcollide(self.asteroids, self.player_lasers, False, True)
        for asteroid, lasers in asteroid_hits.items():
            for laser in lasers:
                if asteroid.get_hit(laser.damage):
                    spawn_explosion(self.particles, asteroid.rect.centerx, asteroid.rect.centery, color=(170, 120, 80), count=24)
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_sfx("zap", pos_x=asteroid.rect.centerx, volume_mult=0.7)
                    elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                        self.game.assets.get_sound("zap").play()
                    self._break_asteroid(asteroid)
                    self.score += asteroid.max_health // 2
                    break
                spawn_sparks(self.particles, laser.rect.centerx, laser.rect.centery, (0, 0), color=(255, 180, 120), count=6)

        missile_hits = pg.sprite.groupcollide(self.asteroids, self.missiles, False, True)
        for asteroid, missiles_hit in missile_hits.items():
            for _ in missiles_hit:
                if asteroid.get_hit(Missile.DAMAGE):
                    spawn_explosion(self.particles, asteroid.rect.centerx, asteroid.rect.centery, color=(255, 150, 0), count=30)
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_sfx("zap", pos_x=asteroid.rect.centerx, volume_mult=0.9)
                    elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                        self.game.assets.get_sound("zap").play()
                    if hasattr(self, 'camera'):
                        self.camera.trigger_hit_stop(0.04)
                    self._break_asteroid(asteroid)
                    self.score += asteroid.max_health // 2

        # 0. Asteroids hitting the player
        player_asteroid_hits = pg.sprite.spritecollide(self.player, self.asteroids, True)
        for asteroid in player_asteroid_hits:
            self.trigger_shake(0.22, 8)
            self.trigger_impulse(0, 8.0, magnitude=14.0)
            spawn_explosion(self.particles, asteroid.rect.centerx, asteroid.rect.centery, color=(150, 110, 80), count=18)
            if self.player.get_hit(asteroid.damage):
                spawn_explosion(self.particles, self.player.rect.centerx, self.player.rect.centery, color=(0, 200, 255), count=40)
                if self.player.lives <= 0:
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.trigger_ducking(0.6, 0.3)
                        self.game.audio.play_sfx("player_death", pos_x=self.player.pos_x)
                    elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                        self.game.assets.get_sound("player_death").play()
                    self.game.change_state(GameOverState(self.game, self.score))
                    return

        # 1. Player lasers hitting enemies
        # pg.sprite.groupcollide detects intersections between sprites of two groups.
        # Arguments: (group1, group2, dokill1, dokill2).
        # Setting dokill2=True automatically deletes the player laser on contact.
        hits = pg.sprite.groupcollide(self.enemies, self.player_lasers, False, True)
        for enemy, lasers in hits.items():
            for laser in lasers:
                # Spawn glowing blue sparks shooting upwards from impact point
                spark_color = (255, 80, 0) if laser.damage > 10 else (0, 255, 255)
                spawn_sparks(self.particles, laser.rect.centerx, laser.rect.top, (0, -1), color=spark_color, count=6)
                
                # Apply laser damage (power laser = 20, normal = 10). get_hit returns True if enemy dies
                if enemy.get_hit(laser.damage):
                    points = int(enemy.score_value * self.combo_multiplier)
                    self.score += points
                    self.kills_since_powerup += 1
                    self._register_kill(enemy.rect.centerx, enemy.rect.top, points)
                    # Large orange radial explosion
                    spawn_explosion(self.particles, enemy.rect.centerx, enemy.rect.centery, color=(255, 120, 0), count=25)
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_sfx("zap", pos_x=enemy.rect.centerx, volume_mult=0.75)
                    elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                        self.game.assets.get_sound("zap").play()
                    # Determine powerup drop pool based on current level
                    self._try_drop_powerup(enemy)

        # 2. Homing missiles hitting enemies (Sprint 2)
        missile_hits = pg.sprite.groupcollide(self.enemies, self.missiles, False, True)
        for enemy, missiles_hit in missile_hits.items():
            for _ in missiles_hit:
                # Big orange-yellow explosion for missile impact
                spawn_explosion(self.particles, enemy.rect.centerx, enemy.rect.centery,
                                color=(255, 150, 0), count=40, speed_range=(80, 300))
                self.trigger_shake(0.4, 8)
                if hasattr(self, 'camera'):
                    self.camera.trigger_hit_stop(0.045)
                
                if enemy.get_hit(Missile.DAMAGE):
                    points = int(enemy.score_value * self.combo_multiplier)
                    self.score += points
                    self.kills_since_powerup += 1
                    self._register_kill(enemy.rect.centerx, enemy.rect.top, points)
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_sfx("zap", pos_x=enemy.rect.centerx, volume_mult=0.9)
                    elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                        self.game.assets.get_sound("zap").play()
                    self._try_drop_powerup(enemy)

        # 3. Enemy lasers hitting Player ship
        # pg.sprite.spritecollide checks one sprite against a group.
        # dokill=True deletes the enemy laser on impact.
        player_laser_hits = pg.sprite.spritecollide(self.player, self.enemy_lasers, True)
        for laser in player_laser_hits:
            # Spawn red sparks shooting downwards from impact
            spawn_sparks(self.particles, laser.rect.centerx, laser.rect.bottom, (0, 1), color=(255, 50, 50), count=8)
            self.trigger_impulse(0, 6.0, magnitude=10.0)
            
            # Apply damage to player. Returns True if player loses a life
            if self.player.get_hit(15):
                self._reset_combo()  # Sprint 7: break combo on damage
                self.trigger_damage_flash(0.5)
                self.spawn_floating_text(self.player.rect.centerx, self.player.rect.top, "-15 HP", color=(255, 100, 100))
                # Major blue explosion representing ship destruction
                spawn_explosion(self.particles, self.player.rect.centerx, self.player.rect.centery, color=(0, 200, 255), count=40)
                # If out of lives, transition to GameOver State
                if self.player.lives <= 0:
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.trigger_ducking(0.6, 0.3)
                        self.game.audio.play_sfx("player_death", pos_x=self.player.pos_x)
                    elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                        self.game.assets.get_sound("player_death").play()
                    self.game.change_state(GameOverState(self.game, self.score))
                    return
            else:
                self._reset_combo()  # Sprint 7: break combo on damage
                self.trigger_damage_flash(0.2)
                self.spawn_floating_text(self.player.rect.centerx, self.player.rect.top, "-15 HP", color=(255, 120, 120))

        # 4. Enemy ships colliding directly with Player ship
        # (Crashing deals heavy damage and destroys the enemy)
        crash_hits = pg.sprite.spritecollide(self.player, self.enemies, True)
        for enemy in crash_hits:
            spawn_explosion(self.particles, enemy.rect.centerx, enemy.rect.centery, color=(255, 80, 0), count=30)
            self.score += enemy.score_value // 2
            self.trigger_impulse(0, 10.0, magnitude=16.0)
            if hasattr(self, 'camera'):
                self.camera.trigger_hit_stop(0.035)
            
            if self.player.get_hit(30):
                self._reset_combo()  # Sprint 7: break combo on crash
                self.trigger_damage_flash(0.6)
                self.spawn_floating_text(self.player.rect.centerx, self.player.rect.top, "-30 HP", color=(255, 90, 90))
                spawn_explosion(self.particles, self.player.rect.centerx, self.player.rect.centery, color=(0, 200, 255), count=40)
                if self.player.lives <= 0:
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.trigger_ducking(0.6, 0.3)
                        self.game.audio.play_sfx("player_death", pos_x=self.player.pos_x)
                    elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                        self.game.assets.get_sound("player_death").play()
                    self.game.change_state(GameOverState(self.game, self.score))
                    return
            else:
                self._reset_combo()  # Sprint 7: break combo on crash
                self.trigger_damage_flash(0.25)
                self.spawn_floating_text(self.player.rect.centerx, self.player.rect.top, "-30 HP", color=(255, 110, 110))

        # 5. Player ship absorbing floating Power-Ups
        pup_collects = pg.sprite.spritecollide(self.player, self.powerups, True)
        for pup in pup_collects:
            # White particle absorption effect
            spawn_sparks(self.particles, pup.rect.centerx, pup.rect.centery, (0, 0), color=(255, 255, 255), count=15)
            self.spawn_floating_text(pup.rect.centerx, pup.rect.top, "POWER UP", color=(120, 255, 200))

            if pup.type == "shield":
                if hasattr(self.game, 'audio') and self.game.audio:
                    self.game.audio.play_sfx("shield_up", pos_x=pup.rect.centerx)
                elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                    self.game.assets.get_sound("shield_up").play()
                # Recharge player shield points
                self.player.shield = min(self.player.max_shield, self.player.shield + 40)
            else:
                if hasattr(self.game, 'audio') and self.game.audio:
                    self.game.audio.play_sfx("powerup", pos_x=pup.rect.centerx)
                elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
                    self.game.assets.get_sound("powerup").play()

            if pup.type == "triple":
                # Activate triple firing guns for 12 seconds (Sprint 2: increased from 8)
                self.player.triple_shot_timer = 12.0
            elif pup.type == "speed":
                # Activate 1.5x engine speed boost for 12 seconds (Sprint 2: increased from 8)
                self.player.speed_boost_timer = 12.0
            elif pup.type == "health":
                # Restore up to 30 HP, never exceeding max_health (Sprint 2 new)
                self.player.health = min(self.player.max_health, self.player.health + 30)
            elif pup.type == "power_laser":
                # 2x damage red laser for 10 seconds (Sprint 2 new)
                self.player.laser_power_timer = 10.0
            elif pup.type == "missile":
                # Add one homing missile to inventory (Sprint 2 new)
                self.player.missile_count += 1

    def _register_kill(self, x, y, points):
        """Sprint 7: Update combo chain after an enemy kill and show combo text."""
        self.combo_count += 1
        self.combo_timer = self.COMBO_WINDOW  # restart the decay window
        if self.combo_count > 1:
            # Increase multiplier (step each kill, cap at COMBO_CAP)
            old_mult = self.combo_multiplier
            self.combo_multiplier = min(self.COMBO_CAP, 1.0 + (self.combo_count - 1) * self.COMBO_STEP)
            if self.combo_multiplier >= self.COMBO_CAP and old_mult < self.COMBO_CAP and hasattr(self, 'camera'):
                self.camera.trigger_hit_stop(0.04)
            combo_label = f"×{self.combo_multiplier:.1f} COMBO!"
            self.spawn_floating_text(x, y - 20, combo_label, color=(255, 230, 50), life=1.0, drift_y=-40)
        else:
            self.spawn_floating_text(x, y, f"+{points}", color=(255, 210, 80))

    def _reset_combo(self):
        """Sprint 7: Reset the combo chain (called on player damage)."""
        self.combo_count = 0
        self.combo_timer = 0.0
        self.combo_multiplier = 1.0

    def _try_drop_powerup(self, enemy):
        """
        Decides whether a destroyed enemy drops a power-up, and which type.
        A guaranteed pity drop is enforced on the third enemy kill since the
        last power-up reward, while otherwise preserving the normal random roll.
        """
        should_drop = (self.kills_since_powerup >= 3) or (random.random() < 0.15)
        if should_drop:
            # From level 3+, include the new Sprint 2 powerup types
            if self.level_sys.level_number >= 3:
                all_types = PowerUp.BASE_TYPES + PowerUp.EXTRA_TYPES
                # Weights: base types slightly more common than new types
                weights = [0.20, 0.15, 0.15,   # shield, triple, speed
                           0.20, 0.15, 0.15]   # health, power_laser, missile
            else:
                all_types = PowerUp.BASE_TYPES
                weights   = [0.4, 0.3, 0.3]
            
            ptype = random.choices(all_types, weights=weights)[0]
            pup = PowerUp(self.game, enemy.rect.centerx, enemy.rect.centery, ptype)
            self.powerups.add(pup)
            self.all_sprites.add(pup)
            self.kills_since_powerup = 0

    def draw(self, screen):
        # Sprint 11: layered per-mission parallax world (far void / mid nebula / near motes+debris)
        # replaces the flat navy fill, and plays the hyperspace warp overlay while active.
        self.environment.draw(self.canvas)

        # Game elements
        self.player.draw_presentation_back(self.canvas)
        for projectile in (*self.player_lasers, *self.enemy_lasers, *self.missiles):
            if hasattr(projectile, "draw_trail"):
                projectile.draw_trail(self.canvas)
        self.all_sprites.draw(self.canvas)
        self.player.draw_presentation_front(self.canvas)
        self.particles.draw(self.canvas)
        self._draw_float_text(self.canvas)

        # Damage flash overlay for hits
        if self.damage_flash > 0:
            flash_alpha = min(255, max(0, int((self.damage_flash / 0.25) * 120)))
            flash = pg.Surface((self.game.width, self.game.height), pg.SRCALPHA)
            flash.fill((255, 30, 30, flash_alpha))
            self.canvas.blit(flash, (0, 0))

        # Boss warning banner / pulse
        if self.boss_warning_timer > 0:
            pulse = 1.0 + 0.25 * math.sin(pg.time.get_ticks() * 0.015)
            msg = self.game.assets.title_font.render("BOSS ALERT", True, (255, 60, 80))
            msg_rect = msg.get_rect(center=(self.game.width // 2, 110))
            scaled = pg.transform.smoothscale(msg, (int(msg.get_width() * pulse), int(msg.get_height() * pulse)))
            scaled_rect = scaled.get_rect(center=msg_rect.center)
            self.canvas.blit(scaled, scaled_rect)

        # Render User Interface HUD (Health, Shields, Level/Wave text, timers)
        self._draw_hud()

        # Sprint 11 / Pillar D: Unified Render Pipeline Presentation
        if hasattr(self, 'pipeline'):
            health_ratio = self.player.health / max(1, self.player.max_health)
            shield_active = self.player.shield > 0
            speed_boost = self.player.speed_boost_timer > 0
            is_boss_alert = self.boss_warning_timer > 0
            self.pipeline.present(
                screen,
                camera=getattr(self, 'camera', None),
                health_ratio=health_ratio,
                shield_active=shield_active,
                speed_boost=speed_boost,
                is_boss_alert=is_boss_alert,
            )
        else:
            # Final blit onto physical display screen, applying coordinates offset by screen shake values
            screen.blit(self.canvas, self.shake_offset)

    def _draw_hud(self):
        """Renders information layout on screen (Score, Level/Wave, Health/Shield Meters, Powerup Timers)."""
        # 1. SCORE
        score_surf = self.game.assets.hud_font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        self.canvas.blit(score_surf, (25, 20))

        # Sprint 7: Combo counter (shown below score when active)
        if self.combo_count > 1:
            combo_alpha = min(255, int(self.combo_timer / self.COMBO_WINDOW * 255))
            mx = self.combo_multiplier
            combo_color = (255, int(230 - (mx - 1) * 25), max(0, int(100 - (mx - 1) * 15)))
            combo_surf = self.game.assets.hud_font.render(f"COMBO  ×{mx:.1f}  [{self.combo_count} KILLS]", True, combo_color)
            combo_surf.set_alpha(combo_alpha)
            self.canvas.blit(combo_surf, (25, 42))
        
        # 2. LEVEL & WAVE TRACKER (Sprint 2: shows both level and wave)
        if self.level_sys.is_boss_wave:
            wave_txt = f"LVL {self.level_sys.level_number} — BOSS"
            wave_color = (255, 80, 80)
        else:
            wave_txt = f"LVL {self.level_sys.level_number}  WAVE {self.level_sys.wave_number}"
            wave_color = (0, 255, 200)
        wave_surf = self.game.assets.hud_font.render(wave_txt, True, wave_color)
        self.canvas.blit(wave_surf, (self.game.width - wave_surf.get_width() - 25, 20))
        
        # 3. HEALTH & SHIELD PROGRESS BARS (Center Dashboard)
        bar_w, bar_h = 160, 10
        center_x = self.game.width // 2 - bar_w // 2
        
        # Health Bar: Dark Red background container, Green fill bar
        pg.draw.rect(self.canvas, (60, 10, 10), (center_x, 20, bar_w, bar_h), border_radius=3)
        h_fill = int((self.player.health / self.player.max_health) * bar_w)
        if h_fill > 0:
            pg.draw.rect(self.canvas, (0, 255, 100), (center_x, 20, h_fill, bar_h), border_radius=3)
        health_lbl = self.game.assets.hud_font.render("HP", True, (200, 220, 200))
        self.canvas.blit(health_lbl, (center_x - 30, 16))

        # Shield Bar: Dark Cyan container, Cyan fill bar
        pg.draw.rect(self.canvas, (10, 40, 50), (center_x, 36, bar_w, bar_h), border_radius=3)
        s_fill = int((self.player.shield / self.player.max_shield) * bar_w)
        if s_fill > 0:
            pg.draw.rect(self.canvas, (0, 200, 255), (center_x, 36, s_fill, bar_h), border_radius=3)
        shield_lbl = self.game.assets.hud_font.render("SH", True, (180, 220, 240))
        self.canvas.blit(shield_lbl, (center_x - 30, 32))

        # 4. LIVES SHIP ICONS (Bottom Left stack)
        for i in range(self.player.lives):
            # Draw mini player ships to denote lives
            life_img = self.game.assets.get_image("player", 22, 22)
            self.canvas.blit(life_img, (25 + i * 28, 55))

        # 5. MISSILE COUNT INDICATOR (Sprint 2)
        if self.player.missile_count > 0:
            missile_icon = self.game.assets.get_image("missile", 12, 24)
            for i in range(self.player.missile_count):
                self.canvas.blit(missile_icon, (25 + i * 18, 85))
            m_lbl = self.game.assets.hud_font.render("MISSILES [M]", True, (255, 130, 0))
            self.canvas.blit(m_lbl, (25 + self.player.missile_count * 18 + 4, 89))

        # 6. POWER-UP EXPIRY METERS (Sprint 2: updated timers for triple/speed, added power_laser)
        TRIPLE_MAX = 12.0
        SPEED_MAX  = 12.0
        POWER_MAX  = 10.0

        active_timers = []
        if self.player.triple_shot_timer > 0:
            active_timers.append(("TRIPLE SHOT",  self.player.triple_shot_timer, TRIPLE_MAX, (255, 50, 50)))
        if self.player.speed_boost_timer > 0:
            active_timers.append(("SPEED BOOST",  self.player.speed_boost_timer, SPEED_MAX,  (255, 200, 0)))
        if self.player.laser_power_timer > 0:
            active_timers.append(("POWER LASER",  self.player.laser_power_timer, POWER_MAX,  (220, 60, 0)))

        for idx, (label, timer, max_time, color) in enumerate(active_timers):
            lbl_surf = self.game.assets.hud_font.render(label, True, color)
            self.canvas.blit(lbl_surf, (25, self.game.height - 110 + idx * 30))
            
            bar_len = int((timer / max_time) * 100)
            pg.draw.rect(self.canvas, (40, 40, 40), (140, self.game.height - 100 + idx * 30, 100, 6))
            pg.draw.rect(self.canvas, color,        (140, self.game.height - 100 + idx * 30, bar_len, 6))

        # 7. WAVE START BANNERS (Big overlay in center-screen)
        if self.wave_intro_timer > 0:
            overlay_txt   = self.level_sys.banner_text()
            overlay_color = self.level_sys.banner_color()
            
            banner_surf = self.game.assets.title_font.render(overlay_txt, True, overlay_color)
            banner_rect = banner_surf.get_rect(center=(self.game.width // 2, self.game.height // 2 - 40))
            
            # Semi-transparent dark letterbox stripe behind text
            stripe = pg.Surface((self.game.width, 100), pg.SRCALPHA)
            stripe.fill((0, 0, 0, 140))
            self.canvas.blit(stripe, (0, self.game.height // 2 - 90))
            self.canvas.blit(banner_surf, banner_rect)

        # 8. BOSS HEALTH BAR (Top center overlay - only shows if boss is spawned)
        if self.boss_active and self.boss_instance and self.boss_instance.alive():
            boss_bar_w, boss_bar_h = 600, 14
            boss_x = self.game.width // 2 - boss_bar_w // 2
            
            boss_label = self.game.assets.hud_font.render("BOSS - COMMAND SHIP", True, (255, 50, 50))
            self.canvas.blit(boss_label, (boss_x, 70))
            
            # Red progress indicator bar
            pg.draw.rect(self.canvas, (50, 10, 10), (boss_x, 92, boss_bar_w, boss_bar_h), border_radius=4)
            b_fill = int((self.boss_instance.health / self.boss_instance.max_health) * boss_bar_w)
            if b_fill > 0:
                pg.draw.rect(self.canvas, (255, 0, 50), (boss_x, 92, b_fill, boss_bar_h), border_radius=4)
                # Outer white styling outline
                pg.draw.rect(self.canvas, (255, 255, 255), (boss_x, 92, boss_bar_w, boss_bar_h), 1, border_radius=4)


class PauseState(State):
    """
    State representing game execution freezing.
    
    Draws a semi-transparent screen overlay and ignores updates to sprites.
    """
    def __init__(self, game, previous_state):
        super().__init__(game)
        # Store references to frozen state to allow resuming later
        self.previous_state = previous_state
        self.hovered_index = None
        self.buttons = []
        self._build_buttons()
        self.anim_timer = 0.0
        
        # Transparent dark overlay cover
        self.overlay = pg.Surface((self.game.width, self.game.height), pg.SRCALPHA)
        self.overlay.fill((10, 12, 22, 200)) # Dark tint with 200 alpha

    def _build_buttons(self):
        self.buttons = [
            {"label": "RESUME", "rect": pg.Rect(self.game.width // 2 - 110, self.game.height // 2 - 25, 220, 56)},
            {"label": "QUIT TO MENU", "rect": pg.Rect(self.game.width // 2 - 140, self.game.height // 2 + 45, 280, 56)},
        ]

    def handle_events(self, events):
        """Allows resuming or quitting back to Menu State using mouse or keyboard."""
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.hovered_index = None
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        self.hovered_index = idx
                        break
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        if idx == 0:
                            self.game.change_state(self.previous_state)
                        else:
                            self.game.change_state(MenuState(self.game))
                        return
            elif event.type == pg.KEYDOWN:
                # ESC returns back to the active gameplay state
                if event.key == pg.K_ESCAPE:
                    self.game.change_state(self.previous_state)
                # Q returns to the main menu
                elif event.key == pg.K_q:
                    self.game.change_state(MenuState(self.game))

    def update(self, dt):
        self.anim_timer += dt

    def draw(self, screen):
        # 1. Render gameplay frames in background so player can see screen behind overlay
        self.previous_state.draw(screen)
        
        # 2. Layer transparency overlay
        screen.blit(self.overlay, (0, 0))
        
        # 3. Draw Pause menu elements
        title = self.game.assets.title_font.render("GAME PAUSED", True, (255, 200, 0))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 3))
        screen.blit(title, title_rect)

        for idx, button in enumerate(self.buttons):
            rect = button["rect"]
            hovered = (self.hovered_index == idx)
            is_danger = "QUIT" in button["label"]

            if is_danger and hovered:
                fill = (65, 15, 25, 240)
                border = (255, 60, 80, 255)
                text_color = (255, 140, 160)
            elif is_danger:
                fill = (35, 18, 24, 210)
                border = (140, 60, 70, 255)
                text_color = (220, 170, 180)
            else:
                fill = (20, 30, 44, 220)
                border = (90, 120, 150, 255)
                text_color = (240, 240, 240)
                if hovered:
                    fill = (24, 88, 105, 240)
                    border = (0, 255, 255, 255)

            _draw_ui_button(
                screen,
                rect,
                button["label"],
                self.game.assets.font,
                hovered=hovered,
                fill=fill,
                border=border,
                text_color=text_color,
                pulse=self.anim_timer * 10 + idx,
                danger=is_danger,
            )


class GameOverState(State):
    """
    State representing game-over condition.
    
    Accepts pilot text inputs to record names alongside their scores in SaveSystem.
    """
    def __init__(self, game, score):
        super().__init__(game)
        self.score = score
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.trigger_ducking(duration=0.8, factor=0.2)
            self.game.audio.play_sfx("game_over", volume_mult=1.0)
        elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
            self.game.assets.get_sound("game_over").play()
        self.save_system = SaveSystem()
        self.player_name = ""
        self.save_rect = pg.Rect(self.game.width // 2 - 135, self.game.height // 2 + 110, 270, 52)
        self.save_hovered = False
        
        # Blinking cursor indicator variables
        self.cursor_visible = True
        self.cursor_timer = 0.0

    def _save_score(self):
        final_name = self.player_name.strip() or "PILOT"
        self.save_system.save_score(final_name, self.score)
        self.game.change_state(HighScoresState(self.game))

    def handle_events(self, events):
        """Processes keyboard text letters to build the username string."""
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.save_hovered = self.save_rect.collidepoint(event.pos)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.save_rect.collidepoint(event.pos):
                    self._save_score()
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_RETURN:
                    self._save_score()
                elif event.key == pg.K_BACKSPACE:
                    # Remove last character
                    self.player_name = self.player_name[:-1]
                else:
                    # Restrict player name to alphanumeric, max length of 8 characters
                    if len(self.player_name) < 8 and event.unicode.isalnum():
                        self.player_name += event.unicode.upper()

    def update(self, dt):
        """Animates a blinking underscore cursor."""
        self.cursor_timer += dt
        if self.cursor_timer >= 0.4:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

    def draw(self, screen):
        # Clear screen with dark crimson tone
        screen.fill((25, 10, 12))
        
        # Draw "GAME OVER" title
        title = self.game.assets.title_font.render("GAME OVER", True, (255, 50, 50))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 4))
        screen.blit(title, title_rect)
        
        # Draw final score reached
        score_text = self.game.assets.font.render(f"Final Score: {self.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.game.width // 2, self.game.height // 3 + 20))
        screen.blit(score_text, score_rect)
        
        # Input instructions
        prompt_surf = self.game.assets.font.render("ENTER YOUR NAME:", True, (0, 255, 200))
        prompt_rect = prompt_surf.get_rect(center=(self.game.width // 2, self.game.height // 2))
        screen.blit(prompt_surf, prompt_rect)
        
        # Draw dynamic typed username + blinking cursor
        cursor_char = "_" if self.cursor_visible else " "
        display_name = f"{self.player_name}{cursor_char}"
        
        name_surf = self.game.assets.title_font.render(display_name, True, (255, 255, 255))
        name_rect = name_surf.get_rect(center=(self.game.width // 2, self.game.height // 2 + 60))
        screen.blit(name_surf, name_rect)

        _draw_ui_button(
            screen,
            self.save_rect,
            "SAVE SCORE",
            self.game.assets.font,
            hovered=self.save_hovered,
            fill=(40, 12, 20, 220),
            border=(255, 100, 110, 255) if self.save_hovered else (190, 80, 90, 255),
            text_color=(255, 230, 230),
            pulse=self.cursor_timer * 12,
        )


# ---------------------------------------------------------------------------
# Sprint 7 — BossWarningState
# ---------------------------------------------------------------------------
class BossWarningState(State):
    """
    Sprint 7 — Full-screen cinematic warning shown before a boss spawns.
    
    Displays a red-tinted overlay with flashing "!! BOSS INCOMING !!" text for
    ~2.5 s, then resumes the PlayState so the boss can fly in from the top.
    The player cannot move or shoot during the warning (cinematic lock).
    """
    DURATION = 2.6  # seconds

    def __init__(self, game, play_state):
        super().__init__(game)
        self.play_state = play_state
        self.timer = 0.0
        self.done = False
        if hasattr(self.play_state, 'pipeline'):
            self.play_state.pipeline.set_letterbox(True)
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.trigger_ducking(duration=self.DURATION, factor=0.3)
            self.game.audio.play_music("boss", fade_ms=400)
        elif hasattr(self.game, 'assets') and hasattr(self.game.assets, 'get_sound'):
            self.game.assets.get_sound("boss_music").play()

    def handle_events(self, events):
        pass  # lock all input during cinematic

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.DURATION and not self.done:
            self.done = True
            if hasattr(self.play_state, 'pipeline'):
                self.play_state.pipeline.set_letterbox(False)
            # Unfreeze the play state — boss wave will proceed normally
            self.game.change_state(self.play_state)

    def draw(self, screen):
        # Render the frozen gameplay in the background
        self.play_state.draw(screen)

        # Darkening red tint layer, intensity pulses with the flash timer
        flash_intensity = abs(math.sin(self.timer * 5.5))
        overlay = pg.Surface((self.game.width, self.game.height), pg.SRCALPHA)
        overlay.fill((180, 0, 0, int(90 + 80 * flash_intensity)))
        screen.blit(overlay, (0, 0))

        # Animated scan-line stripes for drama
        for sy in range(0, self.game.height, 10):
            stripe = pg.Surface((self.game.width, 3), pg.SRCALPHA)
            stripe.fill((0, 0, 0, 40))
            screen.blit(stripe, (0, sy))

        # "!! BOSS INCOMING !!" text — scales with the flash pulse
        if self.game.level_sys_level_number if hasattr(self.game, 'level_sys_level_number') else False:
            label_str = "!! FINAL BOSS APPROACHING !!"
        else:
            label_str = "!! BOSS INCOMING !!"
        # Determine from play_state's level_sys
        if self.play_state.level_sys.level_number == 10:
            label_str = "!! FINAL BOSS APPROACHING !!"

        scale = 1.0 + 0.12 * flash_intensity
        text_surf = self.game.assets.title_font.render(label_str, True, (255, 60, 60))
        w = int(text_surf.get_width() * scale)
        h = int(text_surf.get_height() * scale)
        scaled = pg.transform.smoothscale(text_surf, (w, h))
        screen.blit(scaled, scaled.get_rect(center=(self.game.width // 2, self.game.height // 2 - 40)))

        sub_surf = self.game.assets.hud_font.render("Brace yourself, pilot!", True, (255, 200, 200))
        screen.blit(sub_surf, sub_surf.get_rect(center=(self.game.width // 2, self.game.height // 2 + 40)))

        # Countdown bar
        progress = max(0.0, 1.0 - self.timer / self.DURATION)
        bar_w = int(400 * progress)
        pg.draw.rect(screen, (80, 0, 0), (self.game.width // 2 - 200, self.game.height // 2 + 90, 400, 10), border_radius=5)
        if bar_w > 0:
            pg.draw.rect(screen, (255, 60, 60), (self.game.width // 2 - 200, self.game.height // 2 + 90, bar_w, 10), border_radius=5)


# ---------------------------------------------------------------------------
# Sprint 7 — BossDefeatedState
# ---------------------------------------------------------------------------
class BossDefeatedState(State):
    """
    Sprint 7 — Short celebratory screen shown immediately after a boss dies.
    Displays "BOSS DEFEATED" with a screen flash, then returns to
    the normal level-advance flow.
    """
    DURATION = 2.8

    def __init__(self, game, play_state, cleared_level):
        super().__init__(game)
        self.play_state = play_state
        self.cleared_level = int(cleared_level)
        self.timer = 0.0
        self.done = False
        self.particles = pg.sprite.Group()
        # Spawn a huge celebratory explosion in the centre of the screen
        from fx import spawn_explosion
        spawn_explosion(self.particles, game.width // 2, game.height // 2,
                        color=(255, 200, 50), count=80, speed_range=(100, 500))
        spawn_explosion(self.particles, game.width // 2, game.height // 2,
                        color=(255, 80, 0), count=50, speed_range=(60, 350))

    def handle_events(self, events):
        pass

    def update(self, dt):
        self.timer += dt
        self.particles.update(dt)
        if self.timer >= self.DURATION and not self.done:
            self.done = True
            # Now actually advance the wave in the underlying play_state
            save_sys = self.play_state.save_system
            level_sys = self.play_state.level_sys
            score = self.play_state.score
            result = level_sys.advance_wave()
            self.play_state.wave_intro_timer = 2.5
            self.play_state.player.base_laser_tier = self.play_state._laser_tier_for_level(level_sys.level_number)
            if result == "level":
                save_sys.save_progress(self.cleared_level)
                self.game.change_state(HyperspaceExitState(
                    self.game, self.play_state, ShopState(self.game, score, self.cleared_level)
                ))
            elif result == "complete":
                save_sys.save_progress(self.play_state.selected_level, completed_levels=list(range(1, 11)))
                self.game.change_state(HyperspaceExitState(
                    self.game, self.play_state, GameCompleteState(self.game, score)
                ))
            else:
                # Just continue playing (next wave)
                self.game.change_state(self.play_state)

    def draw(self, screen):
        self.play_state.draw(screen)
        self.particles.draw(screen)

        # White flash that fades with time
        flash_alpha = max(0, int(180 * (1.0 - self.timer / 0.5)))
        if flash_alpha > 0:
            flash = pg.Surface((self.game.width, self.game.height), pg.SRCALPHA)
            flash.fill((255, 255, 255, flash_alpha))
            screen.blit(flash, (0, 0))

        # "BOSS DEFEATED" title
        pulse = 1.0 + 0.1 * math.sin(self.timer * 6)
        title_color = (
            255,
            int(200 + 55 * abs(math.sin(self.timer * 4))),
            0,
        )
        text_surf = self.game.assets.title_font.render("BOSS DEFEATED", True, title_color)
        w = int(text_surf.get_width() * pulse)
        h = int(text_surf.get_height() * pulse)
        scaled = pg.transform.smoothscale(text_surf, (max(1, w), max(1, h)))
        screen.blit(scaled, scaled.get_rect(center=(self.game.width // 2, self.game.height // 2 - 30)))

        sub = self.game.assets.hud_font.render("Excellent work, pilot!", True, (200, 255, 200))
        screen.blit(sub, sub.get_rect(center=(self.game.width // 2, self.game.height // 2 + 50)))


# ---------------------------------------------------------------------------
# Sprint 11 / Pillar B — HyperspaceExitState
# ---------------------------------------------------------------------------
class HyperspaceExitState(State):
    """
    Sprint 11 — brief reverse-warp cinematic played when a mission is cleared.

    Keeps the frozen PlayState visible while its SpaceEnvironment streaks into
    a reverse hyperspace warp, so the universe *exits* before the congratulations
    screen (ShopState / GameCompleteState) pops in, instead of an instant cut.
    """
    def __init__(self, game, play_state, next_state):
        super().__init__(game)
        self.play_state = play_state
        self.next_state = next_state
        self.timer = 0.0
        self.duration = play_state.environment.WARP_OUT_DURATION
        play_state.environment.start_warp_out()

    def handle_events(self, events):
        pass  # lock input during the cinematic

    def update(self, dt):
        self.timer += dt
        self.play_state.environment.update(dt)
        if self.timer >= self.duration:
            self.game.change_state(self.next_state)

    def draw(self, screen):
        self.play_state.draw(screen)


# ---------------------------------------------------------------------------
# Sprint 7 & 9 — ShopState (between-level upgrade shop)
# ---------------------------------------------------------------------------

# Full upgrade pool — 3 are randomly picked each time
_UPGRADE_POOL = [
    {
        "id": "max_health_bonus",
        "name": "Max Hull HP +20",
        "desc": "Reinforces armor plating and raises ship hull HP capacity by +20.",
        "cost": 300,
        "sprite_alias": "powerup_health",
        "fallback_color": (0, 220, 100),
        "step": 20,
    },
    {
        "id": "max_shield_bonus",
        "name": "Max Shield +20",
        "desc": "Expands forcefield generator capacity by +20 barrier points.",
        "cost": 280,
        "sprite_alias": "powerup_shield",
        "fallback_color": (0, 180, 255),
        "step": 20,
    },
    {
        "id": "extra_lives",
        "name": "Backup Vessel +1",
        "desc": "Deploys 1 spare starship life reserve for the upcoming sector.",
        "cost": 500,
        "sprite_alias": "player",
        "fallback_color": (255, 200, 0),
        "step": 1,
    },
    {
        "id": "reload_reduction",
        "name": "Rapid Blaster Mod",
        "desc": "Accelerates weapon cooling, reducing firing delay by 10% (stacks).",
        "cost": 350,
        "sprite_alias": "powerup_power_laser",
        "fallback_color": (255, 120, 0),
        "step": 0.10,
    },
    {
        "id": "missile_capacity",
        "name": "Missile Rack +1",
        "desc": "Stocks +1 heavy lock-on missile in cargo bay for each level.",
        "cost": 250,
        "sprite_alias": "powerup_missile",
        "fallback_color": (255, 80, 0),
        "step": 1,
    },
    {
        "id": "shield_regen_rate",
        "name": "Nanite Shield Regen",
        "desc": "Installs automated nanite emitters that steadily repair shields over time.",
        "cost": 400,
        "sprite_alias": "powerup_speed",
        "fallback_color": (100, 200, 255),
        "step": 5.0,
    },
]


class ShopState(State):
    """
    Sprint 7 & 9 — Overhauled Between-level Upgrade Shop.
    
    Features spacious upgrade cards, isolated bottom action buttons, authentic
    sprite icons, hover animations, purchase particle bursts, and tactile feedback.
    """
    NUM_OFFERS = 3

    def __init__(self, game, score, cleared_level):
        super().__init__(game)
        self.score = score
        self.cleared_level = int(cleared_level)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=80)
        self.particles = pg.sprite.Group()
        self.timer = 0.0
        self.purchased = set()   # indices of already-bought offers
        self.hovered = None
        self.skip_hovered = False
        self.transition_locked = False

        # Randomly choose 3 distinct upgrades from the pool
        self.offers = random.sample(_UPGRADE_POOL, self.NUM_OFFERS)

        # Build card geometry: spacious 360x290 cards with generous padding
        card_w, card_h = 360, 290
        gap = 35
        total_w = self.NUM_OFFERS * card_w + (self.NUM_OFFERS - 1) * gap
        start_x = (self.game.width - total_w) // 2
        start_y = 155
        self.card_rects = []
        for i in range(self.NUM_OFFERS):
            x = start_x + i * (card_w + gap)
            self.card_rects.append(pg.Rect(x, start_y, card_w, card_h))

        self.skip_rect = pg.Rect(self.game.width // 2 - 130, 590, 260, 52)

    def _proceed(self):
        if self.transition_locked:
            return
        self.transition_locked = True
        self.game.change_state(LevelSelectState(self.game))

    def handle_events(self, events):
        if self.transition_locked:
            return
        for event in events:
            if event.type == pg.MOUSEMOTION:
                mp = event.pos
                self.skip_hovered = self.skip_rect.collidepoint(mp)
                self.hovered = None
                for i, rect in enumerate(self.card_rects):
                    if rect.collidepoint(mp):
                        self.hovered = i
                        break
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                mp = event.pos
                if self.skip_rect.collidepoint(mp):
                    self._proceed()
                    return
                for i, rect in enumerate(self.card_rects):
                    if rect.collidepoint(mp) and i not in self.purchased:
                        self._buy(i)
                        return
            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_SPACE):
                    self._proceed()

    def _buy(self, idx):
        offer = self.offers[idx]
        if self.score < offer["cost"]:
            return  # not enough score
        self.score -= offer["cost"]
        self.purchased.add(idx)
        
        # Accumulate bonus in game.upgrades
        uid = offer["id"]
        if uid not in self.game.upgrades:
            self.game.upgrades[uid] = 0.0 if isinstance(offer["step"], float) else 0
        self.game.upgrades[uid] = self.game.upgrades.get(uid, 0) + offer["step"]

        # Purchase audio & particle juice
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_ui("purchase")
        elif hasattr(self.game, "assets") and hasattr(self.game.assets, "get_sound"):
            self.game.assets.get_sound("powerup").play()
        rect = self.card_rects[idx]
        spawn_sparks(self.particles, rect.centerx, rect.centery, (0, -40), color=(100, 255, 200), count=25)

    def update(self, dt):
        self.starfield.update(dt)
        self.particles.update(dt)
        self.timer += dt

    def draw(self, screen):
        screen.fill((8, 10, 24))
        self.starfield.draw(screen)
        self.particles.draw(screen)

        # Header
        title = self.game.assets.title_font.render("UPGRADE SHOP", True, (255, 210, 0))
        screen.blit(title, title.get_rect(center=(self.game.width // 2, 58)))

        sub = self.game.assets.hud_font.render(
            f"Level {self.cleared_level} Cleared   •   Available Budget: {self.score} PTS",
            True, (190, 220, 250)
        )
        screen.blit(sub, sub.get_rect(center=(self.game.width // 2, 105)))

        for i, (offer, base_rect) in enumerate(zip(self.offers, self.card_rects)):
            bought = i in self.purchased
            hovered = (self.hovered == i)
            can_afford = (self.score >= offer["cost"])

            # Hover micro-animation: smooth lift offset
            rect = base_rect.copy()
            if hovered and not bought:
                rect.move_ip(0, -4)

            # Card background colors
            if bought:
                fill = (18, 55, 30)
                border = (80, 220, 110)
            elif not can_afford:
                fill = (24, 25, 35)
                border = (60, 65, 80)
            elif hovered:
                fill = (25, 52, 85)
                border = (0, 240, 255)
            else:
                fill = (18, 30, 50)
                border = (70, 110, 160)

            card = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
            card.fill((0, 0, 0, 0))
            pg.draw.rect(card, (*fill, 230), card.get_rect(), border_radius=14)
            pg.draw.rect(card, (*border, 255), card.get_rect(), 2, border_radius=14)
            
            if hovered and not bought and can_afford:
                # Glowing neon inner aura
                glow = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
                pg.draw.rect(glow, (0, 230, 255, 22), glow.get_rect(), border_radius=14)
                card.blit(glow, (0, 0))
            screen.blit(card, rect)

            # Icon: Genuine Sprite Icon with procedural fallback
            sprite_alias = offer.get("sprite_alias", "")
            icon_img = None
            if hasattr(self.game, "assets"):
                icon_img = self.game.assets.get_image(sprite_alias)
            
            icon_center = (rect.x + 38, rect.y + 36)
            # Glowing backing circle for icon
            pg.draw.circle(screen, (*fill[:3], 255), icon_center, 22)
            pg.draw.circle(screen, border, icon_center, 22, 2)

            if icon_img:
                scaled_icon = pg.transform.smoothscale(icon_img, (32, 32))
                icon_rect = scaled_icon.get_rect(center=icon_center)
                screen.blit(scaled_icon, icon_rect)
            else:
                fallback_color = offer.get("fallback_color", (0, 200, 255))
                pg.draw.circle(screen, fallback_color, icon_center, 12)

            # Upgrade Title
            name_color = (200, 255, 210) if bought else ((255, 255, 255) if can_afford else (120, 125, 140))
            name_surf = self.game.assets.font.render(offer["name"], True, name_color)
            screen.blit(name_surf, (rect.x + 68, rect.y + 24))

            # Divider line separating header from description
            pg.draw.line(screen, (*border[:3], 80), (rect.x + 16, rect.y + 66), (rect.x + rect.width - 16, rect.y + 66), 1)

            # Description (word-wrapped cleanly across lines)
            words = offer["desc"].split()
            desc_lines = []
            curr_line = []
            for w in words:
                curr_line.append(w)
                t_surf = self.game.assets.hud_font.render(" ".join(curr_line), True, (160, 185, 210))
                if t_surf.get_width() > rect.width - 36:
                    curr_line.pop()
                    desc_lines.append(" ".join(curr_line))
                    curr_line = [w]
            if curr_line:
                desc_lines.append(" ".join(curr_line))

            for line_idx, line_text in enumerate(desc_lines):
                d_surf = self.game.assets.hud_font.render(
                    line_text, True, (150, 175, 200) if not bought else (130, 180, 150)
                )
                screen.blit(d_surf, (rect.x + 18, rect.y + 80 + line_idx * 22))

            # Isolated Bottom Action / Status Button Container
            btn_rect = pg.Rect(rect.x + 16, rect.y + rect.height - 62, rect.width - 32, 46)
            btn_panel = pg.Surface((btn_rect.width, btn_rect.height), pg.SRCALPHA)
            btn_panel.fill((0, 0, 0, 0))

            if bought:
                btn_panel.fill((20, 70, 35, 230))
                pg.draw.rect(btn_panel, (80, 220, 110, 255), btn_panel.get_rect(), 2, border_radius=8)
                txt = self.game.assets.font.render("✓ INSTALLED", True, (120, 255, 160))
                btn_panel.blit(txt, txt.get_rect(center=(btn_rect.width // 2, btn_rect.height // 2)))
            elif can_afford:
                if hovered:
                    btn_panel.fill((0, 170, 220, 240))
                    pg.draw.rect(btn_panel, (200, 255, 255, 255), btn_panel.get_rect(), 2, border_radius=8)
                    txt = self.game.assets.font.render(f"⚡ BUY ({offer['cost']} PTS)", True, (10, 25, 40))
                    btn_panel.blit(txt, txt.get_rect(center=(btn_rect.width // 2, btn_rect.height // 2)))
                else:
                    btn_panel.fill((22, 45, 75, 220))
                    pg.draw.rect(btn_panel, (0, 220, 255, 200), btn_panel.get_rect(), 2, border_radius=8)
                    txt = self.game.assets.font.render(f"⚡ COST: {offer['cost']} PTS", True, (255, 215, 60))
                    btn_panel.blit(txt, txt.get_rect(center=(btn_rect.width // 2, btn_rect.height // 2)))
            else:
                btn_panel.fill((30, 20, 28, 200))
                pg.draw.rect(btn_panel, (120, 60, 70, 180), btn_panel.get_rect(), 1, border_radius=8)
                txt = self.game.assets.font.render(f"🔒 {offer['cost']} PTS (LOCKED)", True, (200, 110, 120))
                btn_panel.blit(txt, txt.get_rect(center=(btn_rect.width // 2, btn_rect.height // 2)))

            screen.blit(btn_panel, btn_rect)

        # Skip / Continue button
        _draw_ui_button(
            screen, self.skip_rect, "CONTINUE →",
            self.game.assets.font,
            hovered=self.skip_hovered,
            fill=(30, 40, 58, 220),
            border=(180, 180, 200, 255) if self.skip_hovered else (100, 110, 140, 255),
            text_color=(210, 225, 245),
            pulse=self.timer * 8,
        )


class LevelCompleteState(State):
    """Short congratulation popup shown immediately after a level clears."""
    def __init__(self, game, score, cleared_level):
        super().__init__(game)
        self.score = score
        self.cleared_level = int(cleared_level)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=100)
        self.timer = 0.0
        self.continue_rect = pg.Rect(self.game.width // 2 - 150, self.game.height - 120, 300, 50)
        self.continue_hovered = False
        self.transition_locked = False

    def _continue(self):
        if self.transition_locked:
            return
        self.transition_locked = True
        self.game.change_state(ShopState(self.game, self.score, self.cleared_level))

    def handle_events(self, events):
        if self.transition_locked:
            return
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.continue_hovered = self.continue_rect.collidepoint(event.pos)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.continue_rect.collidepoint(event.pos):
                    self._continue()

    def update(self, dt):
        self.starfield.update(dt)
        self.timer += dt

    def draw(self, screen):
        screen.fill((8, 10, 24))
        self.starfield.draw(screen)

        title = self.game.assets.title_font.render("CONGRATULATIONS", True, (0, 255, 180))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 4))
        screen.blit(title, title_rect)

        level_text = self.game.assets.hud_font.render(f"LEVEL {self.cleared_level} CLEARED", True, (255, 210, 110))
        level_rect = level_text.get_rect(center=(self.game.width // 2, self.game.height // 3 + 20))
        screen.blit(level_text, level_rect)

        score_text = self.game.assets.font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.game.width // 2, self.game.height // 3 + 70))
        screen.blit(score_text, score_rect)

        _draw_ui_button(
            screen,
            self.continue_rect,
            "CONTINUE TO SHOP",
            self.game.assets.font,
            hovered=self.continue_hovered,
            fill=(20, 70, 90, 220),
            border=(0, 255, 255, 255) if self.continue_hovered else (90, 150, 190, 255),
            text_color=(240, 250, 255),
            pulse=self.timer * 8,
        )


class GameCompleteState(State):
    """
    Sprint 2 — Victory screen shown when the player beats all 10 levels.
    """
    def __init__(self, game, score):
        super().__init__(game)
        self.score = score
        self.save_system = SaveSystem()
        self.starfield   = Starfield(self.game.width, self.game.height, num_stars=150)
        self.timer       = 0.0   # Used for animation
        self.continue_rect = pg.Rect(self.game.width // 2 - 150, self.game.height - 120, 300, 50)
        self.continue_hovered = False
        self.transition_locked = False

    def _finalize(self):
        if self.transition_locked:
            return
        self.transition_locked = True
        self.save_system.save_score("VICTOR", self.score)
        self.game.change_state(HighScoresState(self.game))

    def handle_events(self, events):
        if self.transition_locked:
            return
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.continue_hovered = self.continue_rect.collidepoint(event.pos)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.continue_rect.collidepoint(event.pos):
                    self._finalize()

    def update(self, dt):
        self.starfield.update(dt)
        self.timer += dt

    def draw(self, screen):
        screen.fill((5, 8, 18))
        self.starfield.draw(screen)

        # Pulsing golden title
        pulse = int(200 + 55 * math.sin(self.timer * 3))
        title_color = (pulse, int(pulse * 0.85), 0)
        title = self.game.assets.title_font.render("MISSION COMPLETE", True, title_color)
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 4))
        screen.blit(title, title_rect)

        sub = self.game.assets.hud_font.render("You have defeated all 10 levels!", True, (0, 255, 200))
        sub_rect = sub.get_rect(center=(self.game.width // 2, self.game.height // 4 + 60))
        screen.blit(sub, sub_rect)

        score_surf = self.game.assets.font.render(f"Final Score: {self.score}", True, (255, 255, 255))
        score_rect = score_surf.get_rect(center=(self.game.width // 2, self.game.height // 2))
        screen.blit(score_surf, score_rect)

        _draw_ui_button(
            screen,
            self.continue_rect,
            "VIEW LEADERBOARD",
            self.game.assets.font,
            hovered=self.continue_hovered,
            fill=(26, 40, 52, 220),
            border=(255, 210, 70, 255) if self.continue_hovered else (180, 150, 60, 255),
            text_color=(255, 240, 200),
            pulse=self.timer * 8,
        )


class HighScoresState(State):
    """State representing the Top-10 Leaderboard listing loaded from SaveSystem."""
    def __init__(self, game):
        super().__init__(game)
        self.save_system = SaveSystem()
        self.scores_list = self.save_system.load_scores()
        self.back_rect = pg.Rect(40, 40, 120, 48)
        self.back_hovered = False
        self.anim_timer = 0.0

    def handle_events(self, events):
        """Allows returning back to the Main Menu with mouse or keyboard."""
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.back_hovered = self.back_rect.collidepoint(event.pos)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_rect.collidepoint(event.pos):
                    self.game.change_state(MenuState(self.game))
                    return
            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_RETURN):
                    self.game.change_state(MenuState(self.game))

    def update(self, dt):
        self.anim_timer += dt

    def draw(self, screen):
        # Cosmic dark blue fill
        screen.fill((10, 12, 22))
        
        # Leaderboard Title
        title = self.game.assets.title_font.render("HIGH SCORES", True, (0, 200, 255))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 6))
        screen.blit(title, title_rect)

        _draw_ui_button(
            screen,
            self.back_rect,
            "← MENU",
            self.game.assets.font,
            hovered=self.back_hovered,
            fill=(30, 40, 58, 190),
            border=(90, 140, 180, 255) if self.back_hovered else (90, 120, 150, 255),
            text_color=(190, 210, 220),
            pulse=self.anim_timer * 8,
        )
        
        # Draw high scores in a formatted 3-column table
        for idx, item in enumerate(self.scores_list[:10]):
            rank  = f"{idx+1}."
            name  = item.get("name", "PILOT")
            score = str(item.get("score", 0))
            
            # Gold color for 1st place, silver-cyan for top 3, muted grey for rest
            color = (255, 220, 0) if idx == 0 else ((200, 220, 240) if idx < 3 else (130, 150, 170))
            
            rank_surf  = self.game.assets.font.render(rank,  True, color)
            name_surf  = self.game.assets.font.render(name,  True, color)
            score_surf = self.game.assets.font.render(score, True, color)
            
            # Beautiful horizontal spacing alignments (Rank left, Name center, Score right)
            y_pos = self.game.height // 3.2 + idx * 36
            screen.blit(rank_surf,  (self.game.width // 2 - 180, y_pos))
            screen.blit(name_surf,  (self.game.width // 2 -  80, y_pos))
            screen.blit(score_surf, (self.game.width // 2 + 100, y_pos))
