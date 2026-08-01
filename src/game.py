import pygame as pg
import sys
from assets_loader import AssetsLoader
from states import MenuState

class Game:
    def __init__(self):
        pg.init()
        pg.mixer.init()
        
        self.width = 1280
        self.height = 720
        self.screen = pg.display.set_mode((self.width, self.height))
        pg.display.set_caption("Space Shooters")
        
        self.clock = pg.time.Clock()
        self.assets = AssetsLoader()
        
        # Start state
        self.state = MenuState(self)
        self.running = True

    def change_state(self, new_state):
        self.state = new_state

    def run(self):
        while self.running:
            # Calculate delta time in seconds (max 0.1s to avoid huge jumps)
            dt = min(self.clock.tick(60) / 1000.0, 0.1)
            
            # Event polling
            events = pg.event.get()
            for event in events:
                if event.type == pg.QUIT:
                    self.running = False
            
            # State execution
            self.state.handle_events(events)
            self.state.update(dt)
            self.state.draw(self.screen)
            
            # Show drawing results
            pg.display.flip()
            
        pg.quit()
        sys.exit()

    def quit(self):
        self.running = False


if __name__ == "__main__":
    game = Game()
    game.run()
