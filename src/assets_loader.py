# pyrefly: ignore [missing-import]
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
        self.title_font = None
        self.hud_font = None
        self.font_sources = {"title": None, "ui": None, "hud": None}
        
        # Calculate base directory paths
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(self.base_dir, "assets")
        self.fonts_dir = os.path.join(self.assets_dir, "fonts")
        
        # Build fast lookup indexes for organized assets
        self._image_index = {}
        self._sound_index = {}
        self._build_asset_indexes()
        
        # Semantic aliases for instant backward compatibility & intuitive game entity mapping
        self._aliases = {
            # Player Ships
            "player": "player_fleet/interceptor_strike_blue",
            "player_interceptor": "player_fleet/interceptor_strike_blue",
            "player_cruiser": "player_fleet/heavy_cruiser_assault_blue",
            "player_vanguard": "player_fleet/stealth_vanguard_bomber_blue",
            
            # Enemies
            "enemy_scout": "alien_armada/bio_swarm/bio_scout_dart",
            "enemy_stinger": "alien_armada/crimson_raiders/crimson_wasp_stinger",
            "enemy_cruiser": "alien_armada/shadow_corps/shadow_heavy_cruiser",
            "boss": "alien_armada/boss_motherships/mothership_saucer_crimson_red",
            
            # Lasers & Projectiles
            "laser_player": "weapons_projectiles/blue_photon_beams/laser_blue_stream_long",
            "laser_enemy": "weapons_projectiles/red_crimson_beams/laser_red_stream_long",
            "laser_power": "weapons_projectiles/red_crimson_beams/laser_red_heavy_slug",
            "laser_tier3": "weapons_projectiles/blue_photon_beams/laser_blue_wide_wave",
            "laser_boss": "weapons_projectiles/green_plasma_beams/laser_green_wide_wave",
            
            # Power-ups & Pickups
            "powerup_shield": "powerups_pickups/powerup_orbs/orb_shield_blue",
            "powerup_triple": "powerups_pickups/powerup_orbs/orb_star_red",
            "powerup_health": "powerups_pickups/medical_capsules/capsule_health_green",
            "powerup_power_laser": "powerups_pickups/powerup_orbs/orb_bolt_red",
            "powerup_missile": "powerups_pickups/powerup_orbs/orb_bolt_yellow",
            "powerup_speed": "powerups_pickups/medical_capsules/capsule_velocity_yellow",
            
            # Audio
            "laser": "audio/sfx/laser_blaster_crisp",
            "laser_pew": "audio/sfx/laser_retro_pew_01",
            "boss_music": "audio/music/theme_boss_arcade_battle",
            "player_death": "audio/sfx/player_death_alarm",
            "game_over": "audio/sfx/game_over_defeat",
            "shield_up": "audio/sfx/shield_activate",
            "shield_down": "audio/sfx/shield_depleted",
            "powerup": "audio/sfx/powerup_bonus_chime",
            "zap": "audio/sfx/alien_emp_zap",
        }
        
        # Sprint 10: load each TTF independently so titles, UI, and HUD have distinct roles.
        pg.font.init()
        self.title_font, self.font_sources["title"] = self._load_role_font(
            "audiowide_cyber_display.ttf", size=42, fallback_size=48
        )
        self.font, self.font_sources["ui"] = self._load_role_font(
            "vector_future_bold.ttf", size=22, fallback_size=24
        )
        self.hud_font, self.font_sources["hud"] = self._load_role_font(
            "vector_future_thin.ttf", size=18, fallback_size=20
        )

    def _load_role_font(self, filename, size, fallback_size):
        """Load one TTF for a typography role; fall back to Trebuchet MS only for that role."""
        path = os.path.join(self.fonts_dir, filename)
        if os.path.exists(path):
            try:
                return pg.font.Font(path, size), os.path.basename(path)
            except Exception:
                pass
        return pg.font.SysFont("Trebuchet MS", fallback_size), None

    def _build_asset_indexes(self):
        """Scans the assets directory tree and indexes files for fast O(1) resolution."""
        if not os.path.exists(self.assets_dir):
            return
            
        for root, _, files in os.walk(self.assets_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                rel_path = os.path.relpath(os.path.join(root, file), self.assets_dir).replace("\\", "/")
                key_without_ext = os.path.splitext(rel_path)[0]
                base_name = os.path.splitext(file)[0]
                full_path = os.path.join(root, file)
                
                if ext in (".png", ".jpg", ".jpeg"):
                    self._image_index[key_without_ext] = full_path
                    self._image_index[base_name] = full_path
                    self._image_index[rel_path] = full_path
                elif ext in (".wav", ".ogg", ".mp3"):
                    self._sound_index[key_without_ext] = full_path
                    self._sound_index[base_name] = full_path
                    self._sound_index[rel_path] = full_path

    def _resolve_image_path(self, name):
        """Resolves an image name using aliases, indexed paths, or meteor/asteroid rules."""
        # 1. Check direct alias
        mapped_name = self._aliases.get(name, name)
        if mapped_name in self._image_index:
            return self._image_index[mapped_name]
            
        # 2. Check base name directly in index
        if name in self._image_index:
            return self._image_index[name]
            
        # 3. Dynamic asteroid matching (e.g., asteroid_large_brown -> space_hazards/carbon_meteors/meteor_carbon_titan_01)
        if name.startswith("asteroid_"):
            parts = name.split("_")
            size = parts[1] if len(parts) > 1 else "large"
            color = parts[2] if len(parts) > 2 else "brown"
            cat = "carbon_meteors" if color == "brown" else "iron_meteors"
            color_slug = "carbon" if color == "brown" else "iron"
            
            size_map = {
                "large": "titan_01",
                "medium": "medium_01",
                "small": "small_01",
                "tiny": "tiny_debris_01"
            }
            meteor_file = f"meteor_{color_slug}_{size_map.get(size, 'titan_01')}"
            key = f"space_hazards/{cat}/{meteor_file}"
            if key in self._image_index:
                return self._image_index[key]
                
        return None

    def get_image(self, name, width=None, height=None):
        """
        Retrieves an image from cache, or loads it from disk, or builds a procedural fallback.
        
        Also handles scaling to the requested dimensions.
        """
        # Create a unique cache key that includes target dimensions
        key = (name, width, height)
        if key in self.images:
            return self.images[key]
            
        img_path = self._resolve_image_path(name)
        surface = None
        
        # Try loading the PNG file
        if img_path and os.path.exists(img_path):
            try:
                raw_surf = pg.image.load(img_path)
                surface = raw_surf.convert_alpha() if pg.display.get_surface() is not None else raw_surf
            except Exception as e:
                print(f"Warning: Failed to load image {name} ({img_path}): {e}")
                
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
            
        mapped_name = self._aliases.get(name, name)
        sound_path = self._sound_index.get(mapped_name) or self._sound_index.get(name)
        sound = None
        
        # Check if the pygame audio mixer is initialized and active
        if pg.mixer.get_init():
            if sound_path and os.path.exists(sound_path):
                try:
                    sound = pg.mixer.Sound(sound_path)
                except Exception as e:
                    print(f"Warning: Failed to load sound {name} ({sound_path}): {e}")
        
        # If audio file is missing, mixer is inactive, or loading failed, provide a mock sound object
        if sound is None:
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

        elif name == "laser_power":
            # Power laser: thick red beam with bright white-yellow core (2x damage)
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (220, 0, 0),     (w // 2 - 3, 0, 6, h), border_radius=2)
            pg.draw.rect(surf, (255, 180, 50),  (w // 2 - 1, 2, 2, h - 4), border_radius=1)

        elif name == "laser_tier3":
            # Tier-3 laser: thicker purple beam with bright white-cyan core
            surf = pg.Surface((w, h), pg.SRCALPHA)
            pg.draw.rect(surf, (128, 0, 255),   (w // 2 - 4, 0, 8, h), border_radius=3)
            pg.draw.rect(surf, (210, 210, 255), (w // 2 - 1, 2, 2, h - 4), border_radius=1)

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

        elif name == "powerup_health":
            # Health boost orb: glowing green cross (medical)
            pg.draw.circle(surf, (0, 220, 80), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (0, 100, 40, 100), (w // 2, h // 2), w // 2 - 6)
            # Draw cross shape
            cx, cy = w // 2, h // 2
            bar = max(3, w // 6)
            pg.draw.rect(surf, (255, 255, 255), (cx - bar, cy - 1, bar * 2, 3))
            pg.draw.rect(surf, (255, 255, 255), (cx - 1, cy - bar, 3, bar * 2))

        elif name == "powerup_power_laser":
            # Power laser orb: glowing crimson-red shell with 'P' label
            pg.draw.circle(surf, (220, 0, 0),    (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (120, 0, 0, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("P", True, (255, 180, 50))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        elif name == "powerup_missile":
            # Missile powerup orb: orange shell with 'M' label
            pg.draw.circle(surf, (255, 120, 0),  (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (150, 70, 0, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("M", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        elif name == "missile":
            # Homing missile: orange body with pointed tip and fin detail
            # Body
            pg.draw.rect(surf, (255, 100, 0), (w // 2 - 3, h // 4, 6, h // 2), border_radius=2)
            # Nose cone (triangle pointing up)
            tip_pts = [(w // 2, 0), (w // 2 - 4, h // 4), (w // 2 + 4, h // 4)]
            pg.draw.polygon(surf, (255, 200, 0), tip_pts)
            # Left fin
            pg.draw.polygon(surf, (200, 60, 0), [(w // 2 - 3, h // 2), (w // 2 - 8, h * 3 // 4), (w // 2 - 3, h * 3 // 4)])
            # Right fin
            pg.draw.polygon(surf, (200, 60, 0), [(w // 2 + 3, h // 2), (w // 2 + 8, h * 3 // 4), (w // 2 + 3, h * 3 // 4)])
            # Exhaust glow
            pg.draw.ellipse(surf, (255, 255, 100), (w // 2 - 3, h * 3 // 4, 6, 4))

        elif name == "powerup_speed":
            # Speed boost orb: golden-yellow shell containing letter 'V' (Velocity)
            pg.draw.circle(surf, (255, 200, 0), (w // 2, h // 2), w // 2 - 4, 3)
            pg.draw.circle(surf, (180, 140, 0, 100), (w // 2, h // 2), w // 2 - 6)
            txt = self.hud_font.render("V", True, (255, 255, 255))
            surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        elif name.startswith("asteroid_"):
            # Asteroid hazard: irregular rock, sized by the requested chunk and rock color.
            if "brown" in name:
                rock_fill = (120, 80, 45)
                rock_outline = (170, 120, 80)
            else:
                rock_fill = (130, 130, 130)
                rock_outline = (190, 190, 190)

            points = [
                (w * 0.20, h * 0.10), (w * 0.55, h * 0.05), (w * 0.88, h * 0.25),
                (w * 0.95, h * 0.60), (w * 0.75, h * 0.92), (w * 0.42, h * 0.98),
                (w * 0.10, h * 0.78), (w * 0.02, h * 0.45), (w * 0.08, h * 0.20)
            ]
            pg.draw.polygon(surf, rock_fill, points)
            pg.draw.polygon(surf, rock_outline, points, 2)
            craters = [
                (w * 0.28, h * 0.35, w * 0.12, h * 0.10),
                (w * 0.62, h * 0.50, w * 0.16, h * 0.12),
                (w * 0.38, h * 0.68, w * 0.12, h * 0.09),
            ]
            for cx, cy, cw, ch in craters:
                pg.draw.ellipse(surf, (80, 60, 40) if "brown" in name else (90, 90, 90), (cx, cy, cw, ch))

        else:
            # Fallback graphic: bright magenta box with crosses so it stands out as an error
            pg.draw.rect(surf, (255, 0, 255), (0, 0, w, h), 2)
            pg.draw.line(surf, (255, 0, 255), (0, 0), (w, h), 2)
            pg.draw.line(surf, (255, 0, 255), (w, 0), (0, h), 2)

        return surf

