import os
import sys
import pathlib
import py_compile
import pygame

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

root = pathlib.Path(r'd:\projects\learning_pygame\src')
files = sorted(root.glob('*.py'))
for f in files:
    py_compile.compile(str(f), doraise=True)

sys.path.insert(0, r'd:\projects\learning_pygame\src')
import level_system, sprites, states

print('compile_ok', len(files))
print('imports_ok', level_system.LevelSystem(1).level_number, sprites.Player.__name__, states.PlayState.__name__, sprites.Asteroid.__name__)

pygame.init()
pygame.display.set_mode((1280, 720))
pygame.quit()
