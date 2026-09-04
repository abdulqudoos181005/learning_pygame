# pyrefly: ignore [missing-import]
import math
import pygame as pg
from fx import Starfield
from ui.text_input import TextInput


def _draw_button(screen, rect, label, font, *, hovered=False, pressed=False,
                 fill=(22, 34, 56, 220), border=(90, 120, 150, 255),
                 text_color=(240, 240, 240), danger=False, pulse=0.0):
    """Draws a themed sci-fi button with hover glow and tactile depression."""
    draw_rect = rect.inflate(4, 2) if (hovered and not pressed) else rect.copy()
    if pressed:
        draw_rect = rect.inflate(-2, -2)

    panel = pg.Surface((draw_rect.width, draw_rect.height), pg.SRCALPHA)
    panel.fill((0, 0, 0, 0))

    if danger and (hovered or pressed):
        fill = (65, 15, 25, 240)
        border = (255, 60, 80, 255)
        text_color = (255, 140, 160)
    elif hovered:
        fill_r, fill_g, fill_b, fill_a = fill
        fill = (min(255, fill_r + 28), min(255, fill_g + 50), min(255, fill_b + 60), fill_a)
        border = (0, 255, 220, 255)
        text_color = (120, 255, 255)
    elif pressed:
        fill_r, fill_g, fill_b, fill_a = fill
        fill = (max(0, fill_r - 14), max(0, fill_g - 12), max(0, fill_b - 18), fill_a)
        border = (180, 255, 255, 255)

    fill_r, fill_g, fill_b, fill_a = fill
    border_r, border_g, border_b, border_a = border
    pulse_alpha = int(fill_a + (20 * math.sin(pulse) if pulse else 0))
    panel.fill((fill_r, fill_g, fill_b, max(0, min(255, pulse_alpha))))
    pg.draw.rect(panel, (border_r, border_g, border_b, border_a), panel.get_rect(), 2, border_radius=8)

    if hovered:
        pw, ph = draw_rect.width, draw_rect.height
        accent_c = (0, 255, 220, 255) if not danger else (255, 80, 100, 255)
        pg.draw.line(panel, accent_c, (4, 4), (10, 4), 2)
        pg.draw.line(panel, accent_c, (4, 4), (4, 10), 2)
        pg.draw.line(panel, accent_c, (pw - 5, ph - 5), (pw - 11, ph - 5), 2)
        pg.draw.line(panel, accent_c, (pw - 5, ph - 5), (pw - 5, ph - 11), 2)

    screen.blit(panel, draw_rect)

    shadow_surf = font.render(label, True, (10, 12, 20))
    shadow_rect = shadow_surf.get_rect(center=(draw_rect.centerx + 1, draw_rect.centery + 1))
    screen.blit(shadow_surf, shadow_rect)

    label_surf = font.render(label, True, text_color)
    label_rect = label_surf.get_rect(center=draw_rect.center)
    if pressed:
        label_rect.move_ip(1, 2)
    screen.blit(label_surf, label_rect)


class LoginState:
    """
    Sprint 13 / Phase 1 — User Authentication & Profile Login State.

    Provides:
    - Dual-mode tabbed interface: [LOG IN] vs [REGISTER].
    - Interactive text input fields for Pilot Callsign & Passcode.
    - Password visibility toggle and confirm password validation.
    - Quick [PLAY AS GUEST] flow.
    - Animated status feedback banners (Success / Error / Info).
    - Parallax starfield & atmospheric audio cues.
    """

    def __init__(self, game, return_state=None):
        self.game = game
        self.return_state = return_state
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=90)
        self.anim_timer = 0.0

        # Tab Mode: "login" or "register"
        self.active_tab = "login"

        # Fonts
        self.title_font = getattr(self.game.assets, "title_font", pg.font.SysFont("Trebuchet MS", 40))
        self.font = getattr(self.game.assets, "font", pg.font.SysFont("Trebuchet MS", 22))
        self.hud_font = getattr(self.game.assets, "hud_font", pg.font.SysFont("Trebuchet MS", 18))

        # Status Banner State
        # status_type: "info", "error", "success"
        self.status_message = "ENTER CREDENTIALS TO ACCESS FLEET COMMAND"
        self.status_type = "info"
        self.status_timer = 0.0
        self.status_shake = 0.0

        # Success transition delay
        self.success_redirect_timer = 0.0
        self.pending_user = None

        # Build UI layout
        self._init_layout()

        # Start menu ambient sound bed if not playing
        if hasattr(self.game, "audio"):
            self.game.audio.play_music("menu")

    def _init_layout(self):
        """Constructs layout bounding boxes and text input widgets."""
        cx = self.game.width // 2
        cy = self.game.height // 2

        # Main glassmorphic auth card
        self.card_width = 540
        self.card_height = 500
        self.card_rect = pg.Rect(
            cx - self.card_width // 2, cy - self.card_height // 2 + 15, self.card_width, self.card_height
        )

        # Tab buttons
        tab_w = 200
        tab_h = 38
        self.tab_login_rect = pg.Rect(self.card_rect.x + 40, self.card_rect.y + 45, tab_w, tab_h)
        self.tab_register_rect = pg.Rect(self.card_rect.right - 40 - tab_w, self.card_rect.y + 45, tab_w, tab_h)

        # Input fields for LOGIN mode
        field_w = 440
        field_h = 42
        field_x = cx - field_w // 2

        self.login_user_input = TextInput(
            rect=pg.Rect(field_x, self.card_rect.y + 130, field_w, field_h),
            font=self.font,
            label="PILOT CALLSIGN",
            placeholder="Enter pilot username...",
            max_length=20,
            audio=self.game.audio,
            label_font=self.hud_font,
            on_submit=lambda _: self._submit_login(),
        )

        self.login_pass_input = TextInput(
            rect=pg.Rect(field_x, self.card_rect.y + 205, field_w, field_h),
            font=self.font,
            label="SECURITY PASSCODE",
            placeholder="Enter password...",
            is_password=True,
            max_length=32,
            audio=self.game.audio,
            label_font=self.hud_font,
            on_submit=lambda _: self._submit_login(),
        )

        # Input fields for REGISTER mode
        self.reg_user_input = TextInput(
            rect=pg.Rect(field_x, self.card_rect.y + 115, field_w, field_h),
            font=self.font,
            label="NEW PILOT CALLSIGN",
            placeholder="Choose callsign (3-20 chars)...",
            max_length=20,
            audio=self.game.audio,
            label_font=self.hud_font,
            on_submit=lambda _: self._focus_next(),
        )

        self.reg_pass_input = TextInput(
            rect=pg.Rect(field_x, self.card_rect.y + 185, field_w, field_h),
            font=self.font,
            label="NEW SECURITY PASSCODE",
            placeholder="Min 4 characters...",
            is_password=True,
            max_length=32,
            audio=self.game.audio,
            label_font=self.hud_font,
            on_submit=lambda _: self._focus_next(),
        )

        self.reg_confirm_input = TextInput(
            rect=pg.Rect(field_x, self.card_rect.y + 255, field_w, field_h),
            font=self.font,
            label="CONFIRM SECURITY PASSCODE",
            placeholder="Re-enter password...",
            is_password=True,
            max_length=32,
            audio=self.game.audio,
            label_font=self.hud_font,
            on_submit=lambda _: self._submit_register(),
        )

        # Action Buttons
        btn_w = 440
        self.login_btn_rect = pg.Rect(field_x, self.card_rect.y + 280, btn_w, 44)
        self.reg_btn_rect = pg.Rect(field_x, self.card_rect.y + 325, btn_w, 44)
        self.guest_btn_rect = pg.Rect(field_x, self.card_rect.y + 380, btn_w, 38)
        self.back_btn_rect = pg.Rect(field_x, self.card_rect.y + 430, btn_w, 36)

        # Hover states
        self.hovered_tab_login = False
        self.hovered_tab_reg = False
        self.hovered_login_btn = False
        self.hovered_reg_btn = False
        self.hovered_guest_btn = False
        self.hovered_back_btn = False

        # Set default focus to username input
        self.login_user_input.set_focus(True)

    def _set_status(self, message: str, status_type: str = "info"):
        """Updates the status banner with visual feedback and sound."""
        self.status_message = message
        self.status_type = status_type
        self.status_timer = 0.0

        if status_type == "error":
            self.status_shake = 0.25
            if hasattr(self.game, "audio"):
                self.game.audio.play_ui("danger")
        elif status_type == "success":
            if hasattr(self.game, "audio"):
                self.game.audio.play_ui("confirm")
        else:
            if hasattr(self.game, "audio"):
                self.game.audio.play_ui("tick")

    def _get_active_inputs(self):
        """Returns active text input fields based on current tab."""
        if self.active_tab == "login":
            return [self.login_user_input, self.login_pass_input]
        return [self.reg_user_input, self.reg_pass_input, self.reg_confirm_input]

    def _focus_next(self):
        """Cycles focus to next active text input."""
        inputs = self._get_active_inputs()
        focused_idx = None
        for i, inp in enumerate(inputs):
            if inp.focused:
                focused_idx = i
                break

        if focused_idx is None:
            inputs[0].set_focus(True)
        else:
            inputs[focused_idx].set_focus(False)
            next_idx = (focused_idx + 1) % len(inputs)
            inputs[next_idx].set_focus(True)

    def _submit_login(self):
        """Validates and processes pilot login."""
        username = self.login_user_input.get_text().strip()
        password = self.login_pass_input.get_text()

        if not username:
            self._set_status("PLEASE ENTER YOUR PILOT CALLSIGN", "error")
            self.login_user_input.set_focus(True)
            return

        if not password:
            self._set_status("PLEASE ENTER YOUR SECURITY PASSCODE", "error")
            self.login_pass_input.set_focus(True)
            return

        # Integration with AuthService if available, else local session creation
        auth_service = getattr(self.game, "auth_service", None)
        if auth_service and hasattr(auth_service, "authenticate_user"):
            user, err = auth_service.authenticate_user(username, password)
            if not user:
                self._set_status(f"AUTH FAILED: {err or 'INVALID CREDENTIALS'}", "error")
                return
            session_user = {
                "id": user.get("id"),
                "username": user.get("username", username),
                "is_guest": False,
            }
        else:
            # Phase 1 UI Mock Auth
            session_user = {
                "id": 1,
                "username": username,
                "is_guest": False,
            }

        self.pending_user = session_user
        self._set_status(f"WELCOME BACK, PILOT {username.upper()}! LAUNCHING...", "success")
        self.success_redirect_timer = 0.55

    def _submit_register(self):
        """Validates and processes new pilot registration."""
        username = self.reg_user_input.get_text().strip()
        password = self.reg_pass_input.get_text()
        confirm_pass = self.reg_confirm_input.get_text()

        if len(username) < 3:
            self._set_status("CALLSIGN MUST BE AT LEAST 3 CHARACTERS", "error")
            self.reg_user_input.set_focus(True)
            return

        if len(password) < 4:
            self._set_status("PASSCODE MUST BE AT LEAST 4 CHARACTERS", "error")
            self.reg_pass_input.set_focus(True)
            return

        if password != confirm_pass:
            self._set_status("PASSCODES DO NOT MATCH. PLEASE VERIFY", "error")
            self.reg_confirm_input.set_focus(True)
            return

        # Integration with AuthService if available, else local session creation
        auth_service = getattr(self.game, "auth_service", None)
        if auth_service and hasattr(auth_service, "register_user"):
            user, err = auth_service.register_user(username, password)
            if not user:
                self._set_status(f"REGISTRATION FAILED: {err or 'USERNAME TAKEN'}", "error")
                return
            session_user = {
                "id": user.get("id"),
                "username": user.get("username", username),
                "is_guest": False,
            }
        else:
            # Phase 1 UI Mock Registration
            session_user = {
                "id": 1,
                "username": username,
                "is_guest": False,
            }

        self.pending_user = session_user
        self._set_status(f"PILOT PROFILE CREATED! INITIALIZING HANGAR...", "success")
        self.success_redirect_timer = 0.55

    def _submit_guest(self):
        """Instantly creates a guest session and continues."""
        guest_user = {
            "id": None,
            "username": "Guest Pilot",
            "is_guest": True,
        }
        self.pending_user = guest_user
        self._set_status("INITIALIZING GUEST PILOT SESSION...", "success")
        self.success_redirect_timer = 0.35

    def _return_to_game(self):
        """Applies session user and returns to previous state or MenuState."""
        if self.pending_user:
            if hasattr(self.game, "set_user"):
                self.game.set_user(self.pending_user)
            else:
                self.game.current_user = self.pending_user

        from states import MenuState
        target_state = self.return_state or MenuState(self.game)
        self.game.change_state(target_state)

    def handle_events(self, events):
        """Processes keyboard navigation, tab switching, and input widget events."""
        for event in events:
            # Check active text inputs first
            for inp in self._get_active_inputs():
                inp.handle_event(event)

            if event.type == pg.MOUSEMOTION:
                self.hovered_tab_login = self.tab_login_rect.collidepoint(event.pos)
                self.hovered_tab_reg = self.tab_register_rect.collidepoint(event.pos)
                self.hovered_guest_btn = self.guest_btn_rect.collidepoint(event.pos)
                self.hovered_back_btn = self.back_btn_rect.collidepoint(event.pos)

                if self.active_tab == "login":
                    self.hovered_login_btn = self.login_btn_rect.collidepoint(event.pos)
                    self.hovered_reg_btn = False
                else:
                    self.hovered_reg_btn = self.reg_btn_rect.collidepoint(event.pos)
                    self.hovered_login_btn = False

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                # Tab switches
                if self.tab_login_rect.collidepoint(event.pos) and self.active_tab != "login":
                    self.active_tab = "login"
                    self._set_status("ENTER CREDENTIALS TO ACCESS FLEET COMMAND", "info")
                    self.login_user_input.set_focus(True)
                    return

                if self.tab_register_rect.collidepoint(event.pos) and self.active_tab != "register":
                    self.active_tab = "register"
                    self._set_status("ENTER NEW CALLSIGN & SECURE PASSCODE", "info")
                    self.reg_user_input.set_focus(True)
                    return

                # Action buttons
                if self.active_tab == "login" and self.login_btn_rect.collidepoint(event.pos):
                    self._submit_login()
                    return

                if self.active_tab == "register" and self.reg_btn_rect.collidepoint(event.pos):
                    self._submit_register()
                    return

                if self.guest_btn_rect.collidepoint(event.pos):
                    self._submit_guest()
                    return

                if self.back_btn_rect.collidepoint(event.pos):
                    if hasattr(self.game, "audio"):
                        self.game.audio.play_ui_back()
                    from states import MenuState
                    self.game.change_state(self.return_state or MenuState(self.game))
                    return

            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    if hasattr(self.game, "audio"):
                        self.game.audio.play_ui_back()
                    from states import MenuState
                    self.game.change_state(self.return_state or MenuState(self.game))
                    return

                elif event.key == pg.K_TAB:
                    self._focus_next()
                    return

        # Gamepad / InputMap navigation fallback when not typing
        any_focused = any(inp.focused for inp in self._get_active_inputs())
        if not any_focused:
            if self.game.input.is_pressed("cancel"):
                from states import MenuState
                self.game.change_state(self.return_state or MenuState(self.game))

    def update(self, dt: float):
        """Updates starfield animation, caret blinks, banner physics, and redirects."""
        self.starfield.update(dt)
        self.anim_timer += dt

        # Update input widgets
        for inp in self._get_active_inputs():
            inp.update(dt)

        # Shake timer decay
        if self.status_shake > 0:
            self.status_shake = max(0.0, self.status_shake - dt)

        # Redirect timer on successful login/registration
        if self.success_redirect_timer > 0:
            self.success_redirect_timer -= dt
            if self.success_redirect_timer <= 0:
                self._return_to_game()

    def draw(self, screen: pg.Surface):
        """Draws auth card, parallax stars, active tab widgets, status banner, and buttons."""
        screen.fill((8, 10, 18))
        self.starfield.draw(screen)

        cx = self.game.width // 2

        # Header Title
        title_surf = self.title_font.render("FLEET PILOT TERMINAL", True, (0, 255, 200))
        title_shadow = self.title_font.render("FLEET PILOT TERMINAL", True, (0, 80, 70))
        title_rect = title_surf.get_rect(center=(cx, self.card_rect.top - 36))
        screen.blit(title_shadow, (title_rect.x + 2, title_rect.y + 2))
        screen.blit(title_surf, title_rect)

        # Main Glassmorphic Auth Card
        card_surf = pg.Surface((self.card_width, self.card_height), pg.SRCALPHA)
        card_surf.fill((12, 18, 30, 235))
        pg.draw.rect(card_surf, (0, 255, 220, 160), card_surf.get_rect(), 2, border_radius=14)

        # Decorative cyber grid lines inside card
        for y_line in range(50, self.card_height, 60):
            pg.draw.line(card_surf, (20, 40, 65, 40), (10, y_line), (self.card_width - 10, y_line), 1)

        screen.blit(card_surf, self.card_rect)

        # Draw Status Banner at top of card
        shake_offset = math.sin(self.anim_timer * 40.0) * 6 if self.status_shake > 0 else 0
        banner_rect = pg.Rect(
            self.card_rect.x + 20 + int(shake_offset), self.card_rect.y + 10, self.card_width - 40, 28
        )
        b_surf = pg.Surface((banner_rect.width, banner_rect.height), pg.SRCALPHA)

        if self.status_type == "error":
            b_fill = (70, 15, 25, 220)
            b_border = (255, 60, 80, 240)
            b_text_color = (255, 160, 180)
        elif self.status_type == "success":
            b_fill = (15, 65, 40, 220)
            b_border = (50, 255, 150, 240)
            b_text_color = (160, 255, 200)
        else:
            b_fill = (18, 32, 50, 200)
            b_border = (40, 90, 140, 200)
            b_text_color = (140, 190, 230)

        b_surf.fill(b_fill)
        pg.draw.rect(b_surf, b_border, b_surf.get_rect(), 1, border_radius=4)
        screen.blit(b_surf, banner_rect)

        status_txt = self.hud_font.render(self.status_message, True, b_text_color)
        status_txt_rect = status_txt.get_rect(center=banner_rect.center)
        screen.blit(status_txt, status_txt_rect)

        # Draw Tab Buttons ([LOG IN] and [REGISTER])
        # Log In Tab
        is_login_active = (self.active_tab == "login")
        _draw_button(
            screen,
            self.tab_login_rect,
            "LOG IN",
            self.font,
            hovered=self.hovered_tab_login or is_login_active,
            fill=(30, 55, 85, 240) if is_login_active else (18, 26, 40, 200),
            border=(0, 255, 220, 255) if is_login_active else (60, 80, 110, 220),
            text_color=(0, 255, 220) if is_login_active else (140, 165, 190),
        )

        # Register Tab
        is_reg_active = (self.active_tab == "register")
        _draw_button(
            screen,
            self.tab_register_rect,
            "REGISTER",
            self.font,
            hovered=self.hovered_tab_reg or is_reg_active,
            fill=(30, 55, 85, 240) if is_reg_active else (18, 26, 40, 200),
            border=(0, 255, 220, 255) if is_reg_active else (60, 80, 110, 220),
            text_color=(0, 255, 220) if is_reg_active else (140, 165, 190),
        )

        # Draw Input Fields
        for inp in self._get_active_inputs():
            inp.draw(screen)

        # Draw Primary Action Button
        if self.active_tab == "login":
            _draw_button(
                screen,
                self.login_btn_rect,
                "AUTHENTICATE PILOT",
                self.font,
                hovered=self.hovered_login_btn,
                pulse=self.anim_timer * 6.0,
                fill=(20, 55, 80, 230),
                border=(0, 255, 220, 255),
                text_color=(200, 255, 255),
            )
        else:
            _draw_button(
                screen,
                self.reg_btn_rect,
                "CREATE PILOT ACCOUNT",
                self.font,
                hovered=self.hovered_reg_btn,
                pulse=self.anim_timer * 6.0,
                fill=(20, 65, 55, 230),
                border=(0, 255, 180, 255),
                text_color=(200, 255, 230),
            )

        # Guest and Back Buttons
        _draw_button(
            screen,
            self.guest_btn_rect,
            "⚡ PLAY AS GUEST (QUICK START)",
            self.hud_font,
            hovered=self.hovered_guest_btn,
            fill=(18, 35, 52, 210),
            border=(70, 130, 170, 220),
            text_color=(170, 215, 245),
        )

        _draw_button(
            screen,
            self.back_btn_rect,
            "← RETURN TO MAIN MENU",
            self.hud_font,
            hovered=self.hovered_back_btn,
            fill=(16, 22, 32, 200),
            border=(60, 75, 95, 200),
            text_color=(140, 160, 180),
        )
