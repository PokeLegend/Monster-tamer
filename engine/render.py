import pygame
import math
import random
from pygame import gfxdraw

# ------------------------------------------------------------
# Constants
PANEL_BG = (28, 28, 38)
PANEL_BORDER = (80, 80, 90)
PANEL_BORDER_LIGHT = (140, 140, 150)

# ------------------------------------------------------------
# Drawing helpers
def draw_panel(screen, rect, bg=PANEL_BG, border=PANEL_BORDER, radius=8):
    """Draw a rounded rectangle panel."""
    pygame.draw.rect(screen, bg, rect, border_radius=radius)
    pygame.draw.rect(screen, border, rect, width=2, border_radius=radius)

def draw_hp_bar(screen, rect, hp, max_hp, color=(80, 200, 80), bg=(40, 40, 50)):
    """Draw a gradient HP bar with smooth transition."""
    ratio = max(0, min(1, hp / max_hp))
    # background
    pygame.draw.rect(screen, bg, rect, border_radius=4)
    # foreground with gradient
    w = max(2, int(rect.width * ratio))
    if w > 0:
        # color from green to red
        r = int(200 * (1 - ratio) + 40)
        g = int(40 * ratio + 200)
        b = 60
        fill_rect = pygame.Rect(rect.x, rect.y, w, rect.height)
        pygame.draw.rect(screen, (r, g, b), fill_rect, border_radius=4)
    # border
    pygame.draw.rect(screen, (80, 80, 90), rect, width=1, border_radius=4)

def draw_text_box(screen, rect, text, font, color=(255,255,255), align='left'):
    """Draw a text box with wrapping and padding."""
    draw_panel(screen, rect)
    lines = []
    words = text.split(' ')
    current = []
    for w in words:
        test = ' '.join(current + [w])
        if font.size(test)[0] < rect.width - 20:
            current.append(w)
        else:
            lines.append(' '.join(current))
            current = [w]
    if current:
        lines.append(' '.join(current))
    y = rect.y + 10
    for line in lines:
        img = font.render(line, True, color)
        if align == 'center':
            x = rect.x + (rect.width - img.get_width()) // 2
        else:
            x = rect.x + 10
        screen.blit(img, (x, y))
        y += font.get_height() + 2

# ------------------------------------------------------------
# Monster sprite with animation
class MonsterSprite:
    def __init__(self, shape, color, size=48):
        self.shape = shape
        self.color = color
        self.size = size
        self.frame = 0
        self.anim_timer = 0
        self.anim_state = 'idle'  # 'idle', 'attack', 'hurt'
        self.attack_progress = 0  # 0..1 for attack lunge
        self.hurt_timer = 0

    def update(self):
        self.anim_timer += 1
        if self.anim_state == 'idle':
            self.frame = (self.anim_timer // 10) % 2  # subtle bob
        elif self.anim_state == 'attack':
            self.attack_progress += 0.05
            if self.attack_progress >= 1:
                self.attack_progress = 1
                self.anim_state = 'idle'
        elif self.anim_state == 'hurt':
            self.hurt_timer -= 1
            if self.hurt_timer <= 0:
                self.anim_state = 'idle'

    def draw(self, screen, x, y, size=None):
        if size is None:
            size = self.size
        # Apply animation offsets
        offset_x = 0
        offset_y = 0
        if self.anim_state == 'idle':
            offset_y = math.sin(self.anim_timer * 0.05) * 2
        elif self.anim_state == 'attack':
            offset_x = -8 * (1 - self.attack_progress)  # lunge forward
        elif self.anim_state == 'hurt':
            if self.hurt_timer % 4 < 2:
                offset_x = 4
            else:
                offset_x = -4

        # Draw the procedural shape
        color = self.color
        if self.anim_state == 'hurt':
            color = (255, 100, 100)

        # Use the original render function
        draw_monster_sprite(screen, self.shape, color, (x + offset_x, y + offset_y), size)

# ------------------------------------------------------------
# Procedural sprite drawing (enhanced)
def draw_monster_sprite(screen, shape, color, pos, size=48):
    """Draw a monster using basic shapes."""
    cx, cy = pos
    color = pygame.Color(color)
    # Scale based on size
    s = size / 48
    # Body
    if shape == 'circle':
        r = int(18 * s)
        pygame.draw.circle(screen, color, (cx, cy), r)
        pygame.draw.circle(screen, (min(255, color.r+40), min(255, color.g+40), min(255, color.b+40)),
                           (cx - int(4*s), cy - int(4*s)), int(r * 0.5))
        # Eyes
        pygame.draw.circle(screen, (255,255,255), (cx - int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (255,255,255), (cx + int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (0,0,0), (cx - int(7*s), cy - int(5*s)), int(2*s))
        pygame.draw.circle(screen, (0,0,0), (cx + int(9*s), cy - int(5*s)), int(2*s))

    elif shape == 'triangle':
        points = [(cx, cy - int(20*s)), (cx - int(20*s), cy + int(15*s)), (cx + int(20*s), cy + int(15*s))]
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, (min(255, color.r+30), min(255, color.g+30), min(255, color.b+30)),
                            [(cx, cy - int(18*s)), (cx - int(16*s), cy + int(12*s)), (cx + int(16*s), cy + int(12*s))])
        # Eyes
        pygame.draw.circle(screen, (255,255,255), (cx - int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (255,255,255), (cx + int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (0,0,0), (cx - int(7*s), cy - int(5*s)), int(2*s))
        pygame.draw.circle(screen, (0,0,0), (cx + int(9*s), cy - int(5*s)), int(2*s))

    elif shape == 'square':
        rect = pygame.Rect(cx - int(18*s), cy - int(18*s), int(36*s), int(36*s))
        pygame.draw.rect(screen, color, rect, border_radius=int(4*s))
        pygame.draw.rect(screen, (min(255, color.r+30), min(255, color.g+30), min(255, color.b+30)),
                         rect.inflate(-int(6*s), -int(6*s)), border_radius=int(2*s))
        # Eyes
        pygame.draw.circle(screen, (255,255,255), (cx - int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (255,255,255), (cx + int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (0,0,0), (cx - int(7*s), cy - int(5*s)), int(2*s))
        pygame.draw.circle(screen, (0,0,0), (cx + int(9*s), cy - int(5*s)), int(2*s))

    else:  # diamond or default
        points = [(cx, cy - int(20*s)), (cx + int(20*s), cy), (cx, cy + int(20*s)), (cx - int(20*s), cy)]
        pygame.draw.polygon(screen, color, points)
        # Eyes
        pygame.draw.circle(screen, (255,255,255), (cx - int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (255,255,255), (cx + int(8*s), cy - int(6*s)), int(4*s))
        pygame.draw.circle(screen, (0,0,0), (cx - int(7*s), cy - int(5*s)), int(2*s))
        pygame.draw.circle(screen, (0,0,0), (cx + int(9*s), cy - int(5*s)), int(2*s))

# ------------------------------------------------------------
# Particle System
class Particle:
    def __init__(self, x, y, color, velocity, size, life):
        self.x = x
        self.y = y
        self.color = color
        self.vx, self.vy = velocity
        self.size = size
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05  # gravity
        self.life -= 1
        self.size *= 0.98

    def draw(self, screen):
        alpha = int(255 * (self.life / self.max_life))
        color = (*self.color, alpha)
        # Use a surface to handle alpha
        surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (self.size, self.size), max(1, int(self.size)))
        screen.blit(surf, (self.x - self.size, self.y - self.size))

class ParticleEmitter:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=30, speed=3, size_range=(2,6), life_range=(20,40)):
        for _ in range(count):
            angle = random.uniform(0, math.pi*2)
            speed_ = random.uniform(1, speed)
            vx = math.cos(angle) * speed_
            vy = math.sin(angle) * speed_
            size = random.randint(*size_range)
            life = random.randint(*life_range)
            self.particles.append(Particle(x, y, color, (vx, vy), size, life))

    def update(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0 or p.size < 0.5:
                self.particles.remove(p)

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)
