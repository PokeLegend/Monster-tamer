"""Turn-based battle engine with status effects, critical hits, PP, and smarter AI."""
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
        self.state = 'ongoing'  # ongoing, won, lost, caught, ran
        self.log = []
        self.turn_pending_switch = False
        self.def_boosts = {'player': 0, 'enemy': 0}
        self.atk_boosts = {'player': 0, 'enemy': 0}
        self.turn_count = 0

        # Ensure monsters have a .status attribute (safe fallback)
        for m in [self.player, self.enemy] + self.player_party + self.enemy_team:
            if not hasattr(m, 'status'):
                m.status = None
            if not hasattr(m, 'pp'):
                m.pp = {move: MOVES[move]['pp'] for move in m.moves}

    # ------------------------------------------------------------- helpers
    def _say(self, text):
        self.log.append(text)

    def _get_stat(self, monster, stat, side):
        """Get effective stat after boosts."""
        boost_key = 'player' if side == 'player' else 'enemy'
        if stat == 'atk':
            base = monster.atk
            boost = self.atk_boosts[boost_key]
        else:  # def
            base = monster.def_
            boost = self.def_boosts[boost_key]
        # Apply status effects: Burn halves Attack
        if stat == 'atk' and monster.status == 'burn':
            return base * (1 + 0.5 * boost) * 0.5
        return base * (1 + 0.5 * boost)

    def _apply_status(self, target, status, chance=1.0):
        """Attempt to apply a status effect."""
        if target.status is not None:
            return False
        if random.random() > chance:
            return False
        # Some types are immune
        if status in ('burn', 'freeze') and target.type == 'Fire':
            return False
        if status == 'poison' and target.type in ('Poison', 'Steel'):
            return False
        if status == 'paralysis' and target.type == 'Electric':
            return False
        target.status = status
        target.status_turns = 0
        self._say(f"{target.nickname} was {status}ed!")
        return True

    def _handle_status_effects(self, monster, side):
        """Called at end of turn. Returns True if monster lost turn."""
        if monster.status is None or monster.is_fainted():
            return False

        status = monster.status
        monster.status_turns += 1

        if status == 'burn':
            dmg = max(1, int(monster.max_hp * 0.0625))
            monster.hp = max(0, monster.hp - dmg)
            self._say(f"{monster.nickname} is hurt by its burn! (-{dmg} HP)")
            if monster.hp <= 0:
                self._say(f"{monster.nickname} fainted!")
                return False
            return False

        elif status == 'poison':
            dmg = max(1, int(monster.max_hp * 0.08))
            monster.hp = max(0, monster.hp - dmg)
            self._say(f"{monster.nickname} is hurt by poison! (-{dmg} HP)")
            if monster.hp <= 0:
                self._say(f"{monster.nickname} fainted!")
                return False
            return False

        elif status == 'paralysis':
            if random.random() < 0.25:
                self._say(f"{monster.nickname} is paralyzed and can't move!")
                return True  # lost turn
            return False

        elif status == 'freeze':
            if random.random() < 0.20:
                monster.status = None
                self._say(f"{monster.nickname} thawed out!")
                return False
            else:
                self._say(f"{monster.nickname} is frozen solid!")
                return True  # lost turn
        return False

    # ------------------------------------------------------------- damage
    def _damage(self, attacker, defender, move_name, side):
        move = MOVES[move_name]
        if move['power'] <= 0:
            return 0

        # Accuracy check
        if random.randint(1, 100) > move['accuracy']:
            self._say(f"{attacker.nickname}'s {move_name} missed!")
            return 0

        # Critical hit (1/16 chance)
        is_crit = random.random() < (1 / 16)
        crit_mult = 1.5 if is_crit else 1.0

        # Stats with boosts
        atk_stat = self._get_stat(attacker, 'atk', side)
        def_stat = self._get_stat(defender, 'def', 'enemy' if side == 'player' else 'player')

        # Type effectiveness
        eff = type_effectiveness(move['type'], defender.type)

        # Damage formula (Gen 3 style)
        base = (2 * attacker.level / 5 + 2) * move['power'] * (atk_stat / max(1, def_stat)) / 50 + 2
        variance = random.uniform(0.85, 1.0)
        dmg = max(1, int(base * eff * crit_mult * variance))

        defender.hp = max(0, defender.hp - dmg)

        # Build message
        msg = f"{attacker.nickname} used {move_name}!"
        if is_crit:
            msg += " A critical hit!"
        if eff > 1:
            msg += " It's super effective!"
        elif eff < 1:
            msg += " It's not very effective..."
        msg += f" ({dmg} dmg)"
        self._say(msg)

        # Apply status effect from move (if any)
        if 'status' in move and move['status']:
            self._apply_status(defender, move['status'], move.get('status_chance', 1.0))

        return dmg

    # ------------------------------------------------------------- turn logic
    def use_move(self, player_move_name):
        """Resolve one full turn: player uses a move, then enemy responds."""
        self.log = []
        self.turn_count += 1

        if self.state != 'ongoing':
            return self.log

        # --- PP handling ---
        player_pp = self.player.pp.get(player_move_name, 0)
        if player_pp <= 0:
            self._say(f"{player_move_name} has no PP left! {self.player.nickname} uses Struggle!")
            # Struggle: 50 power, typeless, recoil
            dmg = max(1, int(self.player.atk * 0.4))
            self.enemy.hp = max(0, self.enemy.hp - dmg)
            recoil = max(1, int(dmg * 0.25))
            self.player.hp = max(0, self.player.hp - recoil)
            self._say(f"It dealt {dmg} damage! {self.player.nickname} took {recoil} recoil!")
            if self.enemy.is_fainted():
                self._say(f"{self.enemy.nickname} fainted!")
        else:
            self.player.pp[player_move_name] = player_pp - 1

        # --- Process turn ---
        # 1. Handle status effects at start of turn (paralysis/freeze skip)
        player_skip = self._handle_status_effects(self.player, 'player')
        enemy_skip = self._handle_status_effects(self.enemy, 'enemy')

        # Check if anyone fainted from status damage
        if self._check_faint():
            return self.log

        # Determine order (speed, with status check)
        order = []
        if not player_skip and self.player.is_alive():
            order.append(('player', self.player, self.enemy, player_move_name))
        if not enemy_skip and self.enemy.is_alive():
            # Enemy AI: choose a move
            enemy_move = self._choose_enemy_move()
            order.append(('enemy', self.enemy, self.player, enemy_move))

        # Sort by speed (higher goes first)
        order.sort(key=lambda t: t[1].spd, reverse=True)

        # Execute moves
        for side, attacker, defender, move_name in order:
            if attacker.is_fainted() or defender.is_fainted():
                continue
            move = MOVES[move_name]
            if move['power'] > 0:
                self._damage(attacker, defender, move_name, side)
            else:
                self._apply_effect(attacker, move_name, side)
            if self._check_faint():
                break

        # 2. End-of-turn status damage (burn/poison)
        if not self._check_faint():
            self._handle_status_effects(self.player, 'player')
            self._handle_status_effects(self.enemy, 'enemy')
            self._check_faint()

        return self.log

    def _choose_enemy_move(self):
        """Smarter AI: prefers status moves if player isn't statused, else highest power."""
        # Filter moves with PP
        available = [m for m in self.enemy.moves if self.enemy.pp.get(m, 0) > 0]
        if not available:
            return self.enemy.moves[0]  # fallback, will struggle

        # If player has no status, check if enemy has a status move
        if self.player.status is None:
            status_moves = [m for m in available if MOVES[m]['power'] == 0 and 'status' in MOVES[m]]
            if status_moves and random.random() < 0.6:
                return random.choice(status_moves)

        # Otherwise pick highest power move with some randomness
        moves_with_power = [(m, MOVES[m]['power']) for m in available if MOVES[m]['power'] > 0]
        if moves_with_power:
            moves_with_power.sort(key=lambda x: x[1], reverse=True)
            # 80% chance to pick the strongest, 20% random among top 3
            if random.random() < 0.8:
                return moves_with_power[0][0]
            else:
                top = moves_with_power[:3]
                return random.choice(top)[0]

        # Fallback to first available
        return available[0]

    def _apply_effect(self, user, move_name, side):
        move = MOVES[move_name]
        eff = move.get('effect')
        if eff == 'raise_def':
            self.def_boosts[side] = min(6, self.def_boosts[side] + 1)
            self._say(f"{user.nickname} raised its defense!")
        elif eff == 'lower_atk':
            other = 'enemy' if side == 'player' else 'player'
            self.atk_boosts[other] = max(-6, self.atk_boosts[other] - 1)
            self._say(f"{user.nickname} used Roar! Opponent's attack fell!")

    def _check_faint(self):
        """Check if either side fainted. Returns True if state changed."""
        if self.enemy.is_fainted():
            self._say(f"{self.enemy.nickname} fainted!")
            exp = self._exp_reward()
            self._say(f"{self.player.nickname} gained {exp} EXP.")
            events = self.player.gain_exp(exp)
            self.log.extend(events)
            self.enemy_index += 1
            if not self.is_wild and self.enemy_index < len(self.enemy_team):
                self.enemy = self.enemy_team[self.enemy_index]
                self.enemy.status = None  # fresh monster
                self._say(f"{self.trainer_name} sent out {self.enemy.nickname}!")
                return False
            else:
                self.state = 'won'
                if not self.is_wild and self.reward:
                    self._say(f"You earned {self.reward} coins!")
                return True

        elif self.player.is_fainted():
            next_alive = next((m for m in self.player_party if not m.is_fainted()), None)
            if next_alive:
                self._say(f"{self.player.nickname} fainted! Choose your next monster.")
                self.turn_pending_switch = True
                return True
            else:
                self._say("All your monsters have fainted! You blacked out...")
                self.state = 'lost'
                return True
        return False

    def _exp_reward(self):
        return int(15 + self.enemy.level * 6)

    # ------------------------------------------------------------- switch / catch / run
    def switch_in(self, monster):
        self.player = monster
        self.turn_pending_switch = False
        self.log = [f"Go, {monster.nickname}!"]
        # Reset boosts for new monster
        self.atk_boosts['player'] = 0
        self.def_boosts['player'] = 0
        return self.log

    def attempt_catch(self, ball_bonus=1.0):
        self.log = []
        if not self.is_wild:
            self._say("You can't catch another trainer's monster!")
            return self.log

        # Catch rate formula with status bonus
        hp_factor = (1 - (self.enemy.hp / self.enemy.max_hp)) * 0.7 + 0.3
        status_bonus = 1.0
        if self.enemy.status in ('freeze', 'sleep'):  # sleep is not implemented but reserved
            status_bonus = 2.0
        elif self.enemy.status in ('burn', 'poison', 'paralysis'):
            status_bonus = 1.5

        chance = min(0.95, (self.enemy.catch_rate / 255) * hp_factor * ball_bonus * status_bonus)
        self._say(f"You threw a capture orb at {self.enemy.nickname}...")
        if random.random() < chance:
            self._say(f"Gotcha! {self.enemy.nickname} was caught!")
            self.state = 'caught'
        else:
            self._say(f"{self.enemy.nickname} broke free!")
            # Enemy retaliates
            enemy_move = self._choose_enemy_move()
            self._damage(self.enemy, self.player, enemy_move, 'enemy')
            self._check_faint()
        return self.log

    def attempt_run(self):
        self.log = []
        if not self.is_wild:
            self._say("You can't run from a trainer battle!")
            return self.log
        # Run chance based on speed comparison
        if random.random() < 0.8:
            self._say("Got away safely!")
            self.state = 'ran'
        else:
            self._say("Couldn't escape!")
            enemy_move = self._choose_enemy_move()
            self._damage(self.enemy, self.player, enemy_move, 'enemy')
            self._check_faint()
        return self.log
