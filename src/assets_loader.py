import pygame as pg
import os

class AssetsLoader:
    """
    Manages loading, caching, and fallbacks for game assets (Images, Sounds, Fonts).
    
    Design Patterns:
    - Cached Resource Pattern (Memoization): Loads files from disk once and keeps them
      in memory (self.images, self.sounds) to avoid slow file I/O operations on subsequent requests.
    - Graceful Procedural Fallbacks: If PNG/WAV files are missing, the system draws
      them dynamically using vector shapes (proc-gen) or spawns a silent DummySound class
      to ensure the game always runs and never crashes due to missing assets.
    """
    def __init__(self):
        # Cache dictionaries
        self.images = {}
        self.sounds = {}
        self.font = None
        
        # Calculate base directory paths
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(self.base_dir, "assets")
        self.images_dir = os.path.join(self.assets_dir, "images")
        self.sounds_dir = os.path.join(self.assets_dir, "sounds")
        self.fonts_dir = os.path.join(self.assets_dir, "fonts")
        
        # Initialize default system fonts. Fallback to default sans-serif font
        # if "Trebuchet MS" is not installed on the operating system.
        pg.font.init()
        self.font = pg.font.SysFont("Trebuchet MS", 24)
        self.title_font = pg.font.SysFont("Trebuchet MS", 48)
        self.hud_font = pg.font.SysFont("Trebuchet MS", 20)

    def get_image(self, name, width=None, height=None):
        """
        Retrieves an image from cache, or loads it from disk, or builds a procedural fallback.
        
        Also handles scaling to the requested dimensions.
        """
        # Create a unique cache key that includes target dimensions
        key = (name, width, height)
        if key in self.images:
            return self.images[key]
            
        img_path = os.path.join(self.images_dir, f"{name}.png")
        surface = None
        
        # Try loading the PNG file from assets/images/
        if os.path.exists(img_path):
            try:
                # convert_alpha() translates the image pixel format to optimize blitting speed
                # and preserves transparency (alpha channel) information.
                surface = pg.image.load(img_path).convert_alpha()
            except Exception as e:
                print(f"Warning: Failed to load image {name}.png: {e}")
                
        # If the file is missing or failed to load, generate high-quality procedural vector art
        if surface is None:
            surface = self._generate_procedural_image(name, width or 64, height or 64)
            
        # Scale the surface using smooth interpolation if dimensions were specified
        if width and height:
            surface = pg.transform.smoothscale(surface, (width, height))
            
        # Store in cache dictionary
        self.images[key] = surface
        return surface

    def get_sound(self, name):
        """
        Retrieves a sound from cache, loads it from disk, or provides a silent dummy fallback.
        """
        if name in self.sounds:
            return self.sounds[name]
            
        sound_path = os.path.join(self.sounds_dir, f"{name}.wav")
        sound = None
        
        # Check if the pygame audio mixer is initialized and active
        if pg.mixer.get_init():
            if os.path.exists(sound_path):
                try:
                    sound = pg.mixer.Sound(sound_path)
                except Exception as e:
                    print(f"Warning: Failed to load sound {name}.wav: {e}")
            
            # If WAV file is missing, create a mock sound class
            if sound is None:
                # Dummy class implements standard mixer.Sound interface so calls
                # to sound.play() or sound.stop() will do nothing rather than crash the game.
                class DummySound:
                    def play(self, *args, **kwargs): pass
                    def stop(self): pass
                    def set_volume(self, vol): pass
                sound = DummySound()
                
        self.sounds[name] = sound
        return sound

    def _generate_procedural_image(self, name, w, h):
        """
        Procedurally draws assets using Pygame's vector shape rendering functions.
        
        Runs when PNG files are missing to ensure the game has working graphics.
        """
        # Create a surface supporting transparency (SRCALPHA)
        surf = pg.Surface((w, h), pg.SRCALPHA)
        
        if name == "player":
            # Sleek futuristic starfighter (Cyan body with neon blue border and orange thruster nozzle)
            points = [(w // 2, 4), (w - 4, h - 12), (w // 2, h - 20), (4, h - 12)]
            pg.draw.polygon(surf, (0, 200, 255), points)
            pg.draw.polygon(surf, (0, 100, 200), points, 3) # border
            # Cockpit glow circle
            pg.draw.circle(surf, (200, 255, 255), (w // 2, h // 2), 6)
            # Thruster flame box
            pg.draw.rect(surf, (255, 100, 0), (w // 2 - 4, h - 12, 8, 8))
            
        elif name == "enemy_scout":
            # Fast scout ship (Purple, triangular dart shape)
            points = [(w // 2, h - 4), (w - 6, 8), (w // 2, 20), (6, 8)]
            pg.draw.polygon(surf, (180, 50, 255), points)
            pg.draw.polygon(surf, (100, 0, 180), points, 2)
            # Energy core glow
            pg.draw.circle(surf, (255, 100, 255), (w // 2, h // 2), 4)
            
        elif name == "enemy_stinger":
            # Aggressive stinger (Yellow/Amber, wasp-like design)
            points = [(w // 2, h - 2), (w - 4, 12), (w // 2 + 6, 20), (w // 2 - 6, 20), (4, 12)]
            pg.draw.polygon(surf, (255, 180, 0), points)
            pg.draw.polygon(surf, (180, 100, 0), points, 2)
            # Glowing yellow weapon tip
            pg.draw.circle(surf, (255, 255, 200), (w // 2, h - 6), 3)

        elif name == "enemy_cruiser":
            # Heavy cruiser (Grey/Crimson, hexagonal tank-like build)
            points = [(w // 2, h - 8), (w - 8, h // 2), (w - 12, 6), (12, 6), (8, h // 2)]
            pg.draw.polygon(surf, (120, 120, 120), points)
            pg.draw.polygon(surf, (200, 0, 50), points, 3)
            # Glowing core block
            pg.draw.rect(surf, (255, 0, 50), (w // 2 - 3, h // 2 - 10, 6, 16))

        elif name == "boss":
            # Giant Boss ship (Obsidian grey shield with glowing acid-green outline and pods)
            points = [(w // 2, h - 10), (w - 10, h // 3), (w - 15, 8), (w // 2 + 20, 25), 
                      (w // 2 - 20, 25), (15, 8), (10, h // 3)]
            pg.draw.polygon(surf, (40, 50, 40), points)
            pg.draw.polygon(surf, (50, 255, 100), points, 4)
            # Heavy engine core circular generator
            pg.draw.circle(surf, (100, 255, 150), (w // 2, h // 2), 15)
            # Left & Right wing weapons
            pg.draw.circle(surf, (50, 255, 100), (25, h // 3), 6)
            pg.draw.circle(surf, (50, 255, 100), (w - 25, h // 3), 6)

        elif name == "laser_player":
            # Player projectile: light-blue vertical glowing laser line
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (0, 200, 255), (w // 2 - 2, 0, 4, h), border_radius=2)
            # White core for brightness contrast
            pg.draw.rect(surf, (255, 255, 255), (w // 2 - 1, 2, 2, h - 4), border_radius=1)

        elif name == "laser_enemy":
            # Enemy projectile: crimson red vertical laser line
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (255, 0, 50), (w // 2 - 2, 0, 4, h), border_radius=2)
            # Orange inner line
            pg.draw.rect(surf, (255, 180, 0), (w // 2 - 1, 2, 2, h - 4), border_radius=1)

        elif name == "laser_boss":
            # Boss heavy projectile: thick glowing green plasma beam
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (50, 255, 100), (w // 2 - 4, 0, 8, h), border_radius=3)
            pg.draw.rect(surf, (200, 255, 200), (w // 2 - 2, 3, 4, h - 6), border_radius=2)

        elif name == "powerup_shield":
            # Shield orb: glowing cyan bubble shell containing letter 'S'
            pg.draw.circle(surf, (0, 200, 255), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (0, 100, 255, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("S", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        elif name == "powerup_triple":
            # Triple shot orb: glowing crimson shell containing letter 'T'
            pg.draw.circle(surf, (255, 50, 50), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (150, 20, 20, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("T", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        elif name == "powerup_speed":
            # Speed boost orb: golden-yellow shell containing letter 'V' (Velocity)
            pg.draw.circle(surf, (255, 200, 0), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (180, 140, 0, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("V", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
            
        else:
            # Fallback graphic: bright magenta box with crosses so it stands out as an error
            pg.draw.rect(surf, (255, 0, 255), (0, 0, w, h), 2)
            pg.draw.line(surf, (255, 0, 255), (0, 0), (w, h), 2)
            pg.draw.line(surf, (255, 0, 255), (w, 0), (0, h), 2)
            
        return surf

