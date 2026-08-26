
# pyrefly: ignore [missing-import]
import pygame as pg
import sys
from assets_loader import AssetsLoader
from states import MenuState

class Game:
    """
    The main coordinator and engine class for 'Space Shooters'.
    
    This class is responsible for:
    1. Initializing Pygame and its sub-modules (like the mixer for audio).
    2. Setting up the display window and clock for frame rate regulation.
    3. Initializing the AssetsLoader to procedurally load/generate assets.
    4. Orchestrating the Game Loop and managing transitions between game states
       (such as MenuState, PlayState, GameOverState) using the State Pattern.
    """
    def __init__(self):
        # Initialize all imported pygame modules (display, image, font, etc.)
        pg.init()
        # Initialize the mixer module for sound loading and playback (graceful fallback if audio device unavailable)
        try:
            pg.mixer.init()
        except Exception as e:
            print(f"[Warning] Audio device initialization failed: {e}. Running in silent mode.")

        
        # Screen dimensions
        self.width = 1280
        self.height = 720
        self.screen = pg.display.set_mode((self.width, self.height))
        pg.display.set_caption("Space Shooters")
        
        # Clock object to manage frame rate and calculate delta time
        self.clock = pg.time.Clock()
        
        # AssetsLoader handles loading PNG files or generating procedural vector designs
        self.assets = AssetsLoader()
        
        # Sprint 11 / Pillar C: Audio Director for multi-bus audio, spatial panning, ducking, & voice limiting
        from audio.director import AudioDirector
        self.audio = AudioDirector(assets=self.assets, screen_width=self.width)
        
        # Save System & persistent player loadout & settings
        from save_system import SaveSystem
        self.save_system = SaveSystem()
        self.settings = self.save_system.load_settings()
        self.loadout = self.save_system.load_loadout()

        # Apply saved bus volumes
        self.audio.set_bus_volumes(
            music=self.settings.get("music_volume", 0.7),
            sfx=self.settings.get("sfx_volume", 0.8),
            ui=self.settings.get("ui_volume", 0.8)
        )

        # Sprint 11 / Pillar G: Device-Agnostic Input Map
        from input_map import InputMap
        self.input = InputMap(keybinds=self.settings.get("keybinds", None))

        # Sprint 11 / Pillar F: Tactical Software Reticle
        from ui.cursor import SoftwareCursor
        self.cursor = SoftwareCursor(self.assets, self.width, self.height)

        # Sprint 11 / Pillar H: Cinematic State Transitions
        from render.transition import StateTransition
        self.transition = StateTransition(self.width, self.height)

        # Fullscreen state
        self.fullscreen = bool(self.settings.get("fullscreen", False))
        if self.fullscreen:
            self.screen = pg.display.set_mode((self.width, self.height), pg.FULLSCREEN)

        # Initialize starting state (MenuState) using the State Design Pattern.
        self.state = MenuState(self)
        self.running = True

        # Sprint 7: persistent upgrade bonuses purchased from the between-level shop.
        self.upgrades = {
            "max_health_bonus": 0,    # flat HP added to player max health
            "max_shield_bonus": 0,    # flat shield added to player max shield
            "extra_lives": 0,         # bonus lives granted at level start
            "reload_reduction": 0.0,  # fraction to reduce shoot_cooldown (e.g. 0.1 = 10% faster)
            "missile_capacity": 0,    # bonus starting missiles
            "shield_regen_rate": 0.0, # shield points regenerated per second (passive)
        }

    def toggle_fullscreen(self):
        """Toggles fullscreen display mode without destroying assets."""
        self.fullscreen = not self.fullscreen
        self.settings["fullscreen"] = self.fullscreen
        self.save_system.save_settings(self.settings)
        flags = pg.FULLSCREEN if self.fullscreen else 0
        self.screen = pg.display.set_mode((self.width, self.height), flags)

    def change_state(self, new_state, transition_type=None, duration=0.22):
        """
        Switches the active game state, optionally routing through a cinematic transition.
        """
        if transition_type:
            self.transition.start(new_state, transition_type=transition_type, duration=duration)
        else:
            self.state = new_state

    def run(self):
        """
        The core Game Loop. Runs continuously while self.running is True.
        Each iteration represents one frame.
        """
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.1)
            
            # 1. EVENT POLLING
            events = pg.event.get()
            for event in events:
                if event.type == pg.QUIT:
                    self.running = False
                elif event.type == pg.KEYDOWN and event.key == pg.K_F11:
                    self.toggle_fullscreen()

            # 2. SUBSYSTEM UPDATES
            self.input.update(dt, events=events)
            self.audio.update(dt)
            self.cursor.update(dt, lerp_aim=isinstance(self.state, PlayState) if 'PlayState' in globals() else False)
            self.transition.update(dt, self)

            # 3. STATE-SPECIFIC EXECUTION
            if not self.transition.active or self.transition.halfway_executed:
                self.state.handle_events(events)
            self.state.update(dt)
            self.state.draw(self.screen)

            # 4. TRANSITION & TACTICAL CURSOR OVERLAY
            self.transition.draw(self.screen)
            self.cursor.draw(self.screen)
            
            # 5. REFRESH SCREEN
            pg.display.flip()
            
        # Clean up pygame resources and exit the process safely
        pg.quit()
        sys.exit()

    def quit(self):
        """Signals the game loop to terminate."""
        self.running = False


if __name__ == "__main__":
    # Create an instance of the Game engine and run it
    game = Game()
    game.run()

