import pygame as pg
import random
import math
from sprites import Player, Enemy, Laser, Boss, PowerUp
from fx import Starfield, spawn_explosion, spawn_sparks
from save_system import SaveSystem

class State:
    def __init__(self, game):
        self.game = game

    def handle_events(self, events):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass


class MenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=80)
        self.title_text = self.game.assets.title_font.render("SPACE SHOOTERS", True, (0, 255, 200))
        self.title_rect = self.title_text.get_rect(center=(self.game.width // 2, self.game.height // 3))
        
        self.options = ["Play Game", "High Scores", "Quit"]
        self.selected_index = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_UP or event.key == pg.K_w:
                    self.selected_index = (self.selected_index - 1) % len(self.options)
                elif event.key == pg.K_DOWN or event.key == pg.K_s:
                    self.selected_index = (self.selected_index + 1) % len(self.options)
                elif event.key == pg.K_RETURN or event.key == pg.K_SPACE:
                    self._select_option()

    def _select_option(self):
        if self.selected_index == 0:
            self.game.change_state(PlayState(self.game))
        elif self.selected_index == 1:
            self.game.change_state(HighScoresState(self.game))
        elif self.selected_index == 2:
            self.game.quit()

    def update(self, dt):
        self.starfield.update(dt)

    def draw(self, screen):
        screen.fill((10, 12, 22))
        
        # Parallax background
        self.starfield.draw(screen)
        
        # Draw Title with a subtle glow
        glow_surf = self.game.assets.title_font.render("SPACE SHOOTERS", True, (0, 100, 80))
        glow_rect = glow_surf.get_rect(center=(self.game.width // 2 + 2, self.game.height // 3 + 2))
        screen.blit(glow_surf, glow_rect)
        screen.blit(self.title_text, self.title_rect)
        
        # Draw options
        for idx, option in enumerate(self.options):
            is_sel = (idx == self.selected_index)
            color = (0, 255, 255) if is_sel else (120, 140, 160)
            prefix = "▶  " if is_sel else "   "
            text_surf = self.game.assets.font.render(f"{prefix}{option}", True, color)
            rect = text_surf.get_rect(center=(self.game.width // 2, self.game.height // 2 + idx * 45))
            screen.blit(text_surf, rect)

        # Drawing controls info at the bottom
        controls_text = self.game.assets.hud_font.render(
            "WASD / Arrows to Move   |   SPACE to Shoot   |   ESC to Pause", True, (80, 100, 120)
        )
        controls_rect = controls_text.get_rect(center=(self.game.width // 2, self.game.height - 40))
        screen.blit(controls_text, controls_rect)


class PlayState(State):
    def __init__(self, game):
        super().__init__(game)
        self.starfield = Starfield(self.game.width, self.game.height, num_stars=120)
        
        # Double-buffered canvas for screen shake
        self.canvas = pg.Surface((self.game.width, self.game.height))
        
        # Sprite groups
        self.all_sprites = pg.sprite.Group()
        self.player_group = pg.sprite.GroupSingle()
        self.enemies = pg.sprite.Group()
        self.player_lasers = pg.sprite.Group()
        self.enemy_lasers = pg.sprite.Group()
        self.powerups = pg.sprite.Group()
        self.particles = pg.sprite.Group()
        
        # Initialize Player
        self.player = Player(self.game, self.game.width // 2, self.game.height - 100)
        self.player_group.add(self.player)
        self.all_sprites.add(self.player)
        
        # Score & Stats
        self.score = 0
        
        # Wave tracking
        self.wave = 1
        self.wave_intro_timer = 2.5 # Intro banner duration
        self.wave_enemies_to_spawn = 6
        self.wave_spawned_count = 0
        self.spawn_timer = 0.0
        self.spawn_delay = 1.6
        self.boss_active = False
        self.boss_instance = None
        
        # Screen shake
        self.shake_duration = 0.0
        self.shake_magnitude = 0
        self.shake_offset = pg.Vector2(0, 0)

    def trigger_shake(self, duration, magnitude):
        self.shake_duration = duration
        self.shake_magnitude = magnitude

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.game.change_state(PauseState(self.game, self))

    def update(self, dt):
        # Update shake offset
        if self.shake_duration > 0:
            self.shake_duration -= dt
            self.shake_offset.x = random.randint(-self.shake_magnitude, self.shake_magnitude)
            self.shake_offset.y = random.randint(-self.shake_magnitude, self.shake_magnitude)
        else:
            self.shake_offset.update(0, 0)

        # Background scrolling
        self.starfield.update(dt)
        
        # Enemy Spawning logic
        if self.wave_intro_timer > 0:
            self.wave_intro_timer -= dt
        else:
            # Handle Boss stage (Wave 5)
            if self.wave == 5:
                if not self.boss_active and self.wave_spawned_count == 0:
                    self.boss_instance = Boss(self.game)
                    self.enemies.add(self.boss_instance)
                    self.all_sprites.add(self.boss_instance)
                    self.boss_active = True
                    self.wave_spawned_count = 1
            else:
                # Regular wave spawning
                if self.wave_spawned_count < self.wave_enemies_to_spawn:
                    self.spawn_timer -= dt
                    if self.spawn_timer <= 0:
                        self.spawn_timer = self.spawn_delay
                        # Build pool of enemy types based on current wave
                        etypes = ["scout"]
                        if self.wave >= 2:
                            etypes.append("stinger")
                        if self.wave >= 3:
                            etypes.append("cruiser")
                            
                        # Balance type probabilities
                        if self.wave == 2:
                            weights = [0.7, 0.3]
                        elif self.wave >= 3:
                            weights = [0.5, 0.35, 0.15]
                        else:
                            weights = [1.0]
                            
                        etype = random.choices(etypes, weights=weights)[0]
                        enemy = Enemy(self.game, random.randint(60, self.game.width - 60), -40, enemy_type=etype)
                        self.enemies.add(enemy)
                        self.all_sprites.add(enemy)
                        self.wave_spawned_count += 1
                else:
                    # Wave finished spawning, check if all cleared to start next wave
                    if len(self.enemies) == 0:
                        self.wave += 1
                        self.wave_intro_timer = 2.5
                        self.wave_spawned_count = 0
                        self.wave_enemies_to_spawn = 6 + self.wave * 4
                        self.spawn_delay = max(0.4, 1.6 - self.wave * 0.15)
                        self.boss_active = False
            
            # Boss specific level-cleared check
            if self.boss_active and len(self.enemies) == 0:
                self.wave += 1
                self.wave_intro_timer = 2.5
                self.wave_spawned_count = 0
                self.wave_enemies_to_spawn = 12
                self.spawn_delay = 1.0
                self.boss_active = False

        # Update sprites
        self.all_sprites.update(dt)
        self.particles.update(dt)

        # COLLISION HANDLING
        self._check_collisions()

    def _check_collisions(self):
        # 1. Player lasers hitting enemies
        hits = pg.sprite.groupcollide(self.enemies, self.player_lasers, False, True)
        for enemy, lasers in hits.items():
            for laser in lasers:
                # Spawn spark particles
                spawn_sparks(self.particles, laser.rect.centerx, laser.rect.top, (0, -1), color=(0, 255, 255), count=6)
                
                # Apply hit damage
                if enemy.get_hit(10): # enemy destroyed
                    self.score += enemy.score_value
                    spawn_explosion(self.particles, enemy.rect.centerx, enemy.rect.centery, color=(255, 120, 0), count=25)
                    
                    # Random chance to spawn power-up (15% rate)
                    if random.random() < 0.15:
                        ptype = random.choices(["shield", "triple", "speed"], weights=[0.4, 0.3, 0.3])[0]
                        pup = PowerUp(self.game, enemy.rect.centerx, enemy.rect.centery, ptype)
                        self.powerups.add(pup)
                        self.all_sprites.add(pup)

        # 2. Enemy lasers hitting Player
        player_laser_hits = pg.sprite.spritecollide(self.player, self.enemy_lasers, True)
        for laser in player_laser_hits:
            spawn_sparks(self.particles, laser.rect.centerx, laser.rect.bottom, (0, 1), color=(255, 50, 50), count=8)
            
            # Deal damage, check if player ran out of lives
            if self.player.get_hit(15): # player lost a life
                spawn_explosion(self.particles, self.player.rect.centerx, self.player.rect.centery, color=(0, 200, 255), count=40)
                if self.player.lives <= 0:
                    self.game.change_state(GameOverState(self.game, self.score))
                    return

        # 3. Enemies colliding directly with Player ship
        crash_hits = pg.sprite.spritecollide(self.player, self.enemies, True)
        for enemy in crash_hits:
            spawn_explosion(self.particles, enemy.rect.centerx, enemy.rect.centery, color=(255, 80, 0), count=30)
            self.score += enemy.score_value // 2
            
            # Crash deals heavier shield/health damage
            if self.player.get_hit(30): # player lost a life
                spawn_explosion(self.particles, self.player.rect.centerx, self.player.rect.centery, color=(0, 200, 255), count=40)
                if self.player.lives <= 0:
                    self.game.change_state(GameOverState(self.game, self.score))
                    return

        # 4. Player picking up PowerUps
        pup_collects = pg.sprite.spritecollide(self.player, self.powerups, True)
        for pup in pup_collects:
            spawn_sparks(self.particles, pup.rect.centerx, pup.rect.centery, (0, 0), color=(255, 255, 255), count=15)
            
            if pup.type == "shield":
                self.player.shield = min(self.player.max_shield, self.player.shield + 40)
            elif pup.type == "triple":
                self.player.triple_shot_timer = 8.0
            elif pup.type == "speed":
                self.player.speed_boost_timer = 8.0

    def draw(self, screen):
        # Draw all visual content on double-buffered canvas
        self.canvas.fill((10, 10, 15))
        
        # Star background
        self.starfield.draw(self.canvas)
        
        # Sprites & Particles
        self.all_sprites.draw(self.canvas)
        self.particles.draw(self.canvas)
        
        # Glowing shield barrier visual effect
        if self.player.shield > 0:
            shield_radius = 42
            shield_surf = pg.Surface((shield_radius * 2, shield_radius * 2), pg.SRCALPHA)
            alpha = int(80 + math.sin(pg.time.get_ticks() * 0.01) * 30) # pulse alpha
            pg.draw.circle(shield_surf, (0, 180, 255, alpha), (shield_radius, shield_radius), shield_radius, 3)
            pg.draw.circle(shield_surf, (0, 100, 255, alpha // 3), (shield_radius, shield_radius), shield_radius - 2)
            self.canvas.blit(shield_surf, shield_surf.get_rect(center=self.player.rect.center))

        # HUD LAYOUT
        self._draw_hud()

        # Render canvas to screen, offsetting by shake values
        screen.blit(self.canvas, self.shake_offset)

    def _draw_hud(self):
        # Score
        score_surf = self.game.assets.font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        self.canvas.blit(score_surf, (25, 20))
        
        # Wave tracker
        wave_txt = f"WAVE: {self.wave}" if self.wave < 5 else "WAVE: FINAL"
        wave_surf = self.game.assets.font.render(wave_txt, True, (0, 255, 200))
        self.canvas.blit(wave_surf, (self.game.width - wave_surf.get_width() - 25, 20))

        # Health & Shield Bars (Top Center Dashboard)
        bar_w, bar_h = 160, 10
        center_x = self.game.width // 2 - bar_w // 2
        
        # Health Bar (Red background, Green fill)
        pg.draw.rect(self.canvas, (60, 10, 10), (center_x, 20, bar_w, bar_h), border_radius=3)
        h_fill = int((self.player.health / self.player.max_health) * bar_w)
        if h_fill > 0:
            pg.draw.rect(self.canvas, (0, 255, 100), (center_x, 20, h_fill, bar_h), border_radius=3)
        health_lbl = self.game.assets.hud_font.render("HP", True, (200, 220, 200))
        self.canvas.blit(health_lbl, (center_x - 30, 16))

        # Shield Bar (Dark Cyan background, Cyan fill)
        pg.draw.rect(self.canvas, (10, 40, 50), (center_x, 36, bar_w, bar_h), border_radius=3)
        s_fill = int((self.player.shield / self.player.max_shield) * bar_w)
        if s_fill > 0:
            pg.draw.rect(self.canvas, (0, 200, 255), (center_x, 36, s_fill, bar_h), border_radius=3)
        shield_lbl = self.game.assets.hud_font.render("SH", True, (180, 220, 240))
        self.canvas.blit(shield_lbl, (center_x - 30, 32))

        # Lives Icons
        for i in range(self.player.lives):
            life_img = self.game.assets.get_image("player", 22, 22)
            self.canvas.blit(life_img, (25 + i * 28, 55))

        # Power-Up Duration timers (Bottom Center)
        active_timers = []
        if self.player.triple_shot_timer > 0:
            active_timers.append(("TRIPLE SHOT", self.player.triple_shot_timer, (255, 50, 50)))
        if self.player.speed_boost_timer > 0:
            active_timers.append(("SPEED BOOST", self.player.speed_boost_timer, (255, 200, 0)))

        for idx, (label, timer, color) in enumerate(active_timers):
            lbl_surf = self.game.assets.hud_font.render(label, True, color)
            self.canvas.blit(lbl_surf, (25, self.game.height - 110 + idx * 30))
            
            # Simple remaining indicator bar
            bar_len = int((timer / 8.0) * 100)
            pg.draw.rect(self.canvas, (40, 40, 40), (140, self.game.height - 100 + idx * 30, 100, 6))
            pg.draw.rect(self.canvas, color, (140, self.game.height - 100 + idx * 30, bar_len, 6))

        # Wave Intro Banner text overlay
        if self.wave_intro_timer > 0:
            overlay_txt = f"WAVE {self.wave}" if self.wave < 5 else "⚠ BOSS INCOMING ⚠"
            overlay_color = (0, 255, 200) if self.wave < 5 else (255, 0, 50)
            
            banner_surf = self.game.assets.title_font.render(overlay_txt, True, overlay_color)
            banner_rect = banner_surf.get_rect(center=(self.game.width // 2, self.game.height // 2.5))
            
            # Background drop stripe
            stripe = pg.Surface((self.game.width, 100), pg.SRCALPHA)
            stripe.fill((0, 0, 0, 140))
            self.canvas.blit(stripe, (0, self.game.height // 2.5 - 50))
            self.canvas.blit(banner_surf, banner_rect)

        # Boss HUD health bar
        if self.boss_active and self.boss_instance and self.boss_instance.alive():
            boss_bar_w, boss_bar_h = 600, 14
            boss_x = self.game.width // 2 - boss_bar_w // 2
            
            # Label
            boss_label = self.game.assets.hud_font.render("BOSS - COMMAND SHIP", True, (255, 50, 50))
            self.canvas.blit(boss_label, (boss_x, 70))
            
            # Draw bar
            pg.draw.rect(self.canvas, (50, 10, 10), (boss_x, 92, boss_bar_w, boss_bar_h), border_radius=4)
            b_fill = int((self.boss_instance.health / self.boss_instance.max_health) * boss_bar_w)
            if b_fill > 0:
                pg.draw.rect(self.canvas, (255, 0, 50), (boss_x, 92, b_fill, boss_bar_h), border_radius=4)
                # Outer styling outline
                pg.draw.rect(self.canvas, (255, 255, 255), (boss_x, 92, boss_bar_w, boss_bar_h), 1, border_radius=4)


class PauseState(State):
    def __init__(self, game, previous_state):
        super().__init__(game)
        self.previous_state = previous_state
        self.overlay = pg.Surface((self.game.width, self.game.height), pg.SRCALPHA)
        self.overlay.fill((10, 12, 22, 200)) # Deep transparent dark overlay

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE or event.key == pg.K_SPACE:
                    self.game.change_state(self.previous_state)
                elif event.key == pg.K_q:
                    self.game.change_state(MenuState(self.game))

    def draw(self, screen):
        # Draw game frame in background
        self.previous_state.draw(screen)
        
        # Apply dark overlay filter
        screen.blit(self.overlay, (0, 0))
        
        # Render pause UI items
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
    def __init__(self, game, score):
        super().__init__(game)
        self.score = score
        self.save_system = SaveSystem()
        self.player_name = ""
        self.cursor_visible = True
        self.cursor_timer = 0.0

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_RETURN:
                    # Save final score
                    final_name = self.player_name.strip() or "PILOT"
                    self.save_system.save_score(final_name, self.score)
                    self.game.change_state(HighScoresState(self.game))
                elif event.key == pg.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                else:
                    # Capture character input
                    if len(self.player_name) < 8 and event.unicode.isalnum():
                        self.player_name += event.unicode.upper()

    def update(self, dt):
        # Pulse typing cursor indicator
        self.cursor_timer += dt
        if self.cursor_timer >= 0.4:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

    def draw(self, screen):
        screen.fill((25, 10, 12))
        
        title = self.game.assets.title_font.render("GAME OVER", True, (255, 50, 50))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 4))
        screen.blit(title, title_rect)
        
        score_text = self.game.assets.font.render(f"Final Score: {self.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.game.width // 2, self.game.height // 3 + 20))
        screen.blit(score_text, score_rect)
        
        # Input prompt
        prompt_surf = self.game.assets.font.render("ENTER YOUR NAME:", True, (0, 255, 200))
        prompt_rect = prompt_surf.get_rect(center=(self.game.width // 2, self.game.height // 2))
        screen.blit(prompt_surf, prompt_rect)
        
        # Name layout (centered input field box)
        cursor_char = "_" if self.cursor_visible else " "
        display_name = f"{self.player_name}{cursor_char}"
        
        name_surf = self.game.assets.title_font.render(display_name, True, (255, 255, 255))
        name_rect = name_surf.get_rect(center=(self.game.width // 2, self.game.height // 2 + 60))
        screen.blit(name_surf, name_rect)
        
        hint = self.game.assets.hud_font.render("Press ENTER to Save Score & View Leaderboard", True, (130, 140, 150))
        hint_rect = hint.get_rect(center=(self.game.width // 2, self.game.height - 80))
        screen.blit(hint, hint_rect)


class HighScoresState(State):
    def __init__(self, game):
        super().__init__(game)
        self.save_system = SaveSystem()
        self.scores_list = self.save_system.load_scores()

    def handle_events(self, events):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_SPACE):
                    self.game.change_state(MenuState(self.game))

    def draw(self, screen):
        screen.fill((10, 12, 22))
        
        title = self.game.assets.title_font.render("HIGH SCORES", True, (0, 200, 255))
        title_rect = title.get_rect(center=(self.game.width // 2, self.game.height // 6))
        screen.blit(title, title_rect)
        
        # Draw high scores table columns
        for idx, item in enumerate(self.scores_list[:10]):
            rank = f"{idx+1}."
            name = item.get("name", "PILOT")
            score = str(item.get("score", 0))
            
            # Colors
            color = (255, 220, 0) if idx == 0 else ((200, 220, 240) if idx < 3 else (130, 150, 170))
            
            rank_surf = self.game.assets.font.render(rank, True, color)
            name_surf = self.game.assets.font.render(name, True, color)
            score_surf = self.game.assets.font.render(score, True, color)
            
            # Align table columns beautifully (Rank left-ish, Name center-left, Score right-ish)
            y_pos = self.game.height // 3.2 + idx * 36
            screen.blit(rank_surf, (self.game.width // 2 - 180, y_pos))
            screen.blit(name_surf, (self.game.width // 2 - 80, y_pos))
            screen.blit(score_surf, (self.game.width // 2 + 100, y_pos))
            
        hint = self.game.assets.font.render("Press ESC/SPACE to Main Menu", True, (100, 120, 140))
        hint_rect = hint.get_rect(center=(self.game.width // 2, self.game.height - 80))
        screen.blit(hint, hint_rect)
