import pygame
import random
import math
import os
import asyncio
import streamlit as st
import subprocess
import os

st.title("🎯 Accuracy Turret Game")
st.write("Click the button below to start the game window.")

if st.button("Start Game"):
    # Ye command game ko server par run karegi
    # Note: Streamlit Cloud par graphics window khulna mushkil hota hai
    os.system("python main.py")

# --- 1. INITIALIZATION ---
# Web compatibility ke liye display mode pehle set karna zaroori hai
pygame.init()
WIDTH, HEIGHT = 450, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🎯 ACCURACY TURRET 🎯")

pygame.mixer.init()
pygame.mixer.set_num_channels(64)
clock = pygame.time.Clock()

# --- 2. ASSETS LOADING ---
def load_sound(file):
    if os.path.exists(file):
        try:
            s = pygame.mixer.Sound(file)
            s.set_volume(0.2)
            return s
        except: return None
    return None

s_shoot = load_sound("shoot.wav")
s_hit = load_sound("hit.wav")
s_blast = load_sound("explosion.wav")

def load_gun():
    if os.path.exists("gun.png"):
        try:
            raw = pygame.image.load("gun.png").convert_alpha()
            fixed = pygame.transform.rotate(raw, 90)
            return pygame.transform.scale(fixed, (110, 150))
        except: return None
    return None

gun_base_img = load_gun()

# Fonts (System fonts web par fast load hote hain)
font_main = pygame.font.SysFont("monospace", 30, bold=True)
font_gui = pygame.font.SysFont("sans-serif", 20, bold=True)

WORD_POOL = ["HARDCORE", "CHAOS", "DANGER", "CYBER", "SYSTEM", "VELOCITY", "PYTHON", "UPSC", "ZOOLOGY"]
WORD_INDEX = 0

# --- 3. CLASSES ---
class Laser:
    def __init__(self, start, target_enemy, char_idx):
        self.x, self.y = start
        self.target = target_enemy
        self.char_idx = char_idx
        self.color = target_enemy.color
        self.speed = 40
        self.reached = False
        self.vx, self.vy = 0, 0

    def update(self):
        tx = self.target.x + (self.char_idx * 24)
        ty = self.target.y
        angle = math.atan2(ty - self.y, tx - self.x)
        self.vx, self.vy = math.cos(angle) * self.speed, math.sin(angle) * self.speed
        self.x += self.vx
        self.y += self.vy
        if math.dist((self.x, self.y), (tx, ty)) < 30:
            self.reached = True

    def draw(self, surf):
        pygame.draw.line(surf, self.color, (self.x, self.y), (self.x - self.vx*0.4, self.y - self.vy*0.4), 6)

class Enemy:
    def __init__(self, word, level):
        self.text = word
        self.base_x = random.randint(50, WIDTH - 180)
        self.x, self.y = self.base_x, -50
        self.speed = 1.5 + (level * 0.2)
        self.move_type = random.choice(["straight", "zigzag", "sine"])
        self.color = random.choice([(0,255,255), (255,0,255), (255,255,0)])
        self.shot_idx, self.blasted = 0, []

    def update(self):
        self.y += self.speed
        t = pygame.time.get_ticks() * 0.005
        if self.move_type == "sine":
            self.x = self.base_x + math.sin(t * 8) * 50
        elif self.move_type == "zigzag":
            self.x = self.base_x + (math.sin(t * 6) > 0) * 60 - 30

# --- 4. ASYNC MAIN LOOP ---
async def main():
    global WORD_INDEX
    enemies, lasers = [], []
    score, words_destroyed, level = 0, 0, 1
    shake, recoil, flash_timer = 0, 0, 0
    spawn_t, shoot_t = 0, 0
    target = None
    ship_pos = (WIDTH // 2, HEIGHT - 100)
    current_angle = 0

    running = True
    while running:
        now = pygame.time.get_ticks()
        screen.fill((10, 10, 25)) # Thoda light background readability ke liye

        # Feedback effects
        if shake > 0: shake -= 1
        if recoil > 0: recoil -= 6
        if flash_timer > 0: flash_timer -= 1
        off_x = random.randint(-shake, shake) if shake > 0 else 0
        off_y = random.randint(-shake, shake) if shake > 0 else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Web par touch support ke liye
            if event.type == pygame.MOUSEBUTTONDOWN and not target:
                pass 

        # Enemy Spawner
        if len(enemies) < 4 and now > spawn_t:
            enemies.append(Enemy(WORD_POOL[WORD_INDEX], level))
            WORD_INDEX = (WORD_INDEX + 1) % len(WORD_POOL)
            spawn_t = now + 2000

        # Auto-Targeting
        if not target or target not in enemies:
            ready = [e for e in enemies if e.y > 100]
            if ready: target = min(ready, key=lambda e: (HEIGHT - e.y))
        
        if target and target.y > HEIGHT - 50:
            target = None

        # Combat Logic
        if target:
            tx_c = target.x + (target.shot_idx * 24)
            dx, dy = tx_c - ship_pos[0], target.y - ship_pos[1]
            target_angle = math.degrees(math.atan2(-dy, dx)) - 90
            current_angle += (target_angle - current_angle) * 0.4 

            if now > shoot_t and target.shot_idx < len(target.text):
                rad = math.radians(-current_angle - 90)
                mx, my = ship_pos[0] + math.cos(rad)*80, ship_pos[1] + math.sin(rad)*80
                lasers.append(Laser((mx, my), target, target.shot_idx))
                target.shot_idx += 1
                shoot_t = now + 200 
                recoil, flash_timer = 12, 3
                if s_shoot: s_shoot.play()

        # Update Entities
        for l in lasers[:]:
            l.update()
            if l.reached:
                if l.target in enemies and l.char_idx not in l.target.blasted:
                    l.target.blasted.append(l.char_idx)
                    score += 10
                    if s_hit: s_hit.play()
                lasers.remove(l)
                shake = 5

        for e in enemies[:]:
            e.update()
            if len(e.blasted) >= len(e.text):
                if s_blast: s_blast.play()
                enemies.remove(e)
                words_destroyed += 1
                shake = 15
                if words_destroyed % 10 == 0: level += 1
            elif e.y > HEIGHT:
                enemies.remove(e)
                shake = 30

        # Rendering
        if gun_base_img:
            rotated_gun = pygame.transform.rotate(gun_base_img, current_angle)
            r_rad = math.radians(-current_angle - 90)
            rx, ry = math.cos(r_rad)*-recoil, math.sin(r_rad)*-recoil
            rect = rotated_gun.get_rect(center=(ship_pos[0]+rx+off_x, ship_pos[1]+ry+off_y))
            screen.blit(rotated_gun, rect)
        else:
            pygame.draw.circle(screen, (100, 100, 100), ship_pos, 40)

        for e in enemies:
            for i, char in enumerate(e.text):
                if i not in e.blasted:
                    color = (255, 255, 255) if target == e else e.color
                    screen.blit(font_main.render(char, True, color), (e.x + i*24, e.y))

        for l in lasers: l.draw(screen)

        # UI
        ui_txt = font_gui.render(f"SCORE: {score}  LVL: {level}", True, (200, 200, 200))
        screen.blit(ui_txt, (20, 20))

        pygame.display.flip()
        await asyncio.sleep(0) # IMPORTANT: Browser ko control dene ke liye
        clock.tick(60)

# Game start
asyncio.run(main())
