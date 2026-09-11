# pyrefly: ignore [missing-import]
import math
import pygame as pg


class HUD:
    """
    Sprint 11 / Pillar F — Dedicated HUD System.

    Renders a unified heads-up display:
    - Segmented glowing Health & Shield energy meters with status pips.
    - Cyber numeral multiplier glyphs for high combo chains.
    - Missile count indicators with charge status.
    - Named boss health bar with phase badges (e.g., 'CRIMSON MOTHERSHIP — PHASE 1').
    - Hitmarker feedback: 80ms white chevron indicator on confirmed enemy hits.
    - Dynamic floating combat text.
    """

    def __init__(self, game):
        self.game = game
        self.assets = game.assets
        self.hitmarker_timer = 0.0
        self.hitmarker_pos = (640, 360)
        self.hitmarkers_enabled = True

        # Load cyber numerals if available
        self.numerals = {}
        for d in range(10):
            self.numerals[str(d)] = self.assets.get_image(f"ui_hud/cyber_numerals/digit_{d}", 16, 22)
        self.numerals["x"] = self.assets.get_image("ui_hud/cyber_numerals/digit_multiplier_x", 16, 22)

    def trigger_hitmarker(self, x=None, y=None):
        """Triggers an 80ms white hitmarker chevron."""
        if not self.hitmarkers_enabled:
            return
        self.hitmarker_timer = 0.08
        if x is not None and y is not None:
            self.hitmarker_pos = (x, y)

    def update(self, dt):
        if self.hitmarker_timer > 0:
            self.hitmarker_timer -= dt

    def draw(self, surface, play_state):
        player = play_state.player
        width = self.game.width
        height = self.game.height
        assets = self.assets

        # 1. SCORE DISPLAY
        score_surf = assets.hud_font.render(f"SCORE: {play_state.score}", True, (255, 255, 255))
        surface.blit(score_surf, (25, 20))

        # Sprint 7 & 11: COMBO DISPLAY WITH CYBER NUMERALS
        if play_state.combo_count > 1:
            combo_alpha = min(255, int(play_state.combo_timer / play_state.COMBO_WINDOW * 255))
            mx = play_state.combo_multiplier
            mult_str = f"x{mx:.1f}"

            # Render cyber numeral multiplier glyphs
            curr_x = 25
            curr_y = 44
            for ch in mult_str:
                if ch == ".":
                    dot = assets.hud_font.render(".", True, (255, 210, 0))
                    dot.set_alpha(combo_alpha)
                    surface.blit(dot, (curr_x, curr_y))
                    curr_x += 8
                elif ch in self.numerals and self.numerals[ch]:
                    img = self.numerals[ch].copy()
                    img.set_alpha(combo_alpha)
                    surface.blit(img, (curr_x, curr_y))
                    curr_x += img.get_width() + 2

            combo_lbl = assets.hud_font.render(f"[{play_state.combo_count} KILLS]", True, (255, 200, 80))
            combo_lbl.set_alpha(combo_alpha)
            surface.blit(combo_lbl, (curr_x + 8, curr_y + 2))

        # 2. LEVEL & WAVE TRACKER
        if play_state.level_sys.is_boss_wave:
            wave_txt = f"LVL {play_state.level_sys.level_number} — BOSS ALERT"
            wave_color = (255, 80, 80)
        else:
            wave_txt = f"LVL {play_state.level_sys.level_number}  WAVE {play_state.level_sys.wave_number}"
            wave_color = (0, 255, 200)
        wave_surf = assets.hud_font.render(wave_txt, True, wave_color)
        surface.blit(wave_surf, (width - wave_surf.get_width() - 25, 20))

        # 3. SEGMENTED ENERGY METERS (CENTER DASHBOARD)
        bar_w, bar_h = 180, 12
        center_x = width // 2 - bar_w // 2

        # Health Meter: Segmented container with outer glow
        pg.draw.rect(surface, (45, 12, 14), (center_x - 1, 19, bar_w + 2, bar_h + 2), border_radius=4)
        pg.draw.rect(surface, (110, 30, 35), (center_x - 1, 19, bar_w + 2, bar_h + 2), 1, border_radius=4)
        h_ratio = max(0.0, min(1.0, player.health / max(1, player.max_health)))
        h_fill = int(h_ratio * bar_w)
        if h_fill > 0:
            pg.draw.rect(surface, (0, 240, 120), (center_x, 20, h_fill, bar_h), border_radius=3)
            # Segment dividers
            for seg in range(1, 6):
                seg_x = center_x + int(seg * (bar_w / 6))
                if seg_x < center_x + h_fill:
                    pg.draw.line(surface, (0, 180, 90), (seg_x, 20), (seg_x, 20 + bar_h - 1), 1)

        hp_lbl = assets.hud_font.render(f"HP {int(player.health)}/{int(player.max_health)}", True, (200, 255, 220))
        surface.blit(hp_lbl, (center_x - hp_lbl.get_width() - 10, 17))

        # Shield Meter: Segmented cyan container
        pg.draw.rect(surface, (10, 35, 48), (center_x - 1, 37, bar_w + 2, bar_h + 2), border_radius=4)
        pg.draw.rect(surface, (30, 90, 130), (center_x - 1, 37, bar_w + 2, bar_h + 2), 1, border_radius=4)
        s_ratio = max(0.0, min(1.0, player.shield / max(1, player.max_shield)))
        s_fill = int(s_ratio * bar_w)
        if s_fill > 0:
            pg.draw.rect(surface, (0, 210, 255), (center_x, 38, s_fill, bar_h), border_radius=3)
            for seg in range(1, 6):
                seg_x = center_x + int(seg * (bar_w / 6))
                if seg_x < center_x + s_fill:
                    pg.draw.line(surface, (0, 150, 200), (seg_x, 38), (seg_x, 38 + bar_h - 1), 1)

        sh_lbl = assets.hud_font.render(f"SH {int(player.shield)}/{int(player.max_shield)}", True, (180, 230, 255))
        surface.blit(sh_lbl, (center_x - sh_lbl.get_width() - 10, 35))

        # 4. LIVES SHIP ICONS (Bottom Left stack)
        hull_name = getattr(player, 'hull_type', 'interceptor')
        color_name = getattr(player, 'color_name', 'blue')
        life_key = f"ui_hud/life_counters/hud_life_{hull_name}_{color_name}"
        life_img = assets.get_image(life_key, 24, 24)
        for i in range(player.lives):
            surface.blit(life_img, (25 + i * 28, 72))

        # 5. MISSILE CHARGE STATUS & PIPS
        if player.missile_count > 0:
            missile_icon = assets.get_image("missile", 12, 24)
            for i in range(player.missile_count):
                surface.blit(missile_icon, (25 + i * 18, 102))
            m_ready = player.missile_cooldown <= 0
            m_color = (0, 255, 200) if m_ready else (255, 140, 40)
            status_text = "READY [M]" if m_ready else f"CHARGING {player.missile_cooldown:.1f}s"
            m_lbl = assets.hud_font.render(status_text, True, m_color)
            surface.blit(m_lbl, (25 + player.missile_count * 18 + 6, 106))

        # 6. POWER-UP EXPIRY METERS
        TRIPLE_MAX = 12.0
        SPEED_MAX  = 12.0
        POWER_MAX  = 10.0

        active_timers = []
        if player.triple_shot_timer > 0:
            active_timers.append(("TRIPLE SHOT",  player.triple_shot_timer, TRIPLE_MAX, (255, 50, 50)))
        if player.speed_boost_timer > 0:
            active_timers.append(("SPEED BOOST",  player.speed_boost_timer, SPEED_MAX,  (255, 200, 0)))
        if player.laser_power_timer > 0:
            active_timers.append(("POWER LASER",  player.laser_power_timer, POWER_MAX,  (220, 60, 0)))

        for idx, (label, timer, max_time, color) in enumerate(active_timers):
            lbl_surf = assets.hud_font.render(label, True, color)
            surface.blit(lbl_surf, (25, height - 110 + idx * 30))
            bar_len = int((timer / max_time) * 100)
            pg.draw.rect(surface, (40, 40, 40), (140, height - 100 + idx * 30, 100, 6))
            pg.draw.rect(surface, color,        (140, height - 100 + idx * 30, bar_len, 6))

        # 7. SEGMENTED MULTI-PHASE BOSS HUD (When Boss is Active)
        if play_state.boss_active and play_state.boss_instance:
            boss = play_state.boss_instance
            boss_bar_w = 500
            boss_bar_h = 18
            boss_bar_x = width // 2 - boss_bar_w // 2
            boss_bar_y = 56

            # A. Boss Nameplate & Phase Badge
            boss_title = getattr(boss, 'boss_title', 'BOSS ENCOUNTER')
            phase_subtitle = getattr(boss, 'phase_subtitle', f'PHASE {getattr(boss, "attack_phase", 1)}')
            
            # Badge frame
            badge_text = f"★ {boss_title}  —  {phase_subtitle} ★"
            name_surf = assets.font.render(badge_text, True, (255, 130, 140))
            name_rect = name_surf.get_rect(center=(width // 2, boss_bar_y - 14))
            
            # Badge background
            bg_pad = 12
            badge_bg = pg.Rect(name_rect.left - bg_pad, name_rect.top - 2, name_rect.width + bg_pad * 2, name_rect.height + 4)
            pg.draw.rect(surface, (20, 10, 22, 220), badge_bg, border_radius=4)
            pg.draw.rect(surface, (160, 40, 60, 255), badge_bg, 1, border_radius=4)
            surface.blit(name_surf, name_rect)

            # B. Background & Frame
            pg.draw.rect(surface, (25, 12, 18), (boss_bar_x - 3, boss_bar_y - 3, boss_bar_w + 6, boss_bar_h + 6), border_radius=6)
            pg.draw.rect(surface, (140, 35, 50), (boss_bar_x - 3, boss_bar_y - 3, boss_bar_w + 6, boss_bar_h + 6), 2, border_radius=6)

            # Ratios
            b_ratio = max(0.0, min(1.0, boss.health / max(1, boss.max_health)))
            
            # Update trailing damage bar
            if not hasattr(self, 'boss_trail_ratio') or self.boss_trail_ratio < b_ratio:
                self.boss_trail_ratio = b_ratio
            else:
                self.boss_trail_ratio = max(b_ratio, self.boss_trail_ratio - 0.25 * getattr(play_state, 'last_dt', 0.016))

            # Trailing damage bar (amber/orange)
            trail_fill = int(self.boss_trail_ratio * boss_bar_w)
            if trail_fill > 0:
                pg.draw.rect(surface, (255, 160, 40), (boss_bar_x, boss_bar_y, trail_fill, boss_bar_h), border_radius=4)

            # Active health bar fill (crimson/ruby)
            b_fill = int(b_ratio * boss_bar_w)
            if b_fill > 0:
                fill_color = (255, 45, 65) if b_ratio > 0.33 else (255, 80, 40)
                pg.draw.rect(surface, fill_color, (boss_bar_x, boss_bar_y, b_fill, boss_bar_h), border_radius=4)

            # C. Shield Overlay Bar (if boss has active shield)
            boss_shield = getattr(boss, 'shield', 0)
            boss_max_shield = getattr(boss, 'max_shield', 0)
            if boss_shield > 0 and boss_max_shield > 0:
                sh_ratio = max(0.0, min(1.0, boss_shield / boss_max_shield))
                sh_fill = int(sh_ratio * boss_bar_w)
                sh_surf = pg.Surface((sh_fill, 4), pg.SRCALPHA)
                sh_surf.fill((0, 240, 255, 230))
                surface.blit(sh_surf, (boss_bar_x, boss_bar_y - 6))
                pg.draw.rect(surface, (0, 160, 220), (boss_bar_x - 1, boss_bar_y - 7, boss_bar_w + 2, 6), 1)

            # D. Phase Segment Pips / Dividers
            thresholds = getattr(boss, 'phase_thresholds', [0.66, 0.33])
            for thresh in thresholds:
                pip_x = int(boss_bar_x + thresh * boss_bar_w)
                # Diamond / metallic divider pip
                pg.draw.line(surface, (20, 8, 12), (pip_x, boss_bar_y - 4), (pip_x, boss_bar_y + boss_bar_h + 3), 3)
                pg.draw.line(surface, (255, 220, 160), (pip_x, boss_bar_y - 3), (pip_x, boss_bar_y + boss_bar_h + 2), 1)
                # Top gemstone triangle
                pg.draw.polygon(surface, (255, 200, 80), [(pip_x - 3, boss_bar_y - 5), (pip_x + 3, boss_bar_y - 5), (pip_x, boss_bar_y - 1)])

            # E. Supernova Countdown Alert (Level 10 Phase 3 DPS check)
            if getattr(boss, 'supernova_active', False):
                sn_timer = getattr(boss, 'supernova_timer', 10.0)
                sn_pulse = (math.sin(pg.time.get_ticks() * 0.02) + 1.0) / 2.0
                sn_color = (255, 50, 60) if sn_pulse > 0.4 else (255, 220, 50)
                sn_text = f"⚠️ CORE MELTDOWN: SUPERNOVA IN {sn_timer:.1f}s ⚠️"
                sn_surf = assets.hud_font.render(sn_text, True, sn_color)
                sn_rect = sn_surf.get_rect(center=(width // 2, boss_bar_y + boss_bar_h + 14))
                surface.blit(sn_surf, sn_rect)


        # 8. HITMARKER FEEDBACK (80ms Chevron at cursor / impact position)
        if self.hitmarker_timer > 0:
            hx, hy = self.hitmarker_pos
            alpha = min(255, int((self.hitmarker_timer / 0.08) * 255))
            hm_surf = pg.Surface((32, 32), pg.SRCALPHA)
            color = (255, 255, 255, alpha)
            size = 8
            # 4 diagonal cross ticks
            pg.draw.line(hm_surf, color, (16 - size, 16 - size), (16 - 3, 16 - 3), 2)
            pg.draw.line(hm_surf, color, (16 + size, 16 - size), (16 + 3, 16 - 3), 2)
            pg.draw.line(hm_surf, color, (16 - size, 16 + size), (16 - 3, 16 + 3), 2)
            pg.draw.line(hm_surf, color, (16 + size, 16 + size), (16 + 3, 16 + 3), 2)
            surface.blit(hm_surf, (hx - 16, hy - 16))

        # 9. ENEMY TELEGRAPH CHEVRONS & ELITE NAMEPLATES (Pillar I)
        for enemy in getattr(play_state, 'enemies', ()):
            if getattr(enemy, 'telegraph_timer', 0) > 0:
                # 400ms warning chevron under firing cruisers
                pulse = int(180 + 75 * math.sin(pg.time.get_ticks() * 0.04))
                chev_surf = pg.Surface((40, 20), pg.SRCALPHA)
                pts = [(6, 4), (20, 16), (34, 4)]
                pg.draw.lines(chev_surf, (255, 40, 40, pulse), False, pts, 3)
                surface.blit(chev_surf, chev_surf.get_rect(center=(enemy.rect.centerx, enemy.rect.bottom + 12)))

            if getattr(enemy, 'is_elite', False):
                # Elite enemy nameplate + small HP bar
                el_lbl = assets.hud_font.render("ELITE", True, (255, 200, 40))
                surface.blit(el_lbl, el_lbl.get_rect(center=(enemy.rect.centerx, enemy.rect.top - 14)))
                hp_w = 40
                hp_ratio = max(0.0, enemy.health / max(1, enemy.max_health))
                pg.draw.rect(surface, (50, 10, 10), (enemy.rect.centerx - 20, enemy.rect.top - 4, hp_w, 4))
                if hp_ratio > 0:
                    pg.draw.rect(surface, (255, 180, 0), (enemy.rect.centerx - 20, enemy.rect.top - 4, int(hp_w * hp_ratio), 4))
