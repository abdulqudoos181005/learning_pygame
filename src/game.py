
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
        # Initialize the mixer module for sound loading and playback
        pg.mixer.init()
        
        # Screen dimensions
        self.width = 1280
        self.height = 720
        self.screen = pg.display.set_mode((self.width, self.height))
        pg.display.set_caption("Space Shooters")
        
        # Clock object to manage frame rate and calculate delta time
        self.clock = pg.time.Clock()
        
        # AssetsLoader handles loading PNG files or generating procedural vector designs
        self.assets = AssetsLoader()
        
        # Initialize starting state (MenuState) using the State Design Pattern.
        # This keeps state-specific logic (menu screens, gameplay, high scores) separate.
        self.state = MenuState(self)
        self.running = True

        # Sprint 7: persistent upgrade bonuses purchased from the between-level shop.
        # These accumulate across the whole run and are applied each time a PlayState is created.
        self.upgrades = {
            "max_health_bonus": 0,    # flat HP added to player max health
            "max_shield_bonus": 0,    # flat shield added to player max shield
            "extra_lives": 0,         # bonus lives granted at level start
            "reload_reduction": 0.0,  # fraction to reduce shoot_cooldown (e.g. 0.1 = 10% faster)
            "missile_capacity": 0,    # bonus starting missiles
            "shield_regen_rate": 0.0, # shield points regenerated per second (passive)
        }

    def change_state(self, new_state):
        """
        Switches the active game state.
        
        This makes switching from the Main Menu -> Play Screen -> Game Over Screen
        as simple as instantiating a new State object.
        """
        self.state = new_state

    def run(self):
        """
        The core Game Loop. Runs continuously while self.running is True.
        Each iteration represents one frame.
        """
        while self.running:
            # 1. FRAME RATE & DELTA TIME
            # self.clock.tick(60) limits the game to 60 frames per second.
            # It returns the milliseconds elapsed since the last tick.
            # We divide by 1000.0 to convert it to seconds (dt = delta time in seconds).
            # min(..., 0.1) clamps dt to a maximum of 0.1 seconds to prevent huge movement jumps
            # (which would let sprites clip through boundaries) if the game lags.
            dt = min(self.clock.tick(60) / 1000.0, 0.1)
            
            # 2. EVENT POLLING
            # Collect and process all system events (key presses, window close, etc.)
            events = pg.event.get()
            for event in events:
                # If the user clicks the 'X' close button of the window, exit the loop
                if event.type == pg.QUIT:
                    self.running = False
            
            # 3. STATE-SPECIFIC EXECUTION
            # Delegate event handling, physics/updates, and drawing to the active state.
            # This is the power of the State Pattern: game.run() doesn't need to know what screen is active.
            self.state.handle_events(events)
            self.state.update(dt)
            self.state.draw(self.screen)
            
            # 4. REFRESH SCREEN
            # pg.display.flip() updates the full display Surface to the screen.
            # It displays the final drawn buffer, preventing screen tearing.
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

