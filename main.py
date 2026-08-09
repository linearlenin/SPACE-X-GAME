#!/usr/bin/env python3
"""
main.py - 2D Archery Game using Pygame

Features:
- Window 800x600 with sky and grass
- Bow on left follows mouse Y
- Hold mouse to charge power, release to shoot
- Arrow physics with gravity
- Three target types moving across screen
- Score and Lives system
- Level system (1-5) increases spawn rate and speeds
- Sound effects and background music (from audio/ folder)
- Instructions on screen and Game Over screen

Run: python main.py  (requires pygame: pip install pygame)
"""

# -----------------------------
# Imports and initialization
# -----------------------------
import pygame
import sys
import random
import math
import os

# Initialize pygame modules (display, event, etc.)
pygame.init()

# -----------------------------
# Constants and configuration
# -----------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors (R,G,B)
SKY_BLUE = (135, 206, 235)
GRASS_GREEN = (60, 179, 113)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
DARK_BROWN = (100, 50, 20)
ARROW_COLOR = (50, 50, 50)

# Bow position (left side)
BOW_X = 80
BOW_WIDTH = 20
BOW_HEIGHT = 80

# Arrow physics
GRAVITY = 0.4  # pixels per frame^2
POWER_CHARGE_RATE = 0.6  # units per frame while holding mouse
MAX_POWER = 30.0  # max initial speed
MIN_POWER = 6.0

# Level system configuration
LEVEL_MAX = 5                     # maximum level
LEVEL_SCORE = 200                 # points required per level (every 200 points -> next level)
# Spawn intervals per level (ms). Lower means more frequent spawns at higher levels.
LEVEL_SPAWN_INTERVALS = [2200, 1800, 1500, 1350, 1200]  # slower spawns to make levels easier
# Speed multipliers per level to make targets faster at higher levels
LEVEL_SPEED_MULTIPLIERS = [1.0, 1.04, 1.08, 1.12, 1.16]  # gentler speed growth for easier pacing
# Display time for "LEVEL UP!" message in milliseconds
LEVEL_UP_DISPLAY_MS = 2000

# Target spawn event (timer will be set based on level)
SPAWN_EVENT = pygame.USEREVENT + 1
# Wind change event - changes wind periodically to cause arrow drift
WIND_EVENT = pygame.USEREVENT + 2
WIND_BASE_INTERVAL_MS = 3800  # change wind interval for level 1 (longer => less frequent)
WIND_INTERVAL_REDUCTION_MS = 300  # faster wind changes at higher levels
WIND_MIN_INTERVAL_MS = 900
WIND_BASE_STRENGTH = 0.35  # reduced base wind strength to make arrows more stable
WIND_LEVEL_STRENGTH = 0.08  # reduced additional wind per level
# Current wind strength (pixels per frame influence)
WIND = 0.0

# Spawn probabilities for targets by level
# Each entry is (red_threshold, blue_threshold), with gold filling the remainder.
LEVEL_SPAWN_DISTRIBUTIONS = [
    (0.60, 0.90),  # L1: 60% red, 30% blue, 10% gold
    (0.55, 0.88),  # L2: 55% red, 33% blue, 12% gold
    (0.50, 0.85),  # L3: 50% red, 35% blue, 15% gold
    (0.45, 0.82),  # L4: 45% red, 37% blue, 18% gold
    (0.40, 0.80),  # L5: 40% red, 40% blue, 20% gold
]

# Font
FONT = pygame.font.SysFont(None, 28)
BIG_FONT = pygame.font.SysFont(None, 72)
# Background headline font (large, used for faded background text)
# Try a serif/classy font if available, fall back to default
def _get_classy_font(size):
    for name in ('Garamond', 'Georgia', 'Times New Roman', 'Palatino', 'Serif'):
        try:
            f = pygame.font.SysFont(name, size)
            return f
        except Exception:
            continue
    return pygame.font.SysFont(None, size)

BACKGROUND_FONT = _get_classy_font(64)  # reduced for less intrusion
BACKGROUND_SUBFONT = _get_classy_font(24)

# Space background stars
# UI safety margin to prevent the player's ship from overlapping corner decorations
TOP_UI_MARGIN = 12
TOP_SAFE_Y = TOP_UI_MARGIN + BACKGROUND_FONT.get_height() + 8

SPACE_BLACK = (6, 6, 20)
STAR_COUNT = 140
# Each star: (x, y, base_radius, phase)
STARS = [(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.uniform(0.6, 1.6), random.uniform(0.5, 2.5)) for _ in range(STAR_COUNT)]

# Lives and score
STARTING_LIVES = 5
POINTS_PER_HIT = 10

# -----------------------------
# Game display setup
# -----------------------------
# Works on desktop and mobile with pygbag
window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Space X")
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
window_width, window_height = SCREEN_WIDTH, SCREEN_HEIGHT
clock = pygame.time.Clock()


def window_to_game_coords(x, y):
    """Convert display window coordinates to fixed game coordinates."""
    scale = min(window_width / SCREEN_WIDTH, window_height / SCREEN_HEIGHT)
    if scale == 0:
        return x, y
    rendered_width = int(SCREEN_WIDTH * scale)
    rendered_height = int(SCREEN_HEIGHT * scale)
    offset_x = (window_width - rendered_width) // 2
    offset_y = (window_height - rendered_height) // 2
    game_x = (x - offset_x) / scale
    game_y = (y - offset_y) / scale
    return max(0, min(SCREEN_WIDTH, int(game_x))), max(0, min(SCREEN_HEIGHT, int(game_y)))

# -----------------------------
# Audio globals (initialized in main)
# -----------------------------
# These variables hold pygame.mixer objects or flags. They start as None/False
# and are set during initialization in main_loop(). If audio files are missing
# the game will continue but sounds won't play.
shoot_sound = None  # sound played when firing an arrow
hit_sound = None    # sound played when an arrow hits a target
miss_sound = None   # sound played when arrow goes off-screen
bg_music_loaded = False  # True if background music was successfully loaded

# -----------------------------
# Helper classes: Arrow and Target
# -----------------------------
class Arrow:
    """Represents a missile fired from the ship.

    The projectile travels in a straight line at fixed velocity, with a limited
    lifetime. It does not arc under gravity, so the shot feels like a true missile.
    """
    def __init__(self, x, y, vx, vy, level=1):
        # Position
        self.x = x
        self.y = y
        # Velocity
        self.vx = vx
        self.vy = vy
        # Length for drawing
        self.length = 28
        # Determine a rectangle for collision checking
        self.radius = 4
        # Alive flag
        self.alive = True
        # Timestamps for lifetime handling (ms)
        self.spawn_time = pygame.time.get_ticks()
        # Missile lifetime is slightly longer to make straight shots more forgiving
        self.lifetime_ms = max(2400, 3600 - (level - 1) * 200)
        # Flags for removal reason
        self.timed_out = False
        self.offscreen = False

    def update(self):
        """Update position using straight-line missile motion."""
        # Move straight in the fired direction without gravity or wind drift
        self.x += self.vx
        self.y += self.vy
        # Lifetime expiration
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime_ms:
            self.alive = False
            self.timed_out = True
        # If missile goes off-screen, mark not alive and offscreen
        if self.x > SCREEN_WIDTH + 100 or self.y > SCREEN_HEIGHT + 200 or self.y < -200:
            self.alive = False
            self.offscreen = True

    def draw(self, surface):
        """Draw the projectile as a missile with a small flame tail."""
        angle = math.atan2(self.vy, self.vx)
        # Missile center and nose
        cx = int(self.x)
        cy = int(self.y)
        # Missile body (rotated rectangle approximated by polygon)
        length = self.length
        nose = (int(cx + math.cos(angle) * (length//2)), int(cy + math.sin(angle) * (length//2)))
        tail = (int(cx - math.cos(angle) * (length//2)), int(cy - math.sin(angle) * (length//2)))
        perp = angle + math.pi / 2
        w = 6
        p1 = (int(nose[0] + math.cos(perp) * (w)), int(nose[1] + math.sin(perp) * (w)))
        p2 = (int(nose[0] - math.cos(perp) * (w)), int(nose[1] - math.sin(perp) * (w)))
        p3 = (int(tail[0] - math.cos(perp) * (w)), int(tail[1] - math.sin(perp) * (w)))
        p4 = (int(tail[0] + math.cos(perp) * (w)), int(tail[1] + math.sin(perp) * (w)))
        pygame.draw.polygon(surface, (180, 30, 30), [p1, p2, p3, p4])
        # Nose cone
        nose_tip = (int(cx + math.cos(angle) * (length//2 + 6)), int(cy + math.sin(angle) * (length//2 + 6)))
        pygame.draw.polygon(surface, (240, 200, 80), [nose_tip, p1, p2])
        # Flame tail
        flame_len = 10
        flame_point = (int(tail[0] - math.cos(angle) * flame_len), int(tail[1] - math.sin(angle) * flame_len))
        pygame.draw.polygon(surface, (255, 180, 40), [tail, p3, flame_point, p4])

    def get_rect(self):
        """Return a small rect around the arrow's tip for collision detection."""
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)


class Target:
    """Represents a moving target of one of three types.

    Types (ttype):
    1 - Red   : fast, small, 10 pts
    2 - Blue  : medium speed/size, 20 pts
    3 - Gold  : slow, large, 50 pts

    The constructor accepts a `level` parameter to scale speed by level.
    """
    def __init__(self, ttype, level=1):
        # Type controls size, base speed, color, and point value
        self.type = ttype  # 1=red,2=blue,3=gold
        self.y = random.randint(80, SCREEN_HEIGHT - 140)
        self.x = SCREEN_WIDTH + 60
        if self.type == 1:
            # Red: fast, small, 10 pts
            self.radius = 12
            base_speed = -4.2
            self.color = (220, 50, 50)
            self.point_value = 10
        elif self.type == 2:
            # Blue: medium, 20 pts
            self.radius = 20
            base_speed = -2.8
            self.color = (80, 120, 220)
            self.point_value = 20
        else:
            # Gold: slow, large, 50 pts
            self.radius = 28
            base_speed = -1.3
            self.color = (255, 215, 0)
            self.point_value = 50
        # Apply level speed multiplier (clamped to LEVEL_MAX)
        lvl_index = max(0, min(level, LEVEL_MAX) - 1)
        multiplier = LEVEL_SPEED_MULTIPLIERS[lvl_index]
        self.speed = base_speed * multiplier
        # Alive flag
        self.alive = True

    def update(self):
        """Move horizontally across the screen."""
        self.x += self.speed
        # If off left side, mark not alive (and will cost a life in game logic)
        if self.x < -80:
            self.alive = False

    def draw(self, surface):
        """Draw alien targets moving across the screen.

        Visuals change by type:
        1 - Small UFO (fast): small saucer with green tint
        2 - Medium Alien (medium): larger alien with antenna
        3 - Big Mothership (slow): large multi-segment saucer
        """
        cx = int(self.x)
        cy = int(self.y)
        if self.type == 1:
            # Small UFO
            pygame.draw.ellipse(surface, (40, 200, 100), (cx - self.radius, cy - self.radius//2, self.radius*2, self.radius))
            pygame.draw.ellipse(surface, (30, 30, 30), (cx - self.radius//2, cy - self.radius//2 - 6, self.radius, self.radius//2))
            # Glow
            pygame.draw.circle(surface, (80, 220, 140), (cx, cy + 6), max(2, self.radius//3), 1)
        elif self.type == 2:
            # Medium alien with antenna
            body_rect = pygame.Rect(cx - self.radius, cy - self.radius, self.radius*2, int(self.radius*1.4))
            pygame.draw.ellipse(surface, (120, 100, 220), body_rect)
            # Eye
            pygame.draw.circle(surface, (255, 255, 255), (cx + 6, cy - 4), max(4, self.radius//4))
            pygame.draw.circle(surface, (20, 20, 20), (cx + 8, cy - 2), max(2, self.radius//7))
            # Antenna
            pygame.draw.line(surface, (200, 200, 255), (cx, cy - self.radius), (cx, cy - self.radius - 12), 2)
            pygame.draw.circle(surface, (255, 200, 100), (cx, cy - self.radius - 14), 4)
        else:
            # Big mothership
            pygame.draw.ellipse(surface, (230, 180, 60), (cx - self.radius, cy - int(self.radius*0.6), self.radius*2, int(self.radius*1.2)))
            pygame.draw.ellipse(surface, (180, 120, 40), (cx - int(self.radius*0.7), cy - int(self.radius*0.45), int(self.radius*1.4), int(self.radius*0.8)))
            # Dome
            pygame.draw.circle(surface, (160, 200, 240), (cx, cy - int(self.radius*0.2)), max(6, int(self.radius*0.4)))
            # Lights
            for i in range(-2, 3):
                lx = cx + i * (self.radius // 3)
                pygame.draw.circle(surface, (255, 100, 100), (lx, cy + int(self.radius*0.25)), 3)

    def get_rect(self):
        """Return a rect for collision detection."""
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)


# -----------------------------
# Game state management
# -----------------------------

def reset_game_state():
    """Initialize or reset game state variables, including level info and particles."""
    state = {}
    state['score'] = 0
    state['lives'] = STARTING_LIVES
    state['arrows'] = []  # list of Arrow
    state['targets'] = []  # list of Target
    state['particles'] = []  # particle effects for hits
    state['power'] = 0.0
    state['charging'] = False
    state['game_over'] = False
    state['bow_y'] = max(TOP_SAFE_Y, SCREEN_HEIGHT // 2)
    # Leveling
    state['level'] = 1
    state['level_up_time'] = 0  # pygame.time.get_ticks() when level up occurs
    # Kills tracking: number of targets destroyed in the current level
    state['level_kills'] = 0
    # Pause state for game freeze
    state['paused'] = False
    # Sound toggle state (start enabled)
    state['sound_enabled'] = True
    return state

state = reset_game_state()
# Ensure the spawn timer matches the starting level's spawn interval
pygame.time.set_timer(SPAWN_EVENT, LEVEL_SPAWN_INTERVALS[state['level'] - 1])
# Start wind timer using level-based interval
pygame.time.set_timer(WIND_EVENT, max(WIND_MIN_INTERVAL_MS, WIND_BASE_INTERVAL_MS - (state['level'] - 1) * WIND_INTERVAL_REDUCTION_MS))


def get_wind_strength(level):
    """Compute how strong the wind should be based on current level."""
    return WIND_BASE_STRENGTH + (level - 1) * WIND_LEVEL_STRENGTH


def get_wind_interval(level):
    """Compute wind change interval based on current level."""
    return max(WIND_MIN_INTERVAL_MS, WIND_BASE_INTERVAL_MS - (level - 1) * WIND_INTERVAL_REDUCTION_MS)

# -----------------------------
# Drawing helpers
# -----------------------------

def draw_background(surface):
    """Draw a space background with twinkling stars.

    Stars are generated once at module load and their brightness is animated
    over time to create a subtle twinkling/starfield effect.
    """
    # Fill with deep space color
    surface.fill(SPACE_BLACK)
    # Simple twinkling stars
    t = pygame.time.get_ticks() / 1000.0
    for sx, sy, base_r, phase in STARS:
        # Brightness oscillates with time and a per-star phase
        b = 0.6 + 0.4 * math.sin(t * (1.0 + phase) + phase * 3.14)
        if b < 0.2:
            b = 0.2
        color_val = int(180 + 75 * b)
        pygame.draw.circle(surface, (color_val, color_val, color_val), (sx, sy), max(1, int(base_r)))


def draw_bow(surface, x, y, power, charging):
    """Draw the player's ship (spaceship) and a missile launcher.

    The ship gently hovers (bobbing) and the thruster visual flickers. The
    missile launcher aims toward the mouse and the power bar shows charge.
    """
    # Time-based animation parameters
    t = pygame.time.get_ticks() / 1000.0
    bob_amp = 3
    bob_speed = 1.5
    bob = math.sin(t * bob_speed * 2 * math.pi) * bob_amp
    # Thruster flicker
    flicker = (math.sin(t * 20.0) + 1.0) * 0.5

    y_draw = int(y + bob)

    # --- Ship body (simple triangular/rounded ship) ---
    ship_color = (180, 180, 200)
    hull = [
        (x - 26, y_draw - 14),
        (x + 24, y_draw),
        (x - 26, y_draw + 14),
    ]
    pygame.draw.polygon(surface, ship_color, hull)
    # Cockpit dome
    pygame.draw.ellipse(surface, (80, 120, 200), (x - 6, y_draw - 10, 24, 16))
    pygame.draw.ellipse(surface, (120, 170, 240), (x - 2, y_draw - 6, 16, 10))
    # Side fins
    pygame.draw.polygon(surface, (160, 160, 180), [(x - 8, y_draw - 12), (x - 20, y_draw - 18), (x - 18, y_draw - 6)])
    pygame.draw.polygon(surface, (160, 160, 180), [(x - 8, y_draw + 12), (x - 20, y_draw + 18), (x - 18, y_draw + 6)])

    # Thruster flame (behind ship) — flicker effect
    flame_h = int(8 + flicker * 6)
    pygame.draw.polygon(surface, (255, 140, 40), [(x - 30, y_draw), (x - 30 - flame_h, y_draw - 6), (x - 30 - flame_h, y_draw + 6)])
    pygame.draw.circle(surface, (255, 200, 80), (x - 30 - flame_h // 2, y_draw), 4)

    # --- Missile launcher: a barrel that aims toward the mouse ---
    mx, my = pygame.mouse.get_pos()
    mx, my = window_to_game_coords(mx, my)
    cx = x + 6
    cy = y_draw
    angle = math.atan2(my - cy, mx - cx)
    barrel_len = 36
    tip_x = int(cx + math.cos(angle) * barrel_len)
    tip_y = int(cy + math.sin(angle) * barrel_len)
    # Barrel
    pygame.draw.line(surface, (40, 40, 40), (cx, cy), (tip_x, tip_y), 8)
    pygame.draw.line(surface, (120, 120, 120), (cx, cy), (tip_x, tip_y), 4)
    # Muzzle glow
    glow_pos = (int(cx + math.cos(angle) * (barrel_len - 6)), int(cy + math.sin(angle) * (barrel_len - 6)))
    pygame.draw.circle(surface, (255, 200, 120), glow_pos, 6)

    # --- Power bar above ship (vertical gradient + percent) ---
    if charging:
        bar_x = x + 50
        bar_y = y_draw - 88
        bar_w = 18
        bar_h = 112
        pygame.draw.rect(surface, BLACK, (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6))
        pygame.draw.rect(surface, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h))
        fill_ratio = max(0.0, min(1.0, power / MAX_POWER))
        fill_h = int(fill_ratio * bar_h)
        green = (50, 200, 50)
        yellow = (255, 215, 0)
        red = (220, 50, 50)
        step = 4
        for i in range(0, bar_h, step):
            rel = i / float(bar_h)
            if rel < 0.5:
                tcol = rel / 0.5
                r = int(green[0] + (yellow[0] - green[0]) * tcol)
                g = int(green[1] + (yellow[1] - green[1]) * tcol)
                b = int(green[2] + (yellow[2] - green[2]) * tcol)
            else:
                tcol = (rel - 0.5) / 0.5
                r = int(yellow[0] + (red[0] - yellow[0]) * tcol)
                g = int(yellow[1] + (red[1] - yellow[1]) * tcol)
                b = int(yellow[2] + (red[2] - yellow[2]) * tcol)
            strip_y = bar_y + (bar_h - i - step)
            if i < fill_h:
                draw_h = min(step, fill_h - i)
                pygame.draw.rect(surface, (r, g, b), (bar_x, strip_y, bar_w, draw_h))
        percent = int(fill_ratio * 100)
        pct_surf = FONT.render(f"{percent}%", True, BLACK)
        pct_x = bar_x + bar_w // 2 - pct_surf.get_width() // 2
        pct_y = bar_y - pct_surf.get_height() - 4
        surface.blit(pct_surf, (pct_x, pct_y))
    else:
        pass


def draw_ui(surface, score, lives, level, level_kills, sound_enabled, wind):
    """Draw Score, Lives, Level, Kills, Sound state, and Wind indicator."""
    ui_color = (255, 255, 255)
    # Lives top-left
    lives_surf = FONT.render(f"Lives: {lives}", True, ui_color)
    surface.blit(lives_surf, (12, 8))
    # Sound top-left (below lives)
    sound_text = "ON" if sound_enabled else "OFF"
    sound_surf = FONT.render(f"Sound: {sound_text}", True, ui_color)
    surface.blit(sound_surf, (12, 8 + lives_surf.get_height() + 6))
    # Score top-right
    score_surf = FONT.render(f"Score: {score}", True, ui_color)
    score_x = SCREEN_WIDTH - score_surf.get_width() - 12
    surface.blit(score_surf, (score_x, 8))
    # Level and Kills top-right in one row below Score
    level_kills_text = f"Level: {level}   Kills: {level_kills}"
    level_kills_surf = FONT.render(level_kills_text, True, ui_color)
    surface.blit(level_kills_surf, (SCREEN_WIDTH - level_kills_surf.get_width() - 12, 8 + score_surf.get_height() + 6))
    # Wind indicator top-center
    wind_direction = "→" if wind >= 0 else "←"
    wind_surf = FONT.render(f"Wind: {wind_direction} {abs(wind):.1f}", True, ui_color)
    surface.blit(wind_surf, (SCREEN_WIDTH // 2 - wind_surf.get_width() // 2, 8))
 
def draw_pause_overlay(surface):
    """Draw the paused game overlay."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))
    pause_text = BIG_FONT.render("PAUSED", True, (255, 255, 255))
    pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
    surface.blit(pause_text, pause_rect)
    hint = FONT.render("Press P to resume or ESC to quit", True, (220, 220, 220))
    hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
    surface.blit(hint, hint_rect)
 
# -----------------------------
# Collision and game rules
# -----------------------------

def handle_collisions(state):
    """Check for collisions between arrows and targets and update score/lives.

    Plays hit sound when a target is successfully hit. Uses global hit_sound
    and respects state['sound_enabled'] so sounds can be toggled. Also spawns
    a simple particle effect at the collision point and tracks kills per level.
    """
    global hit_sound
    arrows = state['arrows']
    targets = state['targets']
    # Check each arrow against each target
    for arrow in arrows[:]:
        a_rect = arrow.get_rect()
        for target in targets[:]:
            t_rect = target.get_rect()
            if a_rect.colliderect(t_rect):
                # Hit detected: update score by target's point value
                state['score'] += getattr(target, 'point_value', POINTS_PER_HIT)
                # Increment kills for this level
                state['level_kills'] = state.get('level_kills', 0) + 1
                # Play hit sound if available and enabled
                if state.get('sound_enabled', True) and hit_sound:
                    try:
                        hit_sound.play()
                    except Exception:
                        # If sound playback fails, ignore and continue
                        print("Warning: failed to play hit sound")
                # Spawn particles at collision location for visual feedback.
                # Stronger particle bursts are used to make hits feel more impactful.
                spawn_particles(state, int(target.x), int(target.y), count=16, color=target.color)
                # Remove arrow and target
                try:
                    arrows.remove(arrow)
                except ValueError:
                    pass
                try:
                    targets.remove(target)
                except ValueError:
                    pass
                break

# -----------------------------
# Particle system for hit effects
# -----------------------------
class Particle:
    """Simple particle used for hit effects.

    Each particle has position, velocity, lifetime and color. Particles fade
    out over their lifetime and are removed when expired.
    """
    def __init__(self, x, y, vx, vy, color, lifetime=700):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime  # ms
        self.birth = pygame.time.get_ticks()

    def update(self):
        self.vy += 0.12  # slight gravity on particles
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        # Fade based on age
        age = pygame.time.get_ticks() - self.birth
        if age >= self.lifetime:
            return
        alpha = max(0, 255 - int((age / self.lifetime) * 255))
        surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        surf.fill((*self.color, alpha))
        surface.blit(surf, (int(self.x), int(self.y)))


def spawn_particles(state, x, y, count=14, color=(255, 255, 255)):
    """Spawn a burst of particles at (x,y)."""
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 5.0)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        p = Particle(x, y, vx, vy, color, lifetime=random.randint(700, 1200))
        state['particles'].append(p)


# -----------------------------
# Main game loop
# -----------------------------

def main_loop():
    """Primary game loop: event handling, updates, drawing, and state transitions.

    This function initializes pygame.mixer and loads audio files. If any audio
    file is missing, a warning is printed but the game continues without that
    audio feature.
    """
    global shoot_sound, hit_sound, bg_music_loaded, WIND, window, window_width, window_height

    running = True

    # -----------------------------
    # Initialize pygame mixer and load sounds
    # -----------------------------
    # Initializing mixer here so that audio initialization occurs during main
    # startup and errors can be handled gracefully without crashing the game.
    try:
        pygame.mixer.init()
    except Exception:
        print("Warning: pygame.mixer could not be initialized. Sounds will be disabled.")
        # Ensure sound globals remain None so playback is skipped
        shoot_sound = None
        hit_sound = None
        miss_sound = None
        bg_music_loaded = False
    else:
        # Attempt to load sound effect files from audio/ directory. If a file is
        # missing or cannot be loaded a warning will be printed and the game
        # continues with that sound omitted.
        try:
            shoot_path = os.path.join('audio', 'shoot.wav')
            if os.path.exists(shoot_path):
                shoot_sound = pygame.mixer.Sound(shoot_path)
            else:
                print(f"Warning: {shoot_path} not found. Shoot sound disabled.")
        except Exception:
            shoot_sound = None
            print("Warning: failed to load shoot sound")

        try:
            hit_path = os.path.join('audio', 'hit.wav')
            if os.path.exists(hit_path):
                hit_sound = pygame.mixer.Sound(hit_path)
            else:
                print(f"Warning: {hit_path} not found. Hit sound disabled.")
        except Exception:
            hit_sound = None
            print("Warning: failed to load hit sound")

        try:
            miss_path = os.path.join('audio', 'miss.wav')
            # Ensure audio directory exists
            audio_dir = os.path.dirname(miss_path)
            if audio_dir and not os.path.exists(audio_dir):
                os.makedirs(audio_dir, exist_ok=True)
            if not os.path.exists(miss_path):
                # Create a small silent WAV placeholder (~50ms) so missing-file warnings do not occur
                try:
                    import wave
                    duration_ms = 50
                    sr = 22050
                    n_frames = int(sr * duration_ms / 1000)
                    with wave.open(miss_path, 'w') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(sr)
                        silence = (0).to_bytes(2, byteorder='little', signed=True)
                        wf.writeframes(silence * n_frames)
                except Exception:
                    # Fallback: create an empty file to avoid file-not-found
                    try:
                        open(miss_path, 'wb').close()
                    except Exception:
                        pass
            try:
                miss_sound = pygame.mixer.Sound(miss_path)
            except Exception:
                miss_sound = None
                print(f"Warning: failed to load miss sound from {miss_path}")

        # Background music disabled per user request — only sound effects (SFX) will be used.
        # Background music loading/playback removed to avoid disturbance.
        bg_music_loaded = False
        # To re-enable background music, restore loading and playback logic here.

    # Main loop
    while running:
        # Cap framerate and get time delta
        dt = clock.tick(FPS) / 1000.0

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Window resized: update display size for responsive scaling
            elif event.type == pygame.VIDEORESIZE:
                window_width, window_height = event.w, event.h
                window = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)

            # Touch motion: update bow position when finger moves on mobile
            elif event.type == pygame.FINGERMOTION and state.get('touch_mode', False):
                touch_x = int(event.x * window_width)
                touch_y = int(event.y * window_height)
                _, game_y = window_to_game_coords(touch_x, touch_y)
                state['bow_y'] = max(TOP_SAFE_Y, min(SCREEN_HEIGHT - 60, game_y))

            # Mouse pressed or touch pressed: start charging power
            elif not state['game_over'] and not state.get('paused', False) and (
                (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
                or event.type == pygame.FINGERDOWN
            ):
                state['charging'] = True
                state['touch_mode'] = True if event.type == pygame.FINGERDOWN else state.get('touch_mode', False)
                # Update bow Y for touch input immediately
                if event.type == pygame.FINGERDOWN:
                    touch_x = int(event.x * window_width)
                    touch_y = int(event.y * window_height)
                    _, game_y = window_to_game_coords(touch_x, touch_y)
                    state['bow_y'] = max(TOP_SAFE_Y, min(SCREEN_HEIGHT - 60, game_y))
 
            # Mouse released or touch released: fire arrow if was charging
            elif not state['game_over'] and not state.get('paused', False) and (
                (event.type == pygame.MOUSEBUTTONUP and event.button == 1)
                or event.type == pygame.FINGERUP
            ):
                if state['charging']:
                    if event.type == pygame.MOUSEBUTTONUP:
                        mouse_x, mouse_y = window_to_game_coords(*event.pos)
                    else:
                        touch_x = int(event.x * window_width)
                        touch_y = int(event.y * window_height)
                        mouse_x, mouse_y = window_to_game_coords(touch_x, touch_y)
                    bx = BOW_X + 6
                    by = state['bow_y']
                    dx = mouse_x - bx
                    dy = mouse_y - by
                    angle = math.atan2(dy, dx)
                    # Map power to speed range
                    power = max(MIN_POWER, min(MAX_POWER, state['power']))
                    vx = math.cos(angle) * power
                    vy = math.sin(angle) * power
                    # Create arrow slightly ahead of bow with lifetime based on level
                    arrow = Arrow(
                        bx + math.cos(angle) * 18,
                        by + math.sin(angle) * 18,
                        vx,
                        vy,
                        level=state.get('level', 1),
                    )
                    state['arrows'].append(arrow)
                    # Play shoot sound (if enabled and loaded)
                    if state.get('sound_enabled', True) and shoot_sound:
                        try:
                            shoot_sound.play()
                        except Exception:
                            print("Warning: failed to play shoot sound")
                # Reset charging
                state['charging'] = False
            # Spawn targets on a timer event; this keeps the game flow separate from firing
            elif event.type == SPAWN_EVENT and not state['game_over'] and not state.get('paused', False):
               lvl = max(1, min(LEVEL_MAX, state.get('level', 1)))
               red_threshold, blue_threshold = LEVEL_SPAWN_DISTRIBUTIONS[lvl - 1]
               r = random.random()
               if r < red_threshold:
                   ttype = 1  # Red (fast, 10 pts)
               elif r < blue_threshold:
                   ttype = 2  # Blue (medium, 20 pts)
               else:
                   ttype = 3  # Gold (slow, 50 pts)
               state['targets'].append(Target(ttype, lvl))            # Wind change event - adjust global WIND randomly every few seconds
            elif event.type == WIND_EVENT:
                lvl = max(1, min(LEVEL_MAX, state.get('level', 1)))
                strength = get_wind_strength(lvl)
                # Choose a new wind strength between negative and positive bounds
                WIND = random.uniform(-strength, strength)
                # Reset the wind timer based on current level speed
                pygame.time.set_timer(WIND_EVENT, get_wind_interval(lvl))
                # Small informational print (optional)
                # print(f"Wind changed: {WIND:.2f}")

            # Key presses for restarting, quitting, and toggling sound
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and state['game_over']:
                    # Restart game: reset state and update spawn timer for level 1
                    new_state = reset_game_state()
                    state.update(new_state)
                    pygame.time.set_timer(SPAWN_EVENT, LEVEL_SPAWN_INTERVALS[state['level'] - 1])
                    # Reset wind to neutral and restart wind timer
                    WIND = 0.0
                    pygame.time.set_timer(WIND_EVENT, get_wind_interval(state['level']))
                    # Background music has been disabled — no music playback on restart.
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    # Toggle sound on/off
                    state['sound_enabled'] = not state.get('sound_enabled', True)
                    # Background music disabled — sound toggle affects only SFX (shoot/hit/miss)
                elif event.key == pygame.K_p and not state['game_over']:
                    state['paused'] = not state.get('paused', False)
                    state['charging'] = False

        # Update bow Y to follow mouse Y on desktop and use game coordinates for responsiveness
        mx, my = pygame.mouse.get_pos()
        mx, my = window_to_game_coords(mx, my)
        state['bow_y'] = max(TOP_SAFE_Y, min(SCREEN_HEIGHT - 60, my))
 
        # If charging, increase power
        if state['charging'] and not state['game_over'] and not state.get('paused', False):
            state['power'] += POWER_CHARGE_RATE
            if state['power'] > MAX_POWER:
                state['power'] = MAX_POWER
 
        # Only update game objects when not paused and not game over
        if not state['game_over'] and not state.get('paused', False):
            # Update arrows
            for arrow in state['arrows'][:]:
                arrow.update()
                if not arrow.alive:
                    # Arrow expired or went off-screen: play miss sound if enabled
                    if state.get('sound_enabled', True) and miss_sound:
                        try:
                            miss_sound.play()
                        except Exception:
                            print("Warning: failed to play miss sound")
                    try:
                        state['arrows'].remove(arrow)
                    except ValueError:
                        pass
 
            # Update targets
            for target in state['targets'][:]:
                target.update()
                # If target moved off left side (alive flag set to False), reduce lives
                if not target.alive:
                    try:
                        state['targets'].remove(target)
                    except ValueError:
                        pass
                    # Deduct life only if it reached left edge (x < -80)
                    if target.x < -70:
                        state['lives'] -= 1
                        if state['lives'] <= 0:
                            state['game_over'] = True
 
            # Check collisions
            handle_collisions(state)
 
            # Check for level up after score changes
            def check_level_up(s):
                """Handle leveling: increase level every LEVEL_SCORE points up to LEVEL_MAX.
 
                When leveling up:
                - update the state's level
                - record the level up time for on-screen message
                - update the spawn timer
                - increase speed of existing targets proportionally
                """
                current = s.get('level', 1)
                new_level = min(LEVEL_MAX, s['score'] // LEVEL_SCORE + 1)
                if new_level > current:
                    old_index = max(0, min(current, LEVEL_MAX) - 1)
                    new_index = max(0, min(new_level, LEVEL_MAX) - 1)
                    old_mult = LEVEL_SPEED_MULTIPLIERS[old_index]
                    new_mult = LEVEL_SPEED_MULTIPLIERS[new_index]
                    # Update level and timestamp
                    s['level'] = new_level
                    s['level_up_time'] = pygame.time.get_ticks()
                    # Reset per-level kill counter when level increases
                    s['level_kills'] = 0
                    # Update spawn timer to the new level's spawn interval
                    pygame.time.set_timer(SPAWN_EVENT, LEVEL_SPAWN_INTERVALS[new_index])
                    # Update wind timer and strength interval for the new level
                    pygame.time.set_timer(WIND_EVENT, get_wind_interval(new_level))
                    # Speed up existing targets proportionally so the change feels immediate
                    if old_mult > 0:
                        ratio = new_mult / old_mult
                        for t in s['targets']:
                            t.speed *= ratio
            check_level_up(state)
        else:
            # If paused or game over during a charge, stop charging and preserve current power
            if state['paused'] and state['charging']:
                state['charging'] = False

        # Drawing section
        draw_background(screen)

        # Draw bow
        draw_bow(screen, BOW_X, state['bow_y'], state['power'], state['charging'])

        # Draw arrows
        for arrow in state['arrows']:
            arrow.draw(screen)

        # Draw targets
        for target in state['targets']:
            target.draw(screen)

        # Update and draw particles (simple particle effect for hits)
        for p in state['particles'][:]:
            p.update()
            # Remove expired particles
            if pygame.time.get_ticks() - p.birth > p.lifetime:
                try:
                    state['particles'].remove(p)
                except ValueError:
                    pass
                continue
            p.draw(screen)

        # Draw UI (score, lives, level, kills, sound state, wind)
        draw_ui(screen, state['score'], state['lives'], state.get('level', 1), state.get('level_kills', 0), state.get('sound_enabled', True), WIND)

        # On-screen instructions for player controls
        if state.get('touch_mode', False):
            instr_main = "Tap and hold to charge, Release to shoot"
        else:
            instr_main = "Click and hold to charge, Release to shoot"
        instr_pause = "Press P to pause/resume"
        instr_text = FONT.render(f"{instr_main}   |   {instr_pause}", True, BLACK)
        instr_rect = instr_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
        # Semi-transparent background for readability
        instr_bg = pygame.Surface((instr_rect.width + 12, instr_rect.height + 8), pygame.SRCALPHA)
        instr_bg.fill((255, 255, 255, 200))
        screen.blit(instr_bg, (instr_rect.left - 6, instr_rect.top - 4))
        screen.blit(instr_text, instr_rect)
 
        if state.get('paused', False):
            draw_pause_overlay(screen)
 
        # Show "LEVEL UP!" message for a short duration when level increases
        if state.get('level_up_time', 0):
            elapsed = pygame.time.get_ticks() - state['level_up_time']
            if elapsed < LEVEL_UP_DISPLAY_MS:
                lvl_text = BIG_FONT.render("LEVEL UP!", True, (255, 255, 120))
                lvl_rect = lvl_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120))
                # Slight drop shadow for readability
                shadow = BIG_FONT.render("LEVEL UP!", True, (40, 40, 40))
                screen.blit(shadow, (lvl_rect.x + 4, lvl_rect.y + 4))
                screen.blit(lvl_text, lvl_rect)
            else:
                # Clear level up timer after display duration
                state['level_up_time'] = 0

        # If game over, show overlay
        if state['game_over']:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            go_text = BIG_FONT.render("GAME OVER", True, (255, 220, 220))
            go_rect = go_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
            screen.blit(go_text, go_rect)
            score_text = FONT.render(f"Final Score: {state['score']}", True, WHITE)
            screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))
            restart_text = FONT.render("Press R to restart or ESC to quit", True, WHITE)
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 56))

        # Scale the game surface to the current window size while preserving aspect ratio
        window.fill(BLACK)
        scale = min(window_width / SCREEN_WIDTH, window_height / SCREEN_HEIGHT)
        scaled_width = max(1, int(SCREEN_WIDTH * scale))
        scaled_height = max(1, int(SCREEN_HEIGHT * scale))
        scaled_surface = pygame.transform.smoothscale(screen, (scaled_width, scaled_height))
        offset_x = (window_width - scaled_width) // 2
        offset_y = (window_height - scaled_height) // 2
        window.blit(scaled_surface, (offset_x, offset_y))
        pygame.display.flip()

    # Clean up
    try:
        pygame.mixer.quit()
    except Exception:
        pass
    pygame.quit()
    sys.exit()


# -----------------------------
# Entry point
# -----------------------------
if __name__ == '__main__':
    main_loop()
