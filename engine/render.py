import pygame
import math

WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
PANEL_BG = (30, 30, 40)
PANEL_BORDER = (230, 230, 240)
HP_GREEN = (90, 210, 90)
HP_YELLOW = (230, 200, 60)
HP_RED = (220, 70, 70)


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw_monster_sprite(surface, shape, color_hex, center, size, facing='down', bounce=0):
    """Draws a procedural creature so no external art assets are needed."""
    color = hex_to_rgb(color_hex)
    dark = tuple(max(0, c - 60) for c in color)
    cx, cy = center[0], center[1] - bounce
    r = size

    if shape == 'circle':
        pygame.draw.circle(surface, color, (cx, cy), r)
        pygame.draw.circle(surface, dark, (cx, cy), r, 3)
        pygame.draw.circle(surface, color, (cx - r * 0.7, cy - r * 0.6), int(r * 0.35))
        pygame.draw.circle(surface, color, (cx + r * 0.7, cy - r * 0.6), int(r * 0.35))
    elif shape == 'triangle':
        pts = [(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, dark, pts, 3)
    elif shape == 'square':
        rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        pygame.draw.rect(surface, color, rect, border_radius=6)
        pygame.draw.rect(surface, dark, rect, 3, border_radius=6)
    elif shape == 'diamond':
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, dark, pts, 3)
    elif shape == 'star':
        pts = []
        for i in range(10):
            ang = math.pi / 5 * i - math.pi / 2
            rad = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, dark, pts, 3)

    # simple eyes
    eye_off = r * 0.35
    pygame.draw.circle(surface, BLACK, (cx - eye_off, cy - r * 0.1), max(2, int(r * 0.09)))
    pygame.draw.circle(surface, BLACK, (cx + eye_off, cy - r * 0.1), max(2, int(r * 0.09)))


def draw_panel(surface, rect, bg=PANEL_BG, border=PANEL_BORDER, radius=10):
    pygame.draw.rect(surface, bg, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, 2, border_radius=radius)


def draw_hp_bar(surface, rect, hp, max_hp):
    pct = max(0, hp / max_hp) if max_hp else 0
    pygame.draw.rect(surface, (60, 60, 60), rect, border_radius=4)
    fill = pygame.Rect(rect.x, rect.y, int(rect.width * pct), rect.height)
    color = HP_GREEN if pct > 0.5 else (HP_YELLOW if pct > 0.2 else HP_RED)
    pygame.draw.rect(surface, color, fill, border_radius=4)
    pygame.draw.rect(surface, WHITE, rect, 2, border_radius=4)


def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_text_box(surface, rect, text, font, color=WHITE):
    draw_panel(surface, rect)
    lines = wrap_text(text, font, rect.width - 30)
    y = rect.y + 14
    for line in lines[:3]:
        img = font.render(line, True, color)
        surface.blit(img, (rect.x + 16, y))
        y += font.get_height() + 4
