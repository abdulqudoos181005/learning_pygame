# pyrefly: ignore [missing-import]
import math
import random
import pygame as pg


class LaserSightline:
    """
    Visual aiming telegraph for high-threat beam cannons.
    
    Phases:
    1. AIMING: Soft pulsing amber guide line tracking player position.
    2. LOCKED: Flashing intense crimson/red line locking firing trajectory.
    3. FIRING: Lethal high-intensity energy beam discharging along locked trajectory.
    4. FINISHED: Expired.
    """

    STATE_AIMING = "aiming"
    STATE_LOCKED = "locked"
    STATE_FIRING = "firing"
    STATE_FINISHED = "finished"

    def __init__(
        self,
        start_provider,
        target_provider,
        aim_duration=1.0,
        lock_duration=0.3,
        fire_duration=0.4,
        beam_width=16,
        damage=25,
        beam_color=(255, 60, 60),
        core_color=(255, 240, 240),
        on_fire_callback=None,
    ):
        self.start_provider = start_provider
        self.target_provider = target_provider
        self.aim_duration = aim_duration
        self.lock_duration = lock_duration
        self.fire_duration = fire_duration
        self.beam_width = beam_width
        self.damage = damage
        self.beam_color = beam_color
        self.core_color = core_color
        self.on_fire_callback = on_fire_callback

        self.state = self.STATE_AIMING
        self.timer = 0.0
        
        # Coordinates
        self.start_pos = pg.Vector2(self._resolve_pos(self.start_provider))
        self.target_pos = pg.Vector2(self._resolve_pos(self.target_provider))
        self.locked_end_pos = pg.Vector2(self.target_pos)
        self.locked_dir = pg.Vector2(0, 1)

        self.has_fired_cb = False
        self.damage_dealt = False

    def _resolve_pos(self, provider):
        if callable(provider):
            return provider()
        if hasattr(provider, "center"):
            return provider.center
        if hasattr(provider, "x") and hasattr(provider, "y"):
            return (provider.x, provider.y)
        return provider

    @property
    def is_aiming(self):
        return self.state == self.STATE_AIMING

    @property
    def is_locked(self):
        return self.state == self.STATE_LOCKED

    @property
    def is_firing(self):
        return self.state == self.STATE_FIRING

    @property
    def is_finished(self):
        return self.state == self.STATE_FINISHED

    def update(self, dt):
        if self.state == self.STATE_FINISHED:
            return

        self.timer += dt

        # Update start position continually while tracking
        self.start_pos = pg.Vector2(self._resolve_pos(self.start_provider))

        if self.state == self.STATE_AIMING:
            # Continually track target
            raw_target = self._resolve_pos(self.target_provider)
            self.target_pos = pg.Vector2(raw_target)
            
            # Calculate ray towards and through target to screen edges
            dir_vec = self.target_pos - self.start_pos
            if dir_vec.length_squared() > 0:
                self.locked_dir = dir_vec.normalize()
            else:
                self.locked_dir = pg.Vector2(0, 1)
            self.locked_end_pos = self.start_pos + self.locked_dir * 1600

            if self.timer >= self.aim_duration:
                self.state = self.STATE_LOCKED
                self.timer = 0.0

        elif self.state == self.STATE_LOCKED:
            # Trajectory is locked — do NOT update locked_dir/locked_end_pos to target
            self.locked_end_pos = self.start_pos + self.locked_dir * 1600
            if self.timer >= self.lock_duration:
                self.state = self.STATE_FIRING
                self.timer = 0.0
                if self.on_fire_callback and not self.has_fired_cb:
                    self.has_fired_cb = True
                    self.on_fire_callback(self)

        elif self.state == self.STATE_FIRING:
            self.locked_end_pos = self.start_pos + self.locked_dir * 1600
            if self.timer >= self.fire_duration:
                self.state = self.STATE_FINISHED

    def check_hit(self, target_rect):
        """Checks if the lethal beam intersects the target rect during FIRING state."""
        if self.state != self.STATE_FIRING or self.damage_dealt:
            return False

        # Ray-box intersection or line distance check
        p1 = self.start_pos
        p2 = self.locked_end_pos
        rect_center = pg.Vector2(target_rect.center)
        
        # Vector from p1 to p2
        line_vec = p2 - p1
        line_len_sq = line_vec.length_squared()
        if line_len_sq == 0:
            return False
            
        t = max(0.0, min(1.0, (rect_center - p1).dot(line_vec) / line_len_sq))
        projection = p1 + line_vec * t
        dist = (rect_center - projection).length()
        
        # Effective collision threshold = beam half width + rect radius
        hit_radius = (self.beam_width / 2.0) + (max(target_rect.width, target_rect.height) / 2.8)
        if dist <= hit_radius:
            self.damage_dealt = True
            return True
        return False

    def draw(self, surface):
        if self.state == self.STATE_FINISHED:
            return

        p1 = (int(self.start_pos.x), int(self.start_pos.y))
        p2 = (int(self.locked_end_pos.x), int(self.locked_end_pos.y))

        if self.state == self.STATE_AIMING:
            # Pulsing semi-transparent soft amber line
            pulse = (math.sin(self.timer * 16.0) + 1.0) / 2.0
            alpha = int(70 + pulse * 110)
            
            guide_surf = pg.Surface(surface.get_size(), pg.SRCALPHA)
            pg.draw.line(guide_surf, (255, 180, 40, alpha), p1, p2, 2)
            
            # Subtle reticle tick at current aim point
            target_pt = (int(self.target_pos.x), int(self.target_pos.y))
            pg.draw.circle(guide_surf, (255, 190, 50, alpha), target_pt, 8, 1)
            surface.blit(guide_surf, (0, 0), special_flags=pg.BLEND_ADD)

        elif self.state == self.STATE_LOCKED:
            # Rapid flashing intense red line
            flash = (math.sin(self.timer * 36.0) + 1.0) / 2.0
            alpha = int(140 + flash * 115)
            
            lock_surf = pg.Surface(surface.get_size(), pg.SRCALPHA)
            # Outer red glow
            pg.draw.line(lock_surf, (255, 30, 30, alpha), p1, p2, 4)
            # Center bright line
            pg.draw.line(lock_surf, (255, 220, 220, min(255, alpha + 40)), p1, p2, 2)
            surface.blit(lock_surf, (0, 0), special_flags=pg.BLEND_ADD)

        elif self.state == self.STATE_FIRING:
            # High-intensity lethal beam with outer glow and white core
            progress = min(1.0, self.timer / self.fire_duration)
            # Beam widens then dissipates
            w_factor = 1.0 if progress < 0.7 else (1.0 - (progress - 0.7) / 0.3)
            current_w = max(4, int(self.beam_width * w_factor))
            
            beam_surf = pg.Surface(surface.get_size(), pg.SRCALPHA)
            
            # Wide outer glow
            glow_color = (*self.beam_color[:3], int(180 * w_factor))
            pg.draw.line(beam_surf, glow_color, p1, p2, current_w + 10)
            
            # Main colored beam
            beam_color = (*self.beam_color[:3], int(240 * w_factor))
            pg.draw.line(beam_surf, beam_color, p1, p2, current_w)
            
            # Hot white central core
            core_color = (*self.core_color[:3], int(255 * w_factor))
            pg.draw.line(beam_surf, core_color, p1, p2, max(2, current_w // 3))
            
            surface.blit(beam_surf, (0, 0), special_flags=pg.BLEND_ADD)


class RingHazard:
    """
    Expanding circular area warning indicating incoming mortar strike, mine, or shockwave.
    """

    STATE_WARNING = "warning"
    STATE_BURST = "burst"
    STATE_FINISHED = "finished"

    def __init__(
        self,
        center,
        radius=60,
        warning_duration=1.2,
        burst_duration=0.35,
        damage=20,
        color=(255, 90, 40),
        on_burst_callback=None,
    ):
        self.center = pg.Vector2(center)
        self.radius = radius
        self.warning_duration = warning_duration
        self.burst_duration = burst_duration
        self.damage = damage
        self.color = color
        self.on_burst_callback = on_burst_callback

        self.state = self.STATE_WARNING
        self.timer = 0.0
        self.damage_dealt = False
        self.has_burst_cb = False

    @property
    def is_warning(self):
        return self.state == self.STATE_WARNING

    @property
    def is_bursting(self):
        return self.state == self.STATE_BURST

    @property
    def is_finished(self):
        return self.state == self.STATE_FINISHED

    def update(self, dt):
        if self.state == self.STATE_FINISHED:
            return

        self.timer += dt

        if self.state == self.STATE_WARNING:
            if self.timer >= self.warning_duration:
                self.state = self.STATE_BURST
                self.timer = 0.0
                if self.on_burst_callback and not self.has_burst_cb:
                    self.has_burst_cb = True
                    self.on_burst_callback(self)

        elif self.state == self.STATE_BURST:
            if self.timer >= self.burst_duration:
                self.state = self.STATE_FINISHED

    def check_hit(self, target_rect):
        """Checks if the blast overlaps target_rect during BURST state."""
        if self.state != self.STATE_BURST or self.damage_dealt:
            return False

        rect_center = pg.Vector2(target_rect.center)
        dist = (rect_center - self.center).length()
        target_rad = max(target_rect.width, target_rect.height) / 2.5
        if dist <= self.radius + target_rad:
            self.damage_dealt = True
            return True
        return False

    def draw(self, surface):
        if self.state == self.STATE_FINISHED:
            return

        cx, cy = int(self.center.x), int(self.center.y)
        rad = int(self.radius)

        if self.state == self.STATE_WARNING:
            progress = min(1.0, self.timer / max(0.01, self.warning_duration))
            pulse = (math.sin(self.timer * 18.0) + 1.0) / 2.0
            
            # Semi-transparent warning fill + expanding ring
            surf = pg.Surface((rad * 2 + 10, rad * 2 + 10), pg.SRCALPHA)
            center_local = (rad + 5, rad + 5)
            
            # Base faint circle
            base_alpha = int(30 + pulse * 25)
            pg.draw.circle(surf, (*self.color[:3], base_alpha), center_local, rad)
            
            # Perimeter border
            border_alpha = int(120 + pulse * 90)
            pg.draw.circle(surf, (*self.color[:3], border_alpha), center_local, rad, 2)
            
            # Inner filling indicator ring
            fill_rad = max(2, int(rad * progress))
            pg.draw.circle(surf, (255, 220, 100, int(160 * progress)), center_local, fill_rad, 2)
            
            surface.blit(surf, (cx - rad - 5, cy - rad - 5), special_flags=pg.BLEND_ADD)

        elif self.state == self.STATE_BURST:
            # Fiery blast shockwave
            progress = min(1.0, self.timer / max(0.01, self.burst_duration))
            alpha = int(255 * (1.0 - progress))
            cur_rad = int(rad * (0.8 + 0.4 * progress))
            
            surf = pg.Surface((cur_rad * 2 + 10, cur_rad * 2 + 10), pg.SRCALPHA)
            center_local = (cur_rad + 5, cur_rad + 5)
            
            pg.draw.circle(surf, (255, 200, 50, alpha // 2), center_local, cur_rad)
            pg.draw.circle(surf, (255, 60, 40, alpha), center_local, cur_rad, max(2, int(6 * (1.0 - progress))))
            pg.draw.circle(surf, (255, 255, 255, alpha), center_local, max(2, cur_rad // 2), 2)
            
            surface.blit(surf, (cx - cur_rad - 5, cy - cur_rad - 5), special_flags=pg.BLEND_ADD)


class ConicalHazard:
    """
    Conical hazard sector indicating sweeping laser or flamethrower arcs.
    """

    STATE_WARNING = "warning"
    STATE_BURST = "burst"
    STATE_FINISHED = "finished"

    def __init__(
        self,
        origin,
        center_angle,
        spread_angle=50.0,
        radius=280,
        warning_duration=1.0,
        burst_duration=0.5,
        damage=30,
        color=(255, 80, 50),
    ):
        self.origin = pg.Vector2(origin)
        self.center_angle = center_angle  # In degrees, 90 = straight down
        self.spread_angle = spread_angle  # Total arc width
        self.radius = radius
        self.warning_duration = warning_duration
        self.burst_duration = burst_duration
        self.damage = damage
        self.color = color

        self.state = self.STATE_WARNING
        self.timer = 0.0
        self.damage_dealt = False

    def update(self, dt):
        if self.state == self.STATE_FINISHED:
            return

        self.timer += dt
        if self.state == self.STATE_WARNING:
            if self.timer >= self.warning_duration:
                self.state = self.STATE_BURST
                self.timer = 0.0
        elif self.state == self.STATE_BURST:
            if self.timer >= self.burst_duration:
                self.state = self.STATE_FINISHED

    def check_hit(self, target_rect):
        if self.state != self.STATE_BURST or self.damage_dealt:
            return False

        rect_center = pg.Vector2(target_rect.center)
        offset = rect_center - self.origin
        dist = offset.length()
        if dist > self.radius + 15:
            return False

        angle_deg = math.degrees(math.atan2(offset.y, offset.x))
        diff = (angle_deg - self.center_angle + 180) % 360 - 180
        if abs(diff) <= (self.spread_angle / 2.0) + 8.0:
            self.damage_dealt = True
            return True
        return False

    def draw(self, surface):
        if self.state == self.STATE_FINISHED:
            return

        ox, oy = int(self.origin.x), int(self.origin.y)
        half_spread = self.spread_angle / 2.0
        start_deg = self.center_angle - half_spread
        end_deg = self.center_angle + half_spread
        
        # Build polygon points along the arc
        points = [(ox, oy)]
        steps = 14
        for i in range(steps + 1):
            deg = start_deg + (end_deg - start_deg) * (i / steps)
            rad = math.radians(deg)
            px = ox + self.radius * math.cos(rad)
            py = oy + self.radius * math.sin(rad)
            points.append((px, py))

        surf = pg.Surface(surface.get_size(), pg.SRCALPHA)
        if self.state == self.STATE_WARNING:
            pulse = (math.sin(self.timer * 16.0) + 1.0) / 2.0
            fill_alpha = int(40 + pulse * 35)
            line_alpha = int(140 + pulse * 90)
            pg.draw.polygon(surf, (*self.color[:3], fill_alpha), points)
            pg.draw.polygon(surf, (*self.color[:3], line_alpha), points, 2)
        elif self.state == self.STATE_BURST:
            progress = min(1.0, self.timer / self.burst_duration)
            alpha = int(220 * (1.0 - progress))
            pg.draw.polygon(surf, (255, 120, 40, alpha), points)
            pg.draw.polygon(surf, (255, 240, 200, alpha), points, 3)

        surface.blit(surf, (0, 0), special_flags=pg.BLEND_ADD)


class PhaseEMPBlast:
    """
    Expanding EMP shockwave ring triggered during boss phase changes.
    Clears player projectiles and displays a dramatic energy distortion.
    """

    def __init__(self, center, max_radius=850, duration=0.8, color=(0, 220, 255)):
        self.center = pg.Vector2(center)
        self.max_radius = max_radius
        self.duration = duration
        self.color = color
        self.timer = 0.0
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        self.timer += dt
        if self.timer >= self.duration:
            self.finished = True

    def draw(self, surface):
        if self.finished:
            return

        progress = min(1.0, self.timer / self.duration)
        cur_radius = int(self.max_radius * (progress ** 0.8))
        alpha = int(240 * (1.0 - progress))

        if cur_radius <= 2:
            return

        surf = pg.Surface(surface.get_size(), pg.SRCALPHA)
        cx, cy = int(self.center.x), int(self.center.y)

        # Outer bright shockwave ring
        ring_w = max(2, int(12 * (1.0 - progress)))
        pg.draw.circle(surf, (*self.color[:3], alpha), (cx, cy), cur_radius, ring_w)
        
        # Secondary inner pulse
        if cur_radius > 15:
            pg.draw.circle(surf, (255, 255, 255, alpha // 2), (cx, cy), max(2, cur_radius - 8), max(1, ring_w // 2))

        surface.blit(surf, (0, 0), special_flags=pg.BLEND_ADD)


class BossPhaseNotification:
    """
    Full-screen boss phase transition banner with animated typography and status glow.
    """

    def __init__(self, title, subtitle, duration=2.5, color=(255, 70, 90)):
        self.title = title
        self.subtitle = subtitle
        self.duration = duration
        self.color = color
        self.timer = 0.0
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        self.timer += dt
        if self.timer >= self.duration:
            self.finished = True

    def draw(self, surface, assets):
        if self.finished or not assets:
            return

        width, height = surface.get_size()
        center_y = height // 2 - 40
        progress = min(1.0, self.timer / self.duration)
        
        # Fade in, hold, fade out
        if progress < 0.2:
            alpha = int((progress / 0.2) * 255)
        elif progress > 0.8:
            alpha = int(((1.0 - progress) / 0.2) * 255)
        else:
            alpha = 255

        if alpha <= 0:
            return

        banner_surf = pg.Surface((width, 100), pg.SRCALPHA)
        # Background bar
        bg_alpha = int(alpha * 0.75)
        pg.draw.rect(banner_surf, (15, 8, 20, bg_alpha), (0, 0, width, 100))
        pg.draw.line(banner_surf, (*self.color[:3], alpha), (0, 0), (width, 0), 2)
        pg.draw.line(banner_surf, (*self.color[:3], alpha), (0, 98), (width, 98), 2)

        # Title
        title_font = getattr(assets, "title_font", None) or getattr(assets, "font", None)
        if title_font:
            t_surf = title_font.render(self.title, True, self.color)
            t_surf.set_alpha(alpha)
            banner_surf.blit(t_surf, t_surf.get_rect(center=(width // 2, 34)))

        # Subtitle
        font = getattr(assets, "font", None)
        if font and self.subtitle:
            sub_surf = font.render(self.subtitle, True, (255, 230, 230))
            sub_surf.set_alpha(alpha)
            banner_surf.blit(sub_surf, sub_surf.get_rect(center=(width // 2, 70)))

        surface.blit(banner_surf, (0, center_y))


class TelegraphManager:
    """
    Central manager for all active attack telegraphs, hazards, and visual warning cues.
    """

    def __init__(self, game=None):
        self.game = game
        self.sightlines = []
        self.hazards = []
        self.emp_blasts = []
        self.notifications = []

    def create_laser_sightline(
        self,
        start_provider,
        target_provider,
        aim_duration=1.0,
        lock_duration=0.3,
        fire_duration=0.4,
        beam_width=16,
        damage=25,
        beam_color=(255, 60, 60),
        core_color=(255, 240, 240),
        on_fire_callback=None,
    ):
        sl = LaserSightline(
            start_provider=start_provider,
            target_provider=target_provider,
            aim_duration=aim_duration,
            lock_duration=lock_duration,
            fire_duration=fire_duration,
            beam_width=beam_width,
            damage=damage,
            beam_color=beam_color,
            core_color=core_color,
            on_fire_callback=on_fire_callback,
        )
        self.sightlines.append(sl)
        return sl

    def create_ring_hazard(
        self,
        center,
        radius=60,
        warning_duration=1.2,
        burst_duration=0.35,
        damage=20,
        color=(255, 90, 40),
        on_burst_callback=None,
    ):
        hz = RingHazard(
            center=center,
            radius=radius,
            warning_duration=warning_duration,
            burst_duration=burst_duration,
            damage=damage,
            color=color,
            on_burst_callback=on_burst_callback,
        )
        self.hazards.append(hz)
        return hz

    def create_conical_hazard(
        self,
        origin,
        center_angle,
        spread_angle=50.0,
        radius=280,
        warning_duration=1.0,
        burst_duration=0.5,
        damage=30,
        color=(255, 80, 50),
    ):
        hz = ConicalHazard(
            origin=origin,
            center_angle=center_angle,
            spread_angle=spread_angle,
            radius=radius,
            warning_duration=warning_duration,
            burst_duration=burst_duration,
            damage=damage,
            color=color,
        )
        self.hazards.append(hz)
        return hz

    def create_emp_blast(self, center, max_radius=850, duration=0.8, color=(0, 220, 255)):
        emp = PhaseEMPBlast(center=center, max_radius=max_radius, duration=duration, color=color)
        self.emp_blasts.append(emp)
        return emp

    def notify_boss_phase(self, title, subtitle, duration=2.5, color=(255, 70, 90)):
        notif = BossPhaseNotification(title=title, subtitle=subtitle, duration=duration, color=color)
        self.notifications.append(notif)
        return notif

    def update(self, dt):
        # Update sightlines
        for sl in self.sightlines:
            sl.update(dt)
        self.sightlines = [sl for sl in self.sightlines if not sl.is_finished]

        # Update hazards
        for hz in self.hazards:
            hz.update(dt)
        self.hazards = [hz for hz in self.hazards if not hz.is_finished]

        # Update EMP blasts
        for emp in self.emp_blasts:
            emp.update(dt)
        self.emp_blasts = [emp for emp in self.emp_blasts if not emp.finished]

        # Update notifications
        for notif in self.notifications:
            notif.update(dt)
        self.notifications = [notif for notif in self.notifications if not notif.finished]

    def check_player_hits(self, player_rect):
        """
        Checks all active lethal beams and hazard bursts against player rect.
        Returns total damage dealt this frame.
        """
        total_dmg = 0
        for sl in self.sightlines:
            if sl.check_hit(player_rect):
                total_dmg += sl.damage

        for hz in self.hazards:
            if hz.check_hit(player_rect):
                total_dmg += hz.damage

        return total_dmg

    def draw(self, surface, assets=None):
        # Draw hazards first (below lasers)
        for hz in self.hazards:
            hz.draw(surface)

        # Draw sightlines
        for sl in self.sightlines:
            sl.draw(surface)

        # Draw EMP shockwaves
        for emp in self.emp_blasts:
            emp.draw(surface)

        # Draw phase banners
        if assets:
            for notif in self.notifications:
                notif.draw(surface, assets)

    def clear(self):
        self.sightlines.clear()
        self.hazards.clear()
        self.emp_blasts.clear()
        self.notifications.clear()
