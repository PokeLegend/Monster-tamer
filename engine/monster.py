"""Monster: an individual creature instance (species data + level + current state)."""
import json
import math
import os
import random

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

with open(os.path.join(_DATA_DIR, 'monsters.json')) as f:
    SPECIES = json.load(f)

with open(os.path.join(_DATA_DIR, 'moves.json')) as f:
    MOVES = json.load(f)

# Type effectiveness chart: ATTACKER -> {DEFENDER: multiplier}
TYPE_CHART = {
    'Fire':     {'Grass': 2.0, 'Water': 0.5, 'Rock': 0.5},
    'Water':    {'Fire': 2.0, 'Rock': 2.0, 'Grass': 0.5, 'Electric': 0.5},
    'Grass':    {'Water': 2.0, 'Rock': 2.0, 'Fire': 0.5, 'Flying': 0.5},
    'Electric': {'Water': 2.0, 'Flying': 2.0, 'Rock': 0.5, 'Electric': 0.5},
    'Rock':     {'Fire': 2.0, 'Flying': 2.0, 'Water': 0.5, 'Grass': 0.5},
    'Flying':   {'Grass': 2.0, 'Electric': 0.5, 'Rock': 0.5},
    'Normal':   {}
}


def type_effectiveness(atk_type, def_type):
    return TYPE_CHART.get(atk_type, {}).get(def_type, 1.0)


def stat_at_level(base, level):
    """Simple linear-ish growth curve."""
    return math.floor(base * (1 + level * 0.12)) + level


def exp_to_next_level(level):
    return int(20 * (level ** 1.6)) + 20


class Monster:
    def __init__(self, species, level, nickname=None):
        self.species = species
        self.level = level
        self.nickname = nickname or species
        data = SPECIES[species]
        self.type = data['type']
        self.shape = data['shape']
        self.color = data['color']
        self.size = data['size']
        self.catch_rate = data['catch_rate']
        self.evolve_level = data.get('evolve_level')
        self.evolves_to = data.get('evolves_to')
        self.move_table = data['moves']

        self.max_hp = self._calc_max_hp()
        self.hp = self.max_hp
        self.atk = stat_at_level(data['base_atk'], level)
        self.def_ = stat_at_level(data['base_def'], level)
        self.spd = stat_at_level(data['base_spd'], level)

        self.exp = 0
        self.exp_next = exp_to_next_level(level)
        self.moves = self._moves_known()
        self.pp = {m: MOVES[m]['pp'] for m in self.moves}

    def _calc_max_hp(self):
        base = SPECIES[self.species]['base_hp']
        return math.floor(base * (1 + self.level * 0.14)) + self.level * 2 + 10

    def _moves_known(self):
        known = [m for lvl, m in self.move_table if lvl <= self.level]
        # most recently learned 4 moves
        return known[-4:] if len(known) > 4 else known

    def recalc_stats(self, heal=False):
        data = SPECIES[self.species]
        old_max = self.max_hp
        self.max_hp = self._calc_max_hp()
        self.atk = stat_at_level(data['base_atk'], self.level)
        self.def_ = stat_at_level(data['base_def'], self.level)
        self.spd = stat_at_level(data['base_spd'], self.level)
        if heal:
            self.hp = self.max_hp
        else:
            self.hp = min(self.max_hp, self.hp + (self.max_hp - old_max))

    def is_fainted(self):
        return self.hp <= 0

    def heal_full(self):
        self.hp = self.max_hp
        self.pp = {m: MOVES[m]['pp'] for m in self.moves}

    def gain_exp(self, amount):
        """Returns list of event strings (level ups / evolution)."""
        events = []
        self.exp += amount
        while self.exp >= self.exp_next and self.evolve_level != 'MAXED':
            self.exp -= self.exp_next
            self.level += 1
            self.recalc_stats(heal=False)
            self.exp_next = exp_to_next_level(self.level)
            events.append(f"{self.nickname} grew to level {self.level}!")
            new_moves = [m for lvl, m in self.move_table if lvl == self.level]
            for m in new_moves:
                if m not in self.moves:
                    if len(self.moves) >= 4:
                        self.moves.pop(0)
                    self.moves.append(m)
                    self.pp[m] = MOVES[m]['pp']
                    events.append(f"{self.nickname} learned {m}!")
            if self.evolve_level and self.level >= self.evolve_level and self.evolves_to:
                events.append(f"{self.nickname} evolved into {self.evolves_to}!")
                self._evolve(self.evolves_to)
            if self.level >= 60:
                break
        return events

    def _evolve(self, new_species):
        data = SPECIES[new_species]
        self.species = new_species
        if self.nickname == self._prev_name_placeholder():
            pass
        self.type = data['type']
        self.shape = data['shape']
        self.color = data['color']
        self.size = data['size']
        self.catch_rate = data['catch_rate']
        self.evolve_level = data.get('evolve_level')
        self.evolves_to = data.get('evolves_to')
        self.move_table = data['moves']
        self.recalc_stats(heal=True)
        self.moves = self._moves_known()
        self.pp = {m: MOVES[m]['pp'] for m in self.moves}

    def _prev_name_placeholder(self):
        return self.nickname

    def to_dict(self):
        return {
            'species': self.species, 'level': self.level, 'nickname': self.nickname,
            'hp': self.hp, 'exp': self.exp
        }

    @staticmethod
    def from_dict(d):
        m = Monster(d['species'], d['level'], d.get('nickname'))
        m.exp = d.get('exp', 0)
        m.exp_next = exp_to_next_level(m.level)
        m.hp = d.get('hp', m.max_hp)
        return m
