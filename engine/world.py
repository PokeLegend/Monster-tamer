import json
import os
import random

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

with open(os.path.join(_DATA_DIR, 'maps.json')) as f:
    MAPS = json.load(f)

BLOCKED_TILES = {'#', '~', 'L'}  # L (lab) is interactable but blocks walking onto it


class World:
    def __init__(self, map_name):
        self.map_name = None
        self.data = None
        self.grid = None
        self.load(map_name)

    def load(self, map_name):
        self.map_name = map_name
        self.data = MAPS[map_name]
        self.grid = [list(row) for row in self.data['grid']]

    def width(self):
        return len(self.grid[0])

    def height(self):
        return len(self.grid)

    def tile_at(self, x, y):
        if 0 <= y < self.height() and 0 <= x < self.width():
            return self.grid[y][x]
        return '#'

    def is_blocked(self, x, y):
        return self.tile_at(x, y) in BLOCKED_TILES or self.trainer_at(x, y) is not None

    def trainer_at(self, x, y):
        t = self.tile_at(x, y)
        if t.isdigit():
            return self.data['trainers'].get(t)
        return None

    def trainer_id_at(self, x, y):
        t = self.tile_at(x, y)
        if t.isdigit():
            return t
        return None

    def exit_at(self, x, y):
        return self.data['exits'].get(f"{y},{x}")

    def is_grass(self, x, y):
        return self.tile_at(x, y) == ','

    def is_lab(self, x, y):
        return self.tile_at(x, y) == 'L'

    def roll_encounter(self):
        if random.random() > self.data.get('encounter_rate', 0):
            return None
        table = self.data.get('encounters', [])
        if not table:
            return None
        total = sum(e['weight'] for e in table)
        r = random.uniform(0, total)
        upto = 0
        for e in table:
            upto += e['weight']
            if r <= upto:
                level = random.randint(e['min_level'], e['max_level'])
                return e['name'], level
        e = table[-1]
        return e['name'], random.randint(e['min_level'], e['max_level'])
