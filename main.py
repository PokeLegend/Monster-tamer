"""
Monster Tamer - a small monster catching / battling / training game.
Run with: python main.py
"""
import os
import sys
import random
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.monster import Monster, SPECIES, MOVES
from engine.player import Player
from engine.world import World
from engine.battle import Battle
from engine import render, save

WIDTH, HEIGHT = 960, 640
TILE = 36
FPS = 60

STARTERS = ["Emberpup", "Droplet", "Sproutling"]

DIRS = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}
FACE = {(0, -1): 'up', (0, 1): 'down', (-1, 0): 'left', (1, 0): 'right'}


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Monster Tamer")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 20)
        self.font_small = pygame.font.SysFont("segoeui", 16)
        self.font_big = pygame.font.SysFont("segoeui", 32, bold=True)
        pygame.key.set_repeat(180, 120)

        self.state = 'TITLE'
        self.title_index = 0
        self.player = None
        self.world = None
        self.battle = None
        self.battle_menu = 'MAIN'
        self.battle_cursor = 0
        self.battle_log_queue = []
        self.battle_current_msg = ""
        self.post_battle_action = None
        self.starter_cursor = 0
        self.dialog_queue = []
        self.dialog_current = ""
        self.after_dialog = None
        self.pause_cursor = 0
        self.party_cursor = 0
        self.switch_reason = None  # 'fainted' or 'voluntary'
        self.pending_trainer = None
        self.wild_encounter_species = None
        self.message_flash = ""
        self.message_flash_timer = 0

        self.running = True

    # ---------------------------------------------------------- utility
    def push_dialog(self, lines, after=None):
        if isinstance(lines, str):
            lines = [lines]
        self.dialog_queue = lines[1:]
        self.dialog_current = lines[0]
        self.after_dialog = after
        self.state = 'DIALOG'

    def advance_dialog(self):
        if self.dialog_queue:
            self.dialog_current = self.dialog_queue.pop(0)
        else:
            cb = self.after_dialog
            self.after_dialog = None
            self.state = 'OVERWORLD'
            if cb:
                cb()

    def flash(self, text):
        self.message_flash = text
        self.message_flash_timer = 90

    # ---------------------------------------------------------- new game
    def new_game(self):
        self.player = Player("Tamer")
        self.world = World('hometown')
        self.state = 'OVERWORLD'

    def continue_game(self):
        p = save.load_game()
        if p:
            self.player = p
            self.world = World(p.map)
            self.state = 'OVERWORLD'
        else:
            self.flash("No save file found.")

    # ---------------------------------------------------------- overworld
    def try_move(self, dx, dy):
        self.player.facing = FACE[(dx, dy)]
        nx, ny = self.player.pos[0] + dx, self.player.pos[1] + dy
        if self.world.is_blocked(nx, ny):
            return
        self.player.pos = [nx, ny]

        exit_data = self.world.exit_at(nx, ny)
        if exit_data:
            self.world.load(exit_data['map'])
            self.player.map = exit_data['map']
            self.player.pos = list(exit_data['spawn'])
            return

        if self.world.is_grass(nx, ny) and self.player.has_alive():
            enc = self.world.roll_encounter()
            if enc:
                species, level = enc
                self.start_wild_battle(species, level)

    def interact(self):
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.player.facing]
        fx, fy = self.player.pos[0] + dx, self.player.pos[1] + dy
        if self.world.is_lab(fx, fy):
            if not self.player.party:
                self.state = 'STARTER'
                self.starter_cursor = 0
            else:
                self.player.heal_party()
                self.push_dialog(["Welcome back to the Lab!", "Your monsters have been fully healed."])
            return
        trainer_id = self.world.trainer_id_at(fx, fy)
        if trainer_id:
            key = f"{self.world.map_name}:{trainer_id}"
            trainer = self.world.data['trainers'][trainer_id]
            if key in self.player.defeated_trainers:
                self.push_dialog(f"{trainer['name']}: Good luck out there, Tamer!")
            elif not self.player.has_alive():
                self.push_dialog("Your monsters need healing first! Go back to the Lab.")
            else:
                self.pending_trainer = (key, trainer)
                self.push_dialog(f"{trainer['name']} wants to battle!", after=self.begin_trainer_battle)

    def begin_trainer_battle(self):
        key, trainer = self.pending_trainer
        team = [Monster(t['species'], t['level']) for t in trainer['team']]
        first = self.player.first_alive()
        self.battle = Battle(first, team[0], is_wild=False, trainer_name=trainer['name'],
                              player_party=self.player.party, enemy_team=team,
                              reward=trainer.get('reward', 0))
        self.state = 'BATTLE'
        self.battle_menu = 'MAIN'
        self.battle_cursor = 0
        self.battle_log_queue = [f"{trainer['name']} sent out {team[0].nickname}!"]
        self._pop_battle_msg()

    def start_wild_battle(self, species, level):
        wild = Monster(species, level)
        self.player.seen_species.add(species)
        first = self.player.first_alive()
        self.battle = Battle(first, wild, is_wild=True, player_party=self.player.party)
        self.wild_encounter_species = species
        self.state = 'BATTLE'
        self.battle_menu = 'MAIN'
        self.battle_cursor = 0
        self.battle_log_queue = [f"A wild {species} appeared!"]
        self._pop_battle_msg()

    # ---------------------------------------------------------- starters
    def pick_starter(self):
        species = STARTERS[self.starter_cursor]
        mon = Monster(species, 5)
        self.player.add_monster(mon)
        self.player.caught_species.add(species)
        self.state = 'OVERWORLD'
        self.push_dialog([f"You chose {species}!", "Take care of your new partner and explore the world!"])

    # ---------------------------------------------------------- battle
    def _pop_battle_msg(self):
        if self.battle_log_queue:
            self.battle_current_msg = self.battle_log_queue.pop(0)
        else:
            self.battle_current_msg = ""
            self._resolve_post_message()

    def _resolve_post_message(self):
        b = self.battle
        if b.turn_pending_switch:
            self.state = 'BATTLE'
            self.battle_menu = 'FORCE_SWITCH'
            self.party_cursor = 0
            return
        if b.state == 'won':
            if not b.is_wild:
                key, trainer = self.pending_trainer
                self.player.defeated_trainers.add(key)
                self.player.coins += b.reward
            self.end_battle()
        elif b.state == 'lost':
            self.player.coins = max(0, self.player.coins - 20)
            for m in self.player.party:
                m.heal_full()
            self.world.load('hometown')
            self.player.map = 'hometown'
            self.player.pos = [4, 4]
            self.end_battle(msg="You rushed back to the Lab to heal up...")
        elif b.state == 'caught':
            species = b.enemy.species
            self.player.caught_species.add(species)
            self.player.add_monster(b.enemy)
            self.end_battle()
        elif b.state == 'ran':
            self.end_battle()
        else:
            self.battle_menu = 'MAIN'
            self.battle_cursor = 0

    def end_battle(self, msg=None):
        self.battle = None
        self.state = 'OVERWORLD'
        self.battle_menu = 'MAIN'
        if msg:
            self.flash(msg)

    def battle_do_move(self, move_name):
        log = self.battle.use_move(move_name)
        self.battle_log_queue = list(log)
        self.battle_menu = 'MSG'
        self._pop_battle_msg()

    def battle_do_catch(self):
        log = self.battle.attempt_catch(ball_bonus=1.0)
        self.player.orbs -= 1
        self.battle_log_queue = list(log)
        self.battle_menu = 'MSG'
        self._pop_battle_msg()

    def battle_do_run(self):
        log = self.battle.attempt_run()
        self.battle_log_queue = list(log)
        self.battle_menu = 'MSG'
        self._pop_battle_msg()

    def battle_do_switch(self, monster):
        if self.battle_menu == 'FORCE_SWITCH':
            log = self.battle.switch_in(monster)
        else:
            log = self.battle.switch_in(monster)
        self.battle_log_queue = list(log)
        self.battle_menu = 'MSG'
        self._pop_battle_msg()

    # ---------------------------------------------------------- input
    def handle_keydown(self, key):
        if self.state == 'TITLE':
            options = self._title_options()
            if key in (pygame.K_UP, pygame.K_w):
                self.title_index = (self.title_index - 1) % len(options)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.title_index = (self.title_index + 1) % len(options)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = options[self.title_index]
                if choice == 'New Game':
                    self.new_game()
                elif choice == 'Continue':
                    self.continue_game()
                elif choice == 'Quit':
                    self.running = False

        elif self.state == 'STARTER':
            if key in (pygame.K_LEFT, pygame.K_a):
                self.starter_cursor = (self.starter_cursor - 1) % 3
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.starter_cursor = (self.starter_cursor + 1) % 3
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.pick_starter()

        elif self.state == 'DIALOG':
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.advance_dialog()

        elif self.state == 'OVERWORLD':
            if key in DIRS:
                self.try_move(*DIRS[key])
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                self.interact()
            elif key == pygame.K_p:
                self.state = 'PAUSE'
                self.pause_cursor = 0
            elif key == pygame.K_ESCAPE:
                self.state = 'PAUSE'
                self.pause_cursor = 0

        elif self.state == 'PAUSE':
            options = ['Party', 'Save', 'Pokedex', 'Return', 'Quit to Title']
            if key in (pygame.K_UP, pygame.K_w):
                self.pause_cursor = (self.pause_cursor - 1) % len(options)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.pause_cursor = (self.pause_cursor + 1) % len(options)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = options[self.pause_cursor]
                if choice == 'Party':
                    self.state = 'PARTY'
                    self.party_cursor = 0
                elif choice == 'Save':
                    save.save_game(self.player)
                    self.flash("Game saved!")
                    self.state = 'OVERWORLD'
                elif choice == 'Pokedex':
                    n, total = self.player.pokedex_progress()
                    self.flash(f"Pokedex: {n}/{total} species caught")
                    self.state = 'OVERWORLD'
                elif choice == 'Return':
                    self.state = 'OVERWORLD'
                elif choice == 'Quit to Title':
                    self.state = 'TITLE'
            elif key == pygame.K_ESCAPE:
                self.state = 'OVERWORLD'

        elif self.state == 'PARTY':
            if not self.player.party:
                if key == pygame.K_ESCAPE:
                    self.state = 'PAUSE'
                return
            if key in (pygame.K_UP, pygame.K_w):
                self.party_cursor = (self.party_cursor - 1) % len(self.player.party)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.party_cursor = (self.party_cursor + 1) % len(self.player.party)
            elif key == pygame.K_ESCAPE:
                self.state = 'PAUSE'

        elif self.state == 'BATTLE':
            self._battle_keydown(key)

    def _title_options(self):
        opts = ['New Game']
        if save.has_save():
            opts.append('Continue')
        opts.append('Quit')
        return opts

    def _battle_keydown(self, key):
        b = self.battle
        if self.battle_menu == 'MSG':
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._pop_battle_msg()
            return

        if self.battle_menu == 'MAIN':
            options = ['Fight', 'Bag', 'Party', 'Run']
            if key in (pygame.K_LEFT, pygame.K_a):
                self.battle_cursor = (self.battle_cursor - 1) % len(options)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.battle_cursor = (self.battle_cursor + 1) % len(options)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = options[self.battle_cursor]
                if choice == 'Fight':
                    self.battle_menu = 'FIGHT'
                    self.battle_cursor = 0
                elif choice == 'Bag':
                    if not b.is_wild:
                        self.battle_log_queue = ["You can't catch another trainer's monster!"]
                        self.battle_menu = 'MSG'
                        self._pop_battle_msg()
                    elif self.player.orbs <= 0:
                        self.battle_log_queue = ["You don't have any capture orbs left!"]
                        self.battle_menu = 'MSG'
                        self._pop_battle_msg()
                    else:
                        self.battle_do_catch()
                elif choice == 'Party':
                    self.battle_menu = 'SWITCH'
                    self.party_cursor = 0
                elif choice == 'Run':
                    self.battle_do_run()

        elif self.battle_menu == 'FIGHT':
            moves = b.player.moves
            if key in (pygame.K_UP, pygame.K_w):
                self.battle_cursor = (self.battle_cursor - 2) % len(moves)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.battle_cursor = (self.battle_cursor + 2) % len(moves)
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.battle_cursor = (self.battle_cursor - 1) % len(moves)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.battle_cursor = (self.battle_cursor + 1) % len(moves)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.battle_do_move(moves[self.battle_cursor])
            elif key == pygame.K_ESCAPE:
                self.battle_menu = 'MAIN'
                self.battle_cursor = 0

        elif self.battle_menu in ('SWITCH', 'FORCE_SWITCH'):
            party = self.player.party
            if key in (pygame.K_UP, pygame.K_w):
                self.party_cursor = (self.party_cursor - 1) % len(party)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.party_cursor = (self.party_cursor + 1) % len(party)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                mon = party[self.party_cursor]
                if mon.is_fainted():
                    return
                if mon is b.player:
                    return
                self.battle_do_switch(mon)
            elif key == pygame.K_ESCAPE and self.battle_menu == 'SWITCH':
                self.battle_menu = 'MAIN'

    # ---------------------------------------------------------- drawing
    def draw(self):
        self.screen.fill((15, 15, 20))
        if self.state == 'TITLE':
            self.draw_title()
        elif self.state == 'STARTER':
            self.draw_starter_select()
        elif self.state in ('OVERWORLD', 'DIALOG', 'PAUSE', 'PARTY'):
            self.draw_overworld()
            if self.state == 'DIALOG':
                self.draw_dialog()
            elif self.state == 'PAUSE':
                self.draw_pause()
            elif self.state == 'PARTY':
                self.draw_party_screen()
        elif self.state == 'BATTLE':
            self.draw_battle()

        if self.message_flash_timer > 0:
            self.message_flash_timer -= 1
            img = self.font.render(self.message_flash, True, (255, 255, 255))
            box = pygame.Rect(WIDTH // 2 - img.get_width() // 2 - 16, 16, img.get_width() + 32, 36)
            render.draw_panel(self.screen, box)
            self.screen.blit(img, (box.x + 16, box.y + 8))

        pygame.display.flip()

    def draw_title(self):
        title = self.font_big.render("MONSTER TAMER", True, (255, 255, 255))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 160))
        sub = self.font_small.render("A catching, battling & training adventure", True, (180, 180, 190))
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 205))

        options = self._title_options()
        for i, opt in enumerate(options):
            color = (255, 220, 80) if i == self.title_index else (255, 255, 255)
            img = self.font.render(("> " if i == self.title_index else "  ") + opt, True, color)
            self.screen.blit(img, (WIDTH // 2 - 60, 320 + i * 40))

        hint = self.font_small.render("Arrow keys to move  |  Enter/Space to confirm  |  P to pause", True,
                                       (140, 140, 150))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 40))

    def draw_starter_select(self):
        title = self.font_big.render("Choose your partner!", True, (255, 255, 255))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
        spacing = 260
        start_x = WIDTH // 2 - spacing
        for i, species in enumerate(STARTERS):
            data = SPECIES[species]
            cx = start_x + i * spacing
            cy = 260
            selected = i == self.starter_cursor
            box = pygame.Rect(cx - 100, cy - 110, 200, 260)
            render.draw_panel(self.screen, box, bg=(40, 40, 55) if selected else (25, 25, 32),
                               border=(255, 220, 80) if selected else render.PANEL_BORDER)
            render.draw_monster_sprite(self.screen, data['shape'], data['color'], (cx, cy - 10), 46)
            name = self.font.render(species, True, (255, 255, 255))
            self.screen.blit(name, (cx - name.get_width() // 2, cy + 60))
            typ = self.font_small.render(data['type'] + " type", True, (180, 180, 190))
            self.screen.blit(typ, (cx - typ.get_width() // 2, cy + 88))
        hint = self.font_small.render("Left/Right to choose, Enter to confirm", True, (180, 180, 190))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 60))

    def draw_overworld(self):
        w, h = self.world.width(), self.world.height()
        ox = (WIDTH - w * TILE) // 2
        oy = 70 + (HEIGHT - 70 - h * TILE) // 2
        colors = {'.': (60, 130, 60), ',': (40, 105, 40), '#': (40, 60, 40),
                  '~': (40, 90, 160), 'L': (120, 110, 160), 'X': (70, 140, 200)}
        for y in range(h):
            for x in range(w):
                t = self.world.tile_at(x, y)
                c = colors.get(t, (50, 90, 50))
                if t.isdigit():
                    c = (70, 70, 70)
                rect = pygame.Rect(ox + x * TILE, oy + y * TILE, TILE, TILE)
                pygame.draw.rect(self.screen, c, rect)
                pygame.draw.rect(self.screen, (0, 0, 0, 30), rect, 1)
                if t == 'L':
                    lbl = self.font_small.render("LAB", True, (255, 255, 255))
                    self.screen.blit(lbl, (rect.x + 3, rect.y + 10))
                if t.isdigit():
                    lbl = self.font_small.render("!", True, (255, 210, 60))
                    self.screen.blit(lbl, (rect.x + TILE // 2 - 3, rect.y + 6))

        px, py = self.player.pos
        prect_x = ox + px * TILE + TILE // 2
        prect_y = oy + py * TILE + TILE // 2
        pygame.draw.circle(self.screen, (255, 210, 90), (prect_x, prect_y), TILE // 2 - 4)
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.player.facing]
        pygame.draw.circle(self.screen, (60, 40, 10),
                            (prect_x + dx * 8, prect_y + dy * 8), 4)

        # HUD
        hud = pygame.Rect(0, 0, WIDTH, 60)
        render.draw_panel(self.screen, hud, bg=(24, 24, 32))
        name = self.font.render(self.world.data['name'], True, (255, 255, 255))
        self.screen.blit(name, (16, 18))
        coins = self.font_small.render(f"Coins: {self.player.coins}   Orbs: {self.player.orbs}", True,
                                        (200, 200, 210))
        self.screen.blit(coins, (16, 40))
        for i, m in enumerate(self.player.party[:6]):
            cx = WIDTH - 30 - i * 40
            col = m.color if not m.is_fainted() else '#505050'
            render.draw_monster_sprite(self.screen, m.shape, col, (cx, 30), 14)
        hint = self.font_small.render("Move: Arrows | Interact: Space | Pause: P", True, (150, 150, 160))
        self.screen.blit(hint, (WIDTH - hint.get_width() - 16, HEIGHT - 24))

    def draw_dialog(self):
        box = pygame.Rect(60, HEIGHT - 150, WIDTH - 120, 110)
        render.draw_text_box(self.screen, box, self.dialog_current, self.font)
        hint = self.font_small.render("Press Enter/Space to continue", True, (170, 170, 180))
        self.screen.blit(hint, (box.right - hint.get_width() - 16, box.bottom - 24))

    def draw_pause(self):
        box = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 140, 300, 280)
        render.draw_panel(self.screen, box)
        title = self.font.render("Paused", True, (255, 255, 255))
        self.screen.blit(title, (box.centerx - title.get_width() // 2, box.y + 14))
        options = ['Party', 'Save', 'Pokedex', 'Return', 'Quit to Title']
        for i, opt in enumerate(options):
            color = (255, 220, 80) if i == self.pause_cursor else (255, 255, 255)
            img = self.font.render(("> " if i == self.pause_cursor else "  ") + opt, True, color)
            self.screen.blit(img, (box.x + 30, box.y + 60 + i * 38))

    def draw_party_screen(self):
        box = pygame.Rect(60, 80, WIDTH - 120, HEIGHT - 160)
        render.draw_panel(self.screen, box)
        title = self.font.render("Your Party", True, (255, 255, 255))
        self.screen.blit(title, (box.x + 20, box.y + 14))
        if not self.player.party:
            empty = self.font_small.render("No monsters yet - visit the Lab!", True, (200, 200, 200))
            self.screen.blit(empty, (box.x + 20, box.y + 60))
        for i, m in enumerate(self.player.party):
            row = pygame.Rect(box.x + 20, box.y + 56 + i * 62, box.width - 40, 54)
            sel = i == self.party_cursor
            render.draw_panel(self.screen, row, bg=(45, 45, 60) if sel else (28, 28, 36))
            render.draw_monster_sprite(self.screen, m.shape, m.color, (row.x + 30, row.centery), 20)
            name = self.font.render(f"{m.nickname}  Lv.{m.level}", True, (255, 255, 255))
            self.screen.blit(name, (row.x + 70, row.y + 6))
            hp_rect = pygame.Rect(row.x + 70, row.y + 30, 200, 14)
            render.draw_hp_bar(self.screen, hp_rect, m.hp, m.max_hp)
            hp_txt = self.font_small.render(f"{m.hp}/{m.max_hp}", True, (255, 255, 255))
            self.screen.blit(hp_txt, (hp_rect.right + 10, hp_rect.y - 2))
            typ = self.font_small.render(m.type, True, (180, 180, 190))
            self.screen.blit(typ, (row.right - 80, row.y + 18))
        hint = self.font_small.render("Esc to go back", True, (170, 170, 180))
        self.screen.blit(hint, (box.x + 20, box.bottom - 26))

    def draw_battle(self):
        b = self.battle
        self.screen.fill((25, 45, 35))
        # enemy
        render.draw_monster_sprite(self.screen, b.enemy.shape, b.enemy.color, (680, 200), b.enemy.size)
        enemy_panel = pygame.Rect(40, 40, 300, 70)
        render.draw_panel(self.screen, enemy_panel)
        self.screen.blit(self.font.render(f"{b.enemy.nickname}  Lv.{b.enemy.level}", True, (255, 255, 255)),
                          (enemy_panel.x + 12, enemy_panel.y + 8))
        render.draw_hp_bar(self.screen, pygame.Rect(enemy_panel.x + 12, enemy_panel.y + 38, 200, 16),
                            b.enemy.hp, b.enemy.max_hp)

        # player
        render.draw_monster_sprite(self.screen, b.player.shape, b.player.color, (250, 430), b.player.size)
        player_panel = pygame.Rect(600, 380, 320, 80)
        render.draw_panel(self.screen, player_panel)
        self.screen.blit(self.font.render(f"{b.player.nickname}  Lv.{b.player.level}", True, (255, 255, 255)),
                          (player_panel.x + 12, player_panel.y + 8))
        render.draw_hp_bar(self.screen, pygame.Rect(player_panel.x + 12, player_panel.y + 38, 220, 16),
                            b.player.hp, b.player.max_hp)
        hp_txt = self.font_small.render(f"{b.player.hp}/{b.player.max_hp}", True, (255, 255, 255))
        self.screen.blit(hp_txt, (player_panel.x + 12, player_panel.y + 58))

        # bottom panel
        bottom = pygame.Rect(0, HEIGHT - 170, WIDTH, 170)
        render.draw_panel(self.screen, bottom, bg=(22, 22, 30))

        if self.battle_menu == 'MSG':
            msg_box = pygame.Rect(20, HEIGHT - 150, WIDTH - 40, 130)
            render.draw_text_box(self.screen, msg_box, self.battle_current_msg, self.font)
            hint = self.font_small.render("Press Enter/Space to continue", True, (170, 170, 180))
            self.screen.blit(hint, (msg_box.right - hint.get_width() - 16, msg_box.bottom - 24))
        elif self.battle_menu == 'MAIN':
            options = ['Fight', 'Bag', 'Party', 'Run']
            for i, opt in enumerate(options):
                col = (WIDTH // 2 - 220 + (i % 2) * 240, HEIGHT - 150 + (i // 2) * 55)
                sel = i == self.battle_cursor
                r = pygame.Rect(col[0], col[1], 220, 46)
                render.draw_panel(self.screen, r, bg=(50, 50, 65) if sel else (30, 30, 40))
                img = self.font.render(opt, True, (255, 220, 80) if sel else (255, 255, 255))
                self.screen.blit(img, (r.x + 16, r.y + 10))
        elif self.battle_menu == 'FIGHT':
            moves = b.player.moves
            for i, mv in enumerate(moves):
                col = (20 + (i % 2) * 470, HEIGHT - 150 + (i // 2) * 55)
                sel = i == self.battle_cursor
                r = pygame.Rect(col[0], col[1], 450, 46)
                render.draw_panel(self.screen, r, bg=(50, 50, 65) if sel else (30, 30, 40))
                mv_data = MOVES[mv]
                txt = f"{mv}  ({mv_data['type']}, PP {b.player.pp.get(mv, mv_data['pp'])}/{mv_data['pp']})"
                img = self.font_small.render(txt, True, (255, 220, 80) if sel else (255, 255, 255))
                self.screen.blit(img, (r.x + 16, r.y + 14))
            hint = self.font_small.render("Esc: back", True, (170, 170, 180))
            self.screen.blit(hint, (WIDTH - 100, HEIGHT - 20))
        elif self.battle_menu in ('SWITCH', 'FORCE_SWITCH'):
            party = self.player.party
            title = "Choose a monster" if self.battle_menu == 'FORCE_SWITCH' else "Switch to..."
            self.screen.blit(self.font.render(title, True, (255, 255, 255)), (20, HEIGHT - 165))
            for i, m in enumerate(party):
                sel = i == self.party_cursor
                r = pygame.Rect(20 + (i % 3) * 320, HEIGHT - 135 + (i // 3) * 40, 300, 36)
                render.draw_panel(self.screen, r, bg=(50, 50, 65) if sel else (30, 30, 40))
                status = "FAINTED" if m.is_fainted() else f"{m.hp}/{m.max_hp} HP"
                txt = f"{m.nickname} Lv.{m.level} - {status}"
                img = self.font_small.render(txt, True,
                                              (120, 120, 120) if m.is_fainted() else
                                              ((255, 220, 80) if sel else (255, 255, 255)))
                self.screen.blit(img, (r.x + 10, r.y + 9))

    # ---------------------------------------------------------- loop
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F4 and (pygame.key.get_mods() & pygame.KMOD_ALT):
                        self.running = False
                    else:
                        self.handle_keydown(event.key)
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == '__main__':
    Game().run()
