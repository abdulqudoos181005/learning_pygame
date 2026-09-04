# pyrefly: ignore [missing-import]
import math
import pygame as pg


class TextInput:
    """
    Sprint 13 / Phase 1 — Interactive Sci-Fi Text Field Component.

    Features:
    - Focus glow & active border illumination.
    - Pulsing caret cursor with sub-character insertion positioning.
    - Dimmed placeholder text support.
    - Password masking ('••••••') with interactive Show/Hide visibility toggle.
    - Full keyboard navigation: Left/Right arrows, Home/End, Delete, Backspace hold-repeat.
    - Max character limits, clipboard paste handling, and event callback hooks.
    """

    def __init__(
        self,
        rect,
        font,
        placeholder="Enter text...",
        label="",
        is_password=False,
        max_length=24,
        initial_text="",
        on_submit=None,
        on_text_change=None,
        audio=None,
        label_font=None,
    ):
        self.rect = pg.Rect(rect)
        self.font = font
        self.label_font = label_font or font
        self.placeholder = placeholder
        self.label = label
        self.is_password = is_password
        self.max_length = max_length
        self.text = str(initial_text)
        self.on_submit = on_submit
        self.on_text_change = on_text_change
        self.audio = audio

        # State flags
        self.focused = False
        self.hovered = False
        self.show_password = False
        self.hovered_toggle = False
        self.cursor_pos = len(self.text)
        self.disabled = False

        # Visual timers
        self.caret_timer = 0.0
        self.anim_timer = 0.0

        # Backspace repeat timers
        self.backspace_held = False
        self.backspace_hold_timer = 0.0
        self.backspace_repeat_timer = 0.0
        self.BACKSPACE_DELAY = 0.35
        self.BACKSPACE_INTERVAL = 0.045

        # Password toggle button rectangle
        self.toggle_rect = pg.Rect(
            self.rect.right - 58, self.rect.y + 4, 52, self.rect.height - 8
        )

    def set_focus(self, focused: bool):
        """Sets focus state and resets caret blink timer."""
        if self.focused != focused:
            self.focused = focused
            self.caret_timer = 0.0
            if self.focused:
                self.cursor_pos = len(self.text)
                if self.audio and hasattr(self.audio, "play_ui_hover"):
                    self.audio.play_ui_hover()

    def set_text(self, text: str):
        """Updates text content safely within max character limit."""
        self.text = str(text)[: self.max_length]
        self.cursor_pos = min(self.cursor_pos, len(self.text))
        if self.on_text_change:
            self.on_text_change(self.text)

    def get_text(self) -> str:
        """Returns current input string."""
        return self.text

    def clear(self):
        """Clears text and resets cursor."""
        self.text = ""
        self.cursor_pos = 0
        if self.on_text_change:
            self.on_text_change(self.text)

    def _get_display_text(self) -> str:
        """Returns masked or plain text based on password mode."""
        if self.is_password and not self.show_password:
            return "•" * len(self.text)
        return self.text

    def _delete_char_before_cursor(self):
        """Deletes one character before the caret position."""
        if self.cursor_pos > 0 and len(self.text) > 0:
            self.text = self.text[: self.cursor_pos - 1] + self.text[self.cursor_pos :]
            self.cursor_pos -= 1
            self.caret_timer = 0.0
            if self.audio and hasattr(self.audio, "play_ui"):
                self.audio.play_ui("tick", volume_mult=0.5)
            if self.on_text_change:
                self.on_text_change(self.text)

    def _delete_char_at_cursor(self):
        """Deletes one character after the caret position (Delete key)."""
        if self.cursor_pos < len(self.text):
            self.text = self.text[: self.cursor_pos] + self.text[self.cursor_pos + 1 :]
            self.caret_timer = 0.0
            if self.audio and hasattr(self.audio, "play_ui"):
                self.audio.play_ui("tick", volume_mult=0.5)
            if self.on_text_change:
                self.on_text_change(self.text)

    def _insert_text(self, new_text: str):
        """Inserts characters at cursor position respecting max length."""
        if not new_text or self.disabled:
            return
        # Filter out control characters
        clean_text = "".join(c for c in new_text if c.isprintable() and c not in "\r\n\t")
        available_slots = self.max_length - len(self.text)
        if available_slots <= 0:
            return

        to_add = clean_text[:available_slots]
        if to_add:
            self.text = self.text[: self.cursor_pos] + to_add + self.text[self.cursor_pos :]
            self.cursor_pos += len(to_add)
            self.caret_timer = 0.0
            if self.audio and hasattr(self.audio, "play_ui"):
                self.audio.play_ui("tick", volume_mult=0.6)
            if self.on_text_change:
                self.on_text_change(self.text)

    def handle_event(self, event) -> bool:
        """
        Handles mouse and keyboard interaction events.
        Returns True if the event was consumed by this widget.
        """
        if self.disabled:
            return False

        if event.type == pg.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            if self.is_password:
                self.hovered_toggle = self.toggle_rect.collidepoint(event.pos)
            else:
                self.hovered_toggle = False
            return self.hovered

        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_password and self.toggle_rect.collidepoint(event.pos):
                self.show_password = not self.show_password
                if self.audio and hasattr(self.audio, "play_ui_toggle"):
                    self.audio.play_ui_toggle()
                return True

            if self.rect.collidepoint(event.pos):
                if not self.focused:
                    self.set_focus(True)

                # Calculate approximate cursor position from click X
                click_x = event.pos[0] - (self.rect.x + 14)
                display_str = self._get_display_text()
                best_idx = len(display_str)
                for idx in range(len(display_str) + 1):
                    sub = display_str[:idx]
                    w = self.font.size(sub)[0]
                    if w >= click_x:
                        best_idx = idx
                        break
                self.cursor_pos = min(len(self.text), max(0, best_idx))
                self.caret_timer = 0.0
                return True
            else:
                if self.focused:
                    self.set_focus(False)
                return False

        elif event.type == pg.KEYDOWN:
            if not self.focused:
                return False

            if event.key == pg.K_BACKSPACE:
                self._delete_char_before_cursor()
                self.backspace_held = True
                self.backspace_hold_timer = 0.0
                self.backspace_repeat_timer = 0.0
                return True

            elif event.key == pg.K_DELETE:
                self._delete_char_at_cursor()
                return True

            elif event.key == pg.K_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                    self.caret_timer = 0.0
                return True

            elif event.key == pg.K_RIGHT:
                if self.cursor_pos < len(self.text):
                    self.cursor_pos += 1
                    self.caret_timer = 0.0
                return True

            elif event.key == pg.K_HOME:
                self.cursor_pos = 0
                self.caret_timer = 0.0
                return True

            elif event.key == pg.K_END:
                self.cursor_pos = len(self.text)
                self.caret_timer = 0.0
                return True

            elif event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                if self.on_submit:
                    self.on_submit(self.text)
                return True

            # Paste from clipboard if Ctrl+V
            mods = pg.key.get_mods()
            if (mods & pg.KMOD_CTRL) and event.key == pg.K_v:
                try:
                    if pg.scrap and pg.scrap.get_init():
                        clip = pg.scrap.get(pg.SCRAP_TEXT)
                        if clip:
                            if isinstance(clip, bytes):
                                clip_str = clip.decode("utf-8", errors="ignore").replace("\x00", "")
                            else:
                                clip_str = str(clip)
                            self._insert_text(clip_str)
                            return True
                except Exception:
                    pass

            # Regular typed characters
            if event.unicode and event.unicode.isprintable() and event.unicode not in "\r\n\t":
                self._insert_text(event.unicode)
                return True

        elif event.type == pg.KEYUP:
            if event.key == pg.K_BACKSPACE:
                self.backspace_held = False
                return True

        return False

    def update(self, dt: float):
        """Processes caret blinking and key repeat physics."""
        self.anim_timer += dt
        self.caret_timer = (self.caret_timer + dt) % 1.0

        if self.focused and self.backspace_held:
            self.backspace_hold_timer += dt
            if self.backspace_hold_timer >= self.BACKSPACE_DELAY:
                self.backspace_repeat_timer += dt
                if self.backspace_repeat_timer >= self.BACKSPACE_INTERVAL:
                    self.backspace_repeat_timer -= self.BACKSPACE_INTERVAL
                    self._delete_char_before_cursor()

    def draw(self, screen: pg.Surface):
        """Renders the sci-fi styled input box with status glow, caret, and labels."""
        # 1. Draw optional label above input field
        if self.label:
            lbl_color = (0, 255, 220) if self.focused else (160, 185, 215)
            lbl_surf = self.label_font.render(self.label, True, lbl_color)
            screen.blit(lbl_surf, (self.rect.x + 2, self.rect.y - 24))

        # 2. Base box surface with glassmorphism fill
        draw_rect = self.rect.copy()
        box_surf = pg.Surface((draw_rect.width, draw_rect.height), pg.SRCALPHA)

        if self.disabled:
            fill_color = (15, 20, 28, 180)
            border_color = (50, 65, 85, 180)
            border_w = 1
        elif self.focused:
            pulse = 15 * math.sin(self.anim_timer * 6.0)
            fill_color = (20, 38, 58, int(235 + pulse))
            border_color = (0, 255, 220, 255)
            border_w = 2
        elif self.hovered:
            fill_color = (18, 30, 48, 220)
            border_color = (80, 180, 210, 240)
            border_w = 2
        else:
            fill_color = (14, 22, 34, 200)
            border_color = (55, 75, 100, 220)
            border_w = 1

        box_surf.fill(fill_color)
        pg.draw.rect(box_surf, border_color, box_surf.get_rect(), border_w, border_radius=8)

        # Draw glowing cyber corner accents when focused
        if self.focused:
            accent_c = (0, 255, 220, 255)
            w, h = draw_rect.width, draw_rect.height
            pg.draw.line(box_surf, accent_c, (4, 4), (12, 4), 2)
            pg.draw.line(box_surf, accent_c, (4, 4), (4, 12), 2)
            pg.draw.line(box_surf, accent_c, (w - 5, h - 5), (w - 13, h - 5), 2)
            pg.draw.line(box_surf, accent_c, (w - 5, h - 5), (w - 5, h - 13), 2)

        screen.blit(box_surf, draw_rect)

        # 3. Text and Caret Rendering
        # Available text width excludes password toggle button area if active
        avail_width = draw_rect.width - 24
        if self.is_password:
            avail_width -= 60

        # Sub-surface clipping for long strings
        text_clip_rect = pg.Rect(draw_rect.x + 14, draw_rect.y, avail_width, draw_rect.height)
        prev_clip = screen.get_clip()
        screen.set_clip(text_clip_rect)

        display_str = self._get_display_text()
        has_text = len(self.text) > 0

        # Compute horizontal scroll offset so caret is always visible
        sub_to_caret = display_str[: self.cursor_pos]
        caret_x_offset = self.font.size(sub_to_caret)[0]
        scroll_x = 0
        if caret_x_offset > avail_width - 10:
            scroll_x = caret_x_offset - (avail_width - 10)

        text_render_x = draw_rect.x + 14 - scroll_x
        text_render_y = draw_rect.centery - (self.font.get_height() // 2)

        if has_text:
            text_surf = self.font.render(display_str, True, (240, 248, 255))
            screen.blit(text_surf, (text_render_x, text_render_y))
        elif not self.focused and self.placeholder:
            placeholder_surf = self.font.render(self.placeholder, True, (110, 135, 160))
            screen.blit(placeholder_surf, (text_render_x, text_render_y))

        # 4. Caret rendering (blinking vertical cyber bar)
        if self.focused and self.caret_timer < 0.5:
            caret_x = text_render_x + caret_x_offset
            caret_top = draw_rect.centery - 10
            caret_bottom = draw_rect.centery + 10
            pg.draw.line(screen, (0, 255, 230), (caret_x, caret_top), (caret_x, caret_bottom), 2)

        screen.set_clip(prev_clip)

        # 5. Password toggle button
        if self.is_password:
            self.toggle_rect = pg.Rect(
                draw_rect.right - 62, draw_rect.y + 6, 54, draw_rect.height - 12
            )
            t_surf = pg.Surface((self.toggle_rect.width, self.toggle_rect.height), pg.SRCALPHA)
            t_fill = (35, 55, 80, 220) if self.hovered_toggle else (22, 34, 50, 160)
            t_border = (0, 255, 220) if self.hovered_toggle else (65, 85, 115)
            t_surf.fill(t_fill)
            pg.draw.rect(t_surf, t_border, t_surf.get_rect(), 1, border_radius=4)
            screen.blit(t_surf, self.toggle_rect)

            btn_label = "HIDE" if self.show_password else "SHOW"
            btn_color = (0, 255, 220) if self.hovered_toggle else (150, 180, 210)
            btn_txt = self.label_font.render(btn_label, True, btn_color)
            # Scale down if label font is too large
            if btn_txt.get_width() > self.toggle_rect.width - 6:
                btn_txt = pg.transform.smoothscale(
                    btn_txt,
                    (self.toggle_rect.width - 8, int(btn_txt.get_height() * (self.toggle_rect.width - 8) / btn_txt.get_width())),
                )
            btn_rect = btn_txt.get_rect(center=self.toggle_rect.center)
            screen.blit(btn_txt, btn_rect)
