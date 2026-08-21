import math
import pygame as pg


class PlayerPresentation:
    """Visual layers for the player ship, kept outside the gameplay state."""

    def __init__(self, player):
        self.player = player
        assets = player.game.assets
        self.thrusters = [
            assets.get_image(f"vfx_effects/thruster_plumes/thruster_flame_{index:02d}", 30, 42)
            for index in range(20)
        ]
        self.shield_layers = (
            assets.get_image("vfx_effects/energy_shields/forcefield_bubble_outer", 92, 92),
            assets.get_image("vfx_effects/energy_shields/forcefield_bubble_core", 86, 86),
            assets.get_image("vfx_effects/energy_shields/forcefield_bubble_dense", 80, 80),
        )
        self.damage_layers = (
            assets.get_image("player_fleet/damage_overlays/interceptor_damage_light", 60, 60),
            assets.get_image("player_fleet/damage_overlays/interceptor_damage_moderate", 60, 60),
            assets.get_image("player_fleet/damage_overlays/interceptor_damage_critical", 60, 60),
        )
        self.sparkle = assets.get_image("vfx_effects/sparkles/sparkle_stardust_medium", 44, 44)
        self.time = 0.0
        self.shield_ripple = 0.0
        self.repair_timer = 0.0

    def update(self, dt):
        self.time += dt
        self.shield_ripple = max(0.0, self.shield_ripple - dt)
        self.repair_timer = max(0.0, self.repair_timer - dt)

    def trigger_shield_ripple(self):
        self.shield_ripple = 0.22

    def trigger_repair(self):
        self.repair_timer = 0.4

    def _damage_layer(self):
        ratio = self.player.health / max(1, self.player.max_health)
        if ratio <= 0.15:
            return self.damage_layers[2]
        if ratio <= 0.40:
            return self.damage_layers[1]
        if ratio <= 0.70:
            return self.damage_layers[0]
        return None

    def draw_back(self, surface):
        center = self.player.rect.center
        speed_ratio = min(1.0, self.player.velocity.length() / max(1.0, self.player.max_speed))
        if self.player.hit_stutter > 0 or self.player.invincible_timer > 0 and int(self.time * 18) % 2:
            return

        frame = int((self.time * (8 + speed_ratio * 18)) % len(self.thrusters))
        plume = self.thrusters[frame]
        plume_alpha = min(230, int(95 + speed_ratio * 135))
        plume = plume.copy()
        plume.set_alpha(plume_alpha)
        plume_rect = plume.get_rect(midtop=(center[0], center[1] + self.player.rect.height // 2 - 4))
        surface.blit(plume, plume_rect, special_flags=pg.BLEND_ADD)

    def draw_front(self, surface):
        center = self.player.rect.center
        if self.player.muzzle_timer > 0:
            flash = self.player.game.assets.get_image("vfx_effects/sparkles/sparkle_stardust_flare", 28, 28).copy()
            flash.set_alpha(int(255 * min(1.0, self.player.muzzle_timer / 0.07)))
            surface.blit(flash, flash.get_rect(midbottom=(center[0], self.player.rect.top + 5)), special_flags=pg.BLEND_ADD)
        if self.player.shield > 0:
            pulse = 1.0 + 0.04 * math.sin(self.time * 7.0)
            if self.shield_ripple > 0:
                pulse += (self.shield_ripple / 0.22) * 0.18
            for index, layer in enumerate(self.shield_layers):
                size = int(layer.get_width() * (pulse + index * 0.015))
                shield = pg.transform.smoothscale(layer, (size, size))
                shield.set_alpha(max(30, 110 - index * 22))
                surface.blit(shield, shield.get_rect(center=center), special_flags=pg.BLEND_ADD)

        damage = self._damage_layer()
        if damage is not None:
            damage = damage.copy()
            damage.set_alpha(150 + int(35 * math.sin(self.time * 9.0)))
            surface.blit(damage, damage.get_rect(center=center))

        if self.repair_timer > 0:
            sparkle = self.sparkle.copy()
            sparkle.set_alpha(int(255 * self.repair_timer / 0.4))
            surface.blit(sparkle, sparkle.get_rect(center=center), special_flags=pg.BLEND_ADD)

        if self.player.missile_hold_timer >= 0.15:
            target = self.player._missile_target()
            if target is not None and target.alive():
                diamond = pg.Surface((28, 28), pg.SRCALPHA)
                points = [(14, 1), (27, 14), (14, 27), (1, 14)]
                pg.draw.lines(diamond, (255, 170, 50, 230), True, points, 2)
                surface.blit(diamond, diamond.get_rect(center=target.rect.center), special_flags=pg.BLEND_ADD)
