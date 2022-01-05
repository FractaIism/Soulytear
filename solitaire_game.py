import logging
import random
from dataclasses import dataclass
from collections import deque

from config import DEBUG

class icons:
    SPADE = "♠"
    HEART = "♥"
    DIAMOND = "♦"
    CLUB = "♣"
    CARD = "🂠"
    BLING = "✨"

suits = [icons.CLUB, icons.DIAMOND, icons.HEART, icons.SPADE]

@dataclass
class Card:
    suit: int
    rank: int
    visible: bool = False if not DEBUG else True

    def __str__(self):
        return f"{suits[self.suit]}{self.rank}" if self.visible else "*"

class InvalidMoveError(Exception):
    pass

@dataclass
class Game:
    """
        ♣(0):
        ♦(1):
        ♥(2):
        ♠(3):
        🂠(4):
        row0(5):♣1
        row1(6):♦1 *
        row2(7):♠1 * *
        row3(8):♥2 * * *
        row4(9):♥3 * * * *
        row5(10):♠4 * * * * *
        row6(11):♦6 * * * * * *
    """
    rows: list[deque[Card]]

    def __init__(self):
        # initialize empty rows
        self.rows = [deque() for _ in range(12)]
        # get shuffled deck
        shuffled_deck = Game.get_shuffled_deck(52)
        # assign shuffled cards to each row
        self.rows[5] = deque(shuffled_deck[0:1])
        self.rows[6] = deque(shuffled_deck[1:3])
        self.rows[7] = deque(shuffled_deck[3:6])
        self.rows[8] = deque(shuffled_deck[6:10])
        self.rows[9] = deque(shuffled_deck[10:15])
        self.rows[10] = deque(shuffled_deck[15:21])
        self.rows[11] = deque(shuffled_deck[21:28])
        self.rows[4] = deque(shuffled_deck[28:])
        # flip up first card in rows 0~6
        for i in range(4, 12):
            self.rows[i][0].visible = True

    def __str__(self):
        row2str = lambda row: " ".join([str(card) for card in self.rows[row]])
        game_str = "\n".join([
            f"{icons.CLUB}(0): " + row2str(0),
            f"{icons.DIAMOND}(1): " + row2str(1),
            f"{icons.HEART}(2): " + row2str(2),
            f"{icons.SPADE}(3): " + row2str(3),
            f"  {icons.CARD}  (4): " + row2str(4),
            ])
        for i in range(5, 12):
            game_str += f"\nrow{i-5}({i}): " + row2str(i)
        return game_str

    @staticmethod
    def get_shuffled_deck(n: int = 52) -> list[Card]:
        """ Get a list of shuffled cards. """
        # generate random numbers
        rand_nums = list(range(0, n))
        random.shuffle(rand_nums)
        # function to convert int to Card
        convert_func = lambda n: Card(int(n/13), n%13+1)
        # generate requested card set and remainder card set
        cards = list(map(convert_func, rand_nums))
        return cards

    def draw_card(self) -> None:
        """ Draw a card (rotate deck left). """
        deck = self.rows[4]
        if len(deck) >= 2:
            deck.rotate(-1)
            deck[0].visible = True
            deck[-1].visible = False if not DEBUG else True

    def move_card(self, from_row: int, to_row: int, card_idx: int) -> None:
        """ Move card at <card_idx> and all cards before it from <from_row> to beginning of <to_row>. """
        # first check if move is valid
        self.check_move_valid(from_row, to_row, card_idx)
        # alias relevant rows for ease of access
        src_row = self.rows[from_row]
        dst_row = self.rows[to_row]
        # number of cards to move
        num_cards = card_idx + 1
        # move cards
        src_row.rotate(-num_cards)
        for i in range(0, num_cards):
            card = src_row.pop()
            dst_row.appendleft(card)
        # turn next card in src_row face up
        if len(src_row) > 0:
            src_row[0].visible = True

    def check_move_valid(self, from_row: int, to_row: int, card_idx: int) -> bool:
        """
            Check if a move is valid. Raise exception if move is invalid.
            NOTE: THE ORDER OF THESE CHECKS MATTERS!
        """
        # check if from and to rows are valid
        if not 0 <= from_row <= 11:
            raise InvalidMoveError(f"from_row out of bounds. (0 <= row <= 11)")
        if not 0 <= to_row <= 11:
            raise InvalidMoveError(f"to_row out of bounds. (0 <= row <= 11)")
        # reference to the relevant rows
        src_row: deque[Card] = self.rows[from_row]
        dst_row: deque[Card] = self.rows[to_row]
        # check if card exists in row
        if card_idx > (max_idx := len(src_row) - 1):
            raise InvalidMoveError(f"Card index out of bounds. Max index for row {from_row} is {max_idx}.")
        else:
            card = src_row[card_idx]
        # check if card at card_idx is face up
        if not card.visible:
            raise InvalidMoveError("Selected card is not visible.")
        # check if card is being placed into the same row
        if from_row == to_row:
            raise InvalidMoveError("Cannot move cards to the same row.")
        # check if card is being misplaced into deck
        if to_row == 4:
            raise InvalidMoveError("Cards cannot be moved into deck.")
        # check if any card in card chain is being misplaced into an answer row
        if to_row in [0, 1, 2, 3]:
            if card_idx > 0:
                raise InvalidMoveError(f"Cannot move more than one card at a time into {''.join(suits)} rows.")
            elif card.suit != to_row:
                raise InvalidMoveError(f"Cannot place {card} into {suits[to_row]} row.")
            elif len(dst_row) == 0:
                if card.rank < 13:
                    raise InvalidMoveError(f"Cards with rank 13 must be placed first into {''.join(suits)} rows.")
                elif card.rank == 13:
                    return True
            elif card.rank + 1 != dst_row[0].rank:
                raise InvalidMoveError(f"Non-consecutive cards {card} {dst_row[0]}. (Expecting {Card(to_row, dst_row[0].rank - 1, True)})")
            else:
                logging.info("Check passed: suit row valid move.")
                return True
        # if dst_row is empty, you can always move cards there
        if len(dst_row) == 0:
            logging.info("Check passed: dst_row is empty.")
            return True
        # check if cards are consecutive after move
        if card.rank != dst_row[0].rank + 1:
            raise InvalidMoveError(f"Non-consecutive cards {card} {dst_row[0]}.")
        # otherwise the move is considered valid
        logging.info("Check passed: default.")
        return True

    def check_game_over(self) -> bool:
        """ Check if victory condition has been fulfilled. """
        return sum([len(row) for row in self.rows[0:4]]) >= 52

    def cheat(self) -> None:
        """ Fill all suit rows to test game termination. """
        for suit in [0, 1, 2, 3]:
            for i in range(13, 0, -1):
                card = Card(suit=suit, rank=i, visible=True)
                self.rows[suit].appendleft(card)

if __name__ == '__main__':
    game = Game()
    print(game)
