# pyrefly: ignore [missing-import]
import os
import sys
import unittest
import pygame as pg

# Ensure 'src' is in python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from ui.text_input import TextInput
from ui.login_state import LoginState
from game import Game
from states import MenuState


class DummyAudio:
    def __init__(self):
        self.played = []

    def play_ui(self, sound_type="tick", volume_mult=1.0):
        self.played.append(sound_type)

    def play_ui_hover(self):
        self.played.append("hover")

    def play_ui_click(self):
        self.played.append("click")

    def play_ui_back(self):
        self.played.append("back")

    def play_ui_toggle(self):
        self.played.append("toggle")

    def play_music(self, track, loop=True):
        pass


class TestSprint13AuthUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        if not pg.display.get_surface():
            pg.display.set_mode((1280, 720), pg.HIDDEN)

    def setUp(self):
        self.font = pg.font.SysFont("Trebuchet MS", 20)
        self.hud_font = pg.font.SysFont("Trebuchet MS", 16)
        self.audio = DummyAudio()

    def test_text_input_typing_and_limits(self):
        """Tests insertion, max length, and clear on TextInput."""
        inp = TextInput(
            rect=pg.Rect(100, 100, 200, 40),
            font=self.font,
            max_length=8,
            audio=self.audio,
        )
        inp.set_focus(True)
        self.assertTrue(inp.focused)

        # Type "STAR"
        for ch in "STAR":
            evt = pg.event.Event(pg.KEYDOWN, {"key": ord(ch.lower()), "unicode": ch, "mod": 0})
            inp.handle_event(evt)

        self.assertEqual(inp.get_text(), "STAR")
        self.assertEqual(inp.cursor_pos, 4)

        # Type exceeding max length (max_length=8)
        for ch in "SHIP12345":
            evt = pg.event.Event(pg.KEYDOWN, {"key": ord(ch.lower()), "unicode": ch, "mod": 0})
            inp.handle_event(evt)

        self.assertEqual(inp.get_text(), "STARSHIP")
        self.assertEqual(len(inp.get_text()), 8)

        # Clear
        inp.clear()
        self.assertEqual(inp.get_text(), "")
        self.assertEqual(inp.cursor_pos, 0)

    def test_text_input_cursor_navigation_and_deletion(self):
        """Tests cursor movements and backspace/delete operations."""
        inp = TextInput(
            rect=pg.Rect(100, 100, 200, 40),
            font=self.font,
            initial_text="PILOT",
            audio=self.audio,
        )
        inp.set_focus(True)
        self.assertEqual(inp.cursor_pos, 5)

        # Left arrow twice -> cursor at index 3 ("PIL|OT")
        left_evt = pg.event.Event(pg.KEYDOWN, {"key": pg.K_LEFT, "unicode": "", "mod": 0})
        inp.handle_event(left_evt)
        inp.handle_event(left_evt)
        self.assertEqual(inp.cursor_pos, 3)

        # Backspace -> deletes 'L' -> "PIOT", cursor at 2
        bk_evt = pg.event.Event(pg.KEYDOWN, {"key": pg.K_BACKSPACE, "unicode": "", "mod": 0})
        inp.handle_event(bk_evt)
        self.assertEqual(inp.get_text(), "PIOT")
        self.assertEqual(inp.cursor_pos, 2)

        # Delete -> deletes 'O' -> "PIT", cursor at 2
        del_evt = pg.event.Event(pg.KEYDOWN, {"key": pg.K_DELETE, "unicode": "", "mod": 0})
        inp.handle_event(del_evt)
        self.assertEqual(inp.get_text(), "PIT")
        self.assertEqual(inp.cursor_pos, 2)

        # Home key -> cursor at 0
        home_evt = pg.event.Event(pg.KEYDOWN, {"key": pg.K_HOME, "unicode": "", "mod": 0})
        inp.handle_event(home_evt)
        self.assertEqual(inp.cursor_pos, 0)

        # End key -> cursor at 3
        end_evt = pg.event.Event(pg.KEYDOWN, {"key": pg.K_END, "unicode": "", "mod": 0})
        inp.handle_event(end_evt)
        self.assertEqual(inp.cursor_pos, 3)

    def test_text_input_password_masking_and_toggle(self):
        """Tests password masking and show/hide toggle."""
        inp = TextInput(
            rect=pg.Rect(100, 100, 300, 40),
            font=self.font,
            is_password=True,
            initial_text="SecretPass123",
            audio=self.audio,
        )
        self.assertEqual(inp._get_display_text(), "•••••••••••••")

        # Toggle password via toggle rect click
        toggle_click = pg.event.Event(
            pg.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (inp.toggle_rect.centerx, inp.toggle_rect.centery)},
        )
        inp.handle_event(toggle_click)
        self.assertTrue(inp.show_password)
        self.assertEqual(inp._get_display_text(), "SecretPass123")

        # Toggle back
        inp.handle_event(toggle_click)
        self.assertFalse(inp.show_password)
        self.assertEqual(inp._get_display_text(), "•••••••••••••")

    def test_login_state_validation_and_tabs(self):
        """Tests tab switching and client-side validation logic in LoginState."""
        game = Game()
        login_state = LoginState(game)

        # 1. Check default state is 'login' tab
        self.assertEqual(login_state.active_tab, "login")

        # 2. Submit empty login -> error banner
        login_state._submit_login()
        self.assertEqual(login_state.status_type, "error")
        self.assertIn("CALLSIGN", login_state.status_message)

        # 3. Switch to Register tab
        tab_reg_click = pg.event.Event(
            pg.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (login_state.tab_register_rect.centerx, login_state.tab_register_rect.centery)},
        )
        login_state.handle_events([tab_reg_click])
        self.assertEqual(login_state.active_tab, "register")

        # 4. Short username validation (< 3 chars)
        login_state.reg_user_input.set_text("ab")
        login_state.reg_pass_input.set_text("12345")
        login_state.reg_confirm_input.set_text("12345")
        login_state._submit_register()
        self.assertEqual(login_state.status_type, "error")
        self.assertIn("3 CHARACTERS", login_state.status_message)

        # 5. Password mismatch validation
        login_state.reg_user_input.set_text("Viper")
        login_state.reg_pass_input.set_text("pass1234")
        login_state.reg_confirm_input.set_text("different")
        login_state._submit_register()
        self.assertEqual(login_state.status_type, "error")
        self.assertIn("NOT MATCH", login_state.status_message)

        # 6. Valid registration
        login_state.reg_confirm_input.set_text("pass1234")
        login_state._submit_register()
        self.assertEqual(login_state.status_type, "success")
        self.assertIsNotNone(login_state.pending_user)
        self.assertEqual(login_state.pending_user["username"], "Viper")
        self.assertFalse(login_state.pending_user["is_guest"])

    def test_guest_session_and_game_user_management(self):
        """Tests guest login flow and Game user coordinator methods."""
        game = Game()
        self.assertTrue(game.current_user["is_guest"])
        self.assertFalse(game.is_logged_in())

        # Set user
        game.set_user({"id": 42, "username": "StarCommander", "is_guest": False})
        self.assertEqual(game.current_user["username"], "StarCommander")
        self.assertTrue(game.is_logged_in())

        # Logout
        game.logout()
        self.assertEqual(game.current_user["username"], "Guest Pilot")
        self.assertTrue(game.current_user["is_guest"])
        self.assertFalse(game.is_logged_in())

    def test_menu_state_pilot_badge_and_rendering(self):
        """Tests MenuState pilot badge hover, click, and render."""
        game = Game()
        menu = MenuState(game)
        screen = pg.Surface((1280, 720))

        # Update and draw menu
        menu.update(0.016)
        menu.draw(screen)

        # Hover pilot badge
        hover_evt = pg.event.Event(
            pg.MOUSEMOTION,
            {"pos": (menu.pilot_badge_rect.centerx, menu.pilot_badge_rect.centery)},
        )
        menu.handle_events([hover_evt])
        self.assertTrue(menu.hovered_pilot_badge)

        menu.update(0.016)
        self.assertTrue(game.tooltip.active)
        self.assertEqual(game.tooltip.title, "PILOT PROFILE")

        # Click pilot badge switches to LoginState
        click_evt = pg.event.Event(
            pg.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (menu.pilot_badge_rect.centerx, menu.pilot_badge_rect.centery)},
        )
        menu.handle_events([click_evt])
        self.assertIsInstance(game.state, LoginState)


if __name__ == "__main__":
    unittest.main()
