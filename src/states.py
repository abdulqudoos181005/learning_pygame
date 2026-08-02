# pyrefly: ignore [missing-import]
import pygame as pg
import random
import math
from sprites import Player, Enemy, Laser, Boss, PowerUp
from fx import Starfield, spawn_explosion, spawn_sparks
from save_system import SaveSystem

class State:
    """
    The abstract base class representing a generic Game State (State Pattern).
    
    All states (MenuState, PlayState, etc.) inherit from this class and
    override its lifecycle methods: handle_events, update, and draw.
    """
    def __init__(self, game):
        # Reference to the main Game class to allow state switching and screen size checks
        self.game = game

    def handle_events(self, events):
        """Processes user input events (keyboard, mouse, window closures)."""
        pass

    def update(self, dt):
        """Executes physics, mechanics, and timer updates for the current frame."""
        pass

    def draw(self, screen):
        """Draws visual assets, sprites, and UI elements to the active display screen."""
        pass


class MenuState(State):
    """
    State representing the Main Menu screen.
    
    Provides option selection (Play, High Scores, Quit) and a background starfield.
    """
    def __init__(self, game):
        super().__init__(game)
        # Parallax background with 80 stars for the menu
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=80)
        
        # Render the menu title with a nice neon-cyan color
        self.title_text = self.game.assets.title_font.render("SPACE SHOOTERS", True, (0, 255, 200))
        self.title_rect = self.title_text.get_rect(center=(self.game.width // 2, self.game.height // 3))
        
        # Available choices and navigation cursor index
        self.options = ["Play Game", "High Scores", "Quit"]
        self.selected_index = 0

    def handle_events(self, events):
        """Navigates options using the keyboard."""
        for event in events:
            if event.type == pg.KEYDOWN:
                # W or UP arrow goes up
                if event.key == pg.K_UP or event.key == pg.K_w:
                    self.selected_index = (self.selected_index - 1) % len(self.options)
                # S or DOWN arrow goes down
                elif event.key == pg.K_DOWN or event.key == pg.K_s:
                    self.selected_index = (self.selected_index + 1) % len(self.options)
                # ENTER or SPACE selects the currently highlighted option
                elif event.key == pg.K_RETURN or event.key == pg.K_SPACE:
                    self._select_option()

    def _select_option(self):
        """Executes the action corresponding to the highlighted option."""
        if self.selected_index == 0:
            # Transition to active gameplay
            self.game.change_state(PlayState(self.game))
        elif self.selected_index == 1:
            # Transition to high scores leaderboard
            self.game.change_state(HighScoresState(self.game))
        elif self.selected_index == 2:
            # Exit game
            self.game.quit()

    def update(self, dt):
        """Scroll the background stars."""
        self.starfield.update(dt)

    def draw(self, screen):
        # Clear screen with a very deep cosmic blue background
        screen.fill((10, 12, 22))
        
        # Draw background stars first
        self.starfield.draw(screen)
        
        # Draw Title with a offset dark green/teal shadow glow effect
        glow_surf = self.game.assets.title_font.render("SPACE SHOOTERS", True, (0, 100, 80))
        glow_rect = glow_surf.get_rect(center=(self.game.width // 2 + 2, self.game.height // 3 + 2))
        screen.blit(glow_surf, glow_rect)
        screen.blit(self.title_text, self.title_rect)
        
        # Draw menu options list
        for idx, option in enumerate(self.options):
            is_sel = (idx == self.selected_index)
            # Highlight selected option with Cyan, else show in muted slate-blue
            color = (0, 255, 255) if is_sel else (120, 140, 160)
            prefix = "▶  " if is_sel else "   "
            
            text_surf = self.game.assets.font.render(f"{prefix}{option}", True, color)
            # Place options stacked vertically, separated by 45 pixels
            rect = text_surf.get_rect(center=(self.game.width // 2, self.game.height // 2 + idx * 45))
            screen.blit(text_surf, rect)

        # Draw controller instruction banner at the bottom
        controls_text = self.game.assets.hud_font.render(
            "WASD / Arrows to Move   |   SPACE to Shoot   |   ESC to Pause", True, (80, 100, 120)
        )
        controls_rect = controls_text.get_rect(center=(self.game.width // 2, self.game.height - 40))
        screen.blit(controls_text, controls_rect)


class PlayState(State):
    """
    The primary gameplay state.
    
    Manages the player, active enemy waves, power-ups, particles, collisions,
    screen shaking, and heads-up display (HUD).
    """
    def __init__(self, game):
        super().__init__(game)
        # Background starfield (higher density of stars for active speed feel)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=120)
        
        # SCREEN SHAKE DOUBLE BUFFERING:
        # We draw the entire game onto a separate offscreen Surface (self.canvas).
        # When blitting this canvas onto the physical window surface (screen), we offset
        # it by random X and Y coordinates (shake_offset) to simulate impact tremors.
        self.canvas = pg.Surface((self.game.width, self.game.height))
        
        # Pygame sprite groups for clean collision and batch updating
        self.all_sprites = pg.sprite.Group()
        self.player_group = pg.sprite.GroupSingle()
        self.enemies = pg.sprite.Group()
        self.player_lasers = pg.sprite.Group()
        self.enemy_lasers = pg.sprite.Group()
        self.powerups = pg.sprite.Group()
        self.particles = pg.sprite.Group()
        
        # Initialize Player in the center-bottom of the viewport
        self.player = Player(self.game, self.game.width // 2, self.game.height - 100)
        self.player_group.add(self.player)
        self.all_sprites.add(self.player)
        
        # Game stats
        self.score = 0
        
        # Wave management
        self.wave = 1
        self.wave_intro_timer = 2.5 # Display "WAVE X" banner on screen for 2.5 seconds
        self.wave_enemies_to_spawn = 6
        self.wave_spawned_count = 0
        self.spawn_timer = 0.0
        self.spawn_delay = 1.6      # Time in seconds between enemy spawns
        self.boss_active = False
        self.boss_instance = None
        
        # Screen shake status
        self.shake_duration = 0.0
        self.shake_magnitude = 0
        self.shake_offset = pg.Vector2(0, 0)

    def trigger_shake(self, duration, magnitude):
        """Enables screen shake with a specific duration and strength."""
        self.shake_duration = duration
        self.shake_magnitude = magnitude

    def handle_events(self, events):
        """Checks for pause triggers (ESC key)."""
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    # Freeze the game by pushing the PauseState on top, passing self (PlayState) to resume later
                    self.game.change_state(PauseState(self.game, self))

    def update(self, dt):
        # 1. SCREEN SHAKE MATH
        if self.shake_duration > 0:
            self.shake_duration -= dt
            # Choose a random offset within [-magnitude, magnitude] range
            self.shake_offset.x = random.randint(-self.shake_magnitude, self.shake_magnitude)
            self.shake_offset.y = random.randint(-self.shake_magnitude, self.shake_magnitude)
        else:
            self.shake_offset.update(0, 0)

        # 2. BACKGROUND ANIMATION
        self.starfield.update(dt)
        
        # 3. ENEMY SPAWNING ALGORITHM
        if self.wave_intro_timer > 0:
            # Freeze enemy spawning while the wave intro text is showing
            self.wave_intro_timer -= dt
        else:
            # Wave 5 is the final Boss wave
            if self.wave == 5:
                if not self.boss_active and self.wave_spawned_count == 0:
                    self.boss_instance = Boss(self.game)
                    self.enemies.add(self.boss_instance)
                    self.all_sprites.add(self.boss_instance)
                    self.boss_active = True
                    self.wave_spawned_count = 1
            else:
                # Spawn regular waves of enemies
                if self.wave_spawned_count < self.wave_enemies_to_spawn:
                    self.spawn_timer -= dt
                    if self.spawn_timer <= 0:
                        self.spawn_timer = self.spawn_delay
                        
                        # Build enemy pool: scouts are standard, stingers spawn on Wave 2+, cruisers on Wave 3+
                        etypes = ["scout"]
                        if self.wave >= 2:
                            etypes.append("stinger")
                        if self.wave >= 3:
                            etypes.append("cruiser")
                            
                        # Balance type spawning probabilities based on current wave level
                        if self.wave == 2:
                            weights = [0.7, 0.3]
                        elif self.wave >= 3:
                            weights = [0.5, 0.35, 0.15]
                        else:
                            weights = [1.0] # 100% scouts on Wave 1
                            
                        etype = random.choices(etypes, weights=weights)[0]
                        # Instantiate enemy at random X position offscreen-top (-40 y)
                        enemy = Enemy(self.game, random.randint(60, self.game.width - 60), -40, enemy_type=etype)
                        self.enemies.add(enemy)
                        self.all_sprites.add(enemy)
                        self.wave_spawned_count += 1
                else:
                    # Wave finished spawning, wait until all enemies are destroyed to trigger next wave
                    if len(self.enemies) == 0:
                        self.wave += 1
                        self.wave_intro_timer = 2.5
                        self.wave_spawned_count = 0
                        self.wave_enemies_to_spawn = 6 + self.wave * 4
                        # Dynamically speed up spawn rates in higher waves
                        self.spawn_delay = max(0.4, 1.6 - self.wave * 0.15)
                        self.boss_active = False
            
            # Special check for Boss stage defeat
            if self.boss_active and len(self.enemies) == 0:
                self.wave += 1
                self.wave_intro_timer = 2.5
                self.wave_spawned_count = 0
                self.wave_enemies_to_spawn = 12
                self.spawn_delay = 1.0
                self.boss_active = False

        # 4. SPRITE & PARTICLE PHYSICS
        self.all_sprites.update(dt)
        self.particles.update(dt)

        # 5. COLLISION CHECKS
        self._check_collisions()

    def _check_collisions(self):
        """Handles hitbox intersections between game elements."""
        
        # 1. Player lasers hitting enemies
        # pg.sprite.groupcollide detects intersections between sprites of two groups.
        # Arguments: (group1, group2, dokill1, dokill2).
        # Setting dokill2=True automatically deletes the player laser on contact.
        hits = pg.sprite.groupcollide(self.enemies, self.player_lasers, False, True)
        for enemy, lasers in hits.items():
            for laser in lasers:
                # Spawn glowing blue sparks shooting upwards from impact point
                spawn_sparks(self.particles, laser.rect.centerx, laser.rect.top, (0, -1), color=(0, 255, 255), count=6)
                
                # Apply laser damage. get_hit returns True if enemy dies
                if enemy.get_hit(10):
                    self.score += enemy.score_value
                    # Large orange radial explosion
                    spawn_explosion(self.particles, enemy.rect.centerx, enemy.rect.centery, color=(255, 120, 0), count=25)
                    
                    # 15% probability to spawn a power-up drop
                    if random.random() < 0.15:
                        ptype = random.choices(["shield", "triple", "speed"], weights=[0.4, 0.3, 0.3])[0]
                        pup = PowerUp(self.game, enemy.rect.centerx, enemy.rect.centery, ptype)
                        self.powerups.add(pup)
                        self.all_sprites.add(pup)

        # 2. Enemy lasers hitting Player ship
        # pg.sprite.spritecollide checks one sprite against a group.
        # dokill=True deletes the enemy laser on impact.
        player_laser_hits = pg.sprite.spritecollide(self.player, self.enemy_lasers, True)
        for laser in player_laser_hits:
            # Spawn red sparks shooting downwards from impact
            spawn_sparks(self.particles, laser.rect.centerx, laser.rect.bottom, (0, 1), color=(255, 50, 50), count=8)
            
            # Apply damage to player. Returns True if player loses a life
            if self.player.get_hit(15):
                # Major blue explosion representing ship destruction
                spawn_explosion(self.particles, self.player.rect.centerx, self.player.rect.centery, color=(0, 200, 255), count=40)
                # If out of lives, transition to GameOver State
                if self.player.lives <= 0:
                    self.game.change_state(GameOverState(self.game, self.score))
                    return

        # 3. Enemy ships colliding directly with Player ship
        # (Crashing deals heavy damage and destroys the enemy)
        crash_hits = pg.sprite.spritecollide(self.player, self.enemies, True)
        for enemy in crash_hits:
            spawn_explosion(self.particles, enemy.rect.centerx, enemy.rect.centery, color=(255, 80, 0), count=30)
            self.score += enemy.score_value // 2
            
            if self.player.get_hit(30):
                spawn_explosion(self.particles, self.player.rect.centerx, self.player.rect.centery, color=(0, 200, 255), count=40)
                if self.player.lives <= 0:
                    self.game.change_state(GameOverState(self.game, self.score))
                    return

        # 4. Player ship absorbing floating Power-Ups
        pup_collects = pg.sprite.spritecollide(self.player, self.powerups, True)
        for pup in pup_collects:
            # White particle absorption effect
            spawn_sparks(self.particles, pup.rect.centerx, pup.rect.centery, (0, 0), color=(255, 255, 255), count=15)
            
            if pup.type == "shield":
                # Recharge player shield points
                self.player.shield = min(self.player.max_shield, self.player.shield + 40)
            elif pup.type == "triple":
                # Activate triple firing guns for 8 seconds
                self.player.triple_shot_timer = 8.0
            elif pup.type == "speed":
                # Activate 1.5x engine speed boost for 8 seconds
                self.player.speed_boost_timer = 8.0

    def draw(self, screen):
        # Draw everything onto the offscreen double-buffer canvas
        self.canvas.fill((10, 10, 15))
        
        # Starfield background scrolling
        self.starfield.draw(self.canvas)
        
        # Game elements
        self.all_sprites.draw(self.canvas)
        self.particles.draw(self.canvas)
        
        # Draw glowing neon shield barrier aura around player if shield points exist
        if self.player.shield > 0:
            shield_radius = 42
            shield_surf = pg.Surface((shield_radius * 2, shield_radius * 2), pg.SRCALPHA)
            # Create a pulsing transparency effect using a sine wave timer
            alpha = int(80 + math.sin(pg.time.get_ticks() * 0.01) * 30)
            
            # Draw outer shield shell ring
            pg.draw.circle(shield_surf, (0, 180, 255, alpha), (shield_radius, shield_radius), shield_radius, 3)
            # Draw semi-transparent shield filling interior
            pg.draw.circle(shield_surf, (0, 100, 255, alpha // 3), (shield_radius, shield_radius), shield_radius - 2)
            # Center the shield aura relative to player coordinates
            self.canvas.blit(shield_surf, shield_surf.get_rect(center=self.player.rect.center))

        # Render User Interface HUD (Health, Shields, Wave text, timers)
        self._draw_hud()

        # Final blit onto physical display screen, applying coordinates offset by screen shake values
        screen.blit(self.canvas, self.shake_offset)

    def _draw_hud(self):
        """Renders information layout on screen (Score, Wave, Health/Shield Meters, Powerup Timers)."""
        # 1. SCORE
        score_surf = self.game.assets.font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        self.canvas.blit(score_surf, (25, 20))
        
        # 2. WAVE TRACKER
        wave_txt = f"WAVE: {self.wave}" if self.wave < 5 else "WAVE: FINAL"
        wave_surf = self.game.assets.font.render(wave_txt, True, (0, 255, 200))
        self.canvas.blit(wave_surf, (self.game.width - wave_surf.get_width() - 25, 20))
        
        # 3. HEALTH & SHIELD PROGRESS BARS (Center Dashboard)
        bar_w, bar_h = 160, 10
        center_x = self.game.width // 2 - bar_w // 2
        
        # Health Bar: Dark Red background container, Green fill bar
        pg.draw.rect(self.canvas, (60, 10, 10), (center_x, 20, bar_w, bar_h), border_radius=3)
        h_fill = int((self.player.health / self.player.max_health) * bar_w)
        if h_fill > 0:
            pg.draw.rect(self.canvas, (0, 255, 100), (center_x, 20, h_fill, bar_h), border_radius=3)
        health_lbl = self.game.assets.hud_font.render("HP", True, (200, 220, 200))
        self.canvas.blit(health_lbl, (center_x - 30, 16))

        # Shield Bar: Dark Cyan container, Cyan fill bar
        pg.draw.rect(self.canvas, (10, 40, 50), (center_x, 36, bar_w, bar_h), border_radius=3)
        s_fill = int((self.player.shield / self.player.max_shield) * bar_w)
        if s_fill > 0:
            pg.draw.rect(self.canvas, (0, 200, 255), (center_x, 36, s_fill, bar_h), border_radius=3)
        shield_lbl = self.game.assets.hud_font.render("SH", True, (180, 220, 240))
        self.canvas.blit(shield_lbl, (center_x - 30, 32))

        # 4. LIVES SHIP ICONS (Bottom Left stack)
        for i in range(self.player.lives):
            # Draw mini player ships to denote lives
            life_img = self.game.assets.get_image("player", 22, 22)
            self.canvas.blit(life_img, (25 + i * 28, 55))

        # 5. POWER-UP EXPIRY METERS
        active_timers = []
        if self.player.triple_shot_timer > 0:
            active_timers.append(("TRIPLE SHOT", self.player.triple_shot_timer, (255, 50, 50)))
        if self.player.speed_boost_timer > 0:
            active_timers.append(("SPEED BOOST", self.player.speed_boost_timer, (255, 200, 0)))

        for idx, (label, timer, color) in enumerate(active_timers):
            # Render text label (e.g. "TRIPLE SHOT")
            lbl_surf = self.game.assets.hud_font.render(label, True, color)
            self.canvas.blit(lbl_surf, (25, self.game.height - 110 + idx * 30))
            
            # Render a shrinking bar showing duration remaining
            bar_len = int((timer / 8.0) * 100)
            pg.draw.rect(self.canvas, (40, 40, 40), (140, self.game.height - 100 + idx * 30, 100, 6))
            pg.draw.rect(self.canvas, color, (140, self.game.height - 100 + idx * 30, bar_len, 6))

        # 6. WAVE START BANNERS (Big overlay in center-screen)
        if self.wave_intro_timer > 0:
            overlay_txt = f"WAVE {self.wave}" if self.wave < 5 else "⚠ BOSS INCOMING ⚠"
            overlay_color = (0, 255, 200) if self.wave < 5 else (255, 0, 50)
            
            banner_surf = self.game.assets.title_font.render(overlay_txt, True, overlay_color)
            banner_rect = banner_surf.get_rect(center=(self.game.width // 2, self.game.height // 2.5))
            
            # Semi-transparent dark letterbox stripe behind text
            stripe = pg.Surface((self.game.width, 100), pg.SRCALPHA)
            stripe.fill((0, 0, 0, 140))
            self.canvas.blit(stripe, (0, self.game.height // 2.5 - 50))
            self.canvas.blit(banner_surf, banner_rect)

        # 7. BOSS HEALTH BAR (Top center overlay - only shows if boss is spawned)
        if self.boss_active and self.boss_instance and self.boss_instance.alive():
            boss_bar_w, boss_bar_h = 600, 14
            boss_x = self.game.width // 2 - boss_bar_w // 2
            
            boss_label = self.game.assets.hud_font.render("BOSS - COMMAND SHIP", True, (255, 50, 50))
            self.canvas.blit(boss_label, (boss_x, 70))
            
            # Red progress indicator bar
            pg.draw.rect(self.canvas, (50, 10, 10), (boss_x, 92, boss_bar_w, boss_bar_h), border_radius=4)
            b_fill = int((self.boss_instance.health / self.boss_instance.max_health) * boss_bar_w)
            if b_fill > 0:
                pg.draw.rect(self.canvas, (255, 0, 50), (boss_x, 92, b_fill, boss_bar_h), border_radius=4)
                # Outer white styling outline
                pg.draw.rect(self.canvas, (255, 255, 255), (boss_x, 92, boss_bar_w, boss_bar_h), 1, border_radius=4)


class PauseState(State):
    """
    State representing game execution freezing.
    
    Draws a semi-transparent screen overlay and ignores updates to sprites.
    """
    def __init__(self, game, previous_state):
        super().__init__(game)
        # Store references to frozen state to allow resuming later
        self.previous_state = previous_state
        
        # Transparent dark overlay cover
        self.overlay = pg.Surface((self.game.width, self.game.height), pg.SRCALPHA)
        self.overlay.fill((10, 12, 22, 200)) # Dark tint with 200 alpha

    def handle_events(self, events):
        """Allows resuming or quitting back to Menu State."""
        for event in events:
            if event.type == pg.KEYDOWN:
                # ESC or SPACE returns back to the active gameplay state
                if event.key == pg.K_ESCAPE or event.key == pg.K_SPACE:
                    self.game.change_state(self.previous_state)
                # Q returns to the main menu
                elif event.key == pg.K_q:
                    self.game.change_state(MenuState(self.game))

    def draw(self, screen):
        # 1. Render gameplay frames in background so player can see screen behind overlay
        self.previous_state.draw(screen)
        
        # 2. Layer transparency overlay
        screen.blit(self.overlay, (0, 0))
        
        # 3. Draw Pause menu elements
        title = self.game.assets.title_font.render("GAME PAUSED", True, (255, 200, 0))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 3))
        screen.blit(title, title_rect)
        
        hint = self.game.assets.font.render("Press SPACE / ESC to Resume", True, (220, 220, 220))
        hint_rect = hint.get_rect(center=(self.game.width // 2, self.game.height // 2))
        screen.blit(hint, hint_rect)
        
        quit_hint = self.game.assets.font.render("Press Q to Quit to Main Menu", True, (130, 150, 160))
        quit_rect = quit_hint.get_rect(center=(self.game.width // 2, self.game.height // 2 + 50))
        screen.blit(quit_hint, quit_rect)


class GameOverState(State):
    """
    State representing game-over condition.
    
    Accepts pilot text inputs to record names alongside their scores in SaveSystem.
    """
    def __init__(self, game, score):
        super().__init__(game)
        self.score = score
        self.save_system = SaveSystem()
        self.player_name = ""
        
        # Blinking cursor indicator variables
        self.cursor_visible = True
        self.cursor_timer = 0.0

    def handle_events(self, events):
        """Processes keyboard text letters to build the username string."""
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_RETURN:
                    # Save finalized score entry
                    final_name = self.player_name.strip() or "PILOT"
                    self.save_system.save_score(final_name, self.score)
                    # Transition to leaderboard
                    self.game.change_state(HighScoresState(self.game))
                elif event.key == pg.K_BACKSPACE:
                    # Remove last character
                    self.player_name = self.player_name[:-1]
                else:
                    # Restrict player name to alphanumeric, max length of 8 characters
                    if len(self.player_name) < 8 and event.unicode.isalnum():
                        self.player_name += event.unicode.upper()

    def update(self, dt):
        """Animates a blinking underscore cursor."""
        self.cursor_timer += dt
        if self.cursor_timer >= 0.4:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

    def draw(self, screen):
        # Clear screen with dark crimson tone
        screen.fill((25, 10, 12))
        
        # Draw "GAME OVER" title
        title = self.game.assets.title_font.render("GAME OVER", True, (255, 50, 50))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 4))
        screen.blit(title, title_rect)
        
        # Draw final score reached
        score_text = self.game.assets.font.render(f"Final Score: {self.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.game.width // 2, self.game.height // 3 + 20))
        screen.blit(score_text, score_rect)
        
        # Input instructions
        prompt_surf = self.game.assets.font.render("ENTER YOUR NAME:", True, (0, 255, 200))
        prompt_rect = prompt_surf.get_rect(center=(self.game.width // 2, self.game.height // 2))
        screen.blit(prompt_surf, prompt_rect)
        
        # Draw dynamic typed username + blinking cursor
        cursor_char = "_" if self.cursor_visible else " "
        display_name = f"{self.player_name}{cursor_char}"
        
        name_surf = self.game.assets.title_font.render(display_name, True, (255, 255, 255))
        name_rect = name_surf.get_rect(center=(self.game.width // 2, self.game.height // 2 + 60))
        screen.blit(name_surf, name_rect)
        
        # Bottom hint
        hint = self.game.assets.hud_font.render("Press ENTER to Save Score & View Leaderboard", True, (130, 140, 150))
        hint_rect = hint.get_rect(center=(self.game.width // 2, self.game.height - 80))
        screen.blit(hint, hint_rect)


class HighScoresState(State):
    """State representing the Top-10 Leaderboard listing loaded from SaveSystem."""
    def __init__(self, game):
        super().__init__(game)
        self.save_system = SaveSystem()
        self.scores_list = self.save_system.load_scores()

    def handle_events(self, events):
        """Allows returning back to the Main Menu."""
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_SPACE):
                    self.game.change_state(MenuState(self.game))

    def draw(self, screen):
        # Cosmic dark blue fill
        screen.fill((10, 12, 22))
        
        # Leaderboard Title
        title = self.game.assets.title_font.render("HIGH SCORES", True, (0, 200, 255))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 6))
        screen.blit(title, title_rect)
        
        # Draw high scores in a formatted 3-column table
        for idx, item in enumerate(self.scores_list[:10]):
            rank = f"{idx+1}."
            name = item.get("name", "PILOT")
            score = str(item.get("score", 0))
            
            # Gold color for 1st place, silver-cyan for top 3, muted grey for rest
            color = (255, 220, 0) if idx == 0 else ((200, 220, 240) if idx < 3 else (130, 150, 170))
            
            rank_surf = self.game.assets.font.render(rank, True, color)
            name_surf = self.game.assets.font.render(name, True, color)
            score_surf = self.game.assets.font.render(score, True, color)
            
            # Beautiful horizontal spacing alignments (Rank left, Name center, Score right)
            y_pos = self.game.height // 3.2 + idx * 36
            screen.blit(rank_surf, (self.game.width // 2 - 180, y_pos))
            screen.blit(name_surf, (self.game.width // 2 - 80, y_pos))
            screen.blit(score_surf, (self.game.width // 2 + 100, y_pos))
            
        # Return instructions
        hint = self.game.assets.font.render("Press ESC/SPACE to Main Menu", True, (100, 120, 140))
        hint_rect = hint.get_rect(center=(self.game.width // 2, self.game.height - 80))
        screen.blit(hint, hint_rect)
