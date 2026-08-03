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
    
    Uses pg.SRCALPHA to enable smooth alpha transparency fading.
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
        
        # Create a surface with an alpha channel (transparent background)
        self.image = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._update_image()

    def _update_image(self):
        """Clears the particle surface and redraws it with current size and transparency level."""
        self.image.fill((0, 0, 0, 0)) # Clear with transparency
        
        # Calculate alpha (0 to 255) based on remaining life ratio
        alpha = int((self.life / self.max_life) * 255)
        
        # Extract RGB values (ignore original alpha if any)
        base_color = self.color[:3]
        
        # Draw a filled circle in the center of the particle's local surface
        pg.draw.circle(self.image, (*base_color, alpha), (self.size, self.size), self.size)

    def update(self, dt):
        """Updates particle lifespan, position, size, and redraws it."""
        self.life -= dt
        # Remove particle when its life runs out
        if self.life <= 0:
            self.kill()
            return
            
        # Update physical coordinates
        self.x += self.speed_x * dt
        self.y += self.speed_y * dt
        self.rect.center = (int(self.x), int(self.y))
        
        # Linearly shrink the particle as it ages
        self.size = max(1, int(self.start_size * (self.life / self.max_life)))
        self._update_image()


def spawn_explosion(group, x, y, color=(255, 100, 0), count=25, speed_range=(50, 200), size_range=(2, 6)):
    """
    Spawns multiple particles in a radial direction to create an explosion effect.
    
    This is triggered when enemies are destroyed or when the player takes heavy damage.
    """
    for _ in range(count):
        # Choose a random angle (0 to 360 degrees in radians)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        
        # Resolve speed into X and Y component velocities using trigonometry
        speed_x = speed * math.cos(angle)
        speed_y = speed * math.sin(angle)
        
        size = random.randint(*size_range)
        lifetime = random.uniform(0.3, 0.8)
        
        # Create and add particle to the sprite group
        particle = Particle(x, y, color, size, speed_x, speed_y, lifetime)
        group.add(particle)


def spawn_sparks(group, x, y, direction_vector, color=(0, 255, 255), count=8):
    """
    Spawns particles oriented along a specific direction vector to simulate impact sparks.
    
    Used when a laser hits a target to create a satisfying impact flare.
    """
    dir_x, dir_y = direction_vector
    
    # Normalize the direction vector to get a unit vector of length 1.0
    mag = math.sqrt(dir_x**2 + dir_y**2)
    if mag > 0:
        dir_x /= mag
        dir_y /= mag
        
    for _ in range(count):
        # Calculate impact angle and add a slight random spread (up to ~30 degrees or 0.5 rad)
        spread_angle = math.atan2(dir_y, dir_x) + random.uniform(-0.5, 0.5)
        
        # Speed of sparks
        speed = random.uniform(80, 250)
        speed_x = speed * math.cos(spread_angle)
        speed_y = speed * math.sin(spread_angle)
        
        size = random.randint(1, 3)
        lifetime = random.uniform(0.2, 0.5)
        
        particle = Particle(x, y, color, size, speed_x, speed_y, lifetime)
        group.add(particle)

