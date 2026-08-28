# pyrefly: ignore [missing-import]
import pygame as pg
import random
import math
from sprites import Player, Enemy, Laser, Boss, PowerUp, Missile, Asteroid
from fx import Starfield, spawn_explosion, spawn_sparks
from save_system import SaveSystem
from level_system import LevelSystem, get_theater
from world.environment import SpaceEnvironment
from render.camera import Camera
from render.pipeline import RenderPipeline
from ui.hud import HUD


from ui.tooltip import UITooltipManager


def _draw_ui_button(screen, rect, label, font, *, hovered=False, pressed=False,
                    fill=(22, 34, 56, 220), border=(90, 120, 150, 255),
                    text_color=(240, 240, 240), pulse=0.0, danger=False):
    """Shared helper for consistent, mouse-friendly arcade buttons with spring hover scale & cyan glow.

    Supports danger=True for crimson/ruby red highlight feedback on destructive actions.
    """
    draw_rect = rect.inflate(6, 4) if (hovered and not pressed) else rect.copy()
    if pressed:
        draw_rect = rect.inflate(-2, -2)

    panel = pg.Surface((draw_rect.width, draw_rect.height), pg.SRCALPHA)
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
        fill_r = min(255, fill_r + 28)
        fill_g = min(255, fill_g + 50)
        fill_b = min(255, fill_b + 60)
        border = (0, 255, 220, 255)
        fill = (fill_r, fill_g, fill_b, fill_a)
        text_color = (120, 255, 255)
    elif pressed:
        fill_r, fill_g, fill_b, fill_a = fill
        border_r, border_g, border_b, border_a = border
        fill_r = max(0, fill_r - 14)
        fill_g = max(0, fill_g - 12)
        fill_b = max(0, fill_b - 18)
        border = (180, 255, 255, 255)
        fill = (fill_r, fill_g, fill_b, fill_a)

    fill_r, fill_g, fill_b, fill_a = fill
    border_r, border_g, border_b, border_a = border
    pulse_alpha = int(fill_a + (24 * math.sin(pulse) if pulse else 0))
    panel.fill((fill_r, fill_g, fill_b, max(0, min(255, pulse_alpha))))
    pg.draw.rect(panel, (border_r, border_g, border_b, border_a), panel.get_rect(), 2, border_radius=10)

    # Hover glowing accent chevrons on corners
    if hovered:
        pw, ph = draw_rect.width, draw_rect.height
        accent_c = (0, 255, 220, 255) if not danger else (255, 80, 100, 255)
        pg.draw.line(panel, accent_c, (6, 6), (14, 6), 2)
        pg.draw.line(panel, accent_c, (6, 6), (6, 14), 2)
        pg.draw.line(panel, accent_c, (pw - 6, ph - 6), (pw - 14, ph - 6), 2)
        pg.draw.line(panel, accent_c, (pw - 6, ph - 6), (pw - 6, ph - 14), 2)

    screen.blit(panel, draw_rect)

    # Shadow text
    shadow_surf = font.render(label, True, (10, 12, 20))
    shadow_rect = shadow_surf.get_rect(center=(draw_rect.centerx + 1, draw_rect.centery + 1))
    screen.blit(shadow_surf, shadow_rect)

    label_surf = font.render(label, True, text_color)
    label_rect = label_surf.get_rect(center=draw_rect.center)
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
    
    Provides option selection (Play, Hangar, Options, Flight Manual, High Scores, Quit),
    animated starfield, InputMap integration, and rich UI feedback.
    """
    def __init__(self, game):
        super().__init__(game)
        # Parallax background with 80 stars for the menu
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=80)
        self.anim_timer = 0.0
        self.click_timer = 0.0
        self.pending_action_idx = None
        
        # Render the menu title with a nice neon-cyan color
        self.title_text = self.game.assets.title_font.render("SPACE SHOOTERS", True, (0, 255, 200))
        self.title_rect = self.title_text.get_rect(center=(self.game.width // 2, self.game.height // 3.4))
        
        # Available choices and navigation cursor index
        self.options = ["Play Game", "Hangar / Ships", "Options", "Flight Manual", "High Scores", "Quit"]
        self.selected_index = 0
        self.hovered_index = None
        self.buttons = []
        self._build_buttons()

        # Tooltips for options
        self.tooltips = [
            ("PLAY CAMPAIGN", "Launch the 10-level campaign with increasing difficulty and mothership bosses."),
            ("SHIP HANGAR", "Customize ship hull (Interceptor, Cruiser, Vanguard) and laser plasma color loadouts."),
            ("SYSTEM OPTIONS", "Adjust audio volumes, screen shake, bloom, hitmarkers, and fullscreen toggles."),
            ("FLIGHT MANUAL", "Review weapon upgrades, power-up types, controls, and enemy fleet intel."),
            ("HALL OF FAME", "View local top-10 high scores and pilot loadout achievements."),
            ("QUIT GAME", "Safely exit the Space Shooters application to desktop.")
        ]
        
        # Play menu music bed
        if hasattr(self.game, "audio"):
            self.game.audio.play_music("menu")

    def _build_buttons(self):
        self.buttons = []
        for idx, option in enumerate(self.options):
            rect = pg.Rect(self.game.width // 2 - 170, int(self.game.height * 0.38) + idx * 50, 340, 42)
            self.buttons.append({"label": option, "rect": rect})

    def handle_events(self, events):
        """Navigates options using InputMap actions or mouse clicks."""
        prev_sel = self.selected_index

        for event in events:
            if event.type == pg.MOUSEMOTION:
                mouse_hover = None
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        mouse_hover = idx
                        break
                if mouse_hover != self.hovered_index:
                    self.hovered_index = mouse_hover
                    if mouse_hover is not None:
                        self.selected_index = mouse_hover
                        if prev_sel != mouse_hover:
                            self.game.audio.play_ui_hover()

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        self.selected_index = idx
                        self.pending_action_idx = idx
                        self.click_timer = 0.08
                        self.game.audio.play_ui_click()
                        return

        # Device-agnostic InputMap navigation (Keyboard / Gamepad)
        if self.game.input.is_pressed("up"):
            self.selected_index = (self.selected_index - 1) % len(self.options)
            self.hovered_index = None
            self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.buttons[self.selected_index]["rect"].centerx, self.buttons[self.selected_index]["rect"].centery)

        elif self.game.input.is_pressed("down"):
            self.selected_index = (self.selected_index + 1) % len(self.options)
            self.hovered_index = None
            self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.buttons[self.selected_index]["rect"].centerx, self.buttons[self.selected_index]["rect"].centery)

        elif self.game.input.is_pressed("confirm"):
            self.pending_action_idx = self.selected_index
            self.click_timer = 0.08
            self.game.audio.play_ui_click()

    def _select_option(self, idx=None):
        """Executes the action corresponding to the highlighted option."""
        idx = self.selected_index if idx is None else idx
        if idx == 0:
            self.game.change_state(LevelSelectState(self.game))
        elif idx == 1:
            self.game.change_state(HangarState(self.game, return_state="menu"))
        elif idx == 2:
            self.game.change_state(OptionsState(self.game, return_state=self))
        elif idx == 3:
            self.game.change_state(InstructionsState(self.game))
        elif idx == 4:
            self.game.change_state(HighScoresState(self.game))
        elif idx == 5:
            self.game.quit()

    def update(self, dt):
        """Scroll background stars, update click delay timers, and update cursor hover states."""
        self.starfield.update(dt)
        self.anim_timer += dt

        if self.click_timer > 0:
            self.click_timer -= dt
            if self.click_timer <= 0 and self.pending_action_idx is not None:
                action_idx = self.pending_action_idx
                self.pending_action_idx = None
                self._select_option(action_idx)

        # Update cursor hover state
        is_any_hovered = (self.hovered_index is not None) or (self.selected_index is not None)
        self.game.cursor.set_hover_state(is_any_hovered)

        # Update tooltips
        active_idx = self.hovered_index if self.hovered_index is not None else self.selected_index
        if 0 <= active_idx < len(self.tooltips):
            title, body = self.tooltips[active_idx]
            rect = self.buttons[active_idx]["rect"]
            self.game.tooltip.set_tooltip(title, body, (rect.right, rect.top))

    def draw(self, screen):
        screen.fill((10, 12, 22))
        self.starfield.draw(screen)
        
        # Draw Title with neon teal glow
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
            is_pressed = (self.pending_action_idx == idx and self.click_timer > 0)
            is_danger = (option.lower() == "quit")

            _draw_ui_button(
                screen,
                rect,
                option,
                self.game.assets.font,
                hovered=is_hovered or is_sel,
                pressed=is_pressed,
                pulse=self.anim_timer * 8 + idx,
                danger=is_danger,
            )



class InstructionsState(State):
    """
    Sprint 9 & 12 — Tabbed Field Manual & Game Mechanics Guide.
    
    Provides interactive 4-tab breakdown ([CONTROLS], [WEAPONS], [POWER-UPS], [ARMADA / ENEMIES])
    with live sprite icons, InputMap navigation, and auditory feedback.
    """
    def __init__(self, game):
        super().__init__(game)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=90)
        self.anim_timer = 0.0
        self.back_rect = pg.Rect(40, 30, 130, 44)
        self.back_hovered = False

        self.tabs = ["CONTROLS", "WEAPONS", "POWER-UPS", "ARMADA"]
        self.active_tab = 0
        self.tab_rects = []
        self.tab_hovered = None

        # Build tab button rects
        tab_w, tab_h = 220, 38
        start_x = (self.game.width - (4 * tab_w + 3 * 16)) // 2
        for i, tab_name in enumerate(self.tabs):
            self.tab_rects.append(pg.Rect(start_x + i * (tab_w + 16), 115, tab_w, tab_h))

        # Content categories
        self.content_data = {
            0: [ # CONTROLS
                {"title": "FLIGHT VECTORING", "tag": "WASD / ARROWS / DPAD", "color": (0, 240, 255), "desc": "Omnidirectional vector thrusters with subtle inertia banking. Boundary barriers contain your fighter securely inside the theater."},
                {"title": "PRIMARY FIRE", "tag": "SPACEBAR / BUTTON A", "color": (100, 190, 255), "desc": "Fires concentrated energy bolts. Hold for continuous auto-fire. Weapon power scales with campaign level and shop upgrades."},
                {"title": "HOMING MISSILES", "tag": "M KEY / BUTTON Y", "color": (255, 140, 40), "desc": "Launches acoustic warheads that seek the highest-health target on screen, dealing 30 area-of-effect explosive damage."},
                {"title": "PAUSE & OPTIONS", "tag": "ESC / P KEY / START", "color": (255, 200, 50), "desc": "Pauses flight, brings up real-time battle telemetry statistics, and allows on-the-fly volume and graphics adjustments."},
            ],
            1: [ # WEAPONS
                {"title": "TIER-1 PLASMA BLASTER", "tag": "LEVELS 1 - 3", "color": (0, 240, 255), "desc": "Standard blue energy bolts dealing 10 base damage per shot.", "img": "laser"},
                {"title": "TIER-2 CRIMSON CANNON", "tag": "LEVELS 4 - 6", "color": (255, 80, 80), "desc": "Heavy crimson plasma beams dealing 15 damage with increased hit radius.", "img": "laser_power"},
                {"title": "TIER-3 VOID LANCE", "tag": "LEVELS 7 - 10", "color": (200, 80, 255), "desc": "Piercing purple void beams dealing 20 damage that cut through enemy armor.", "img": "laser_power"},
                {"title": "ACOUSTIC MISSILE", "tag": "SPECIAL WEAPON", "color": (255, 140, 40), "desc": "Steerable self-guided warhead with 450 px/s speed and 30 AoE damage.", "img": "missile"},
            ],
            2: [ # POWER-UPS
                {"title": "KINETIC SHIELD", "tag": "DEFENSE DROP", "color": (0, 240, 255), "desc": "Restores +40 barrier energy instantly to protect your hull from fatal breaches.", "img": "powerup_shield"},
                {"title": "TRIPLE SHOT", "tag": "WEAPON BOOST", "color": (255, 200, 40), "desc": "Fires 3 angled laser beams simultaneously for 12 seconds of screen coverage.", "img": "powerup_triple"},
                {"title": "SPEED BOOST", "tag": "ENGINES BOOST", "color": (50, 255, 120), "desc": "Increases thruster velocity and maneuvering agility for 12 seconds.", "img": "powerup_speed"},
                {"title": "POWER LASER", "tag": "OVERCHARGE", "color": (255, 60, 80), "desc": "Instantly upgrades shot tier and doubles damage output for 10 seconds.", "img": "powerup_power_laser"},
            ],
            3: [ # ARMADA
                {"title": "SCOUT RAIDER", "tag": "LIGHT FIGHTER", "color": (0, 255, 180), "desc": "Fast reconnaissance craft with sine-wave movement and rapid light lasers.", "img": "enemy_scout"},
                {"title": "STINGER INTERCEPTOR", "tag": "MEDIUM INTERCEPTOR", "color": (255, 180, 0), "desc": "Agile tactical interceptor that dives aggressively toward the player.", "img": "enemy_stinger"},
                {"title": "HEAVY CRUISER", "tag": "ELITE ARMORED", "color": (255, 70, 90), "desc": "High HP armored platform featuring telegraph chevrons and dual plasma volleys.", "img": "enemy_cruiser"},
                {"title": "CRIMSON MOTHERSHIP", "tag": "BOSS FLAGSHIP", "color": (255, 40, 60), "desc": "Multi-phase boss featuring high-density bullet hell patterns and energy shields.", "img": "boss"},
            ]
        }
        self.mechanics = [
            {"title": "FLIGHT CONTROLS", "tag": "WASD / ARROWS", "color": (0, 230, 255), "desc": "Full omnidirectional vector thrusters with inertial dampening. Boundary barriers keep your fighter securely within combat theater."},
            {"title": "PRIMARY PHOTON BLASTER", "tag": "SPACEBAR", "color": (100, 180, 255), "desc": "Rapid concentrated plasma bolts. Upgradeable with Triple Cannons, Faster Reload modules, and heavy piercing laser slugs."},
            {"title": "HOMING MISSILES", "tag": "M KEY", "color": (255, 130, 40), "desc": "Lock-on acoustic warheads that seek out the highest-threat enemy on screen, dealing massive area-of-effect explosive damage."},
            {"title": "KINETIC SHIELD BARRIER", "tag": "DEFENSE SYSTEM", "color": (0, 255, 200), "desc": "Absorbs 100% of projectile and collision impacts before hull breach. Restored via blue powerup orbs and persistent shop nanites."},
            {"title": "COMBO MULTIPLIER", "tag": "SCORE BOOST", "color": (255, 220, 50), "desc": "Chain rapid enemy takedowns before the decay timer expires to ramp up score multipliers up to x3.0. Taking damage breaks the chain."},
            {"title": "HAZARDS & MOTHERSHIPS", "tag": "COMBAT THREATS", "color": (255, 70, 90), "desc": "Asteroids fragment into dangerous shards upon impact. Boss motherships feature multiple phases and high-density projectile patterns."},
        ]
        self.cards = [{"rect": pg.Rect(0, 0, 100, 100), "data": c} for c in self.mechanics]



    def handle_events(self, events):
        prev_tab = self.active_tab

        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.back_hovered = self.back_rect.collidepoint(event.pos)
                mouse_tab = None
                for i, r in enumerate(self.tab_rects):
                    if r.collidepoint(event.pos):
                        mouse_tab = i
                        break
                if mouse_tab != self.tab_hovered:
                    self.tab_hovered = mouse_tab
                    if mouse_tab is not None:
                        self.game.audio.play_ui_hover()

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_rect.collidepoint(event.pos):
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui_back()
                    self.game.change_state(MenuState(self.game))
                    return
                for i, r in enumerate(self.tab_rects):
                    if r.collidepoint(event.pos):
                        self.active_tab = i
                        if hasattr(self.game, 'audio') and self.game.audio:
                            self.game.audio.play_ui_click()
                        return
            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_BACKSPACE):
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui_back()
                    self.game.change_state(MenuState(self.game))
                    return

        # InputMap action navigation
        inp = getattr(self.game, 'input', None)
        if inp:
            if inp.is_pressed("left"):
                self.active_tab = (self.active_tab - 1) % len(self.tabs)
                if hasattr(self.game, 'audio') and self.game.audio:
                    self.game.audio.play_ui_hover()
                cursor = getattr(self.game, 'cursor', None)
                if cursor:
                    cursor.snap_to(self.tab_rects[self.active_tab].centerx, self.tab_rects[self.active_tab].centery)

            elif inp.is_pressed("right"):
                self.active_tab = (self.active_tab + 1) % len(self.tabs)
                if hasattr(self.game, 'audio') and self.game.audio:
                    self.game.audio.play_ui_hover()
                cursor = getattr(self.game, 'cursor', None)
                if cursor:
                    cursor.snap_to(self.tab_rects[self.active_tab].centerx, self.tab_rects[self.active_tab].centery)

            elif inp.is_pressed("cancel"):
                if hasattr(self.game, 'audio') and self.game.audio:
                    self.game.audio.play_ui_back()
                self.game.change_state(MenuState(self.game))

    def update(self, dt):
        self.starfield.update(dt)
        self.anim_timer += dt

        is_hovered = self.back_hovered or (self.tab_hovered is not None)
        cursor = getattr(self.game, 'cursor', None)
        if cursor:
            cursor.set_hover_state(is_hovered)
        tooltip = getattr(self.game, 'tooltip', None)
        if tooltip:
            tooltip.clear()


    def draw(self, screen):
        screen.fill((10, 12, 22))
        self.starfield.draw(screen)

        # Header
        title = self.game.assets.title_font.render("FLIGHT MANUAL & INTEL", True, (0, 240, 255))
        screen.blit(title, title.get_rect(center=(self.game.width // 2, 44)))

        sub = self.game.assets.hud_font.render("COMPREHENSIVE TACTICAL GUIDE TO STARSHIP SYSTEMS, ARMAMENT & ARMADA INTEL", True, (160, 190, 220))
        screen.blit(sub, sub.get_rect(center=(self.game.width // 2, 80)))

        # Back button
        _draw_ui_button(
            screen,
            self.back_rect,
            "← MENU",
            self.game.assets.font,
            hovered=self.back_hovered,
            fill=(25, 36, 54, 220),
            border=(0, 220, 255, 255) if self.back_hovered else (90, 120, 150, 255),
            text_color=(200, 230, 255),
            pulse=self.anim_timer * 8,
        )

        # Render Tab Buttons
        for i, tab_name in enumerate(self.tabs):
            r = self.tab_rects[i]
            is_active = (i == self.active_tab)
            is_hov = (i == self.tab_hovered)

            fill = (24, 70, 96, 240) if is_active else ((20, 45, 68, 220) if is_hov else (14, 24, 40, 200))
            border = (0, 255, 220, 255) if (is_active or is_hov) else (80, 110, 140, 255)
            text_c = (0, 255, 220) if is_active else ((220, 245, 255) if is_hov else (160, 190, 215))

            _draw_ui_button(screen, r, tab_name, self.game.assets.font, hovered=is_hov or is_active, fill=fill, border=border, text_color=text_c)

        # Render 2x2 Grid Cards for Active Tab
        cards = self.content_data.get(self.active_tab, [])
        card_w, card_h = 560, 240
        gap_x, gap_y = 30, 20
        start_x = (self.game.width - (2 * card_w + gap_x)) // 2
        start_y = 175

        for idx, item in enumerate(cards):
            row = idx // 2
            col = idx % 2
            rect = pg.Rect(start_x + col * (card_w + gap_x), start_y + row * (card_h + gap_y), card_w, card_h)

            card_surf = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
            card_surf.fill((16, 24, 40, 225))
            theme_color = item["color"]
            pg.draw.rect(card_surf, (*theme_color, 180), card_surf.get_rect(), 2, border_radius=12)
            pg.draw.rect(card_surf, (*theme_color, 240), pg.Rect(0, 0, rect.width, 5), border_top_left_radius=12, border_top_right_radius=12)
            screen.blit(card_surf, rect)

            # Title
            t_surf = self.game.assets.font.render(item["title"], True, (255, 255, 255))
            screen.blit(t_surf, (rect.x + 18, rect.y + 16))

            # Tag Badge
            tag_surf = self.game.assets.hud_font.render(f" {item['tag']} ", True, theme_color)
            tag_bg = pg.Surface((tag_surf.get_width() + 8, tag_surf.get_height() + 4), pg.SRCALPHA)
            tag_bg.fill((*theme_color, 35))
            pg.draw.rect(tag_bg, (*theme_color, 120), tag_bg.get_rect(), 1, border_radius=4)
            screen.blit(tag_bg, (rect.x + 14, rect.y + 50))
            screen.blit(tag_surf, (rect.x + 18, rect.y + 52))

            # Optional Sprite Preview Icon
            img_key = item.get("img")
            if img_key and hasattr(self.game, 'assets'):
                icon_img = self.game.assets.get_image(img_key, 54, 54)
                if icon_img:
                    icon_bg = pg.Surface((64, 64), pg.SRCALPHA)
                    icon_bg.fill((10, 16, 28, 200))
                    pg.draw.rect(icon_bg, (*theme_color, 150), icon_bg.get_rect(), 1, border_radius=8)
                    icon_bg.blit(icon_img, icon_img.get_rect(center=(32, 32)))
                    screen.blit(icon_bg, (rect.right - 80, rect.y + 16))

            # Divider line
            pg.draw.line(screen, (*theme_color, 70), (rect.x + 18, rect.y + 88), (rect.x + rect.width - 18, rect.y + 88), 1)

            # Wrapped description text
            words = item["desc"].split()
            lines = []
            curr_line = []
            max_w = rect.width - 36
            for w in words:
                curr_line.append(w)
                rendered = self.game.assets.hud_font.render(" ".join(curr_line), True, (190, 215, 235))
                if rendered.get_width() > max_w:
                    curr_line.pop()
                    lines.append(" ".join(curr_line))
                    curr_line = [w]
            if curr_line:
                lines.append(" ".join(curr_line))

            for l_idx, l_str in enumerate(lines):
                l_surf = self.game.assets.hud_font.render(l_str, True, (190, 215, 235))
                screen.blit(l_surf, (rect.x + 18, rect.y + 102 + l_idx * 22))



# ---------------------------------------------------------------------------
# Sprint 11 / Pillar F — OptionsState (Audio, Visuals, Accessibility, Controls)
# ---------------------------------------------------------------------------
class OptionsState(State):
    """
    Sprint 11 / Pillar F — Full Studio Options Menu.

    Provides interactive options sliders and toggles:
    - Audio Buses: Music Volume, Combat SFX Volume, UI Chimes Volume
    - Visual & Accessibility: Screen Shake, Post-FX Bloom, Hitmarkers, Screen Flash
    - Display Mode: Fullscreen Toggle (F11)
    - Persists all configuration in settings.json
    - Seamlessly returns to caller (Main Menu or Pause State)
    """

    def __init__(self, game, return_state=None):
        super().__init__(game)
        self.return_state = return_state
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=70)
        self.anim_timer = 0.0

        # Load persisted settings
        self.save_system = getattr(self.game, 'save_system', SaveSystem())
        self.settings = self.save_system.load_settings()

        self.music_vol = float(self.settings.get("music_volume", 0.7))
        self.sfx_vol = float(self.settings.get("sfx_volume", 0.8))
        self.ui_vol = float(self.settings.get("ui_volume", 0.8))

        self.shake_enabled = float(self.settings.get("shake_intensity", 1.0)) > 0.1
        self.bloom_enabled = bool(self.settings.get("bloom", False))
        self.hitmarkers_enabled = bool(self.settings.get("hitmarkers", True))
        self.fullscreen_enabled = bool(self.settings.get("fullscreen", False))
        self.screen_flash_enabled = bool(self.settings.get("screen_flash", True))

        # UI Geometry
        self.back_rect = pg.Rect(40, 40, 110, 46)
        self.back_hovered = False
        self.dragging_slider = None

        # Sliders: (x, y, w, h)
        cx = self.game.width // 2
        self.sliders = [
            {"id": "music", "label": "MUSIC VOLUME", "val": self.music_vol, "rect": pg.Rect(cx - 140, 170, 280, 24)},
            {"id": "sfx",   "label": "COMBAT SFX VOLUME", "val": self.sfx_vol,   "rect": pg.Rect(cx - 140, 230, 280, 24)},
            {"id": "ui",    "label": "UI AUDIO VOLUME",  "val": self.ui_vol,    "rect": pg.Rect(cx - 140, 290, 280, 24)},
        ]

        # Toggles
        self.toggles = [
            {"id": "shake",       "label": "SCREEN SHAKE",       "enabled": self.shake_enabled,       "rect": pg.Rect(cx - 210, 360, 200, 44)},
            {"id": "bloom",       "label": "BLOOM POST-FX",      "enabled": self.bloom_enabled,       "rect": pg.Rect(cx + 10,  360, 200, 44)},
            {"id": "hitmarkers",  "label": "HITMARKERS",         "enabled": self.hitmarkers_enabled,  "rect": pg.Rect(cx - 210, 420, 200, 44)},
            {"id": "screen_flash","label": "DAMAGE FLASH",       "enabled": self.screen_flash_enabled,"rect": pg.Rect(cx + 10,  420, 200, 44)},
            {"id": "fullscreen",  "label": "FULLSCREEN [F11]",   "enabled": self.fullscreen_enabled,  "rect": pg.Rect(cx - 100, 480, 200, 44)},
        ]

    def _apply_and_save(self):
        self.settings["music_volume"] = self.music_vol
        self.settings["sfx_volume"] = self.sfx_vol
        self.settings["ui_volume"] = self.ui_vol
        self.settings["shake_intensity"] = 1.0 if self.shake_enabled else 0.0
        self.settings["bloom"] = self.bloom_enabled
        self.settings["hitmarkers"] = self.hitmarkers_enabled
        self.settings["fullscreen"] = self.fullscreen_enabled
        self.settings["screen_flash"] = self.screen_flash_enabled

        self.save_system.save_settings(self.settings)

        # Apply to live subsystems
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.set_bus_volumes(music=self.music_vol, sfx=self.sfx_vol, ui=self.ui_vol)

    def _return(self):
        self._apply_and_save()
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_ui("confirm")
        if self.return_state:
            self.game.change_state(self.return_state)
        else:
            self.game.change_state(MenuState(self.game))

    def handle_events(self, events):
        for event in events:
            if event.type == pg.MOUSEMOTION:
                pos = event.pos
                self.back_hovered = self.back_rect.collidepoint(pos)

                # Slider dragging
                if self.dragging_slider:
                    for s in self.sliders:
                        if s["id"] == self.dragging_slider:
                            r = s["rect"]
                            rel_x = max(0, min(r.width, pos[0] - r.x))
                            s["val"] = rel_x / float(r.width)
                            if s["id"] == "music": self.music_vol = s["val"]
                            elif s["id"] == "sfx": self.sfx_vol = s["val"]
                            elif s["id"] == "ui": self.ui_vol = s["val"]
                            self._apply_and_save()
                            break

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.back_rect.collidepoint(pos):
                    self._return()
                    return

                # Sliders
                for s in self.sliders:
                    if s["rect"].collidepoint(pos):
                        self.dragging_slider = s["id"]
                        rel_x = max(0, min(s["rect"].width, pos[0] - s["rect"].x))
                        s["val"] = rel_x / float(s["rect"].width)
                        if s["id"] == "music": self.music_vol = s["val"]
                        elif s["id"] == "sfx": self.sfx_vol = s["val"]
                        elif s["id"] == "ui": self.ui_vol = s["val"]
                        if hasattr(self.game, 'audio') and self.game.audio:
                            self.game.audio.play_ui_slider()
                        self._apply_and_save()
                        return

                # Toggles
                for t in self.toggles:
                    if t["rect"].collidepoint(pos):
                        t["enabled"] = not t["enabled"]
                        if t["id"] == "shake": self.shake_enabled = t["enabled"]
                        elif t["id"] == "bloom": self.bloom_enabled = t["enabled"]
                        elif t["id"] == "hitmarkers": self.hitmarkers_enabled = t["enabled"]
                        elif t["id"] == "screen_flash": self.screen_flash_enabled = t["enabled"]
                        elif t["id"] == "fullscreen":
                            self.fullscreen_enabled = t["enabled"]
                            if hasattr(self.game, 'toggle_fullscreen'):
                                self.game.toggle_fullscreen()
                        if hasattr(self.game, 'audio') and self.game.audio:
                            self.game.audio.play_ui_toggle()
                        self._apply_and_save()
                        return

            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self.dragging_slider = None

        # InputMap navigation
        if self.game.input.is_pressed("cancel"):
            self._return()

    def update(self, dt):
        self.starfield.update(dt)
        self.anim_timer += dt

        pos = pg.mouse.get_pos()
        is_hovered = self.back_rect.collidepoint(pos) or any(s["rect"].collidepoint(pos) for s in self.sliders) or any(t["rect"].collidepoint(pos) for t in self.toggles)
        self.game.cursor.set_hover_state(is_hovered)
        self.game.tooltip.clear()


    def draw(self, screen):
        screen.fill((10, 13, 22))
        self.starfield.draw(screen)

        # Header Title
        title_surf = self.game.assets.title_font.render("SYSTEM OPTIONS", True, (0, 240, 255))
        screen.blit(title_surf, title_surf.get_rect(center=(self.game.width // 2, 60)))

        sub_header = self.game.assets.hud_font.render("AUDIO BUSES, VISUAL RIG & ACCESSIBILITY CONTROLS", True, (160, 200, 230))
        screen.blit(sub_header, sub_header.get_rect(center=(self.game.width // 2, 95)))

        # Back Button
        _draw_ui_button(
            screen,
            self.back_rect,
            "← BACK",
            self.game.assets.font,
            hovered=self.back_hovered,
            fill=(26, 36, 52, 190),
            border=(80, 120, 160, 255) if self.back_hovered else (60, 90, 130, 255),
            text_color=(190, 215, 235),
            pulse=self.anim_timer * 6,
        )

        # ---------------- SLIDERS ----------------
        for s in self.sliders:
            r = s["rect"]
            label_surf = self.game.assets.hud_font.render(s["label"], True, (200, 230, 255))
            screen.blit(label_surf, (r.x, r.y - 20))

            val_pct = int(s["val"] * 100)
            val_surf = self.game.assets.hud_font.render(f"{val_pct}%", True, (0, 240, 255))
            screen.blit(val_surf, (r.right - val_surf.get_width(), r.y - 20))

            # Track
            pg.draw.rect(screen, (30, 40, 58), r, border_radius=6)
            pg.draw.rect(screen, (70, 100, 140), r, 1, border_radius=6)

            # Fill
            fill_w = int(r.width * s["val"])
            if fill_w > 0:
                pg.draw.rect(screen, (0, 200, 240), (r.x, r.y, fill_w, r.height), border_radius=6)

            # Handle Knob
            knob_x = r.x + fill_w
            pg.draw.circle(screen, (255, 255, 255), (knob_x, r.centery), 10)
            pg.draw.circle(screen, (0, 240, 255), (knob_x, r.centery), 10, width=2)

        # ---------------- TOGGLES ----------------
        for t in self.toggles:
            r = t["rect"]
            is_hov = r.collidepoint(pg.mouse.get_pos())
            en = t["enabled"]

            fill = (22, 60, 42, 220) if en else (36, 38, 48, 190)
            border = (80, 255, 140, 255) if en else ((120, 130, 150, 220) if is_hov else (70, 75, 90, 200))
            text_color = (220, 255, 235) if en else ((200, 210, 225) if is_hov else (150, 160, 175))

            panel = pg.Surface((r.width, r.height), pg.SRCALPHA)
            pg.draw.rect(panel, fill, panel.get_rect(), border_radius=8)
            pg.draw.rect(panel, border, panel.get_rect(), 2 if en else 1, border_radius=8)
            screen.blit(panel, r)

            tag = "ON" if en else "OFF"
            lbl = self.game.assets.hud_font.render(f"{t['label']}: {tag}", True, text_color)
            screen.blit(lbl, lbl.get_rect(center=r.center))

        # Controls reference card at bottom
        ctrl_rect = pg.Rect(self.game.width // 2 - 320, 545, 640, 115)
        ctrl_panel = pg.Surface((ctrl_rect.width, ctrl_rect.height), pg.SRCALPHA)
        pg.draw.rect(ctrl_panel, (18, 26, 42, 220), ctrl_panel.get_rect(), border_radius=10)
        pg.draw.rect(ctrl_panel, (60, 90, 130, 180), ctrl_panel.get_rect(), 1, border_radius=10)
        screen.blit(ctrl_panel, ctrl_rect)

        ctrl_title = self.game.assets.hud_font.render("PILOT FLIGHT CONTROLS & GAMEPAD INPUT", True, (0, 240, 255))
        screen.blit(ctrl_title, (ctrl_rect.x + 20, ctrl_rect.y + 12))

        lines = [
            "KEYBOARD: W/A/S/D or Arrows (Flight)  •  SPACE / J (Cannons)  •  M (Missile)  •  P / Esc (Pause)",
            "GAMEPAD: Left Stick / D-Pad (Flight)   •  A / Cross (Fire)       •  RB (Missile) •  Start (Pause)",
            "ACCESSIBILITY: Toggle Screen Shake & Damage Flash anytime for custom comfort levels."
        ]
        for idx, line in enumerate(lines):
            l_surf = self.game.assets.hud_font.render(line, True, (170, 195, 225))
            screen.blit(l_surf, (ctrl_rect.x + 20, ctrl_rect.y + 40 + idx * 22))



# ---------------------------------------------------------------------------
# Sprint 11 / Pillar E — HangarState (Living Shipyard & Loadout Identity)
# ---------------------------------------------------------------------------
class HangarState(State):
    """
    Sprint 11 / Pillar E — Hangar Identity (The Missing Metagame Fantasy).

    Provides an interactive shipyard bay to select and customize ships:
    - 3 Hull Classes: Interceptor (Balanced), Heavy Cruiser (Assault/Tank), Stealth Vanguard (Agile/Missile).
    - 4 Color Swatches: Blue, Green, Orange, Red.
    - Live ship preview: idle animated thruster plumes, gentle yaw banking, sparkle bursts, nameplate in Audiowide.
    - Modular shipyard greeble backdrop.
    - Saves selection to settings.json and synchronizes with Game and PlayState.
    """

    HULLS = [
        {
            "id": "interceptor",
            "name": "STRIKE INTERCEPTOR",
            "role": "Balanced Air Superiority",
            "speed": "400 PX/S",
            "hp": "100 HP",
            "shield": "100 SH",
            "cooldown": "0.25s",
            "missiles": "3 Starting",
            "trait": "Agile turn radius, balanced fire rate & hull endurance.",
            "color_accent": (0, 220, 255),
        },
        {
            "id": "cruiser",
            "name": "HEAVY ASSAULT CRUISER",
            "role": "Armored Battlecruiser",
            "speed": "340 PX/S",
            "hp": "140 HP",
            "shield": "120 SH",
            "cooldown": "0.28s",
            "missiles": "3 Starting",
            "trait": "Dual-barrel wide volley, massive hull plating & shield pool.",
            "color_accent": (255, 140, 40),
        },
        {
            "id": "vanguard",
            "name": "STEALTH VANGUARD",
            "role": "High-Speed Interceptor / Bomber",
            "speed": "460 PX/S",
            "hp": "80 HP",
            "shield": "80 SH",
            "cooldown": "0.22s",
            "missiles": "4 Starting",
            "trait": "Hyper-velocity thrusters, rapid laser cycle, +1 bonus missile.",
            "color_accent": (160, 255, 120),
        },
    ]

    COLORS = [
        {"id": "blue",   "name": "Sapphire Blue", "swatch": (0, 180, 255)},
        {"id": "green",  "name": "Emerald Green", "swatch": (50, 230, 120)},
        {"id": "orange", "name": "Solar Orange",  "swatch": (255, 140, 20)},
        {"id": "red",    "name": "Crimson Red",   "swatch": (255, 60, 80)},
    ]

    def __init__(self, game, return_state="level_select"):
        super().__init__(game)
        self.return_state = return_state
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=70)
        self.anim_timer = 0.0

        # Load active loadout
        current = getattr(self.game, 'loadout', {"hull": "interceptor", "color": "blue"})
        curr_hull = current.get("hull", "interceptor")
        curr_color = current.get("color", "blue")

        self.selected_hull_idx = 0
        for i, h in enumerate(self.HULLS):
            if h["id"] == curr_hull:
                self.selected_hull_idx = i
                break

        self.selected_color_idx = 0
        for i, c in enumerate(self.COLORS):
            if c["id"] == curr_color:
                self.selected_color_idx = i
                break

        # Animated thruster plume sprites
        assets = self.game.assets
        self.thrusters = [
            assets.get_image(f"vfx_effects/thruster_plumes/thruster_flame_{index:02d}", 36, 52)
            for index in range(20)
        ]
        self.sparkle = assets.get_image("vfx_effects/sparkles/sparkle_stardust_medium", 32, 32)

        # Greebles on the hangar wall for modular shipyard aesthetics
        self.greebles = [
            {"name": "structural_beams/beam_metal_gray_01", "x": 60, "y": 80, "w": 40, "h": 220, "alpha": 65},
            {"name": "structural_beams/beam_metal_gray_02", "x": 1180, "y": 80, "w": 40, "h": 220, "alpha": 65},
            {"name": "structural_beams/beam_metal_gray_03", "x": 480, "y": 480, "w": 320, "h": 30, "alpha": 50},
            {"name": "engines/engine_thruster_01", "x": 100, "y": 490, "w": 48, "h": 48, "alpha": 55},
            {"name": "engines/engine_thruster_03", "x": 1130, "y": 490, "w": 48, "h": 48, "alpha": 55},
            {"name": "cannons_turrets/turret_dual_mount_01", "x": 180, "y": 520, "w": 36, "h": 36, "alpha": 45},
            {"name": "cannons_turrets/turret_dual_mount_02", "x": 1060, "y": 520, "w": 36, "h": 36, "alpha": 45},
        ]

        # Geometry & Interactive Buttons
        self.back_rect = pg.Rect(40, 40, 110, 46)
        self.back_hovered = False
        self.deploy_rect = pg.Rect(self.game.width - 200, 40, 160, 46)
        self.deploy_hovered = False

        # Hull selection tabs (Top middle)
        self.hull_rects = []
        tab_w = 260
        tab_gap = 20
        total_tab_w = len(self.HULLS) * tab_w + (len(self.HULLS) - 1) * tab_gap
        start_tab_x = (self.game.width - total_tab_w) // 2
        for i in range(len(self.HULLS)):
            self.hull_rects.append(pg.Rect(start_tab_x + i * (tab_w + tab_gap), 115, tab_w, 48))

        # Color swatches (Bottom center under live preview)
        self.swatch_rects = []
        swatch_w, swatch_h = 72, 42
        swatch_gap = 18
        total_swatch_w = len(self.COLORS) * swatch_w + (len(self.COLORS) - 1) * swatch_gap
        start_swatch_x = (self.game.width - total_swatch_w) // 2
        for i in range(len(self.COLORS)):
            self.swatch_rects.append(pg.Rect(start_swatch_x + i * (swatch_w + swatch_gap), 440, swatch_w, swatch_h))

        # Carousel arrow buttons
        self.prev_hull_rect = pg.Rect(self.game.width // 2 - 240, 275, 48, 64)
        self.next_hull_rect = pg.Rect(self.game.width // 2 + 192, 275, 48, 64)
        self.prev_hovered = False
        self.next_hovered = False

    def _save_and_sync(self):
        hull_id = self.HULLS[self.selected_hull_idx]["id"]
        color_id = self.COLORS[self.selected_color_idx]["id"]
        self.game.loadout = {"hull": hull_id, "color": color_id}
        if hasattr(self.game, 'save_system'):
            self.game.save_system.save_loadout(hull_id, color_id)

    def _proceed(self):
        self._save_and_sync()
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_ui("confirm")
        if self.return_state == "menu":
            self.game.change_state(MenuState(self.game))
        else:
            self.game.change_state(LevelSelectState(self.game))

    def handle_events(self, events):
        for event in events:
            if event.type == pg.MOUSEMOTION:
                pos = event.pos
                self.back_hovered = self.back_rect.collidepoint(pos)
                self.deploy_hovered = self.deploy_rect.collidepoint(pos)
                self.prev_hovered = self.prev_hull_rect.collidepoint(pos)
                self.next_hovered = self.next_hull_rect.collidepoint(pos)

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.back_rect.collidepoint(pos):
                    self._proceed()
                    return
                if self.deploy_rect.collidepoint(pos):
                    self._save_and_sync()
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui("confirm")
                    self.game.change_state(LevelSelectState(self.game))
                    return
                if self.prev_hull_rect.collidepoint(pos):
                    self.selected_hull_idx = (self.selected_hull_idx - 1) % len(self.HULLS)
                    self._save_and_sync()
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui("tick")
                    return
                if self.next_hull_rect.collidepoint(pos):
                    self.selected_hull_idx = (self.selected_hull_idx + 1) % len(self.HULLS)
                    self._save_and_sync()
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui("tick")
                    return

                # Hull tab click
                for i, r in enumerate(self.hull_rects):
                    if r.collidepoint(pos):
                        self.selected_hull_idx = i
                        self._save_and_sync()
                        if hasattr(self.game, 'audio') and self.game.audio:
                            self.game.audio.play_ui("tick")
                        return

                # Color swatch click
                for i, r in enumerate(self.swatch_rects):
                    if r.collidepoint(pos):
                        self.selected_color_idx = i
                        self._save_and_sync()
                        if hasattr(self.game, 'audio') and self.game.audio:
                            self.game.audio.play_ui("tick")
                        return

            elif event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_BACKSPACE):
                    self._proceed()
                elif event.key in (pg.K_RETURN, pg.K_SPACE):
                    self._proceed()

        # InputMap actions (Gamepad / Keyboard)
        if self.game.input.is_pressed("left"):
            self.selected_hull_idx = (self.selected_hull_idx - 1) % len(self.HULLS)
            self._save_and_sync()
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.hull_rects[self.selected_hull_idx].centerx, self.hull_rects[self.selected_hull_idx].centery)

        elif self.game.input.is_pressed("right"):
            self.selected_hull_idx = (self.selected_hull_idx + 1) % len(self.HULLS)
            self._save_and_sync()
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.hull_rects[self.selected_hull_idx].centerx, self.hull_rects[self.selected_hull_idx].centery)

        elif self.game.input.is_pressed("up") or self.game.input.is_pressed("down"):
            self.selected_color_idx = (self.selected_color_idx + 1) % len(self.COLORS)
            self._save_and_sync()
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()

        elif self.game.input.is_pressed("confirm"):
            self._proceed()

        elif self.game.input.is_pressed("cancel"):
            self.game.audio.play_ui_back()
            self._proceed()

    def update(self, dt):
        self.starfield.update(dt)
        self.anim_timer += dt

        pos = pg.mouse.get_pos()
        is_hovered = self.back_hovered or self.deploy_hovered or self.prev_hovered or self.next_hovered or any(r.collidepoint(pos) for r in self.hull_rects) or any(r.collidepoint(pos) for r in self.swatch_rects)
        cursor = getattr(self.game, 'cursor', None)
        if cursor:
            cursor.set_hover_state(is_hovered)
        tooltip = getattr(self.game, 'tooltip', None)
        if tooltip:
            tooltip.clear()


    def draw(self, screen):
        # Dark industrial hangar bay background
        screen.fill((10, 13, 22))
        self.starfield.draw(screen)

        # Draw structural greeble elements on the hangar wall
        for g in self.greebles:
            img = self.game.assets.get_image(f"modular_shipyard/{g['name']}", g["w"], g["h"])
            if img:
                temp = img.copy()
                temp.set_alpha(g.get("alpha", 50))
                screen.blit(temp, (g["x"], g["y"]))

        # Hangar Bay Landing Pad / Platform Glow
        pad_center = (self.game.width // 2, 305)
        pad_rect = pg.Rect(pad_center[0] - 170, pad_center[1] - 85, 340, 170)
        pad_surf = pg.Surface((pad_rect.width, pad_rect.height), pg.SRCALPHA)
        pg.draw.ellipse(pad_surf, (14, 28, 48, 160), pad_surf.get_rect())
        pg.draw.ellipse(pad_surf, (0, 200, 255, int(100 + 40 * math.sin(self.anim_timer * 3))), pad_surf.get_rect(), 2)
        # Inner staging ring
        inner_rect = pg.Rect(35, 20, pad_rect.width - 70, pad_rect.height - 40)
        pg.draw.ellipse(pad_surf, (0, 240, 255, int(60 + 20 * math.cos(self.anim_timer * 4))), inner_rect, 1)
        screen.blit(pad_surf, pad_rect)

        # Header Title in Audiowide Cyber Display
        title_surf = self.game.assets.title_font.render("SHIPYARD HANGAR", True, (0, 240, 255))
        screen.blit(title_surf, title_surf.get_rect(center=(self.game.width // 2, 55)))

        sub_header = self.game.assets.hud_font.render("SELECT HULL CHASSIS & FLIGHT PALETTE", True, (160, 200, 230))
        screen.blit(sub_header, sub_header.get_rect(center=(self.game.width // 2, 90)))

        # Header Navigation Buttons
        back_label = "← MENU" if self.return_state == "menu" else "← LEVELS"
        _draw_ui_button(
            screen,
            self.back_rect,
            back_label,
            self.game.assets.font,
            hovered=self.back_hovered,
            fill=(26, 36, 52, 190),
            border=(80, 120, 160, 255) if self.back_hovered else (60, 90, 130, 255),
            text_color=(190, 215, 235),
            pulse=self.anim_timer * 6,
        )

        _draw_ui_button(
            screen,
            self.deploy_rect,
            "CONFIRM ✓",
            self.game.assets.font,
            hovered=self.deploy_hovered,
            fill=(18, 75, 45, 220),
            border=(80, 255, 140, 255) if self.deploy_hovered else (40, 200, 100, 255),
            text_color=(220, 255, 230),
            pulse=self.anim_timer * 8,
        )

        # Hull Selection Tabs
        for i, (h, r) in enumerate(zip(self.HULLS, self.hull_rects)):
            is_sel = (i == self.selected_hull_idx)
            is_hov = r.collidepoint(pg.mouse.get_pos())
            fill = (22, 54, 82, 230) if is_sel else ((28, 38, 54, 180) if not is_hov else (34, 48, 70, 210))
            border = (0, 240, 255, 255) if is_sel else ((160, 210, 255, 200) if is_hov else (70, 95, 130, 200))
            text_color = (255, 255, 255) if is_sel else ((210, 235, 255) if is_hov else (150, 175, 200))

            panel = pg.Surface((r.width, r.height), pg.SRCALPHA)
            pg.draw.rect(panel, fill, panel.get_rect(), border_radius=8)
            pg.draw.rect(panel, border, panel.get_rect(), 2 if is_sel else 1, border_radius=8)
            screen.blit(panel, r)

            lbl = self.game.assets.font.render(h["name"].split()[0] + " " + h["name"].split()[1], True, text_color)
            screen.blit(lbl, lbl.get_rect(center=r.center))

        # Carousel Arrows
        _draw_ui_button(
            screen,
            self.prev_hull_rect,
            "◀",
            self.game.assets.title_font,
            hovered=self.prev_hovered,
            fill=(22, 38, 58, 200),
            border=(0, 240, 255, 255) if self.prev_hovered else (70, 110, 150, 200),
            text_color=(0, 240, 255) if self.prev_hovered else (180, 220, 255),
        )
        _draw_ui_button(
            screen,
            self.next_hull_rect,
            "▶",
            self.game.assets.title_font,
            hovered=self.next_hovered,
            fill=(22, 38, 58, 200),
            border=(0, 240, 255, 255) if self.next_hovered else (70, 110, 150, 200),
            text_color=(0, 240, 255) if self.next_hovered else (180, 220, 255),
        )

        # Active Hull & Color Data
        hull_data = self.HULLS[self.selected_hull_idx]
        color_data = self.COLORS[self.selected_color_idx]
        hull_id = hull_data["id"]
        color_id = color_data["id"]

        # ---------------- LIVE SHIP PREVIEW ----------------
        # Hull Sprite lookup
        ship_key = f"player_fleet/interceptor_strike_{color_id}"
        if hull_id == "cruiser":
            ship_key = f"player_fleet/heavy_cruiser_assault_{color_id}"
        elif hull_id == "vanguard":
            ship_key = f"player_fleet/stealth_vanguard_bomber_{color_id}"

        ship_img = self.game.assets.get_image(ship_key, 120, 120)

        # Gentle yaw/tilt animation
        tilt_angle = 3.5 * math.sin(self.anim_timer * 2.0)
        bob_offset = 5.0 * math.sin(self.anim_timer * 2.8)
        ship_center = (pad_center[0], pad_center[1] - 15 + int(bob_offset))

        if ship_img:
            rotated_ship = pg.transform.rotate(ship_img, tilt_angle)
            # Thruster Plume Animation below ship
            thruster_frame = int((self.anim_timer * 16) % len(self.thrusters))
            plume = self.thrusters[thruster_frame]
            plume_w, plume_h = 24, 40
            scaled_plume = pg.transform.smoothscale(plume, (plume_w, plume_h))

            # Position thrusters based on hull
            if hull_id == "cruiser":
                # Dual engines
                screen.blit(scaled_plume, (ship_center[0] - 28 - plume_w // 2, ship_center[1] + 36))
                screen.blit(scaled_plume, (ship_center[0] + 28 - plume_w // 2, ship_center[1] + 36))
            else:
                # Single center engine
                screen.blit(scaled_plume, (ship_center[0] - plume_w // 2, ship_center[1] + 38))

            ship_rect = rotated_ship.get_rect(center=ship_center)
            screen.blit(rotated_ship, ship_rect)

            # Sparkle bursts on the polished hull
            if int(self.anim_timer * 2.5) % 2 == 0:
                sp_x = ship_center[0] + int(24 * math.sin(self.anim_timer * 5))
                sp_y = ship_center[1] - 20 + int(14 * math.cos(self.anim_timer * 4))
                sp_alpha = int(120 + 80 * math.sin(self.anim_timer * 12))
                temp_sp = self.sparkle.copy()
                temp_sp.set_alpha(max(0, min(255, sp_alpha)))
                screen.blit(temp_sp, temp_sp.get_rect(center=(sp_x, sp_y)))

        # Ship Nameplate in Audiowide Cyber Display
        name_surf = self.game.assets.title_font.render(hull_data["name"], True, hull_data["color_accent"])
        screen.blit(name_surf, name_surf.get_rect(center=(self.game.width // 2, 388)))

        role_surf = self.game.assets.hud_font.render(hull_data["role"].upper(), True, (190, 220, 240))
        screen.blit(role_surf, role_surf.get_rect(center=(self.game.width // 2, 416)))

        # ---------------- COLOR SWATCHES ----------------
        for i, (c, r) in enumerate(zip(self.COLORS, self.swatch_rects)):
            is_sel = (i == self.selected_color_idx)
            is_hov = r.collidepoint(pg.mouse.get_pos())
            swatch_surf = pg.Surface((r.width, r.height), pg.SRCALPHA)
            pg.draw.rect(swatch_surf, (*c["swatch"], 220), swatch_surf.get_rect(), border_radius=6)
            if is_sel:
                pg.draw.rect(swatch_surf, (255, 255, 255), swatch_surf.get_rect(), 3, border_radius=6)
            elif is_hov:
                pg.draw.rect(swatch_surf, (220, 240, 255), swatch_surf.get_rect(), 2, border_radius=6)
            else:
                pg.draw.rect(swatch_surf, (20, 25, 35), swatch_surf.get_rect(), 1, border_radius=6)
            screen.blit(swatch_surf, r)

        color_label = self.game.assets.hud_font.render(f"PALETTE: {color_data['name'].upper()}", True, color_data["swatch"])
        screen.blit(color_label, color_label.get_rect(center=(self.game.width // 2, 496)))

        # ---------------- SPECIFICATION CARDS (LEFT & RIGHT PANELS) ----------------
        # Left Panel: Specifications
        spec_rect = pg.Rect(55, 520, 360, 165)
        spec_panel = pg.Surface((spec_rect.width, spec_rect.height), pg.SRCALPHA)
        pg.draw.rect(spec_panel, (18, 26, 40, 220), spec_panel.get_rect(), border_radius=10)
        pg.draw.rect(spec_panel, (60, 95, 140, 200), spec_panel.get_rect(), 2, border_radius=10)
        screen.blit(spec_panel, spec_rect)

        spec_header = self.game.assets.font.render("HULL SPECIFICATIONS", True, (0, 240, 255))
        screen.blit(spec_header, (spec_rect.x + 18, spec_rect.y + 12))

        specs = [
            ("TOP SPEED", hull_data["speed"], (120, 255, 200)),
            ("HULL INTEGRITY", hull_data["hp"], (255, 140, 140)),
            ("SHIELD MATRIX", hull_data["shield"], (100, 220, 255)),
            ("WEAPONS CADENCE", hull_data["cooldown"], (255, 220, 100)),
            ("ORDNANCE PAYLOAD", hull_data["missiles"], (255, 160, 60)),
        ]
        for idx, (label, val, col) in enumerate(specs):
            row_y = spec_rect.y + 40 + idx * 24
            l_surf = self.game.assets.hud_font.render(label, True, (160, 180, 205))
            v_surf = self.game.assets.hud_font.render(val, True, col)
            screen.blit(l_surf, (spec_rect.x + 18, row_y))
            screen.blit(v_surf, (spec_rect.right - 18 - v_surf.get_width(), row_y))

        # Right Panel: Tactical Combat Trait
        trait_rect = pg.Rect(self.game.width - 415, 520, 360, 165)
        trait_panel = pg.Surface((trait_rect.width, trait_rect.height), pg.SRCALPHA)
        pg.draw.rect(trait_panel, (18, 26, 40, 220), trait_panel.get_rect(), border_radius=10)
        pg.draw.rect(trait_panel, (60, 95, 140, 200), trait_panel.get_rect(), 2, border_radius=10)
        screen.blit(trait_panel, trait_rect)

        trait_header = self.game.assets.font.render("COMBAT CAPABILITY", True, (0, 240, 255))
        screen.blit(trait_header, (trait_rect.x + 18, trait_rect.y + 12))

        # Multi-line wrapped trait description
        words = hull_data["trait"].split()
        t_lines = []
        curr_l = []
        for w in words:
            curr_l.append(w)
            rendered = self.game.assets.hud_font.render(" ".join(curr_l), True, (190, 215, 240))
            if rendered.get_width() > trait_rect.width - 36:
                curr_l.pop()
                t_lines.append(" ".join(curr_l))
                curr_l = [w]
        if curr_l:
            t_lines.append(" ".join(curr_l))

        for line_idx, line_str in enumerate(t_lines):
            line_surf = self.game.assets.hud_font.render(line_str, True, (200, 225, 245))
            screen.blit(line_surf, (trait_rect.x + 18, trait_rect.y + 44 + line_idx * 24))

        # Persistent status notice at bottom center
        ready_tag = self.game.assets.hud_font.render("LOADOUT STORED IN SETTINGS.JSON — READY FOR FLIGHT", True, (140, 175, 210))
        screen.blit(ready_tag, ready_tag.get_rect(center=(self.game.width // 2, 695)))



class LevelSelectState(State):
    """Interactive campaign-level chooser with 3-star ratings, InputMap, and theater previews."""
    def __init__(self, game):
        super().__init__(game)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=100)
        self.save_system = getattr(self.game, 'save_system', SaveSystem())
        self.progress = self.save_system.load_progress()
        self.hovered_index = None
        self.selected_index = 0
        self.buttons = []
        self.blink_timer = 0.0
        self.back_rect = pg.Rect(40, 40, 110, 48)
        self.back_hovered = False
        self.hangar_rect = pg.Rect(self.game.width - 170, 40, 130, 48)
        self.hangar_hovered = False
        self._build_buttons()

        # Stop combat soundtracks when entering campaign screen
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_music("menu")

    def _build_buttons(self):
        self.buttons = []
        highest_unlocked = self.progress.get("highest_unlocked", 1)
        completed_levels = set(self.progress.get("completed_levels", []))
        stars_map = self.progress.get("level_stars", {})
        scores_map = self.progress.get("level_scores", {})

        for level_num in range(1, 11):
            row = (level_num - 1) // 5
            col = (level_num - 1) % 5
            x = 110 + col * 220
            y = 180 + row * 160
            rect = pg.Rect(x, y, 180, 110)
            is_unlocked = level_num <= highest_unlocked
            is_completed = level_num in completed_levels
            star_cnt = int(stars_map.get(str(level_num), 3 if is_completed else 0))
            best_sc = int(scores_map.get(str(level_num), 0))

            self.buttons.append({
                "level": level_num,
                "rect": rect,
                "unlocked": is_unlocked,
                "completed": is_completed,
                "stars": star_cnt,
                "best_score": best_sc,
            })

    def handle_events(self, events):
        prev_sel = self.selected_index

        for event in events:
            if event.type == pg.MOUSEMOTION:
                mouse_pos = event.pos
                self.back_hovered = self.back_rect.collidepoint(mouse_pos)
                self.hangar_hovered = self.hangar_rect.collidepoint(mouse_pos)
                mouse_hover = None
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(mouse_pos):
                        mouse_hover = idx
                        break
                if mouse_hover != self.hovered_index:
                    self.hovered_index = mouse_hover
                    if mouse_hover is not None:
                        self.selected_index = mouse_hover
                        if prev_sel != mouse_hover and hasattr(self.game, 'audio') and self.game.audio:
                            self.game.audio.play_ui_hover()

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if self.back_rect.collidepoint(mouse_pos):
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui_back()
                    self.game.change_state(MenuState(self.game))
                    return
                if self.hangar_rect.collidepoint(mouse_pos):
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui_click()
                    self.game.change_state(HangarState(self.game, return_state="level_select"))
                    return
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(mouse_pos):
                        self.selected_index = idx
                        self._launch_level(button["level"])
                        return

        # InputMap 2D Grid navigation
        if self.game.input.is_pressed("up"):
            self._move_selection(-5)
        elif self.game.input.is_pressed("down"):
            self._move_selection(5)
        elif self.game.input.is_pressed("left"):
            self._move_selection(-1)
        elif self.game.input.is_pressed("right"):
            self._move_selection(1)
        elif self.game.input.is_pressed("confirm"):
            level_num = self.buttons[self.selected_index]["level"]
            if self.buttons[self.selected_index]["unlocked"]:
                self._launch_level(level_num)
        elif self.game.input.is_pressed("cancel"):
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_back()
            self.game.change_state(MenuState(self.game))

    def _move_selection(self, delta):
        next_idx = self.selected_index + delta
        if 0 <= next_idx < len(self.buttons):
            self.selected_index = next_idx
            self.hovered_index = None
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.buttons[next_idx]["rect"].centerx, self.buttons[next_idx]["rect"].centery)

    def _launch_level(self, level_num):
        if level_num <= self.progress.get("highest_unlocked", 1):
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_click()
            self.game.change_state(PlayState(self.game, selected_level=level_num))

    def update(self, dt):
        self.starfield.update(dt)
        self.blink_timer += dt

        pos = pg.mouse.get_pos()
        is_hovered = self.back_hovered or self.hangar_hovered or (self.hovered_index is not None)
        self.game.cursor.set_hover_state(is_hovered)

        # Update floating tooltips for selected / hovered level tile
        active_idx = self.hovered_index if self.hovered_index is not None else self.selected_index
        if 0 <= active_idx < len(self.buttons):
            btn = self.buttons[active_idx]
            lvl = btn["level"]
            theater = get_theater(lvl)
            is_boss = lvl in (5, 10)
            
            title = f"MISSION LEVEL {lvl} — {theater.get('name', 'SECTOR')}"
            body = f"Theater: {theater.get('subtitle', 'Deep Space')}. "
            if is_boss:
                body += "⚠️ WARNING: MOTHERSHIP BOSS ENCOUNTER AHEAD! "
            if btn["best_score"] > 0:
                body += f"Best Mission Score: {btn['best_score']} PTS. "
            if not btn["unlocked"]:
                body = f"🔒 LOCKED SECTOR. Clear Level {lvl - 1} to unlock mission clearance."
            
            rect = btn["rect"]
            self.game.tooltip.set_tooltip(title, body, (rect.centerx, rect.bottom))

    def draw(self, screen):
        screen.fill((8, 10, 24))
        self.starfield.draw(screen)

        title = self.game.assets.title_font.render("CAMPAIGN MISSION SELECTOR", True, (0, 240, 255))
        title_rect = title.get_rect(center=(self.game.width // 2, 85))
        screen.blit(title, title_rect)

        sub_title = self.game.assets.hud_font.render("SELECT AN UNLOCKED LEVEL SECTOR TO DEPLOY YOUR FIGHTER", True, (160, 190, 220))
        screen.blit(sub_title, sub_title.get_rect(center=(self.game.width // 2, 120)))

        # Exit button to return to menu
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

        # Hangar shortcut button
        _draw_ui_button(
            screen,
            self.hangar_rect,
            "HANGAR ⚙",
            self.game.assets.font,
            hovered=self.hangar_hovered,
            fill=(24, 50, 75, 190),
            border=(0, 200, 255, 255) if self.hangar_hovered else (70, 140, 190, 255),
            text_color=(180, 240, 255),
            pulse=self.blink_timer * 6,
        )

        for idx, button in enumerate(self.buttons):
            rect = button["rect"]
            unlocked = button["unlocked"]
            completed = button["completed"]
            hovered = (self.hovered_index == idx) or (self.selected_index == idx)
            blink = idx == (self.progress.get("highest_unlocked", 1) - 1) and self.blink_timer % 1.0 < 0.5

            theater = get_theater(button["level"])
            accent = theater.get("accent_color", (110, 170, 255))
            ar, ag, ab = accent

            if not unlocked:
                fill = (24, 26, 34)
                border = (60, 65, 75)
            elif completed:
                fill = (max(0, int(ar * 0.16)), max(0, int(ag * 0.32 + 20)), max(0, int(ab * 0.22)))
                border = (0, 255, 180)
            else:
                fill = (max(0, int(ar * 0.2)), max(0, int(ag * 0.2)), max(0, int(ab * 0.28)))
                border = (min(255, int(ar * 0.8)), min(255, int(ag * 0.8)), min(255, int(ab * 0.9)))

            if hovered:
                if unlocked:
                    fill = (min(255, int(fill[0] + 35)), min(255, int(fill[1] + 35)), min(255, int(fill[2] + 40)))
                    border = (0, 255, 220)
                else:
                    fill = (45, 48, 56)
                    border = (100, 105, 120)

            if unlocked and blink:
                fill = (min(255, int(ar * 0.35)), min(255, int(ag * 0.35)), min(255, int(ab * 0.45)))
                border = (200, 255, 255)

            panel = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
            panel.fill((0, 0, 0, 0))
            pg.draw.rect(panel, fill, panel.get_rect(), border_radius=12)
            pg.draw.rect(panel, border, panel.get_rect(), 2, border_radius=12)

            # Boss Alert Banner Tag if Level 5 or 10
            if button["level"] in (5, 10):
                b_tag_c = (255, 60, 80) if unlocked else (120, 50, 60)
                pg.draw.rect(panel, b_tag_c, pg.Rect(0, 0, rect.width, 4), border_top_left_radius=12, border_top_right_radius=12)

            screen.blit(panel, rect)

            label = self.game.assets.hud_font.render(f"LEVEL {button['level']}", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=(rect.centerx, rect.y + 22)))

            # Theater name subtitle
            theater_sub = self.game.assets.hud_font.render(theater.get("name", ""), True, (min(255, int(ar * 0.9 + 20)), min(255, int(ag * 0.9 + 20)), min(255, int(ab * 0.9 + 20))))
            screen.blit(theater_sub, theater_sub.get_rect(center=(rect.centerx, rect.y + 44)))

            # 3-Star Rating Badges
            if unlocked:
                stars_earned = button["stars"]
                star_x_start = rect.centerx - 22
                for s_i in range(3):
                    star_c = (255, 215, 0) if (s_i < stars_earned) else (70, 80, 95)
                    star_cx = star_x_start + s_i * 22
                    star_cy = rect.y + 68
                    pg.draw.circle(screen, star_c, (star_cx, star_cy), 7)
                    if s_i < stars_earned:
                        pg.draw.circle(screen, (255, 255, 200), (star_cx, star_cy), 3)

            # Best score label
            if button["best_score"] > 0:
                sc_lbl = self.game.assets.hud_font.render(f"{button['best_score']} PTS", True, (0, 230, 255))
                screen.blit(sc_lbl, sc_lbl.get_rect(center=(rect.centerx, rect.bottom - 14)))
            elif completed:
                done_tag = self.game.assets.hud_font.render("CLEARED", True, (0, 255, 180))
                screen.blit(done_tag, done_tag.get_rect(center=(rect.centerx, rect.bottom - 14)))
            elif not unlocked:
                lock_tag = self.game.assets.hud_font.render("LOCKED 🔒", True, (160, 160, 175))
                screen.blit(lock_tag, lock_tag.get_rect(center=(rect.centerx, rect.bottom - 14)))
            else:
                status_tag = self.game.assets.hud_font.render("READY", True, (0, 240, 255))
                screen.blit(status_tag, status_tag.get_rect(center=(rect.centerx, rect.bottom - 14)))



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
        
        # Sprint 11 / Pillar D & F: Camera, Pipeline, and Dedicated HUD
        self.camera = Camera(self.game.width, self.game.height)
        self.pipeline = RenderPipeline(self.game.width, self.game.height, assets=self.game.assets)
        self.canvas = self.pipeline.world_canvas
        self.hud = HUD(self.game)
        
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

        # Play the combat track once at level start (no loop — silence during gameplay after intro)
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_music("combat", loop=False, fade_ms=600)

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
                if hasattr(self, 'hud'):
                    self.hud.trigger_hitmarker(laser.rect.centerx, laser.rect.top)
                
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

        # Render User Interface HUD via dedicated HUD subsystem
        self.hud.update(getattr(self, 'last_dt', 0.016))
        self.hud.draw(self.canvas, self)

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
        """Delegates HUD rendering to the dedicated HUD subsystem."""
        self.hud.draw(self.canvas, self)


class PauseState(State):
    """
    Sprint 11 & 12 — Reactive Pause Telemetry & Options Overlay.
    
    Draws a glassmorphism dark tint overlay, displays real-time mission telemetry,
    and supports InputMap menu navigation with full audio feedback.
    """
    def __init__(self, game, previous_state):
        super().__init__(game)
        self.previous_state = previous_state
        self.selected_index = 0
        self.hovered_index = None
        self.buttons = []
        self._build_buttons()
        self.anim_timer = 0.0
        
        self.overlay = pg.Surface((self.game.width, self.game.height), pg.SRCALPHA)
        self.overlay.fill((8, 12, 22, 215))

    def _build_buttons(self):
        cx = self.game.width // 3 - 40
        self.buttons = [
            {"label": "RESUME FLIGHT",  "rect": pg.Rect(cx - 130, 260, 260, 46)},
            {"label": "RESTART LEVEL",  "rect": pg.Rect(cx - 130, 320, 260, 46)},
            {"label": "SYSTEM OPTIONS", "rect": pg.Rect(cx - 130, 380, 260, 46)},
            {"label": "QUIT TO MENU",   "rect": pg.Rect(cx - 130, 440, 260, 46)},
        ]

    def handle_events(self, events):
        prev_sel = self.selected_index

        for event in events:
            if event.type == pg.MOUSEMOTION:
                mouse_hover = None
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        mouse_hover = idx
                        break
                if mouse_hover != self.hovered_index:
                    self.hovered_index = mouse_hover
                    if mouse_hover is not None:
                        self.selected_index = mouse_hover
                        if prev_sel != mouse_hover and hasattr(self.game, 'audio') and self.game.audio:
                            self.game.audio.play_ui_hover()

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                for idx, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(event.pos):
                        self._trigger_action(idx)
                        return

        # InputMap navigation
        if self.game.input.is_pressed("up"):
            self.selected_index = (self.selected_index - 1) % len(self.buttons)
            self.hovered_index = None
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.buttons[self.selected_index]["rect"].centerx, self.buttons[self.selected_index]["rect"].centery)

        elif self.game.input.is_pressed("down"):
            self.selected_index = (self.selected_index + 1) % len(self.buttons)
            self.hovered_index = None
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.buttons[self.selected_index]["rect"].centerx, self.buttons[self.selected_index]["rect"].centery)

        elif self.game.input.is_pressed("confirm"):
            self._trigger_action(self.selected_index)

        elif self.game.input.is_pressed("cancel") or self.game.input.is_pressed("pause"):
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_back()
            self.game.change_state(self.previous_state)

    def _trigger_action(self, idx):
        if idx == 0: # Resume
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_click()
            self.game.change_state(self.previous_state)
        elif idx == 1: # Restart level
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_click()
            lvl = getattr(self.previous_state, 'selected_level', 1)
            self.game.change_state(PlayState(self.game, selected_level=lvl))
        elif idx == 2: # Options
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_click()
            self.game.change_state(OptionsState(self.game, return_state=self))
        elif idx == 3: # Quit to Menu
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_back()
            self.game.change_state(MenuState(self.game))

    def update(self, dt):
        self.anim_timer += dt
        is_hovered = (self.hovered_index is not None)
        self.game.cursor.set_hover_state(is_hovered)
        self.game.tooltip.clear()

    def draw(self, screen):
        # Render gameplay frame behind overlay
        self.previous_state.draw(screen)
        screen.blit(self.overlay, (0, 0))
        
        # Pause Title Header
        title = self.game.assets.title_font.render("SYSTEM PAUSED", True, (0, 240, 255))
        screen.blit(title, title.get_rect(center=(self.game.width // 2, 110)))

        sub = self.game.assets.hud_font.render("FLIGHT SUSPENDED — MISSION TELEMETRY & CONTROLS ACTIVE", True, (160, 190, 220))
        screen.blit(sub, sub.get_rect(center=(self.game.width // 2, 148)))

        # Draw Menu Action Buttons (Left side)
        for idx, button in enumerate(self.buttons):
            rect = button["rect"]
            hovered = (self.hovered_index == idx) or (self.selected_index == idx)
            is_danger = "QUIT" in button["label"]

            _draw_ui_button(
                screen,
                rect,
                button["label"],
                self.game.assets.font,
                hovered=hovered,
                pulse=self.anim_timer * 8 + idx,
                danger=is_danger,
            )

        # ---------------- MISSION TELEMETRY CARD (Right side) ----------------
        t_rect = pg.Rect(self.game.width // 2 + 30, 220, 480, 280)
        t_panel = pg.Surface((t_rect.width, t_rect.height), pg.SRCALPHA)
        t_panel.fill((16, 24, 40, 225))
        pg.draw.rect(t_panel, (0, 220, 255, 200), t_panel.get_rect(), 2, border_radius=12)
        pg.draw.rect(t_panel, (0, 240, 255, 240), pg.Rect(0, 0, t_rect.width, 5), border_top_left_radius=12, border_top_right_radius=12)
        screen.blit(t_panel, t_rect)

        t_title = self.game.assets.font.render("MISSION TELEMETRY METRICS", True, (0, 255, 220))
        screen.blit(t_title, (t_rect.x + 20, t_rect.y + 16))

        # Read live play state data
        ps = self.previous_state
        curr_score = getattr(ps, 'score', 0)
        lvl_num = getattr(ps, 'level_sys', None).level_number if hasattr(ps, 'level_sys') else 1
        wave_num = getattr(ps, 'level_sys', None).wave_number if hasattr(ps, 'level_sys') else 1
        player = getattr(ps, 'player', None)
        hp_val = f"{int(player.health)}/{int(player.max_health)}" if player else "N/A"
        sh_val = f"{int(player.shield)}/{int(player.max_shield)}" if player else "N/A"
        missiles_val = str(player.missile_count) if player else "0"

        metrics = [
            ("CURRENT SCORE", f"{curr_score} PTS", (255, 220, 50)),
            ("MISSION SECTOR", f"LEVEL {lvl_num} — WAVE {wave_num}", (0, 240, 255)),
            ("HULL INTEGRITY", hp_val, (255, 120, 120)),
            ("SHIELD MATRIX", sh_val, (120, 220, 255)),
            ("MISSILES READY", f"{missiles_val} WARHEADS", (255, 160, 60)),
        ]

        for i, (m_lbl, m_val, m_col) in enumerate(metrics):
            y_pos = t_rect.y + 55 + i * 40
            l_surf = self.game.assets.hud_font.render(m_lbl, True, (160, 190, 220))
            v_surf = self.game.assets.font.render(m_val, True, m_col)
            screen.blit(l_surf, (t_rect.x + 20, y_pos))
            screen.blit(v_surf, (t_rect.right - 20 - v_surf.get_width(), y_pos - 2))



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
        loadout = getattr(self.game, 'loadout', {})
        hull = loadout.get("hull", "interceptor")
        color = loadout.get("color", "blue")
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_ui_click()
        self.save_system.save_score(final_name, self.score, hull=hull, color=color)
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
            # Boss warning: stop music and let silence build tension (no looping soundtrack)
            self.game.audio.stop_music(fade_ms=400)
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
        prev_hov = self.hovered

        for event in events:
            if event.type == pg.MOUSEMOTION:
                mp = event.pos
                self.skip_hovered = self.skip_rect.collidepoint(mp)
                mouse_h = None
                for i, rect in enumerate(self.card_rects):
                    if rect.collidepoint(mp):
                        mouse_h = i
                        break
                if mouse_h != self.hovered:
                    self.hovered = mouse_h
                    if mouse_h is not None and hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui_hover()

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                mp = event.pos
                if self.skip_rect.collidepoint(mp):
                    self._proceed()
                    return
                for i, rect in enumerate(self.card_rects):
                    if rect.collidepoint(mp) and i not in self.purchased:
                        self._buy(i)
                        return

        # InputMap navigation
        if self.game.input.is_pressed("left"):
            self.hovered = 0 if self.hovered is None else (self.hovered - 1) % len(self.card_rects)
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.card_rects[self.hovered].centerx, self.card_rects[self.hovered].centery)

        elif self.game.input.is_pressed("right"):
            self.hovered = 0 if self.hovered is None else (self.hovered + 1) % len(self.card_rects)
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_hover()
            self.game.cursor.snap_to(self.card_rects[self.hovered].centerx, self.card_rects[self.hovered].centery)

        elif self.game.input.is_pressed("confirm"):
            if self.hovered is not None and self.hovered not in self.purchased:
                self._buy(self.hovered)
            else:
                self._proceed()

        elif self.game.input.is_pressed("cancel"):
            self._proceed()

    def _buy(self, idx):
        offer = self.offers[idx]
        if self.score < offer["cost"]:
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui("danger")
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

        pos = pg.mouse.get_pos()
        is_hovered = self.skip_hovered or (self.hovered is not None)
        cursor = getattr(self.game, 'cursor', None)
        if cursor:
            cursor.set_hover_state(is_hovered)

        tooltip = getattr(self.game, 'tooltip', None)
        if tooltip:
            if self.hovered is not None and 0 <= self.hovered < len(self.offers):
                off = self.offers[self.hovered]
                r = self.card_rects[self.hovered]
                upgrades = getattr(self.game, 'upgrades', {})
                curr_val = upgrades.get(off["id"], 0)
                next_val = curr_val + off["step"]
                unit = "%" if isinstance(off["step"], float) else ""
                mult = 100 if unit == "%" else 1
                
                title = f"UPGRADE MODULE — {off['name']}"
                body = f"{off['desc']} Current Bonus: +{curr_val * mult}{unit} → Next Tier: +{next_val * mult}{unit}. Cost: {off['cost']} PTS."
                tooltip.set_tooltip(title, body, (r.centerx, r.top))
            else:
                tooltip.clear()


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
    """Congratulation popup shown immediately after a level clears with 3-star evaluation."""
    def __init__(self, game, score, cleared_level, lives_lost=0):
        super().__init__(game)
        self.score = score
        self.cleared_level = int(cleared_level)
        self.lives_lost = lives_lost
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=100)
        self.timer = 0.0
        self.continue_rect = pg.Rect(self.game.width // 2 - 150, self.game.height - 120, 300, 50)
        self.continue_hovered = False
        self.transition_locked = False

        # Calculate 3-star rating: 1 star = clear, 2 stars = score target, 3 stars = no lives lost
        target_score = 3000 * self.cleared_level
        self.stars = 1
        if self.score >= target_score:
            self.stars += 1
        if self.lives_lost == 0:
            self.stars += 1

        # Save progress to save system
        self.save_system = getattr(self.game, 'save_system', SaveSystem())
        self.save_system.save_progress(self.cleared_level, stars=self.stars, score=self.score)

    def _continue(self):
        if self.transition_locked:
            return
        self.transition_locked = True
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_ui_click()
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

        inp = getattr(self.game, 'input', None)
        if inp and (inp.is_pressed("confirm") or inp.is_pressed("cancel")):
            self._continue()

    def update(self, dt):
        self.starfield.update(dt)
        self.timer += dt
        self.game.cursor.set_hover_state(self.continue_hovered)
        self.game.tooltip.clear()

    def draw(self, screen):
        screen.fill((8, 10, 24))
        self.starfield.draw(screen)

        title = self.game.assets.title_font.render("CONGRATULATIONS", True, (0, 255, 180))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 4))
        screen.blit(title, title_rect)

        level_text = self.game.assets.hud_font.render(f"LEVEL {self.cleared_level} CLEARED", True, (255, 210, 110))
        level_rect = level_text.get_rect(center=(self.game.width // 2, self.game.height // 3 + 10))
        screen.blit(level_text, level_rect)

        # Draw 3-Star Rating Badges
        star_x_start = self.game.width // 2 - 40
        star_y = self.game.height // 3 + 50
        for s_i in range(3):
            s_earned = s_i < self.stars
            s_color = (255, 215, 0) if s_earned else (60, 70, 85)
            cx = star_x_start + s_i * 40
            pg.draw.circle(screen, s_color, (cx, star_y), 14)
            if s_earned:
                pg.draw.circle(screen, (255, 255, 200), (cx, star_y), 6)

        score_text = self.game.assets.font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.game.width // 2, self.game.height // 3 + 100))
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
        if hasattr(self.game, 'audio') and self.game.audio:
            self.game.audio.play_ui_click()
        loadout = getattr(self.game, 'loadout', {})
        hull = loadout.get("hull", "interceptor")
        color = loadout.get("color", "blue")
        self.save_system.save_score("VICTOR", self.score, hull=hull, color=color)
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

        if self.game.input.is_pressed("confirm") or self.game.input.is_pressed("cancel"):
            self._finalize()

    def update(self, dt):
        self.starfield.update(dt)
        self.timer += dt
        self.game.cursor.set_hover_state(self.continue_hovered)
        self.game.tooltip.clear()


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
    """Sprint 9 & 12 — Leaderboard Listing with Trophy Badges, Loadout Icons, and InputMap navigation."""
    def __init__(self, game):
        super().__init__(game)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=90)
        self.save_system = getattr(self.game, 'save_system', SaveSystem())
        self.scores_list = self.save_system.load_scores()
        self.back_rect = pg.Rect(40, 40, 120, 48)
        self.back_hovered = False
        self.anim_timer = 0.0

    def handle_events(self, events):
        """Allows returning back to Main Menu with mouse, keyboard, or gamepad."""
        for event in events:
            if event.type == pg.MOUSEMOTION:
                self.back_hovered = self.back_rect.collidepoint(event.pos)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_rect.collidepoint(event.pos):
                    if hasattr(self.game, 'audio') and self.game.audio:
                        self.game.audio.play_ui_back()
                    self.game.change_state(MenuState(self.game))
                    return

        if self.game.input.is_pressed("cancel") or self.game.input.is_pressed("confirm"):
            if hasattr(self.game, 'audio') and self.game.audio:
                self.game.audio.play_ui_back()
            self.game.change_state(MenuState(self.game))

    def update(self, dt):
        self.starfield.update(dt)
        self.anim_timer += dt
        self.game.cursor.set_hover_state(self.back_hovered)
        self.game.tooltip.clear()

    def draw(self, screen):
        screen.fill((10, 12, 22))
        self.starfield.draw(screen)
        
        # Leaderboard Header Title
        title = self.game.assets.title_font.render("HALL OF FAME", True, (0, 240, 255))
        title_rect = title.get_rect(center=(self.game.width // 2, 75))
        screen.blit(title, title_rect)

        sub_title = self.game.assets.hud_font.render("TOP PILOT RECORDS & STARSHIP LOADOUT ACHIEVEMENTS", True, (160, 190, 220))
        screen.blit(sub_title, sub_title.get_rect(center=(self.game.width // 2, 112)))

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

        # Table Container Panel
        table_rect = pg.Rect(self.game.width // 2 - 340, 150, 680, 510)
        table_panel = pg.Surface((table_rect.width, table_rect.height), pg.SRCALPHA)
        table_panel.fill((16, 24, 40, 225))
        pg.draw.rect(table_panel, (0, 220, 255, 200), table_panel.get_rect(), 2, border_radius=12)
        screen.blit(table_panel, table_rect)

        # Column Header
        h_rank = self.game.assets.hud_font.render("RANK", True, (0, 255, 220))
        h_ship = self.game.assets.hud_font.render("CRAFT", True, (0, 255, 220))
        h_name = self.game.assets.hud_font.render("PILOT CALLSIGN", True, (0, 255, 220))
        h_score = self.game.assets.hud_font.render("TOTAL SCORE", True, (0, 255, 220))
        screen.blit(h_rank, (table_rect.x + 25, table_rect.y + 18))
        screen.blit(h_ship, (table_rect.x + 110, table_rect.y + 18))
        screen.blit(h_name, (table_rect.x + 210, table_rect.y + 18))
        screen.blit(h_score, (table_rect.right - 25 - h_score.get_width(), table_rect.y + 18))
        pg.draw.line(screen, (0, 220, 255, 120), (table_rect.x + 20, table_rect.y + 44), (table_rect.right - 20, table_rect.y + 44), 1)
        
        # Rows
        trophies = ["🥇", "🥈", "🥉"]
        for idx, item in enumerate(self.scores_list[:10]):
            y_pos = table_rect.y + 60 + idx * 42

            # Trophy / Rank Label
            if idx < 3:
                rank_str = f"{trophies[idx]} {idx+1}."
                color = (255, 215, 0) if idx == 0 else ((220, 225, 240) if idx == 1 else (255, 160, 80))
            else:
                rank_str = f"{idx+1}."
                color = (150, 180, 210)

            name = item.get("name", "PILOT")
            score = str(item.get("score", 0))
            hull = item.get("hull", "interceptor")
            hull_color = item.get("color", "blue")

            rank_surf = self.game.assets.font.render(rank_str, True, color)
            name_surf = self.game.assets.font.render(name, True, color)
            score_surf = self.game.assets.font.render(score, True, color)

            # Ship icon representation
            life_key = f"ui_hud/life_counters/hud_life_{hull}_{hull_color}"
            life_img = self.game.assets.get_image(life_key, 22, 22)

            screen.blit(rank_surf, (table_rect.x + 25, y_pos))
            if life_img:
                screen.blit(life_img, (table_rect.x + 120, y_pos + 2))
            screen.blit(name_surf, (table_rect.x + 210, y_pos))
            screen.blit(score_surf, (table_rect.right - 25 - score_surf.get_width(), y_pos))

