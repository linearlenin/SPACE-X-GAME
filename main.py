#!/usr/bin/env python3
"""Space X shooter with arcade progression, fullscreen web support and touch controls."""

import asyncio
import json
import math
import os
import random
import sys
from pathlib import Path

import pygame
import pygame.gfxdraw

pygame.init()
pygame.mixer.init()
pygame.font.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("SPACE X")
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("Consolas", 22, bold=True)
BIG_FONT = pygame.font.SysFont("Impact", 64)
LEVEL_FONT = pygame.font.SysFont("Impact", 80)
HUD_FONT = pygame.font.SysFont("Verdana", 30, bold=True)
TITLE_FONT = pygame.font.SysFont("Impact", 120)

SAVE_PATH = Path(__file__).with_name("space_x_game_save.json")


def load_sound(filename):
    path = os.path.join("audio", filename)
    if os.path.exists(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception as exc:  # pragma: no cover - runtime-only audio error
            print(f"Error loading sound {path}: {exc}")
    return None


SOUND_SHOOT = load_sound("shoot.wav")
SOUND_HIT = load_sound("hit.wav")
SOUND_MISS = load_sound("miss.wav")


def play_sound(snd):
    if snd and pygame.mixer.get_init() is not None:
        try:
            snd.play()
        except Exception:  # pragma: no cover - browser environment can ignore this
            pass


def unlock_audio():
    if pygame.mixer.get_init() is None:
        return
    try:
        if SOUND_SHOOT:
            SOUND_SHOOT.play()
            SOUND_SHOOT.stop()
    except Exception:  # pragma: no cover
        pass


def load_high_score():
    if not SAVE_PATH.exists():
        return 0
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return int(data.get("high_score", 0))
        return int(data)
    except Exception:
        return 0


def save_high_score(value):
    try:
        SAVE_PATH.write_text(json.dumps({"high_score": int(value)}), encoding="utf-8")
    except Exception:  # pragma: no cover - filesystem may be read-only in some envs
        pass


class ParallaxSpace:
    def __init__(self):
        self.stars = []
        for _ in range(180):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            speed = random.uniform(0.6, 4.2)
            size = max(1, int(speed * 0.9))
            alpha = min(255, int(speed * 70))
            self.stars.append([x, y, speed, size, alpha])

    def update(self, frame_scale=1.0):
        for star in self.stars:
            star[0] -= star[2] * frame_scale
            if star[0] < 0:
                star[0] = SCREEN_WIDTH
                star[1] = random.randint(0, SCREEN_HEIGHT)

    def draw(self, surface):
        surface.fill((6, 8, 22))
        for x, y, speed, size, alpha in self.stars:
            col = (200, 230, 255)
            pygame.gfxdraw.filled_circle(surface, int(x), int(y), size, (*col, alpha))


class GlowParticle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(3, 11)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life = random.randint(18, 40)
        self.age = 0
        self.radius = random.randint(4, 9)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.age += 1

    def draw(self, surface):
        if self.age < self.life:
            alpha = max(0, int(255 * (1.0 - self.age / self.life)))
            radius = max(1, int(self.radius * (1.0 - self.age / self.life)))
            particle_surface = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.gfxdraw.filled_circle(particle_surface, radius * 2, radius * 2, radius, (*self.color, alpha))
            pygame.gfxdraw.filled_circle(particle_surface, radius * 2, radius * 2, max(1, radius // 2), (255, 255, 255, alpha))
            surface.blit(particle_surface, (int(self.x - radius * 2), int(self.y - radius * 2)), special_flags=pygame.BLEND_ADD)


class LaserArrow:
    def __init__(self, x, y, speed, double_shot=False):
        self.x = float(x)
        self.y = float(y)
        self.speed = float(speed)
        self.alive = True
        self.double_shot = double_shot

    def update(self, frame_scale=1.0):
        self.x += self.speed * frame_scale
        if self.x > SCREEN_WIDTH + 100:
            self.alive = False

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        pygame.gfxdraw.filled_circle(surface, cx, cy, 7, (50, 255, 220))
        pygame.gfxdraw.filled_circle(surface, cx, cy, 12, (0, 255, 220, 90))
        pygame.draw.line(surface, (0, 255, 220), (cx, cy), (cx - 32, cy), 5)
        pygame.draw.line(surface, (255, 255, 255), (cx, cy), (cx - 32, cy), 2)

    def get_rect(self):
        return pygame.Rect(int(self.x - 24), int(self.y - 8), 38, 16)


class PowerUp:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.speed = 2.3
        self.alive = True
        self.width = 20
        self.height = 20

    def update(self, frame_scale=1.0):
        self.x -= self.speed * frame_scale
        if self.x < -40:
            self.alive = False

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        color = {"double": (255, 190, 70), "shield": (90, 190, 255), "+life": (255, 100, 125)}.get(self.kind, (255, 255, 255))
        pygame.draw.rect(surface, color, (cx - 18, cy - 10, 36, 20), border_radius=8)
        pygame.draw.rect(surface, (25, 25, 25), (cx - 12, cy - 4, 24, 8), border_radius=4)
        label = {"double": "2x", "shield": "S", "+life": "+1"}.get(self.kind, "?")
        text = FONT.render(label, True, (10, 10, 20))
        surface.blit(text, (cx - text.get_width() // 2, cy - text.get_height() // 2 + 1))

    def get_rect(self):
        return pygame.Rect(int(self.x - 18), int(self.y - 10), 36, 20)


class AlienTarget:
    def __init__(self, level):
        self.x = SCREEN_WIDTH + 60
        self.y = random.randint(80, SCREEN_HEIGHT - 120)
        self.phase = random.random() * math.tau
        self.kind = "standard"
        self.alive = True

        if level >= 5 and random.random() < 0.10:
            self.kind = "boss"
            self.radius = 68
            self.color = (255, 90, 140)
            self.score_val = 200
            self.speed = 1.5 + level * 0.12
            self.health = 4
        else:
            roll = random.random()
            if level >= 4 and roll < 0.22:
                self.kind = "zigzag"
                self.radius = 22
                self.color = (50, 180, 255)
                self.score_val = 25
                self.speed = 2.6 + level * 0.2
            elif level >= 3 and roll < 0.42:
                self.kind = "fast"
                self.radius = 16
                self.color = (255, 120, 70)
                self.score_val = 15
                self.speed = 3.2 + level * 0.2
            else:
                self.kind = "heavy"
                self.radius = 30
                self.color = (255, 210, 0)
                self.score_val = 30
                self.speed = 2.0 + level * 0.18

        if self.kind == "boss":
            self.width = 150
            self.height = 80
        else:
            self.width = self.radius * 2
            self.height = self.radius * 2

    def update(self, frame_scale=1.0):
        self.x -= self.speed * frame_scale
        if self.kind in {"zigzag", "boss"}:
            self.y += math.sin((self.x / 30.0) + self.phase) * 1.2 * frame_scale
        if self.x < -150:
            self.alive = False

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        if self.kind == "boss":
            glow = pygame.Surface((180, 120), pygame.SRCALPHA)
            pygame.gfxdraw.filled_circle(glow, 90, 60, 60, (*self.color, 60))
            surface.blit(glow, (cx - 90, cy - 60), special_flags=pygame.BLEND_ADD)
            body = pygame.Rect(cx - 70, cy - 38, 140, 76)
            pygame.draw.ellipse(surface, self.color, body)
            pygame.draw.ellipse(surface, (255, 255, 255), body, 3)
            eye_y = cy - 5
            pygame.draw.circle(surface, (0, 0, 0), (cx - 28, eye_y), 7)
            pygame.draw.circle(surface, (0, 0, 0), (cx + 28, eye_y), 7)
            pygame.draw.line(surface, (255, 255, 255), (cx - 18, cy + 18), (cx + 18, cy + 18), 4)
            return

        base = pygame.Surface((self.radius * 3, self.radius * 3), pygame.SRCALPHA)
        pygame.gfxdraw.filled_circle(base, self.radius * 3 // 2, self.radius * 3 // 2, self.radius, (*self.color, 80))
        surface.blit(base, (cx - self.radius * 3 // 2, cy - self.radius * 3 // 2), special_flags=pygame.BLEND_ADD)

        if self.kind == "standard":
            pts = [(cx - self.radius, cy), (cx + self.radius, cy - self.radius * 0.7), (cx + self.radius * 0.7, cy), (cx + self.radius, cy + self.radius * 0.7)]
            pygame.draw.polygon(surface, self.color, pts)
            pygame.gfxdraw.filled_circle(surface, cx - 5, cy, max(4, self.radius // 3), (255, 255, 255))
        elif self.kind == "zigzag":
            pygame.gfxdraw.filled_ellipse(surface, cx, cy, self.radius + 8, self.radius - 4, self.color)
            blink = cx + int(math.sin((self.x + self.phase) / 14.0) * 18)
            pygame.gfxdraw.filled_circle(surface, blink, cy + 4, 4, (255, 0, 0))
        elif self.kind == "fast":
            pygame.gfxdraw.filled_ellipse(surface, cx, cy, self.radius + 10, self.radius - 2, self.color)
            pygame.draw.line(surface, (255, 255, 255), (cx - self.radius, cy), (cx + self.radius, cy), 3)
        else:
            pygame.gfxdraw.filled_ellipse(surface, cx, cy, self.radius + 10, self.radius - 4, self.color)
            pygame.gfxdraw.filled_circle(surface, cx - 8, cy, 8, (0, 255, 220))

    def get_rect(self):
        return pygame.Rect(int(self.x - self.width / 2), int(self.y - self.height / 2), self.width, self.height)


class ControlsHUD:
    def __init__(self):
        self.btn_up = pygame.Rect(44, SCREEN_HEIGHT - 226, 88, 88)
        self.btn_down = pygame.Rect(44, SCREEN_HEIGHT - 120, 88, 88)
        self.btn_fire = pygame.Rect(SCREEN_WIDTH - 156, SCREEN_HEIGHT - 160, 120, 120)
        self.btn_pause = pygame.Rect(SCREEN_WIDTH - 90, 24, 56, 56)

    def draw(self, surface, charging, paused):
        hud_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        pygame.gfxdraw.filled_circle(hud_surface, self.btn_up.centerx, self.btn_up.centery, 40, (255, 255, 255, 40))
        pygame.gfxdraw.aacircle(hud_surface, self.btn_up.centerx, self.btn_up.centery, 40, (255, 255, 255, 120))
        pygame.draw.polygon(hud_surface, (255, 255, 255, 200), [(82, SCREEN_HEIGHT - 203), (56, SCREEN_HEIGHT - 160), (108, SCREEN_HEIGHT - 160)])

        pygame.gfxdraw.filled_circle(hud_surface, self.btn_down.centerx, self.btn_down.centery, 40, (255, 255, 255, 40))
        pygame.gfxdraw.aacircle(hud_surface, self.btn_down.centerx, self.btn_down.centery, 40, (255, 255, 255, 120))
        pygame.draw.polygon(hud_surface, (255, 255, 255, 200), [(82, SCREEN_HEIGHT - 62), (56, SCREEN_HEIGHT - 100), (108, SCREEN_HEIGHT - 100)])

        fire_color = (255, 60, 80, 200) if charging else (255, 255, 255, 60)
        pygame.gfxdraw.filled_circle(hud_surface, self.btn_fire.centerx, self.btn_fire.centery, 55, fire_color)
        pygame.gfxdraw.aacircle(hud_surface, self.btn_fire.centerx, self.btn_fire.centery, 55, (255, 80, 80, 240))
        fire_label = FONT.render("FIRE", True, (255, 255, 255))
        hud_surface.blit(fire_label, (self.btn_fire.centerx - fire_label.get_width() // 2, self.btn_fire.centery - fire_label.get_height() // 2))

        pygame.draw.rect(hud_surface, (25, 25, 35, 180), self.btn_pause, border_radius=14)
        if paused:
            pygame.draw.polygon(hud_surface, (255, 255, 255, 220), [(SCREEN_WIDTH - 72, 40), (SCREEN_WIDTH - 72, 66), (SCREEN_WIDTH - 52, 53)])
        else:
            pygame.draw.rect(hud_surface, (255, 255, 255, 220), (SCREEN_WIDTH - 75, 39, 7, 27), border_radius=3)
            pygame.draw.rect(hud_surface, (255, 255, 255, 220), (SCREEN_WIDTH - 58, 39, 7, 27), border_radius=3)

        surface.blit(hud_surface, (0, 0))


def draw_ship(surface, ship_y, invincible_timer):
    flicker = invincible_timer > 0 and (pygame.time.get_ticks() // 80) % 2 == 0
    if flicker:
        return

    ship_pts = [(125, int(ship_y)), (80, int(ship_y) - 22), (90, int(ship_y)), (80, int(ship_y) + 22)]
    pygame.draw.polygon(surface, (0, 220, 255), ship_pts)
    pygame.draw.polygon(surface, (255, 255, 255), ship_pts, 2)
    pygame.gfxdraw.filled_ellipse(surface, 95, int(ship_y), 12, 6, (255, 255, 255))


def draw_charge_bar(surface, ship_y, power):
    fill = int((min(power, 20.0) / 20.0) * 120)
    bar_rect = pygame.Rect(60, int(ship_y) - 45, 120, 8)
    pygame.draw.rect(surface, (40, 40, 40), bar_rect, border_radius=4)
    pygame.draw.rect(surface, (0, 255, 180), (bar_rect.x, bar_rect.y, fill, bar_rect.height), border_radius=4)


def draw_hud(surface, score, lives, level, high_score, state, shield_timer, double_timer, power, ship_y):
    score_text = HUD_FONT.render(f"SCORE {score}", True, (255, 255, 255))
    high_score_text = HUD_FONT.render(f"BEST {high_score}", True, (125, 214, 255))
    lives_text = HUD_FONT.render("".join("♥" for _ in range(max(0, min(5, lives)))), True, (255, 95, 95))
    level_text = HUD_FONT.render(f"LEVEL {level}", True, (0, 255, 180))

    surface.blit(score_text, (20, 18))
    surface.blit(high_score_text, (SCREEN_WIDTH - 200, 18))
    surface.blit(lives_text, (20, 50))
    surface.blit(level_text, (SCREEN_WIDTH // 2 - level_text.get_width() // 2, 18))

    if shield_timer > 0:
        shield_box = FONT.render("SHIELD", True, (120, 220, 255))
        surface.blit(shield_box, (SCREEN_WIDTH - 160, 58))
    if double_timer > 0:
        double_box = FONT.render("2X FIRE", True, (255, 210, 115))
        surface.blit(double_box, (SCREEN_WIDTH - 160, 82))
    if state == "playing":
        draw_charge_bar(surface, ship_y, power)


def draw_menu(surface, title_alpha):
    surface.fill((6, 8, 22))
    title = TITLE_FONT.render("SPACE X", True, (32, 220, 255))
    title_shadow = TITLE_FONT.render("SPACE X", True, (0, 0, 0))
    title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120))
    surface.blit(title_shadow, (title_rect.x + 6, title_rect.y + 6))
    surface.blit(title, title_rect)

    subtitle = HUD_FONT.render("PRESS SPACE OR TAP TO START", True, (255, 255, 255))
    surface.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, SCREEN_HEIGHT // 2 + 40))

    bar_bg = pygame.Rect(SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT // 2 + 100, 440, 18)
    pygame.draw.rect(surface, (35, 35, 40), bar_bg, border_radius=9)
    progress = min(1.0, (title_alpha % 180) / 180.0)
    pygame.draw.rect(surface, (0, 255, 170), (bar_bg.x, bar_bg.y, int(bar_bg.width * progress), bar_bg.height), border_radius=9)


async def main():
    space_bg = ParallaxSpace()
    controls_hud = ControlsHUD()
    high_score = load_high_score()
    game_state = "menu"
    title_alpha = 0

    ship_y = SCREEN_HEIGHT // 2
    lives = 5
    score = 0
    level = 1
    arrows = []
    targets = []
    particles = []
    powerups = []
    power = 0.0
    charging = False
    spawn_timer = 0.0
    level_up_display = 0
    shake_timer = 0
    fire_repeat = 0.0
    invincible_timer = 0.0
    shield_timer = 0.0
    double_timer = 0.0
    move_up = False
    move_down = False
    fire_held = False
    active_touches = {}
    touch_directions = {}
    fire_pointer = None
    mouse_drag = False
    mouse_move_direction = 0

    def reset_game():
        nonlocal ship_y, lives, score, level, arrows, targets, particles, powerups, power, charging, spawn_timer, level_up_display, shake_timer, fire_repeat, invincible_timer, shield_timer, double_timer, move_up, move_down, fire_held, fire_pointer, mouse_drag, mouse_move_direction
        ship_y = SCREEN_HEIGHT // 2
        lives = 5
        score = 0
        level = 1
        arrows = []
        targets = []
        particles = []
        powerups = []
        power = 0.0
        charging = False
        spawn_timer = 0.0
        level_up_display = 0
        shake_timer = 0
        fire_repeat = 0.0
        invincible_timer = 0.0
        shield_timer = 0.0
        double_timer = 0.0
        move_up = False
        move_down = False
        fire_held = False
        fire_pointer = None
        mouse_drag = False
        mouse_move_direction = 0
        active_touches.clear()
        touch_directions.clear()

    def pointer_position(event):
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            window_width, window_height = pygame.display.get_window_size()
            scale = min(window_width / SCREEN_WIDTH, window_height / SCREEN_HEIGHT)
            canvas_width = SCREEN_WIDTH * scale
            canvas_height = SCREEN_HEIGHT * scale
            offset_x = (window_width - canvas_width) / 2
            offset_y = (window_height - canvas_height) / 2
            return (
                int((event.x * window_width - offset_x) / scale),
                int((event.y * window_height - offset_y) / scale),
            )
        return event.pos

    def fire_charged_shot():
        nonlocal power, charging, fire_held, fire_pointer
        if charging:
            shot_speed = max(18.0, min(36.0, 18.0 + (power * 0.8)))
            arrows.append(LaserArrow(125, ship_y, shot_speed))
            play_sound(SOUND_SHOOT)
            power = 0.0
        charging = False
        fire_held = False
        fire_pointer = None

    while True:
        dt = clock.tick(FPS)
        title_alpha += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == "playing":
                        game_state = "paused"
                    else:
                        pygame.quit()
                        sys.exit()
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    unlock_audio()
                    if game_state == "menu":
                        game_state = "playing"
                        reset_game()
                    elif game_state == "game_over":
                        reset_game()
                        game_state = "playing"
                    elif game_state == "paused":
                        game_state = "playing"
                elif event.key == pygame.K_p:
                    if game_state == "playing":
                        game_state = "paused"
                    elif game_state == "paused":
                        game_state = "playing"
                elif game_state == "playing":
                    if event.key in (pygame.K_w, pygame.K_UP):
                        move_up = True
                    if event.key in (pygame.K_s, pygame.K_DOWN):
                        move_down = True
                    if event.key == pygame.K_SPACE:
                        fire_held = True
                        charging = True
                if event.key == pygame.K_r and game_state == "game_over":
                    reset_game()
                    game_state = "playing"

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_w, pygame.K_UP):
                    move_up = False
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    move_down = False
                if event.key == pygame.K_SPACE:
                    fire_held = False
                    if charging and game_state == "playing":
                        shot_speed = max(18.0, min(36.0, 18.0 + (power * 0.8)))
                        arrows.append(LaserArrow(125, ship_y, shot_speed))
                        play_sound(SOUND_SHOOT)
                        power = 0.0
                        charging = False

            if event.type == pygame.FINGERDOWN:
                unlock_audio()
                pos = pointer_position(event)
                active_touches[event.finger_id] = pos
                if game_state == "menu":
                    game_state = "playing"
                    reset_game()
                elif game_state == "game_over":
                    reset_game()
                    game_state = "playing"
                else:
                    if controls_hud.btn_fire.collidepoint(pos):
                        charging = True
                        fire_held = True
                        fire_pointer = event.finger_id
                    elif controls_hud.btn_pause.collidepoint(pos):
                        if game_state == "playing":
                            game_state = "paused"
                        else:
                            game_state = "playing"
                    elif controls_hud.btn_up.collidepoint(pos):
                        touch_directions[event.finger_id] = -1
                    elif controls_hud.btn_down.collidepoint(pos):
                        touch_directions[event.finger_id] = 1
                    elif game_state == "playing":
                        ship_y = max(50, min(SCREEN_HEIGHT - 60, pos[1]))

            if event.type == pygame.FINGERMOTION:
                pos = pointer_position(event)
                if event.finger_id in active_touches:
                    active_touches[event.finger_id] = pos
                    if game_state == "playing" and event.finger_id != fire_pointer and event.finger_id not in touch_directions:
                        ship_y = max(50, min(SCREEN_HEIGHT - 60, pos[1]))

            if event.type == pygame.FINGERUP:
                active_touches.pop(event.finger_id, None)
                touch_directions.pop(event.finger_id, None)
                if event.finger_id == fire_pointer:
                    fire_charged_shot()

            if event.type == pygame.MOUSEBUTTONDOWN and not getattr(event, "touch", False):
                unlock_audio()
                pos = pointer_position(event)
                if game_state == "menu":
                    game_state = "playing"
                    reset_game()
                elif game_state == "game_over":
                    reset_game()
                    game_state = "playing"
                elif controls_hud.btn_fire.collidepoint(pos):
                    charging = True
                    fire_held = True
                    fire_pointer = "mouse"
                elif controls_hud.btn_pause.collidepoint(pos):
                    game_state = "paused" if game_state == "playing" else "playing"
                elif controls_hud.btn_up.collidepoint(pos):
                    mouse_move_direction = -1
                elif controls_hud.btn_down.collidepoint(pos):
                    mouse_move_direction = 1
                elif game_state == "playing":
                    mouse_drag = True
                    ship_y = max(50, min(SCREEN_HEIGHT - 60, pos[1]))

            if event.type == pygame.MOUSEMOTION and mouse_drag and game_state == "playing" and not getattr(event, "touch", False):
                _, pointer_y = pointer_position(event)
                ship_y = max(50, min(SCREEN_HEIGHT - 60, pointer_y))

            if event.type == pygame.MOUSEBUTTONUP and not getattr(event, "touch", False):
                if fire_pointer == "mouse":
                    fire_charged_shot()
                mouse_drag = False
                mouse_move_direction = 0

        space_bg.update(dt / (1000.0 / FPS))

        if game_state == "playing":
            frame_scale = dt / (1000.0 / FPS)
            ship_speed = 480.0
            keys = pygame.key.get_pressed()
            touch_up = any(direction < 0 for direction in touch_directions.values())
            touch_down = any(direction > 0 for direction in touch_directions.values())
            move_delta = int(move_down or touch_down or mouse_move_direction > 0) - int(move_up or touch_up or mouse_move_direction < 0)
            ship_y += move_delta * ship_speed * dt / 1000.0
            ship_y = max(50, min(SCREEN_HEIGHT - 60, ship_y))

            if charging:
                power += 0.75
                if power > 20.0:
                    power = 20.0

            if keys[pygame.K_SPACE]:
                fire_repeat += dt
                if fire_repeat >= 150:
                    shot_speed = 24.0
                    if double_timer > 0:
                        arrows.append(LaserArrow(125, ship_y - 10, shot_speed, double_shot=True))
                        arrows.append(LaserArrow(125, ship_y + 10, shot_speed, double_shot=True))
                    else:
                        arrows.append(LaserArrow(125, ship_y, shot_speed))
                    play_sound(SOUND_SHOOT)
                    fire_repeat = 0.0

            spawn_interval = max(1400, 2600 - level * 100)
            spawn_timer += dt
            if spawn_timer >= spawn_interval:
                targets.append(AlienTarget(level))
                spawn_timer = 0.0

            target_level = max(1, int(score / 500) + 1)
            if target_level > level:
                level = target_level
                level_up_display = 1000

            if level_up_display > 0:
                level_up_display -= dt

            if invincible_timer > 0:
                invincible_timer -= dt
            if shield_timer > 0:
                shield_timer -= dt
            if double_timer > 0:
                double_timer -= dt

            for a in arrows[:]:
                a.update(frame_scale)
                if not a.alive:
                    arrows.remove(a)

            for t in targets[:]:
                t.update(frame_scale)
                if t.x < -80:
                    targets.remove(t)
                    if random.random() < 0.18:
                        powerups.append(PowerUp(t.x, t.y, random.choice(["double", "shield", "+life"])))
                    continue

            for p in particles[:]:
                p.update()
                if p.age >= p.life:
                    particles.remove(p)

            for p in powerups[:]:
                p.update(frame_scale)
                ship_rect = pygame.Rect(80, int(ship_y) - 20, 45, 45)
                if p.get_rect().colliderect(ship_rect):
                    if p.kind == "double":
                        double_timer = 8000
                    elif p.kind == "shield":
                        shield_timer = 8000
                    elif p.kind == "+life":
                        lives = min(9, lives + 1)
                    p.alive = False
                    particles.extend([GlowParticle(p.x, p.y, (255, 255, 255)) for _ in range(20)])
                if not p.alive:
                    powerups.remove(p)

            for t in targets[:]:
                ship_rect = pygame.Rect(80, int(ship_y) - 20, 45, 45)
                if t.get_rect().colliderect(ship_rect):
                    if shield_timer <= 0:
                        if invincible_timer <= 0:
                            lives -= 1
                            invincible_timer = 1000.0
                            shake_timer = 18
                            play_sound(SOUND_HIT)
                            for _ in range(40):
                                particles.append(GlowParticle(t.x, t.y, t.color))
                            if lives <= 0:
                                high_score = max(high_score, score)
                                save_high_score(high_score)
                                game_state = "game_over"
                                charging = False
                                fire_held = False
                                continue
                    if t in targets:
                        targets.remove(t)
                    if random.random() < 0.25:
                        powerups.append(PowerUp(t.x, t.y, random.choice(["double", "shield", "+life"])))

            for a in arrows[:]:
                a_rect = a.get_rect()
                for t in targets[:]:
                    if a_rect.colliderect(t.get_rect()):
                        score += t.score_val
                        if score > high_score:
                            high_score = score
                            save_high_score(high_score)
                        play_sound(SOUND_HIT)
                        shake_timer = 7
                        for _ in range(26):
                            particles.append(GlowParticle(t.x, t.y, t.color))
                        if random.random() < 0.22:
                            powerups.append(PowerUp(t.x, t.y, random.choice(["double", "shield", "+life"])))
                        if a in arrows:
                            arrows.remove(a)
                        if t in targets:
                            targets.remove(t)
                        break

            if not charging and fire_held:
                charging = True

        if game_state == "menu":
            draw_menu(screen, title_alpha)
        else:
            space_bg.draw(screen)
            if game_state == "playing":
                for _ in range(3):
                    tx = 85 - random.randint(10, 22)
                    ty = int(ship_y + random.randint(-6, 6))
                    pygame.gfxdraw.filled_circle(screen, tx, ty, random.randint(3, 7), (0, 220, 255))
                draw_ship(screen, ship_y, invincible_timer)
                if shield_timer > 0:
                    shield_radius = 35
                    pygame.gfxdraw.aacircle(screen, 100, int(ship_y), shield_radius, (120, 220, 255, 200))
            for t in targets:
                t.draw(screen)
            for p in powerups:
                p.draw(screen)
            for a in arrows:
                a.draw(screen)
            for p in particles:
                p.draw(screen)
            if game_state == "playing":
                controls_hud.draw(screen, charging, False)
            elif game_state == "paused":
                controls_hud.draw(screen, False, True)
                pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.rect(pause_overlay, (10, 15, 25, 160), (SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT // 2 - 110, 360, 220), border_radius=24)
                pause_title = BIG_FONT.render("PAUSED", True, (255, 255, 255))
                pause_overlay.blit(pause_title, (SCREEN_WIDTH // 2 - pause_title.get_width() // 2, SCREEN_HEIGHT // 2 - 55))
                pause_hint = FONT.render("PRESS P OR TAP PAUSE TO RESUME", True, (180, 220, 255))
                pause_overlay.blit(pause_hint, (SCREEN_WIDTH // 2 - pause_hint.get_width() // 2, SCREEN_HEIGHT // 2 + 20))
                screen.blit(pause_overlay, (0, 0))
            else:
                controls_hud.draw(screen, False, False)

            if game_state == "playing" and level_up_display > 0:
                level_burst = LEVEL_FONT.render(f"LEVEL {level}", True, (0, 255, 180))
                screen.blit(level_burst, (SCREEN_WIDTH // 2 - level_burst.get_width() // 2, 130))

            draw_hud(screen, score, lives, level, high_score, game_state, shield_timer, double_timer, power, ship_y)

            if game_state == "game_over":
                panel = pygame.Surface((600, 360), pygame.SRCALPHA)
                pygame.draw.rect(panel, (12, 20, 35, 200), (0, 0, 600, 360), border_radius=22)
                pygame.draw.rect(panel, (90, 150, 255, 220), (18, 18, 564, 324), border_radius=18, width=3)
                title = BIG_FONT.render("GAME OVER", True, (255, 120, 120))
                panel.blit(title, (150, 40))
                final = HUD_FONT.render(f"FINAL SCORE: {score}", True, (255, 255, 255))
                best = HUD_FONT.render(f"BEST SCORE: {high_score}", True, (125, 214, 255))
                panel.blit(final, (190, 140))
                panel.blit(best, (210, 180))
                button_rect = pygame.Rect(180, 230, 240, 68)
                pygame.draw.rect(panel, (0, 190, 240), button_rect, border_radius=18)
                button_text = HUD_FONT.render("PLAY AGAIN", True, (255, 255, 255))
                panel.blit(button_text, (button_rect.x + 45, button_rect.y + 18))
                screen.blit(panel, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 180))

        if shake_timer > 0:
            shake_timer -= 1
            render_offset = [random.randint(-6, 6), random.randint(-6, 6)]
        else:
            render_offset = [0, 0]

        window.blit(screen, render_offset)
        pygame.display.flip()
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
