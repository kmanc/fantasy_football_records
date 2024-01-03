from enum import Enum, IntEnum, auto


class GameOutcome(Enum):
    WIN = auto()
    LOSS = auto()
    TIE = auto()

    def __repr__(self):
        return self.name


class GameType(Enum):
    REGULAR_SEASON = auto()
    PLAYOFF = auto()

    def __repr__(self):
        return self.name


class PlayerPosition(IntEnum):
    QB = 0
    RB = 2
    WR = 4
    TE = 6
    FLEX = 23
    DEFENSE = 16
    KICKER = 17
    BENCH = 20
    IR = 21

    def __repr__(self):
        return self.name
