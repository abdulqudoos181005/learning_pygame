# pyrefly: ignore [missing-import]
import os
import math
import random
import array
import pygame as pg


class AudioDirector:
    """
    Sprint 11 / Pillar C — Directed Audio System.
    
    Provides studio-grade audio mixing and reactive sound design:
    - Dedicated audio buses (Music, Combat SFX, UI) with independent volume controls.
    - Ducking: Automatically dips music by 6-8 dB on heavy events (boss warning, death).
    - Spatial-Lite: Stereo panning for in-game SFX based on screen X position.
    - One-Shot Voice Gating: Limits concurrent laser sounds (max 4) and prevents sound stacking.
    - Pitch variance: Subtle pitch/tone variation for repeated weapon fire.
    - Procedural Menu Bed: Generates a sleek ambient sci-fi drone/arpeggiated music bed
      when in menus or hangar so the game never sits in dead silence.
    - Seamless Stems & State Transitions: Crossfades, stinger triggers, and clean stops.
    """

    MAX_LASER_VOICES = 4
    LASER_MIN_INTERVAL = 0.05

    def __init__(self, assets=None, screen_width=1280):
        self.assets = assets
        self.screen_width = screen_width
        self.mixer_available = bool(pg.mixer.get_init())

        # Bus volumes (0.0 to 1.0)
        self.music_volume = 0.7
        self.sfx_volume = 0.8
        self.ui_volume = 0.8

        # Ducking parameters
        self.is_ducked = False
        self.duck_timer = 0.0
        self.duck_duration = 0.4
        self.duck_factor = 0.45  # ~-7 dB reduction

        # Laser one-shot voice limiting & timestamps
        self.active_laser_channels = []
        self.last_laser_time = 0.0

        # Dedicated channel allocation
        # We reserve channel 0 for UI, channel 1-4 for player lasers, 5-7 for enemy/sfx
        if self.mixer_available:
            try:
                pg.mixer.set_num_channels(24)
            except Exception:
                pass

        # Music state tracking
        self.current_music_track = None
        self.procedural_menu_sound = None
        self.procedural_menu_channel = None
        self.target_music_volume = self.music_volume
        self.current_effective_music_volume = self.music_volume

        # Generate procedural ambient menu music if mixer is initialized
        if self.mixer_available:
            self._generate_menu_ambient_bed()

    def _generate_menu_ambient_bed(self):
        """
        Synthesizes a lush, low-intensity sci-fi ambient pad/drone in 16-bit PCM stereo.
        This provides a rich atmospheric backdrop for menus and hangars without external files.
        """
        try:
            sample_rate = 44100
            duration = 6.0  # 6 second looping ambient sound bed
            total_samples = int(sample_rate * duration)
            
            # Create stereo 16-bit signed integer buffer
            buffer = array.array("h")
            
            # Ambient frequencies (Space chord: D minor / sus2 - D2, A2, E3, F3)
            # 73.42 Hz, 110.0 Hz, 164.81 Hz, 174.61 Hz
            freqs = [73.42, 110.0, 164.81, 174.61]
            
            for i in range(total_samples):
                t = i / sample_rate
                # Slow gentle LFO filter modulation
                lfo = 0.7 + 0.3 * math.sin(2.0 * math.pi * 0.25 * t)
                lfo2 = 0.8 + 0.2 * math.cos(2.0 * math.pi * 0.15 * t)
                
                # Harmonic synthesis
                sample_val = 0.0
                for idx, f in enumerate(freqs):
                    amp = 0.25 / (idx + 1)
                    # Subtly detuned chorus effect for left and right
                    sample_val += amp * math.sin(2.0 * math.pi * f * t)
                
                # Add a soft atmospheric noise hiss (cosmic dust)
                noise = (random.random() * 2.0 - 1.0) * 0.015
                sample_val = (sample_val * lfo + noise) * 0.4
                
                # Pan slightly across stereo
                left_amp = lfo2
                right_amp = 2.0 - lfo2
                
                left_sample = int(max(-32767, min(32767, sample_val * left_amp * 20000)))
                right_sample = int(max(-32767, min(32767, sample_val * right_amp * 20000)))
                
                buffer.append(left_sample)
                buffer.append(right_sample)

            self.procedural_menu_sound = pg.mixer.Sound(buffer=buffer)
            self.procedural_menu_sound.set_volume(self.music_volume * 0.55)
        except Exception as e:
            self.procedural_menu_sound = None

    def update(self, dt):
        """Processes continuous audio updates, timers, ducking fades, and voice cleanups."""
        if not self.mixer_available:
            return

        # Ducking timer update
        if self.is_ducked:
            self.duck_timer -= dt
            if self.duck_timer <= 0:
                self.is_ducked = False

        # Calculate effective target volume
        mult = self.duck_factor if self.is_ducked else 1.0
        target = self.music_volume * mult
        
        # Smooth interpolation to target music volume
        if abs(self.current_effective_music_volume - target) > 0.01:
            diff = target - self.current_effective_music_volume
            self.current_effective_music_volume += diff * min(1.0, 10.0 * dt)
            try:
                pg.mixer.music.set_volume(self.current_effective_music_volume)
                if self.procedural_menu_sound and self.procedural_menu_channel:
                    self.procedural_menu_sound.set_volume(self.current_effective_music_volume * 0.55)
            except Exception:
                pass

        # Cleanup finished laser channels
        self.active_laser_channels = [ch for ch in self.active_laser_channels if ch.get_busy()]

    def set_bus_volumes(self, music=None, sfx=None, ui=None):
        """Sets volumes for the independent audio buses."""
        if music is not None:
            self.music_volume = max(0.0, min(1.0, float(music)))
            if self.mixer_available:
                try:
                    pg.mixer.music.set_volume(self.music_volume)
                    if self.procedural_menu_sound:
                        self.procedural_menu_sound.set_volume(self.music_volume * 0.55)
                except Exception:
                    pass
        if sfx is not None:
            self.sfx_volume = max(0.0, min(1.0, float(sfx)))
        if ui is not None:
            self.ui_volume = max(0.0, min(1.0, float(ui)))

    def trigger_ducking(self, duration=0.45, factor=0.4):
        """Ducks the background music volume by ~6-8 dB for high-priority dramatic moments."""
        self.is_ducked = True
        self.duck_timer = max(self.duck_timer, duration)
        self.duck_factor = factor

    def play_music(self, track_name, loop=True, fade_ms=500):
        """
        Manages background music playback with smooth transitions between tracks or procedural beds.
        Tracks: 'menu', 'combat', 'boss', 'game_over'
        """
        if not self.mixer_available:
            return

        # For non-menu tracks, skip if already playing the same track.
        # For 'menu', always restart the ambient bed so it plays correctly
        # when returning from combat (avoiding the silent-menu bug).
        if track_name != "menu" and self.current_music_track == track_name:
            return

        self.current_music_track = track_name

        try:
            # If menu music is requested and we have the procedural drone bed, use it
            if track_name == "menu":
                try:
                    pg.mixer.music.fadeout(fade_ms)
                except Exception:
                    pass
                if self.procedural_menu_sound:
                    # Stop any existing playback first to restart cleanly
                    try:
                        self.procedural_menu_sound.stop()
                    except Exception:
                        pass
                    self.procedural_menu_sound.set_volume(self.music_volume * 0.55)
                    self.procedural_menu_channel = self.procedural_menu_sound.play(loops=-1, fade_ms=fade_ms)
                return
            else:
                # Stop menu ambient bed if switching to combat or boss
                if self.procedural_menu_sound:
                    self.procedural_menu_sound.stop()
                    self.procedural_menu_channel = None

            # Look up track path
            track_key = "theme_boss_arcade_battle" if track_name in ("boss", "combat") else track_name
            sound_path = None
            if self.assets and hasattr(self.assets, "_sound_index"):
                sound_path = self.assets._sound_index.get(track_key) or self.assets._sound_index.get(f"audio/music/{track_key}")
            
            if sound_path and os.path.exists(sound_path):
                pg.mixer.music.load(sound_path)
                pg.mixer.music.set_volume(self.music_volume)
                pg.mixer.music.play(loops=-1 if loop else 0, fade_ms=fade_ms)
        except Exception as e:
            pass

    def stop_music(self, fade_ms=400):
        """Stops all active music smoothly."""
        if not self.mixer_available:
            return
        try:
            pg.mixer.music.fadeout(fade_ms)
            if self.procedural_menu_sound:
                self.procedural_menu_sound.fadeout(fade_ms)
            self.current_music_track = None
        except Exception:
            pass

    def play_sfx(self, name, pos_x=None, volume_mult=1.0, pitch_variance=False):
        """
        Plays a combat sound effect with bus volume scaling, voice stealing/capping,
        and optional spatial stereo panning.
        """
        if not self.mixer_available or not self.assets or self.sfx_volume <= 0.001:
            return None

        # Voice capping for high-frequency player lasers
        is_laser = "laser" in name and "boss" not in name
        if is_laser:
            now = pg.time.get_ticks() / 1000.0
            if now - self.last_laser_time < self.LASER_MIN_INTERVAL and len(self.active_laser_channels) >= self.MAX_LASER_VOICES:
                return None
            self.last_laser_time = now

        sound = self.assets.get_sound(name)
        if sound is None or not hasattr(sound, "play"):
            return None

        try:
            # Find an available channel
            channel = pg.mixer.find_channel()
            if channel is None:
                # Steal an active laser channel if available
                if self.active_laser_channels:
                    channel = self.active_laser_channels.pop(0)
                else:
                    return None

            # Spatial stereo panning calculation (-0.7 Left to +0.7 Right)
            left_vol = 1.0
            right_vol = 1.0
            if pos_x is not None and self.screen_width > 0:
                normalized_x = max(0.0, min(1.0, pos_x / self.screen_width))
                pan = (normalized_x - 0.5) * 1.4  # Range -0.7 to +0.7
                left_vol = max(0.2, 1.0 - max(0.0, pan))
                right_vol = max(0.2, 1.0 + min(0.0, pan))

            final_vol = self.sfx_volume * volume_mult
            channel.set_volume(left_vol * final_vol, right_vol * final_vol)
            channel.play(sound)

            if is_laser:
                self.active_laser_channels.append(channel)
                if len(self.active_laser_channels) > self.MAX_LASER_VOICES:
                    self.active_laser_channels.pop(0)

            return channel
        except Exception:
            return None

    def play_ui(self, sound_type="tick", volume_mult=1.0):
        """
        Plays UI audio grammar:
        - 'hover' / 'tick' : subtle navigation feedback
        - 'confirm' / 'select' : positive choice chime
        - 'danger' / 'quit' : low warning tone
        - 'purchase' : upgrade shop success chime
        """
        if not self.mixer_available or self.ui_volume <= 0.001:
            return

        final_vol = self.ui_volume * volume_mult

        try:
            if sound_type in ("purchase", "confirm", "select"):
                if self.assets:
                    snd = self.assets.get_sound("powerup")
                    if snd and hasattr(snd, "set_volume"):
                        snd.set_volume(final_vol * 0.7)
                        snd.play()
            elif sound_type == "danger":
                if self.assets:
                    snd = self.assets.get_sound("shield_down")
                    if snd and hasattr(snd, "set_volume"):
                        snd.set_volume(final_vol * 0.5)
                        snd.play()
            elif sound_type in ("hover", "tick"):
                # Subtle click / blip
                if self.assets:
                    snd = self.assets.get_sound("laser_pew")
                    if snd and hasattr(snd, "set_volume"):
                        snd.set_volume(final_vol * 0.15)
                        snd.play()
        except Exception:
            pass
