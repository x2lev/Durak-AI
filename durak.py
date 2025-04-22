from dataclasses import dataclass, field
import itertools
import random
import os

class UserIntelligenceError(Exception):
    def __init__(self, message=None):
        if message:
            self.message = message
        else:
            self.message = f'{os.getlogin()} appears to be a dumbass'
        super().__init__(self.message)

@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    ranks = ['6', '7', '8', '9']#, 'T', 'J', 'Q', 'K', 'A']
    suits = ['S', 'C', 'H', 'D']

    def __post_init__(self):
        if self.rank not in Card.ranks or self.suit not in Card.suits:
            raise ValueError(f"Invalid card: {self}")

    def __lt__(self, other):
        if Card.suits.index(self.suit) == Card.suits.index(other.suit):
            return Card.ranks.index(self.rank) < Card.ranks.index(other.rank)
        return Card.suits.index(self.suit) < Card.suits.index(other.suit)

    def __repr__(self):
        return f'{self.rank}{self.suit}'

    def tuple(self):
        return Card.ranks.index(self.rank), Card.suits.index(self.suit)


@dataclass
class Deck:
    revealed: dict[Card, int] = field(default_factory=dict)
    cards: list[Card] = field(default_factory=list)
    trump: Card = None

    def __post_init__(self):
        self.cards = [Card(rank, suit) for suit in Card.suits for rank in Card.ranks]
        random.shuffle(self.cards)

    def choose_trump(self):
        self.trump = self.cards.pop()
        self.cards.insert(0, self.trump)
        self.revealed[self.trump] = -1
        print(f'The chosen trump is: {self.trump}')

    def pop(self):
        return self.cards.pop()

    def has_cards(self):
        return len(self.cards) > 0

class GameState:
    def __init__(self, number_of_players):
        self.number_of_players = number_of_players
        self.primary_attacker = None
        self.discard = []
        self.deck = None
        self.trump = None

        self.primary_attacker = number_of_players
        self.field = {}
        self.out = []
        self.durak = None

        self.hands = []

    def reset(self):
        self.discard = []
        self.deck = Deck()
        self.deck.choose_trump()
        self.trump = self.deck.trump

        self.primary_attacker = 0
        self.field = {}
        self.out = []
        self.durak = None

        self.hands = [[] for _ in range(self.number_of_players)]
        for _ in range(6):
            for i, _ in enumerate(self.hands):
                self.hands[i].append(self.deck.pop())

    def next_after(self, player_idx):
        if len(self.out) == len(self.hands):
            return self.number_of_players
        na = (player_idx + 1) % self.number_of_players
        if na in self.out:
            return self.next_after(na)
        return na

    def defender(self):
        return self.next_after(self.primary_attacker)

    def legal_attacks(self, player_idx):
        if not self.field:
            legal_cards = self.hands[player_idx].copy()
        else:
            existing_ranks = {c.rank for c in self.field} | \
                            {c.rank for c in self.field.values() if c}
            legal_cards = [card for card in self.hands[player_idx] if card.rank in existing_ranks]

        combinations = [[card] for card in legal_cards]

        rank_groups = {}
        for card in legal_cards:
            if card.rank not in rank_groups:
                rank_groups[card.rank] = []
            rank_groups[card.rank].append(card)

        for cards in rank_groups.values():
            if len(cards) >= 2:
                for i in range(2, len(cards) + 1):
                    for combo in itertools.combinations(cards, i):
                        combinations.append(sorted(combo))

        if self.field:
            combinations.append(None)

        return combinations

    def legal_defenses(self):
        if self.durak is not None:
            return ['take']

        passable_combos = []
        if self.field and all(v is None for v in self.field.values()):
            rank = list(self.field.keys())[0].rank
            cards = [c for c in self.hands[self.defender()] if c.rank == rank]
            passable = list(itertools.chain.from_iterable(
                itertools.combinations(cards, r+1) for r in range(len(cards))))
            for combo in passable:
                passable_combos.append(('play', list(combo)))
            for card in cards:
                if card.suit == self.trump.suit:
                    passable_combos.append(('show', card))
                    break

        legal_cards = []
        for attack_card, defense_card in self.field.items():
            if defense_card is None:
                for card in self.hands[self.defender()]:
                    if self.can_beat(attack_card, card):
                        legal_cards.append((attack_card, card))

        def_groups = {}
        for a, d in legal_cards:
            if a not in def_groups:
                def_groups[a] = []
            def_groups[a].append(d)

        combinations = []

        for r in range(1, len(def_groups) + 1):
            for key_subset in itertools.combinations(list(def_groups.keys()), r):
                for values in itertools.product(*(def_groups[k] for k in key_subset)):
                    combinations.append(list(zip(key_subset, values)))

        unique_combos = []

        for group in combinations:
            n = len(group)
            for r in range(1, n+1):
                for subset in itertools.combinations(group, r):
                    second_cards = [card[1] for card in subset]
                    if len(set(second_cards)) == len(second_cards):
                        unique_combos.append(list(subset))

        discard_cap = 6 if self.discard else 5
        defense_cap = min(discard_cap - sum(1 for _, d in self.field.items() if d is not None), \
                        sum(1 for _, d in self.field.items() if d is None))
        capped_combos = [c for c in unique_combos if len(c) <= defense_cap]

        capped_combos.append(None)
        if None in self.field.values():
            capped_combos.append('take')

        return capped_combos + passable_combos

    def legal_pickup(self):
        discard_cap = 6 if self.discard else 5
        num_pickup = min([discard_cap - sum(1 for _, d in self.field.items() if d is not None),
                            sum(1 for _, d in self.field.items() if d is None),
                            len(self.hands[self.defender()])])
        unbeaten_cards = [a for a, d in self.field.items() if d is None]
        combos = [list(c) for c in itertools.combinations(unbeaten_cards, num_pickup)]
        return combos

    def can_beat(self, attack, defense):
        if defense.suit == attack.suit:
            return Card.ranks.index(defense.rank) > Card.ranks.index(attack.rank)
        return defense.suit == self.trump.suit and attack.suit != self.trump.suit

    def attack(self, player_idx, cards):
        for card in cards:
            self.deck.revealed[card] = player_idx
            self.hands[player_idx].remove(card)
            self.field[card] = None
        print(f'{player_idx} attacks with {cards}')
        if not self.deck.has_cards() and not self.hands[player_idx]:
            self.check_outs()

    def defend(self, attack_card, defense_card):
        print(f'{self.defender()} defends {attack_card} with {defense_card}')
        self.deck.revealed[defense_card] = self.defender()
        self.field[attack_card] = defense_card
        self.hands[self.defender()].remove(defense_card)

    def pass_it_on(self, method, card):
        print(f'{self.defender()} passes onto {self.next_after(self.defender())} by {method}ing {card}')
        self.deck.revealed[card] = self.defender()
        if method == 'play':
            self.field[card] = None
            self.hands[self.defender()].remove(card)
        self.primary_attacker = self.defender()

    def beat(self):
        print(f'{self.defender()} beat the allegations!')
        for a, d in self.field.items():
            self.deck.revealed[a] = -2
            self.deck.revealed[d] = -2
            self.discard.append(a)
            self.discard.append(d)
        self.field.clear()

        self.draw_cards()
        self.check_outs()

        self.primary_attacker = self.next_after(self.primary_attacker)

    def surrender(self, pickup):
        picked_up = []
        for a, d in self.field.items():
            if self.deck.revealed[a] == self.defender():
                self.hands[self.deck.revealed[a]].append(a)
                if d:
                    self.deck.revealed[d] = self.defender()
                    self.hands[self.defender()].append(d)
                    picked_up.append(d)
                picked_up.append(a)
            elif a in pickup:
                self.deck.revealed[a] = self.defender()
                self.hands[self.defender()].append(a)
                picked_up.append(a)
            elif d:
                self.deck.revealed[a] = self.defender()
                self.deck.revealed[d] = self.defender()
                self.hands[self.defender()].append(a)
                self.hands[self.defender()].append(d)
                picked_up.append(a)
                picked_up.append(d)
            else:
                self.hands[self.deck.revealed[a]].append(a)
                print(f'{self.deck.revealed[a]} took back {a}')
        print(f'{self.defender()} surrendered and picked up {picked_up}')
        self.field.clear()

        self.draw_cards()
        self.check_outs()

        self.primary_attacker = self.next_after(self.defender())

    def draw_cards(self):
        if self.deck.has_cards():
            draw_order = [self.primary_attacker]
            p = self.next_after(self.defender())
            while p != self.primary_attacker:
                draw_order.append(p)
                p = self.next_after(p)
            draw_order.append(self.defender())

            for p in draw_order:
                while self.deck.has_cards() and len(self.hands[p]) < 6:
                    self.hands[p].append(self.deck.pop())

    def check_outs(self):
        for i, hand in enumerate(self.hands):
            if i not in self.out and not hand and not self.deck.has_cards():
                self.out.append(i)
                if len(self.out) + 1 == self.number_of_players:
                    for j in range(self.number_of_players):
                        if j not in self.out:
                            self.durak = j
                            return

class Player:
    def __init__(self, name):
        self.name = name

    def decide_attack(self, _game_state, _idx):
        return None

    def decide_defense(self, _game_state):
        return None

    def decide_pickup(self, _game_state):
        return None

class BotPlayer(Player):
    def decide_attack(self, game_state, idx):
        return random.choice(game_state.legal_attacks(idx))

    def decide_defense(self, game_state):
        return random.choice(game_state.legal_defenses())

    def decide_pickup(self, game_state):
        return random.choice(game_state.legal_pickup())

class HumanPlayer(Player):
    def decide_attack(self, game_state, idx):
        print('           ATTACK')
        print(f'  Play Field: {game_state.field}')
        print(f'Current Hand: {game_state.hands[idx]}')
        print(f' Legal Plays: {game_state.legal_attacks(idx)}')
        print('Input cards space separated (e.g. "AS AH")')
        print('To wait, simply press enter.')
        attack = None
        while attack not in game_state.legal_attacks(idx):
            request = input('What card(s) to play? ').upper().split(' ')
            if request == ['']:
                return None
            attack = sorted(card for card in game_state.hands[idx] if str(card) in request)
        return attack

    def decide_defense(self, game_state):
        print('           DEFENSE')
        print(f'  Play Field: {game_state.field}')
        print(f'Current Hand: {game_state.hands[game_state.defender()]}')
        print(f' Legal Plays: {game_state.legal_defenses()}')
        print('Input attack card and then defense card (e.g. "6C TC 8H AH")')
        print('To pass it on, type play or show and then the cards you want to use')
        print('To wait, simply press enter. To take, type "take"')
        while True:
            request = input('What card(s) to play? ').upper().split(' ')
            if request == ['']:
                return None
            if request == ['TAKE']:
                return 'take'
            if request[0] == 'SHOW' and len(request) == 2:
                for card in game_state.hands[game_state.defender()]:
                    if ('show', card) in game_state.legal_defenses() and card == request[1]:
                        return 'show', card
            if request[0] == 'PLAY':
                for defense in game_state.legal_defenses():
                    if defense:
                        ld = list(defense)
                        if ld[0] == 'play' and len(ld[1]) == len(request[1:]):
                            for card in ld[1]:
                                if str(card) not in request:
                                    break
                            else:
                                return defense
            if len(request) % 2 == 0:
                pairs = [(request[i], request[i+1]) for i in range(0, len(request), 2)]
                cards = []
                for a in game_state.field:
                    for d in game_state.hands[game_state.defender()]:
                        if (str(a), str(d)) in pairs:
                            cards.append((a, d))
                if len(pairs) == len(cards):
                    return cards

    def decide_pickup(self, game_state):
        print('           PICKUP')
        print(f'  Play Field: {game_state.field}')
        print(f'Current Hand: {game_state.hands[game_state.defender()]}')
        print(f' Legal Picks: {game_state.legal_pickup()}')
        print('All beaten cards are automatically picked up')
        print('List unbeaten cards to pick up (e.g. "6C TC")')
        while True:
            request = input('What card(s) to pick up? ').upper().split(' ')
            if len(request) == len(game_state.legal_pickup()[0]):
                for pickup in game_state.legal_pickup():
                    for card in pickup:
                        if str(card) not in request:
                            break
                    else:
                        return pickup

class GameController:
    def __init__(self, *players: list[Player]):
        self.game_state = GameState(len(players))
        self.phase = None
        self.players = players
        self.special_state = None
        self.turns_since_action = 0

    def play_game(self):
        self.game_state.reset()
        while self.game_state.durak is None:
            self.phase = 0 # Initial attack
            attacker = self.game_state.primary_attacker
            defender = self.game_state.defender()
            if attacker == defender:
                self.game_state.durak = attacker
                break
            print(f'{self.game_state.hands}')
            self.handle_attack(attacker)
            self.turns_since_action = 0
            while self.turns_since_action < 5:
                self.phase = 1 # Defense
                defended = self.handle_defense()
                if defended == 'pass':
                    defender = self.game_state.next_after(self.game_state.defender())
                    print(self.game_state.defender())
                    self.turns_since_action = 0
                else:
                    if defended:
                        if not self.game_state.hands[defender] or defended == 'take':
                            break
                        self.turns_since_action = 0
                    self.phase = 2 # Additional attacks
                    p = self.game_state.next_after(defender)
                    attacked = False
                    for _ in range(len(self.game_state.hands)-len(self.game_state.out) - 1):
                        attacked = self.handle_attack(p) or attacked
                        p = self.game_state.next_after(p)
                    if attacked:
                        self.turns_since_action = 0
                    if not attacked and not defended:
                        self.turns_since_action += 1

            discard_cap = 6 if self.game_state.discard else 5
            defense_cap = min(discard_cap - sum(1 for _, d in
                                                self.game_state.field.items() if d is not None), \
                            sum(1 for _, d in self.game_state.field.items() if d is None))

            if not self.game_state.hands[defender] or defense_cap == 0:
                print(self.game_state.field)
                self.game_state.beat()
                self.special_state = 'beat'
            else:
                self.phase = 3 # In chase
                p = self.game_state.next_after(defender)
                for _ in range(len(self.game_state.hands)-len(self.game_state.out) - 1):
                    self.handle_attack(p)
                    p = self.game_state.next_after(p)
                print(self.game_state.field)
                self.game_state.surrender(self.handle_pickup())
                self.special_state = 'surrender'
        print(f'durak is {self.players[self.game_state.durak].name}')

    def handle_attack(self, idx):
        attack = self.players[idx].decide_attack(self.game_state, idx)
        if attack is None:
            return False
        self.game_state.attack(idx, attack)
        return True

    def handle_defense(self):
        defense = self.players[self.game_state.defender()].decide_defense(self.game_state)
        if defense is None:
            return False
        if defense == 'take':
            return 'take'
        if isinstance(defense, tuple):
            m, c = defense
            if m == 'show':
                self.game_state.pass_it_on(m, c)
            elif m == 'play':
                for card in c:
                    self.game_state.pass_it_on(m, card)
            return 'pass'
        for a, d in defense:
            self.game_state.defend(a, d)
        return True

    def handle_pickup(self):
        return self.players[self.game_state.defender()].decide_pickup(self.game_state)

    def get_state(self, idx):
        hands = self.game_state.hands
        hands = hands[idx:] + hands[:idx] # rotate hands such that own index is 0
        def adjusted_index(i):
            return (i-idx) % len(hands)

        unknown_cards = self.game_state.deck.cards[1:]
        for hand in hands[1:]:
            for card in hand:
                if not card.revealed:
                    unknown_cards.append(card)
        match self.special_state:
            case 'surrender':
                sp = 0
            case 'beat':
                sp = 1
            case _:
                sp = None
        self.special_state = None
        state = {
            'own_cards': [c.tuple() for c in hands[0]],
            'field_cards': [((a.tuple(), adjusted_index(self.game_state.deck.revealed[a])),
                             None if d is None else (d.tuple(), adjusted_index(
                                                                self.game_state.deck.revealed[d]
                                                                )))
                            for a, d in self.game_state.field.items()],
            'opponent_cards': [[c.tuple() if c.revealed else None for c in h] for h in hands[1:]],
            'discarded_cards': [c.tuple() for c in self.game_state.discard],
            'trump_card': self.game_state.trump.tuple() if self.game_state.deck.has_cards() \
                          else None,
            'unknown_cards': [c.tuple() for c in unknown_cards],
            'defender_index': adjusted_index(self.game_state.defender()),
            'phase': self.phase, # 0: inital attack, 1: defense, 2: additional attack, 
                                 # 3: in chase, 4: picking up
            'turns_since_action': self.turns_since_action, # always <5
            'special_action': sp
        }
        return state

if __name__ == '__main__':
    gc = GameController(BotPlayer('Bot0'), BotPlayer('Bot1'))
    for _ in range(10000):
        gc.play_game()
