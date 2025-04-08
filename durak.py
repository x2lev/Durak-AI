from dataclasses import dataclass
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

    def __repr__(self):
        return f"{self.rank}{self.suit}"

@dataclass
class Deck:
    cards: list[Card] = []
    trump: str = ''

    def __post_init__(self):
        self.cards = [Card(rank, suit) for suit in Card.suits for rank in Card.ranks]
        random.shuffle(self.cards)

    def choose_trump(self):
        trump_card = self.cards.pop()
        self.trump = trump_card.suit
        self.cards.insert(0, trump_card)

    def pop(self):
        return self.cards.pop()

    def has_cards(self):
        return len(self.cards) > 0

    def shown_trump(self):
        if self.cards:
            return self.cards[0]

class GameState:
    def __init__(self, number_of_players):
        self.number_of_players = number_of_players
        self.reset()

    def reset(self):
        self.deck = Deck()
        self.deck.choose_trump()
        self.trump = self.deck.trump

        self.primary_attacker = random.randrange(self.number_of_players)
        self.field = {}
        self.done = False
        self.winner = None

        self.hands = [[] for _ in range(self.number_of_players)]
        for _ in range(6):
            for i, _ in enumerate(self.hands):
                self.hands[i].append(self.deck.pop())

    def next_after(self, player_idx):
        return (player_idx + 1) % self.number_of_players

    def legal_attack_combinations(self, player_idx):
        if player_idx == self.next_after(self.primary_attacker):
            return []

        legal_cards = []

        if not self.field:
            legal_cards = self.hands[player_idx].copy()
        else:
            existing_ranks = {c.rank for c in self.field} | \
                             {c.rank for c in self.field.values() if c}
            legal_cards = [card for card in self.hands[player_idx] if card.rank in existing_ranks]

        combinations = []

        combinations.extend([card] for card in legal_cards)

        rank_groups = {}
        for card in legal_cards:
            if card.rank not in rank_groups:
                rank_groups[card.rank] = []
            rank_groups[card.rank].append(card)

        # Add combinations of 2+ cards of the same rank
        for rank, cards in rank_groups.items():
            if len(cards) >= 2:
                for i in range(2, len(cards) + 1):
                    for combo in itertools.combinations(cards, i):
                        combinations.append(list(combo))

        return combinations

    def legal_defenses(self):
        legal = []
        for attack_card, defense_card in self.field.items():
            if defense_card is None:
                for card in self.hands[self.defender]:
                    if self.can_beat(attack_card, card):
                        legal.append((attack_card, card))
        return legal

    def can_beat(self, attack, defense):
        if defense.suit == attack.suit:
            return Card.ranks.index(defense.rank) > Card.ranks.index(attack.rank)
        return defense.suit == self.trump and attack.suit != self.trump

    def initial_attack(self, card):
        ...
    
    def step_attack(self, card):
        if card in self.hands[self.attacker] and (not self.field or card.rank in [c.rank for c in self.field] + [c.rank for c in self.field.values() if c]):
            self.field[card] = None
            self.hands[self.attacker].remove(card)
            return True
        return False

    def step_defend(self, attack_card, defense_card):
        if (
            attack_card in self.field
            and self.field[attack_card] is None
            and defense_card in self.hands[self.defender]
            and self.can_beat(attack_card, defense_card)
        ):
            self.field[attack_card] = defense_card
            self.hands[self.defender].remove(defense_card)
            return True
        return False

    def end_turn(self, success):
        # success = True if all attacks were defended
        if not success:
            # defender picks up all cards
            for attack, defense in self.field.items():
                self.hands[self.defender].append(attack)
                if defense:
                    self.hands[self.defender].append(defense)
        # refill hands to 6
        for i in [self.attacker, self.defender]:
            while len(self.hands[i]) < 6 and self.deck.has_cards():
                self.hands[i].append(self.deck.pop())

        # rotate attacker/defender
        if success:
            self.attacker = self.attacker
            self.defender = 1 - self.attacker
        else:
            self.attacker = 1 - self.attacker
            self.defender = 1 - self.attacker

        self.field.clear()
        self.check_winner()

    def check_winner(self):
        for i, hand in enumerate(self.hands):
            if not hand and not self.deck.has_cards():
                self.done = True
                self.winner = 1 - i  # last player to run out loses

    def get_observation(self, player_idx):
        return {
            'hand': self.hands[player_idx],
            'opponent_hand_size': len(self.hands[1 - player_idx]),
            'field': self.field.copy(),
            'trump': self.trump,
            'deck_size': len(self.deck.cards),
            'is_attacker': player_idx == self.attacker
        }

    def get_legal_actions(self, player_idx):
        if player_idx == self.attacker:
            return self.legal_attacks()
        else:
            return self.legal_defenses()


if __name__ == '__main__':
    _deck = Deck()
    _player.draw_to_six()
    _deck.choose_trump()
    _player.attacker()
