import pygame as pg
import random
import math

class Starfield:
    def __init__(self, width, height, num_stars=120):
        self.width = width
        self.height = height
        self.stars = []
        
        # Define 3 layers of stars for parallax effect: (count, speed_range, size_range, color)
        layers = [
            (int(num_stars * 0.6), (20, 50), (1, 2), (100, 120, 150)),      # Background layer (slow, small, dim)
            (int(num_stars * 0.3), (60, 120), (2, 3), (180, 200, 220)),     # Midground layer
            (int(num_stars * 0.1), (150, 250), (3, 4), (230, 245, 255))      # Foreground layer (fast, larger, bright)
        ]
        
        for count, speed_range, size_range, color in layers:
            for _ in range(count):
                self.stars.append({
                    "x": random.uniform(0, self.width),
                    "y": random.uniform(0, self.height),
                    "speed": random.uniform(*speed_range),
                    "size": random.randint(*size_range),
                    "color": color
                })

    def update(self, dt):
        for star in self.stars:
            star["y"] += star["speed"] * dt
            if star["y"] > self.height:
                star["y"] = 0
                star["x"] = random.uniform(0, self.width)

    def draw(self, screen):
        for star in self.stars:
            pg.draw.circle(screen, star["color"], (int(star["x"]), int(star["y"])), star["size"])


class Particle(pg.sprite.Sprite):
    def __init__(self, x, y, color, size, speed_x, speed_y, lifetime):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.start_size = size
        self.size = size
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.max_life = lifetime
        self.life = lifetime
        
        # Redraw surface to support alpha fade-out
        self.image = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._update_image()

    def _update_image(self):
        self.image.fill((0, 0, 0, 0)) # Clear transparent surface
        alpha = int((self.life / self.max_life) * 255)
        # Handle RGB or RGBA colors safely
        base_color = self.color[:3]
        pg.draw.circle(self.image, (*base_color, alpha), (self.size, self.size), self.size)

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
            
        # Move
        self.x += self.speed_x * dt
        self.y += self.speed_y * dt
        self.rect.center = (int(self.x), int(self.y))
        
        # Shrink particle
        self.size = max(1, int(self.start_size * (self.life / self.max_life)))
        self._update_image()


def spawn_explosion(group, x, y, color=(255, 100, 0), count=25, speed_range=(50, 200), size_range=(2, 6)):
    """Spawns radial explosion particles."""
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        speed_x = speed * math.cos(angle)
        speed_y = speed * math.sin(angle)
        size = random.randint(*size_range)
        lifetime = random.uniform(0.3, 0.8)
        
        particle = Particle(x, y, color, size, speed_x, speed_y, lifetime)
        group.add(particle)


def spawn_sparks(group, x, y, direction_vector, color=(0, 255, 255), count=8):
    """Spawns directional hit spark particles."""
    dir_x, dir_y = direction_vector
    # Normalize direction
    mag = math.sqrt(dir_x**2 + dir_y**2)
    if mag > 0:
        dir_x /= mag
        dir_y /= mag
        
    for _ in range(count):
        # Scatter angle slightly around main direction
        spread_angle = math.atan2(dir_y, dir_x) + random.uniform(-0.5, 0.5)
        speed = random.uniform(80, 250)
        speed_x = speed * math.cos(spread_angle)
        speed_y = speed * math.sin(spread_angle)
        size = random.randint(1, 3)
        lifetime = random.uniform(0.2, 0.5)
        
        particle = Particle(x, y, color, size, speed_x, speed_y, lifetime)
        group.add(particle)
