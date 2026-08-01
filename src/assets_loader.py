import pygame as pg
import os

class AssetsLoader:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.font = None
        
        # Base paths
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(self.base_dir, "assets")
        self.images_dir = os.path.join(self.assets_dir, "images")
        self.sounds_dir = os.path.join(self.assets_dir, "sounds")
        self.fonts_dir = os.path.join(self.assets_dir, "fonts")
        
        # Initialize default system fonts
        pg.font.init()
        self.font = pg.font.SysFont("Trebuchet MS", 24)
        self.title_font = pg.font.SysFont("Trebuchet MS", 48)
        self.hud_font = pg.font.SysFont("Trebuchet MS", 20)

    def get_image(self, name, width=None, height=None):
        """Get cached image, load it if not cached, or generate a procedural fallback."""
        key = (name, width, height)
        if key in self.images:
            return self.images[key]
            
        img_path = os.path.join(self.images_dir, f"{name}.png")
        surface = None
        
        if os.path.exists(img_path):
            try:
                surface = pg.image.load(img_path).convert_alpha()
            except Exception as e:
                print(f"Warning: Failed to load image {name}.png: {e}")
                
        if surface is None:
            # Generate professional-looking procedural fallback graphics
            surface = self._generate_procedural_image(name, width or 64, height or 64)
            
        # Scale if requested
        if width and height:
            surface = pg.transform.smoothscale(surface, (width, height))
            
        self.images[key] = surface
        return surface

    def get_sound(self, name):
        """Get cached sound, load it if not cached, or return a dummy sound object."""
        if name in self.sounds:
            return self.sounds[name]
            
        sound_path = os.path.join(self.sounds_dir, f"{name}.wav")
        sound = None
        
        if pg.mixer.get_init():
            if os.path.exists(sound_path):
                try:
                    sound = pg.mixer.Sound(sound_path)
                except Exception as e:
                    print(f"Warning: Failed to load sound {name}.wav: {e}")
            
            if sound is None:
                # Return a Dummy sound so the game doesn't crash
                class DummySound:
                    def play(self, *args, **kwargs): pass
                    def stop(self): pass
                    def set_volume(self, vol): pass
                sound = DummySound()
                
        self.sounds[name] = sound
        return sound

    def _generate_procedural_image(self, name, w, h):
        """Draw high-quality vector/procedural graphics on the fly."""
        surf = pg.Surface((w, h), pg.SRCALPHA)
        
        if name == "player":
            # Sleek futuristic starfighter (Cyan / Neon Blue glow)
            points = [(w // 2, 4), (w - 4, h - 12), (w // 2, h - 20), (4, h - 12)]
            pg.draw.polygon(surf, (0, 200, 255), points)
            pg.draw.polygon(surf, (0, 100, 200), points, 3) # border
            # Cockpit glow
            pg.draw.circle(surf, (200, 255, 255), (w // 2, h // 2), 6)
            # Thruster nozzle
            pg.draw.rect(surf, (255, 100, 0), (w // 2 - 4, h - 12, 8, 8))
            
        elif name == "enemy_scout":
            # Fast scout ship (Purple, dart shaped)
            points = [(w // 2, h - 4), (w - 6, 8), (w // 2, 20), (6, 8)]
            pg.draw.polygon(surf, (180, 50, 255), points)
            pg.draw.polygon(surf, (100, 0, 180), points, 2)
            # Core
            pg.draw.circle(surf, (255, 100, 255), (w // 2, h // 2), 4)
            
        elif name == "enemy_stinger":
            # Aggressive stinger (Yellow/Amber, wasp-like)
            points = [(w // 2, h - 2), (w - 4, 12), (w // 2 + 6, 20), (w // 2 - 6, 20), (4, 12)]
            pg.draw.polygon(surf, (255, 180, 0), points)
            pg.draw.polygon(surf, (180, 100, 0), points, 2)
            # Glowing gun port
            pg.draw.circle(surf, (255, 255, 200), (w // 2, h - 6), 3)

        elif name == "enemy_cruiser":
            # Heavy cruiser (Grey/Crimson, tanky hexagonal design)
            points = [(w // 2, h - 8), (w - 8, h // 2), (w - 12, 6), (12, 6), (8, h // 2)]
            pg.draw.polygon(surf, (120, 120, 120), points)
            pg.draw.polygon(surf, (200, 0, 50), points, 3)
            # Power lines/glow
            pg.draw.rect(surf, (255, 0, 50), (w // 2 - 3, h // 2 - 10, 6, 16))

        elif name == "boss":
            # Giant Boss ship (Obsidian/Acid Green, mechanical skull style)
            points = [(w // 2, h - 10), (w - 10, h // 3), (w - 15, 8), (w // 2 + 20, 25), 
                      (w // 2 - 20, 25), (15, 8), (10, h // 3)]
            pg.draw.polygon(surf, (40, 50, 40), points)
            pg.draw.polygon(surf, (50, 255, 100), points, 4)
            # Glowing core
            pg.draw.circle(surf, (100, 255, 150), (w // 2, h // 2), 15)
            # Left/Right gun pods
            pg.draw.circle(surf, (50, 255, 100), (25, h // 3), 6)
            pg.draw.circle(surf, (50, 255, 100), (w - 25, h // 3), 6)

        elif name == "laser_player":
            # Light blue glowing beam
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (0, 200, 255), (w // 2 - 2, 0, 4, h), border_radius=2)
            # Inner white hot beam
            pg.draw.rect(surf, (255, 255, 255), (w // 2 - 1, 2, 2, h - 4), border_radius=1)

        elif name == "laser_enemy":
            # Blood red glowing beam
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (255, 0, 50), (w // 2 - 2, 0, 4, h), border_radius=2)
            # Inner orange-yellow beam
            pg.draw.rect(surf, (255, 180, 0), (w // 2 - 1, 2, 2, h - 4), border_radius=1)

        elif name == "laser_boss":
            # Heavy plasma beam (Green)
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (50, 255, 100), (w // 2 - 4, 0, 8, h), border_radius=3)
            pg.draw.rect(surf, (200, 255, 200), (w // 2 - 2, 3, 4, h - 6), border_radius=2)

        elif name == "powerup_shield":
            # Bright cyan bubble with 'S' inside
            pg.draw.circle(surf, (0, 200, 255), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (0, 100, 255, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("S", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        elif name == "powerup_triple":
            # Crimson sphere with 'T' inside
            pg.draw.circle(surf, (255, 50, 50), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (150, 20, 20, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("T", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        elif name == "powerup_speed":
            # Gold sphere with 'V' (Velocity) inside
            pg.draw.circle(surf, (255, 200, 0), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (180, 140, 0, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("V", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
            
        else:
            # Default fallback box
            pg.draw.rect(surf, (255, 0, 255), (0, 0, w, h), 2)
            pg.draw.line(surf, (255, 0, 255), (0, 0), (w, h), 2)
            pg.draw.line(surf, (255, 0, 255), (w, 0), (0, h), 2)
            
        return surf
