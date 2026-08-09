"""Turn-based battle engine. Pure logic - UI layer reads .log after each call."""
import random
from engine.monster import MOVES, type_effectiveness, Monster


class Battle:
    def __init__(self, player_monster, enemy_monster, is_wild=True, trainer_name=None,
                 player_party=None, enemy_team=None, reward=0):
        self.player = player_monster
        self.enemy = enemy_monster
        self.is_wild = is_wild
        self.trainer_name = trainer_name
        self.player_party = player_party or [player_monster]
        self.enemy_team = enemy_team or [enemy_monster]
        self.enemy_index = 0
        self.reward = reward
        self.state = 'ongoing'   # ongoing, won, lost, caught, ran, fled_by_enemy
        self.log = []
        self.turn_pending_switch = False
        self.def_boosts = {'player': 0, 'enemy': 0}
        self.atk_boosts = {'player': 0, 'enemy': 0}

    def _say(self, text):
        self.log.append(text)

    def _damage(self, attacker, defender, move_name, side):
        move = MOVES[move_name]
        if move['power'] <= 0:
            return 0
        if random.randint(1, 100) > move['accuracy']:
            self._say(f"{attacker.nickname}'s {move_name} missed!")
            return 0
        atk_stat = attacker.atk * (1 + 0.5 * self.atk_boosts['player' if side == 'player' else 'enemy'])
        def_stat = defender.def_ * (1 + 0.5 * self.def_boosts['enemy' if side == 'player' else 'player'])
        eff = type_effectiveness(move['type'], defender.type)
        base = (2 * attacker.level / 5 + 2) * move['power'] * (atk_stat / max(1, def_stat)) / 50 + 2
        variance = random.uniform(0.85, 1.0)
        dmg = max(1, int(base * eff * variance))
        defender.hp = max(0, defender.hp - dmg)
        eff_text = ""
        if eff > 1:
            eff_text = " It's super effective!"
        elif eff < 1:
            eff_text = " It's not very effective..."
        self._say(f"{attacker.nickname} used {move_name}!{eff_text} ({dmg} dmg)")
        return dmg

    def _apply_effect(self, user, move_name, side):
        move = MOVES[move_name]
        eff = move.get('effect')
        if eff == 'raise_def':
            self.def_boosts[side] += 1
            self._say(f"{user.nickname} raised its defense!")
        elif eff == 'lower_atk':
            other = 'enemy' if side == 'player' else 'player'
            self.atk_boosts[other] -= 1
            self._say(f"{user.nickname} used Roar! Opponent's attack fell!")

    def use_move(self, player_move_name):
        """Resolve one full turn: player uses a move, then enemy (if alive) uses a random move."""
        self.log = []
        if self.state != 'ongoing':
            return self.log

        enemy_move_name = random.choice(self.enemy.moves)
        order = [('player', self.player, self.enemy, player_move_name),
                 ('enemy', self.enemy, self.player, enemy_move_name)]
        order.sort(key=lambda t: t[1].spd, reverse=True)
        order[0] = (order[0][0], order[0][1], order[0][2], order[0][3])

        for side, attacker, defender, move_name in order:
            if attacker.is_fainted():
                continue
            if defender.is_fainted():
                continue
            move = MOVES[move_name]
            if move['power'] > 0:
                self._damage(attacker, defender, move_name, side)
            else:
                self._apply_effect(attacker, move_name, side)
            if defender.is_fainted():
                self._say(f"{defender.nickname} fainted!")
                break

        self._check_end_of_turn()
        return self.log

    def _check_end_of_turn(self):
        if self.enemy.is_fainted():
            exp = self._exp_reward()
            self._say(f"{self.enemy.nickname} was defeated! {self.player.nickname} gained {exp} EXP.")
            events = self.player.gain_exp(exp)
            self.log.extend(events)
            self.enemy_index += 1
            if not self.is_wild and self.enemy_index < len(self.enemy_team):
                self.enemy = self.enemy_team[self.enemy_index]
                self._say(f"{self.trainer_name} sent out {self.enemy.nickname}!")
            else:
                self.state = 'won'
                if not self.is_wild and self.reward:
                    self._say(f"You earned {self.reward} coins!")
        elif self.player.is_fainted():
            next_alive = next((m for m in self.player_party if not m.is_fainted()), None)
            if next_alive:
                self._say(f"{self.player.nickname} fainted! Choose your next monster.")
                self.turn_pending_switch = True
            else:
                self._say("All your monsters have fainted! You blacked out...")
                self.state = 'lost'

    def _exp_reward(self):
        base = 15 + self.enemy.level * 6
        return int(base)

    def switch_in(self, monster):
        self.player = monster
        self.turn_pending_switch = False
        self.log = [f"Go, {monster.nickname}!"]
        return self.log

    def attempt_catch(self, ball_bonus=1.0):
        self.log = []
        if not self.is_wild:
            self._say("You can't catch another trainer's monster!")
            return self.log
        hp_factor = (1 - (self.enemy.hp / self.enemy.max_hp)) * 0.7 + 0.3
        chance = min(0.95, (self.enemy.catch_rate / 255) * hp_factor * ball_bonus)
        self._say(f"You threw a capture orb at {self.enemy.nickname}...")
        if random.random() < chance:
            self._say(f"Gotcha! {self.enemy.nickname} was caught!")
            self.state = 'caught'
        else:
            self._say(f"{self.enemy.nickname} broke free!")
            enemy_move = random.choice(self.enemy.moves)
            self._damage(self.enemy, self.player, enemy_move, 'enemy')
            self._check_end_of_turn()
        return self.log

    def attempt_run(self):
        self.log = []
        if not self.is_wild:
            self._say("You can't run from a trainer battle!")
            return self.log
        if random.random() < 0.8:
            self._say("Got away safely!")
            self.state = 'ran'
        else:
            self._say("Couldn't escape!")
            enemy_move = random.choice(self.enemy.moves)
            self._damage(self.enemy, self.player, enemy_move, 'enemy')
            self._check_end_of_turn()
        return self.log
