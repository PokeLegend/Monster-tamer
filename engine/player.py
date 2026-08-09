from engine.monster import Monster


class Player:
    def __init__(self, name="Tamer"):
        self.name = name
        self.party = []          # list[Monster], max 6 active
        self.box = []            # overflow storage
        self.coins = 200
        self.orbs = 5
        self.map = 'hometown'
        self.pos = [4, 4]
        self.facing = 'down'
        self.defeated_trainers = set()   # "mapname:trainerid"
        self.caught_species = set()
        self.seen_species = set()
        self.playtime_frames = 0

    def add_monster(self, monster):
        if len(self.party) < 6:
            self.party.append(monster)
        else:
            self.box.append(monster)

    def first_alive(self):
        return next((m for m in self.party if not m.is_fainted()), None)

    def has_alive(self):
        return any(not m.is_fainted() for m in self.party)

    def heal_party(self):
        for m in self.party:
            m.heal_full()

    def pokedex_progress(self):
        return len(self.caught_species), 18

    def to_dict(self):
        return {
            'name': self.name,
            'party': [m.to_dict() for m in self.party],
            'box': [m.to_dict() for m in self.box],
            'coins': self.coins,
            'orbs': self.orbs,
            'map': self.map,
            'pos': self.pos,
            'facing': self.facing,
            'defeated_trainers': list(self.defeated_trainers),
            'caught_species': list(self.caught_species),
            'seen_species': list(self.seen_species),
        }

    @staticmethod
    def from_dict(d):
        p = Player(d.get('name', 'Tamer'))
        p.party = [Monster.from_dict(m) for m in d.get('party', [])]
        p.box = [Monster.from_dict(m) for m in d.get('box', [])]
        p.coins = d.get('coins', 200)
        p.orbs = d.get('orbs', 5)
        p.map = d.get('map', 'hometown')
        p.pos = d.get('pos', [4, 4])
        p.facing = d.get('facing', 'down')
        p.defeated_trainers = set(d.get('defeated_trainers', []))
        p.caught_species = set(d.get('caught_species', []))
        p.seen_species = set(d.get('seen_species', []))
        return p
