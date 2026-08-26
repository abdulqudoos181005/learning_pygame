# pyrefly: ignore [missing-import]
import pygame as pg


class InputMap:
    """
    Sprint 11 / Pillar G — Device-Agnostic Input Subsystem.

    Provides a clean action graph decoupled from raw keycodes:
    - Actions: 'up', 'down', 'left', 'right', 'fire', 'missile', 'pause', 'confirm', 'cancel'
    - Tracks three action states:
        - `is_held(action)`: Action is currently active/held down
        - `is_pressed(action)`: Action triggered down this exact frame (rising edge)
        - `is_released(action)`: Action released this exact frame (falling edge)
    - Supports dynamic keyboard key rebinding and persists bindings.
    - Gamepad support with hotplugging, stick deadzones, face buttons, and rumble feedback.
    """

    KEY_NAMES_TO_PG = {
        "w": pg.K_w, "s": pg.K_s, "a": pg.K_a, "d": pg.K_d,
        "up": pg.K_UP, "down": pg.K_DOWN, "left": pg.K_LEFT, "right": pg.K_RIGHT,
        "space": pg.K_SPACE, "j": pg.K_j, "k": pg.K_k, "m": pg.K_m,
        "p": pg.K_p, "escape": pg.K_ESCAPE, "return": pg.K_RETURN,
        "lshift": pg.K_LSHIFT, "rshift": pg.K_RSHIFT,
    }

    def __init__(self, keybinds=None):
        self.keybinds = {
            "up": "w",
            "down": "s",
            "left": "a",
            "right": "d",
            "fire": "space",
            "missile": "m",
            "pause": "p",
        }
        if keybinds and isinstance(keybinds, dict):
            self.keybinds.update(keybinds)

        # Internal action tracking
        self.actions_held = {k: False for k in ("up", "down", "left", "right", "fire", "missile", "pause", "confirm", "cancel")}
        self.actions_pressed = {k: False for k in self.actions_held}
        self.actions_released = {k: False for k in self.actions_held}

        # Gamepad support
        self.joystick = None
        self.gamepad_connected = False
        self.gamepad_name = ""
        self._init_gamepad()

        # Rumble timer / state
        self.rumble_timer = 0.0

    def _init_gamepad(self):
        """Initializes any connected gamepad/controller."""
        if pg.joystick.get_init():
            count = pg.joystick.get_count()
            if count > 0:
                try:
                    self.joystick = pg.joystick.Joystick(0)
                    self.joystick.init()
                    self.gamepad_connected = True
                    self.gamepad_name = self.joystick.get_name()
                except Exception:
                    self.joystick = None
                    self.gamepad_connected = False

    def update(self, dt, events=None):
        """
        Polls input state for the current frame.
        Must be called once at the start of the frame.
        """
        if self.rumble_timer > 0:
            self.rumble_timer -= dt
            if self.rumble_timer <= 0 and self.joystick and hasattr(self.joystick, 'rumble'):
                try:
                    self.joystick.rumble(0, 0, 0)
                except Exception:
                    pass

        # Handle gamepad hotplugging events
        if events:
            for event in events:
                if event.type == pg.JOYDEVICEADDED:
                    self._init_gamepad()
                elif event.type == pg.JOYDEVICEREMOVED:
                    self.joystick = None
                    self.gamepad_connected = False

        # Read keyboard state
        keys = pg.key.get_pressed()

        # Build current frame raw held dict
        current_held = {}
        for action, key_str in self.keybinds.items():
            pg_key = self.KEY_NAMES_TO_PG.get(key_str.lower(), getattr(pg, f"K_{key_str.lower()}", None))
            held = bool(keys[pg_key]) if pg_key is not None else False

            # Add standard secondary fallbacks for navigation/combat
            if action == "up": held = held or keys[pg.K_UP]
            elif action == "down": held = held or keys[pg.K_DOWN]
            elif action == "left": held = held or keys[pg.K_LEFT]
            elif action == "right": held = held or keys[pg.K_RIGHT]
            elif action == "fire": held = held or keys[pg.K_j] or keys[pg.K_SPACE]
            elif action == "pause": held = held or keys[pg.K_ESCAPE] or keys[pg.K_p]

            current_held[action] = held

        # Navigation confirm / cancel actions
        current_held["confirm"] = keys[pg.K_RETURN] or keys[pg.K_SPACE]
        current_held["cancel"] = keys[pg.K_ESCAPE] or keys[pg.K_BACKSPACE]

        # Read Gamepad Axis / Buttons if connected
        if self.joystick and self.gamepad_connected:
            try:
                # Left stick / D-Pad
                axis_x = self.joystick.get_axis(0) if self.joystick.get_numaxes() > 0 else 0.0
                axis_y = self.joystick.get_axis(1) if self.joystick.get_numaxes() > 1 else 0.0
                DEADZONE = 0.25

                if axis_x < -DEADZONE: current_held["left"] = True
                elif axis_x > DEADZONE: current_held["right"] = True
                if axis_y < -DEADZONE: current_held["up"] = True
                elif axis_y > DEADZONE: current_held["down"] = True

                # D-pad Hats
                if self.joystick.get_numhats() > 0:
                    hat_x, hat_y = self.joystick.get_hat(0)
                    if hat_x < 0: current_held["left"] = True
                    elif hat_x > 0: current_held["right"] = True
                    if hat_y > 0: current_held["up"] = True
                    elif hat_y < 0: current_held["down"] = True

                # Buttons (0: A/Cross, 1: B/Circle, 5: RB/R1, 7: Start/Options)
                num_buttons = self.joystick.get_numbuttons()
                if num_buttons > 0 and self.joystick.get_button(0):  # A Button -> Fire / Confirm
                    current_held["fire"] = True
                    current_held["confirm"] = True
                if num_buttons > 1 and self.joystick.get_button(1):  # B Button -> Cancel
                    current_held["cancel"] = True
                if num_buttons > 5 and self.joystick.get_button(5):  # RB Button -> Missile
                    current_held["missile"] = True
                if num_buttons > 7 and self.joystick.get_button(7):  # Start Button -> Pause
                    current_held["pause"] = True
            except Exception:
                pass

        # Compute pressed (rising edge) and released (falling edge)
        for act in self.actions_held:
            is_now = current_held.get(act, False)
            was_then = self.actions_held[act]
            self.actions_pressed[act] = is_now and not was_then
            self.actions_released[act] = not is_now and was_then
            self.actions_held[act] = is_now

    def is_held(self, action):
        """Returns True if the action is currently active/held."""
        return self.actions_held.get(action, False)

    def is_pressed(self, action):
        """Returns True only on the frame the action was first pressed down."""
        return self.actions_pressed.get(action, False)

    def is_released(self, action):
        """Returns True only on the frame the action was released."""
        return self.actions_released.get(action, False)

    def trigger_rumble(self, low=0.4, high=0.4, duration=0.2):
        """Triggers gamepad vibration if supported and connected."""
        if self.joystick and hasattr(self.joystick, 'rumble'):
            try:
                self.joystick.rumble(low, high, int(duration * 1000))
                self.rumble_timer = duration
            except Exception:
                pass
