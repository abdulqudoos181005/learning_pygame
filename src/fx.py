# pyrefly: ignore [missing-import]
import pygame as pg
import random
import math

class Starfield:
    """
    Creates a scrolling starfield background using three layers of stars.
    
    This simulates a 3D depth effect (parallax scrolling) where foreground stars
    move faster and are larger/brighter than background stars.
    """
    def __init__(self, width, height, num_stars=120):
        self.width = width
        self.height = height
        self.stars = []
        
        # Define 3 layers of stars for parallax effect:
        # Format: (star_count, speed_range, size_range, color)
        layers = [
            (int(num_stars * 0.6), (20, 50), (1, 2), (100, 120, 150)),      # Layer 1: Background (slowest, smallest, dimmest)
            (int(num_stars * 0.3), (60, 120), (2, 3), (180, 200, 220)),     # Layer 2: Midground
            (int(num_stars * 0.1), (150, 250), (3, 4), (230, 245, 255))      # Layer 3: Foreground (fastest, largest, brightest)
        ]
        
        # Generate random stars for each layer
        for count, speed_range, size_range, color in layers:
            for _ in range(count):
                self.stars.append({
                    "x": random.uniform(0, self.width),
                    "y": random.uniform(0, self.height),
                    "speed": random.uniform(*speed_range),  # Pixels per second downward
                    "size": random.randint(*size_range),
                    "color": color
                })

    def update(self, dt):
        """Scrolls stars downward. If a star leaves the bottom of the screen, recycle it to the top."""
        for star in self.stars:
            star["y"] += star["speed"] * dt
            # If the star moves off the bottom of the screen
            if star["y"] > self.height:
                star["y"] = 0  # Put back at top
                star["x"] = random.uniform(0, self.width) # Give it a new random X position

    def draw(self, screen):
        """Draws each star as a simple filled circle on the screen."""
        for star in self.stars:
            pg.draw.circle(screen, star["color"], (int(star["x"]), int(star["y"])), star["size"])


class Particle(pg.sprite.Sprite):
    """
    An individual visual effect particle that moves, fades out, and shrinks over its lifespan.
    
    Performance note: The circle is drawn ONCE at spawn time. Each frame only
    calls set_alpha() on the pre-baked surface — avoiding a full Surface re-alloc
    and draw.circle call every update tick, which matters greatly during boss fights
    with 200+ simultaneous particles.
    """
    def __init__(self, x, y, color, size, speed_x, speed_y, lifetime):
        super().__init__()
        # Store positions as floats to ensure smooth sub-pixel physics updates
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.start_size = size
        self.size = size
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.max_life = lifetime # Total lifetime in seconds
        self.life = lifetime     # Remaining lifetime in seconds
        
        # Create a surface with an alpha channel (transparent background).
        # The circle is drawn once here — update() only tweaks alpha, never redraws.
        self.image = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
        base_color = color[:3]
        pg.draw.circle(self.image, (*base_color, 255), (size, size), size)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self, dt):
        """Updates particle lifespan, position, and fade alpha.\n        Does NOT redraw the surface — only calls set_alpha for performance."""
        self.life -= dt
        # Remove particle when its life runs out
        if self.life <= 0:
            self.kill()
            return
            
        # Update physical coordinates
        self.x += self.speed_x * dt
        self.y += self.speed_y * dt
        self.rect.center = (int(self.x), int(self.y))
        
        # Fade out by adjusting alpha — much cheaper than fill+draw.circle every frame
        alpha = max(0, int((self.life / self.max_life) * 255))
        self.image.set_alpha(alpha)


class ParticlePool:
    """
    Sprint 11 / Pillar J — Particle Pool for zero-allocation performance.

    Pre-allocates 384 reusable Particle objects to prevent garbage collector spikes
    during intense combat or multi-kill chain explosions.
    """

    def __init__(self, capacity=384):
        self.capacity = capacity
        self.pool = [Particle(0, 0, (255, 255, 255), 3, 0, 0, 0.5) for _ in range(capacity)]
        for p in self.pool:
            p.kill()

    def get(self, x, y, color, size, speed_x, speed_y, lifetime):
        """Retrieves an idle particle from the pool or re-uses the oldest if full."""
        particle = None
        for p in self.pool:
            if not p.alive() and p.life <= 0:
                particle = p
                break

        if particle is None:
            particle = self.pool[0]  # recycle oldest

        particle.x = float(x)
        particle.y = float(y)
        particle.color = color
        particle.start_size = size
        particle.size = size
        particle.speed_x = speed_x
        particle.speed_y = speed_y
        particle.max_life = lifetime
        particle.life = lifetime

        # Re-render base surface for new size/color
        particle.image = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
        base_color = color[:3]
        pg.draw.circle(particle.image, (*base_color, 255), (size, size), size)
        particle.rect = particle.image.get_rect(center=(int(x), int(y)))
        return particle


_GLOBAL_PARTICLE_POOL = None

def get_particle_pool():
    global _GLOBAL_PARTICLE_POOL
    if _GLOBAL_PARTICLE_POOL is None:
        _GLOBAL_PARTICLE_POOL = ParticlePool(capacity=384)
    return _GLOBAL_PARTICLE_POOL


def spawn_explosion(group, x, y, color=(255, 100, 0), count=25, speed_range=(50, 200), size_range=(2, 6)):
    """
    Spawns multiple particles in a radial direction to create an explosion effect using the pool.
    """
    pool = get_particle_pool()
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        speed_x = speed * math.cos(angle)
        speed_y = speed * math.sin(angle)
        size = random.randint(*size_range)
        lifetime = random.uniform(0.3, 0.8)

        particle = pool.get(x, y, color, size, speed_x, speed_y, lifetime)
        group.add(particle)


def spawn_sparks(group, x, y, direction_vector, color=(0, 255, 255), count=8):
    """
    Spawns particles oriented along a specific direction vector to simulate impact sparks using the pool.
    """
    dir_x, dir_y = direction_vector
    mag = math.sqrt(dir_x**2 + dir_y**2)
    if mag > 0:
        dir_x /= mag
        dir_y /= mag

    pool = get_particle_pool()
    for _ in range(count):
        spread_angle = math.atan2(dir_y, dir_x) + random.uniform(-0.5, 0.5)
        speed = random.uniform(80, 250)
        speed_x = speed * math.cos(spread_angle)
        speed_y = speed * math.sin(spread_angle)
        size = random.randint(1, 3)
        lifetime = random.uniform(0.2, 0.5)

        particle = pool.get(x, y, color, size, speed_x, speed_y, lifetime)
        group.add(particle)

