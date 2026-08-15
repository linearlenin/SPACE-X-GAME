#!/usr/bin/env python3
"""
main.py - Space Shooter (Vercel Web + Audio + Mobile Touch Restart Edition)
Compatible with Pygbag / Web Assembly Deployment
"""

import asyncio
import pygame
import pygame.gfxdraw
import sys
import random
import math
import os

# -----------------------------
# Initialization & Audio Setup
# -----------------------------
pygame.init()
pygame.mixer.init()
pygame.font.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("Space Shooter - Audio & Procedural Glow Edition")
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("Consolas", 22, bold=True)
BIG_FONT = pygame.font.SysFont("Impact", 64)
LEVEL_FONT = pygame.font.SysFont("Impact", 80)

# Load Sound Effects safely from 'audio/' folder
def load_sound(filename):
    path = os.path.join("audio", filename)
    if os.path.exists(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print(f"Error loading sound {path}: {e}")
    else:
        print(f"Sound file not found: {path}")
    return None

SOUND_SHOOT = load_sound("shoot.wav")
SOUND_HIT = load_sound("hit.wav")
SOUND_MISS = load_sound("miss.wav")

def play_sound(snd):
    if snd:
        snd.play()

# -----------------------------
# Parallax Starfield Background
# -----------------------------
class ParallaxSpace:
    def __init__(self):
        self.stars = []
        for _ in range(160):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            speed = random.uniform(0.5, 3.5)
            size = max(1, int(speed * 0.9))
            alpha = int(speed * 70)
            self.stars.append([x, y, speed, size, alpha])

    def update(self):
        for star in self.stars:
            star[0] -= star[2]
            if star[0] < 0:
                star[0] = SCREEN_WIDTH
                star[1] = random.randint(0, SCREEN_HEIGHT)

    def draw(self, surface):
        surface.fill((6, 8, 22))  # Deep Space
        for x, y, speed, size, alpha in self.stars:
            col = (200, 230, 255)
            pygame.gfxdraw.filled_circle(surface, int(x), int(y), size, (*col, alpha))

# -----------------------------
# Glow Particles
# -----------------------------
class GlowParticle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(3, 10)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life = random.randint(18, 35)
        self.age = 0
        self.radius = random.randint(4, 9)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.age += 1

    def draw(self, surface):
        if self.age < self.life:
            alpha = max(0, int(255 * (1.0 - self.age / self.life)))
            r = max(1, int(self.radius * (1.0 - self.age / self.life)))
            p_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.gfxdraw.filled_circle(p_surf, r * 2, r * 2, r, (*self.color, alpha))
            pygame.gfxdraw.filled_circle(p_surf, r * 2, r * 2, max(1, r // 2), (255, 255, 255, alpha))
            surface.blit(p_surf, (int(self.x - r * 2), int(self.y - r * 2)), special_flags=pygame.BLEND_ADD)

# -----------------------------
# Lasers & Missiles
# -----------------------------
class LaserArrow:
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x > SCREEN_WIDTH + 60 or self.y < -50 or self.y > SCREEN_HEIGHT + 50:
            self.alive = False

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        angle = math.atan2(self.vy, self.vx)
        length = 32

        glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.gfxdraw.filled_circle(glow_surf, 30, 30, 16, (0, 255, 220, 70))
        pygame.gfxdraw.filled_circle(glow_surf, 30, 30, 7, (255, 255, 255, 200))
        surface.blit(glow_surf, (cx - 30, cy - 30), special_flags=pygame.BLEND_ADD)

        end_x = cx - int(math.cos(angle) * length)
        end_y = cy - int(math.sin(angle) * length)
        pygame.draw.line(surface, (0, 255, 220), (cx, cy), (end_x, end_y), 5)
        pygame.draw.line(surface, (255, 255, 255), (cx, cy), (end_x, end_y), 2)

    def get_rect(self):
        return pygame.Rect(int(self.x - 8), int(self.y - 8), 16, 16)

# -----------------------------
# Enemy Targets
# -----------------------------
class AlienTarget:
    def __init__(self, level):
        self.x = SCREEN_WIDTH + 60
        self.y = random.randint(80, SCREEN_HEIGHT - 120)
        self.type = random.choice([1, 2, 3])
        self.alive = True
        base_speed = random.uniform(3.0, 5.0)
        self.speed = base_speed + (level * 0.7)

        if self.type == 1:
            self.radius = 18
            self.color = (255, 50, 100)
            self.score_val = 10
        elif self.type == 2:
            self.radius = 26
            self.color = (50, 180, 255)
            self.score_val = 20
        else:
            self.radius = 36
            self.color = (255, 210, 0)
            self.score_val = 30

    def update(self):
        self.x -= self.speed
        if self.x < -60:
            self.alive = False

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        t = pygame.time.get_ticks() / 150.0

        glow_surf = pygame.Surface((self.radius * 3, self.radius * 3), pygame.SRCALPHA)
        pygame.gfxdraw.filled_circle(glow_surf, self.radius * 3 // 2, self.radius * 3 // 2, self.radius, (*self.color, 60))
        surface.blit(glow_surf, (cx - self.radius * 3 // 2, cy - self.radius * 3 // 2), special_flags=pygame.BLEND_ADD)

        if self.type == 1:
            pts = [(cx - 18, cy), (cx + 15, cy - 12), (cx + 5, cy), (cx + 15, cy + 12)]
            pygame.draw.polygon(surface, self.color, pts)
            pygame.gfxdraw.filled_circle(surface, cx - 4, cy, 5, (255, 255, 255))
        elif self.type == 2:
            pygame.gfxdraw.filled_ellipse(surface, cx, cy, 26, 13, self.color)
            pygame.gfxdraw.filled_circle(surface, cx, cy - 5, 8, (255, 255, 255))
            pulse_x = cx + int(math.sin(t) * 14)
            pygame.gfxdraw.filled_circle(surface, pulse_x, cy + 4, 3, (255, 0, 0))
        else:
            pygame.gfxdraw.filled_ellipse(surface, cx, cy, 38, 18, (150, 40, 220))
            pts = [(cx - 28, cy - 8), (cx + 25, cy), (cx - 28, cy + 8)]
            pygame.draw.polygon(surface, self.color, pts)
            pygame.gfxdraw.filled_circle(surface, cx - 10, cy, 10, (0, 255, 220))

    def get_rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

# -----------------------------
# On-Screen Touch Controls
# -----------------------------
class ControlsHUD:
    def __init__(self):
        self.btn_up = pygame.Rect(60, SCREEN_HEIGHT - 220, 80, 80)
        self.btn_down = pygame.Rect(60, SCREEN_HEIGHT - 110, 80, 80)
        self.btn_fire = pygame.Rect(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 160, 110, 110)

    def draw(self, surface, charging):
        hud_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.gfxdraw.filled_circle(hud_surf, self.btn_up.centerx, self.btn_up.centery, 38, (255, 255, 255, 40))
        pygame.gfxdraw.aacircle(hud_surf, self.btn_up.centerx, self.btn_up.centery, 38, (255, 255, 255, 120))
        pygame.draw.polygon(hud_surf, (255, 255, 255, 180), [(100, SCREEN_HEIGHT - 210), (80, SCREEN_HEIGHT - 175), (120, SCREEN_HEIGHT - 175)])

        pygame.gfxdraw.filled_circle(hud_surf, self.btn_down.centerx, self.btn_down.centery, 38, (255, 255, 255, 40))
        pygame.gfxdraw.aacircle(hud_surf, self.btn_down.centerx, self.btn_down.centery, 38, (255, 255, 255, 120))
        pygame.draw.polygon(hud_surf, (255, 255, 255, 180), [(100, SCREEN_HEIGHT - 45), (80, SCREEN_HEIGHT - 80), (120, SCREEN_HEIGHT - 80)])

        f_color = (255, 60, 80, 170) if charging else (255, 255, 255, 50)
        pygame.gfxdraw.filled_circle(hud_surf, self.btn_fire.centerx, self.btn_fire.centery, 52, f_color)
        pygame.gfxdraw.aacircle(hud_surf, self.btn_fire.centerx, self.btn_fire.centery, 52, (255, 80, 80, 220))
        
        lbl = FONT.render("FIRE", True, (255, 255, 255))
        hud_surf.blit(lbl, (self.btn_fire.centerx - lbl.get_width() // 2, self.btn_fire.centery - lbl.get_height() // 2))

        surface.blit(hud_surf, (0, 0))

# -----------------------------
# Main Game Function (Async for Web)
# -----------------------------
async def main():
    space_bg = ParallaxSpace()
    controls_hud = ControlsHUD()

    # Reset game state function
    def reset_game():
        nonlocal ship_y, lives, score, level, arrows, targets, particles, power, charging, game_over, spawn_timer, level_up_display, shake_timer
        ship_y = SCREEN_HEIGHT // 2
        lives = 5
        score = 0
        level = 1
        arrows = []
        targets = []
        particles = []
        power = 0.0
        charging = False
        game_over = False
        spawn_timer = 0
        level_up_display = 0
        shake_timer = 0

    ship_y = SCREEN_HEIGHT // 2
    lives = 5
    score = 0
    level = 1
    arrows = []
    targets = []
    particles = []

    power = 0.0
    charging = False
    game_over = False
    
    spawn_timer = 0
    level_up_display = 0
    shake_timer = 0

    while True:
        dt = clock.tick(FPS)

        # -----------------------------
        # 1️⃣ Event Handling Loop
        # -----------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: 
                    pygame.quit()
                    sys.exit()
                
                # Keyboard Restart support
                if game_over:
                    if event.key == pygame.K_r:
                        reset_game()
                else:
                    if event.key == pygame.K_SPACE:
                        arrows.append(LaserArrow(90, ship_y, 20, 0))
                        play_sound(SOUND_SHOOT)

            # Touch and Mouse Click Event logic
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                if game_over:
                    # Touch/Click anywhere on screen to Restart
                    reset_game()
                else:
                    mpos = pygame.mouse.get_pos()
                    if controls_hud.btn_fire.collidepoint(mpos):
                        charging = True

            elif event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                if not game_over and charging:
                    mx, my = pygame.mouse.get_pos()
                    angle = math.atan2(my - ship_y, mx - 90)
                    pwr = max(9.0, min(32.0, power))
                    vx = math.cos(angle) * pwr
                    vy = math.sin(angle) * pwr

                    arrows.append(LaserArrow(90, ship_y, vx, vy))
                    play_sound(SOUND_SHOOT)
                    power = 0.0
                    charging = False

        # -----------------------------
        # Game State Updates (When active)
        # -----------------------------
        space_bg.update()

        if not game_over:
            spawn_timer += dt

            target_level = (score // 100) + 1
            if target_level > level:
                level = target_level
                level_up_display = 90

            if charging:
                power += 0.75

            keys = pygame.key.get_pressed()
            if keys[pygame.K_w] or keys[pygame.K_UP]: ship_y -= 8
            if keys[pygame.K_s] or keys[pygame.K_DOWN]: ship_y += 8

            if pygame.mouse.get_pressed()[0]:
                mpos = pygame.mouse.get_pos()
                if controls_hud.btn_up.collidepoint(mpos): ship_y -= 8
                if controls_hud.btn_down.collidepoint(mpos): ship_y += 8

            ship_y = max(50, min(SCREEN_HEIGHT - 60, ship_y))

            spawn_interval = max(450, 1600 - (level * 220))
            if spawn_timer >= spawn_interval:
                targets.append(AlienTarget(level))
                spawn_timer = 0

            for a in arrows[:]:
                a.update()
                if not a.alive: arrows.remove(a)

            for t in targets[:]:
                t.update()
                if not t.alive:
                    targets.remove(t)
                    play_sound(SOUND_MISS)
                    lives -= 1
                    if lives <= 0: 
                        game_over = True
                        charging = False

            for p in particles[:]:
                p.update()
                if p.age >= p.life: particles.remove(p)

            for a in arrows[:]:
                a_rect = a.get_rect()
                for t in targets[:]:
                    if a_rect.colliderect(t.get_rect()):
                        score += t.score_val
                        shake_timer = 7
                        play_sound(SOUND_HIT)
                        
                        for _ in range(30):
                            particles.append(GlowParticle(t.x, t.y, t.color))

                        if a in arrows: arrows.remove(a)
                        if t in targets: targets.remove(t)
                        break

        # -----------------------------
        # Drawing Logic
        # -----------------------------
        space_bg.draw(screen)

        if not game_over:
            # Thruster & Ship Drawing
            for _ in range(3):
                tx = 80 - random.randint(10, 22)
                ty = ship_y + random.randint(-5, 5)
                pygame.gfxdraw.filled_circle(screen, tx, ty, random.randint(3, 7), (0, 220, 255))

            ship_pts = [(125, int(ship_y)), (75, int(ship_y) - 22), (85, int(ship_y)), (75, int(ship_y) + 22)]
            pygame.draw.polygon(screen, (0, 220, 255), ship_pts)
            pygame.draw.polygon(screen, (255, 255, 255), ship_pts, 2)
            pygame.gfxdraw.filled_ellipse(screen, 95, int(ship_y), 12, 6, (255, 255, 255))

            if charging:
                fill = int((power / 32.0) * 120)
                pygame.draw.rect(screen, (40, 40, 40), (60, ship_y - 45, 120, 8), border_radius=4)
                pygame.draw.rect(screen, (0, 255, 180), (60, ship_y - 45, fill, 8), border_radius=4)

        for t in targets: t.draw(screen)
        for a in arrows: a.draw(screen)
        for p in particles: p.draw(screen)

        if not game_over:
            controls_hud.draw(screen, charging)

        hud_txt = FONT.render(f"SCORE: {score}  |  LIVES: {lives}  |  LEVEL: {level}", True, (255, 255, 255))
        screen.blit(hud_txt, (20, 20))

        if level_up_display > 0 and not game_over:
            level_up_display -= 1
            lvl_lbl = LEVEL_FONT.render(f"LEVEL {level} UP!", True, (0, 255, 180))
            screen.blit(lvl_lbl, (SCREEN_WIDTH // 2 - lvl_lbl.get_width() // 2, 130))

        # -----------------------------
        # 2️⃣ Game Over UI & Touch Restart Button
        # -----------------------------
        if game_over:
            # Game Over Heading
            go_txt = BIG_FONT.render("GAME OVER", True, (255, 60, 60))
            screen.blit(go_txt, (SCREEN_WIDTH // 2 - go_txt.get_width() // 2, SCREEN_HEIGHT // 2 - 90))

            # Touch Restart Button Box
            btn_w, btn_h = 280, 60
            restart_btn = pygame.Rect(SCREEN_WIDTH // 2 - btn_w // 2, SCREEN_HEIGHT // 2, btn_w, btn_h)
            pygame.draw.rect(screen, (0, 190, 240), restart_btn, border_radius=14)
            pygame.draw.rect(screen, (255, 255, 255), restart_btn, 3, border_radius=14)

            # Button Text
            btn_text = FONT.render("TAP TO RESTART", True, (255, 255, 255))
            screen.blit(btn_text, (restart_btn.centerx - btn_text.get_width() // 2, restart_btn.centery - btn_text.get_height() // 2))

            # Keyboard Subtext
            r_txt = FONT.render("( or Press 'R' Key )", True, (170, 170, 170))
            screen.blit(r_txt, (SCREEN_WIDTH // 2 - r_txt.get_width() // 2, SCREEN_HEIGHT // 2 + 75))

        # Screen Shake effect
        render_offset = [0, 0]
        if shake_timer > 0:
            shake_timer -= 1
            render_offset[0] = random.randint(-5, 5)
            render_offset[1] = random.randint(-5, 5)

        window.blit(screen, render_offset)
        pygame.display.flip()

        # Crucial for Web Browser Playability!
        await asyncio.sleep(0)

if __name__ == '__main__':
    asyncio.run(main())