from dataclasses import dataclass, field
import itertools
import pickle
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
    trump: str = ''

    def __post_init__(self):
        self.cards = [Card(rank, suit) for suit in Card.suits for rank in Card.ranks]
        random.shuffle(self.cards)

    def choose_trump(self):
        trump_card = self.cards.pop()
        self.trump = trump_card.suit
        self.cards.insert(0, trump_card)
        print(trump_card)

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

    def reset(self):
        self.discard = []
        self.deck = Deck()
        self.deck.choose_trump()
        self.trump = self.deck.trump

        self.primary_attacker = random.randrange(self.number_of_players)
        self.field = {}
        self.out = []
        self.durak = None

        self.hands = [[] for _ in range(self.number_of_players)]
        for _ in range(6):
            for i, _ in enumerate(self.hands):
                self.hands[i].append(self.deck.pop())

    def next_after(self, player_idx):
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

        discard_cap = 6 if self.discard else 5
        capped_combos = [combo for combo in combinations if len(combo)+len(self.field) < discard_cap]

        if self.field:
            capped_combos.append([None])

        return capped_combos

    def legal_defenses(self):
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

        combinations.append([(None, None)])
        
        return combinations

    def can_beat(self, attack, defense):
        if defense.suit == attack.suit:
            return Card.ranks.index(defense.rank) > Card.ranks.index(attack.rank)
        return defense.suit == self.trump and attack.suit != self.trump

    def attack(self, player_idx, cards):
        for card in cards:
            self.hands[player_idx].remove(card)
            self.field[card] = None

    def defend(self, attack_card, defense_card):
        self.field[attack_card] = defense_card
        print(defense_card)
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
        draw_order = [self.primary_attacker]
        p = self.next_after(self.defender())
        while p !=  self.primary_attacker:
            draw_order.append(p)
            p = self.next_after(p)
        draw_order.append(self.defender())

        for p in draw_order:
            while self.deck.has_cards() and len(self.hands[p]) < 6:
                self.hands[p].append(self.deck.pop())
            if not self.deck.has_cards():
                break

    def check_outs(self):
        self.outs = []
        for i, hand in enumerate(self.hands):
            if not hand and not self.deck.has_cards():
                self.out.append(i)
        ins = list(set(i for i in range(self.number_of_players)) - set(self.outs))
        if len(ins) == 1:
            self.durak = ins[0]

class Player:
    def __init__(self, name):
        self.name = name

    def decide_attack(self, game_state, idx):
        return [None]

    def decide_defense(self, game_state):
        return (None, None)

class BotPlayer(Player):
    def decide_attack(self, game_state, idx):
        c = random.choice(game_state.legal_attacks(idx))
        return c

    def decide_defense(self, game_state):
        c = random.choice(game_state.legal_defenses())
        return c

class HumanPlayer(Player):
    def decide_attack(self, game_state, idx):
        assert 1 == 0
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
        self.players = players

    def play_game(self):
        self.game_state.reset()
        while self.game_state.durak is None:
            attacker = self.game_state.primary_attacker
            defender = self.game_state.defender()
            self.handle_attack(attacker)

            turns_since_defense = 0
            while turns_since_defense < 5:
                if (defended := self.handle_defense()):
                    turns_since_defense = 0
                p = self.game_state.next_after(defender)
                attacked = False
                for _ in range(len(self.game_state.hands)-len(self.game_state.out) - 1):
                    attacked = attacked or self.handle_attack(p)
                    p = self.game_state.next_after(p)
                if not attacked and not defended:
                    turns_since_defense += 1

            if None in self.game_state.field.values():
                p = self.game_state.next_after(defender)
                for _ in range(len(self.game_state.hands)-len(self.game_state.out) - 1):
                    self.handle_attack(p)
                    p = self.game_state.next_after(p)
                self.game_state.surrender()
            else:
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

if __name__ == '__main__':
    if input('use seed? ').lower() in ['yes', 'y']:
        print('loading seed...')
        with open('seed', 'rb') as f:
            random.setstate(pickle.loads(f))

    try:
        gc = GameController(HumanPlayer('Lev'), BotPlayer('Bot'))
        gc.play_game()
    except Exception as e:
        print(e)

    if input('save seed? ').lower() in ['yes', 'y']:
        print('dumping seed...')
        with open('seed', 'wb') as f:
            pickle.dumps(f, random.getstate())
