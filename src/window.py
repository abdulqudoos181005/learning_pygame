import pygame as pg

# Initialize all imported pygame modules
pg.init()

# Set up the drawing window (width, height)
screen = pg.display.set_mode((600, 400))
pg.display.set_caption("My Pygame Window")

# Game clock to manage frame rate
clock = pg.time.Clock()

running = True
while running:
    # Event handling loop
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

    # Fill the screen background with a color (RGB)
    screen.fill((30, 30, 30))

    # Flip the display to show the drawings
    pg.display.flip()

    # Limit frame rate to 60 FPS
    clock.tick(60)

# Done! Time to clean up.
pg.quit()