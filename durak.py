from dataclasses import dataclass, field
import itertools
import random

@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    ranks = ['6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    suits = ['S', 'C', 'H', 'D']

    def __post_init__(self):
        if self.rank not in Card.ranks or self.suit not in Card.suits:
            raise ValueError(f"Invalid card: {self}")

    def __lt__(self, other):
        if Card.suits.index(self.suit) == Card.suits.index(other.suit):
            return Card.ranks.index(self.rank) < Card.ranks.index(other.rank)
        return Card.suits.index(self.suit) < Card.suits.index(other.suit)

    def __repr__(self):
        return f"{self.rank}{self.suit}"

@dataclass
class Deck:
    cards: list[Card] = field(default_factory=list)
    trump: Card = None

    def __post_init__(self):
        self.cards = [Card(rank, suit) for suit in Card.suits for rank in Card.ranks]
        random.shuffle(self.cards)

    def choose_trump(self):
        self.trump = self.cards.pop()
        self.cards.insert(0, self.trump)
        print(self.trump)

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

        discard_cap = min(6 if self.discard else 5, len(self.hands[self.defender()]))
        capped_combos = [c for c in combinations if len(c)+len(self.field) <= discard_cap]

        if self.field:
            capped_combos.append([None])

        return capped_combos

    def legal_defenses(self):
        '''
        pass_it_on = []
        if self.field and not self.field.values():
            rank = list(self.field.keys())[0].rank
            cards = [c for c in self.hands[self.defender()] if c.rank == rank]
            passable = [itertools.combinations(cards, r) for r in range(len(cards))]
            pass_it_on = []
            for combo in passable:
                pass_it_on.append([])
                for card in combo:
                    pass_it_on[-1].append(('pass', card))
            for card in cards:
                if card.suit == self.trump.suit:
                    pass_it_on[-1].append(('hold', card))
                    break'''

        if self.durak is not None:
            return [[(None, None)]]

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

        unique_combos.append([(None, None)])
        
        return unique_combos + pass_it_on

    def can_beat(self, attack, defense):
        if defense.suit == attack.suit:
            return Card.ranks.index(defense.rank) > Card.ranks.index(attack.rank)
        return defense.suit == self.trump.suit and attack.suit != self.trump.suit

    def attack(self, player_idx, cards):
        for card in cards:
            self.hands[player_idx].remove(card)
            self.field[card] = None
        print(f'those who attack with {cards}')
        if not self.deck.has_cards() and not self.hands[player_idx]:
            self.check_outs()
            print(self.durak)

    def defend(self, attack_card, defense_card):
        self.field[attack_card] = defense_card
        self.hands[self.defender()].remove(defense_card)

    def beat(self):
        for a, d in self.field.items():
            self.discard.append(a)
            self.discard.append(d)
        self.field.clear()

        self.draw_cards()
        self.check_outs()

        self.primary_attacker = self.next_after(self.primary_attacker)

    def surrender(self):
        for a, d in self.field.items():
            self.hands[self.defender()].append(a)
            if d:
                self.hands[self.defender()].append(d)
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

    def decide_attack(self, game_state, idx):
        return [None]

    def decide_defense(self, game_state):
        return (None, None)

class BotPlayer(Player):
    def decide_attack(self, game_state, idx):
        return random.choice(game_state.legal_attacks(idx))

    def decide_defense(self, game_state):
        return random.choice(game_state.legal_defenses())

class HumanPlayer(Player):
    def decide_attack(self, game_state, idx):
        print('           ATTACK')
        print(f'  Play Field: {game_state.field}')
        print(f'Current Hand: {game_state.hands[idx]}')
        print(f' Legal Plays: {game_state.legal_attacks(idx)}')
        print('Input cards space separated (e.g. "AS AH")')
        attack = None
        while attack not in game_state.legal_attacks(idx):
            request = input('What card(s) to play? ').upper().split(' ')
            if request == ['']:
                return [None]
            attack = sorted(card for card in game_state.hands[idx] if str(card) in request)
        return attack

    def decide_defense(self, game_state):
        print('           DEFENSE')
        print(f'  Play Field: {game_state.field}')
        print(f'Current Hand: {game_state.hands[game_state.defender()]}')
        print(f' Legal Plays: {game_state.legal_defenses()}')
        print('Input attack card and then defense card (e.g. "6C TC 8H AH")')
        while True:
            request = input('What card(s) to play? ').upper().split(' ')
            if request == ['']:
                return [(None, None)]
            if len(request) % 2 == 0:
                pairs = [(request[i], request[i+1]) for i in range(0, len(request), 2)]
                cards = []
                for a in game_state.field:
                    for d in game_state.hands[game_state.defender()]:
                        if (str(a), str(d)) in pairs:
                            cards.append((a, d))
                if len(pairs) == len(cards):
                    return cards

class GameController:
    def __init__(self, *players: list[Player]):
        self.game_state = GameState(len(players))
        self.phase = None
        self.players = players
        self.current_player = 0

    def play_game(self):
        self.game_state.reset()
        while self.game_state.durak is None:
            self.phase = 0 # Initial attack
            self.current_player = self.game_state.primary_attacker
            attacker = self.game_state.primary_attacker
            defender = self.game_state.defender()
            if attacker == defender:
                self.game_state.durak = attacker
                break
            print(f'{self.game_state.hands[attacker]}, {self.game_state.hands[defender]}')
            self.handle_attack(attacker)
            turns_since_defense = 0
            while turns_since_defense < 5:
                self.phase = 1 # Defense
                self.current_player = self.game_state.defender()
                if (defended := self.handle_defense()):
                    if not self.game_state.hands[defender]:
                        break
                    turns_since_defense = 0
                self.phase = 2 # Additional attacks
                p = self.game_state.next_after(defender)
                attacked = False
                for _ in range(len(self.game_state.hands)-len(self.game_state.out) - 1):
                    self.current_player = p
                    attacked = self.handle_attack(p) or attacked
                    p = self.game_state.next_after(p)
                self.phase = 1 # Defense
                if not attacked and not defended:
                    turns_since_defense += 1

            if None in self.game_state.field.values():
                self.phase = 4 # In chase
                p = self.game_state.next_after(defender)
                for _ in range(len(self.game_state.hands)-len(self.game_state.out) - 1):
                    self.current_player = p
                    self.handle_attack(p)
                    p = self.game_state.next_after(p)
                print(self.game_state.field)
                print(f'{self.players[self.game_state.defender()].name} surrendered')
                self.game_state.surrender()
            else:
                print(self.game_state.field)
                print(f'{self.players[self.game_state.defender()].name} is a beater')
                self.game_state.beat()
        print(f'durak is {self.players[self.game_state.durak].name}')

    def handle_attack(self, idx):
        attack = self.players[idx].decide_attack(self.game_state, idx)
        if attack == [None]:
            return False
        self.game_state.attack(idx, attack)
        return True

    def handle_defense(self):
        pairs = self.players[self.game_state.defender()].decide_defense(self.game_state)
        if pairs == [(None, None)]:
            return False
        for a, d in pairs:
            self.game_state.defend(a, d)
        return True
    
    def get_state(self, idx):
        state = {
            'hand': [str(c) for c in self.game_state.hands[idx]],
            'field': {str(a): str(d) for a, d in self.game_state.field.items()},
            'discard': [str(c) for c in self.game_state.discard],
            'trump': str(self.game_state.trump),
            'phase': self.phase, # 1, 2, 3, 4
            'defending': idx == self.game_state.defender(),
            'deck_size': len(self.game_state.deck.cards),
            'opp_sizes': [len(h) for h in self.game_state.hands]
        }
        return state

if __name__ == '__main__':
    gc = GameController(BotPlayer('Bot1'), BotPlayer('Bot2'))
    for _ in range(1000):
        gc.play_game()
