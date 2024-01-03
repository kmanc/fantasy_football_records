from __future__ import annotations
from new_fantasy_enums import GameType, GameOutcome, PlayerPosition


class FantasyLeague:
    active_year: int
    espn_s2: str
    espn_swid: str
    founded_year: int
    id: int
    members: set[Member]
    name: str
    max_completed_year: int

    def __init__(self, espn_s2, espn_swid, founded_year, league_id):
        self.active_year = 0
        self.espn_s2 = espn_s2
        self.espn_swid = espn_swid
        self.founded_year = founded_year
        self.id = league_id
        self.max_completed_year = 0
        self.members = set()
        self.name = ""

    def add_member(self, member):
        """Add a new member to the league"""
        self.members.add(member)

    def update_active_year(self, year):
        """Set the league's active year to be the larger of the current active year and the year given"""
        self.active_year = max(self.active_year, year)

    def update_max_completed_year(self, year):
        """Set the league's max completed year to be the larger of the current max completed year and the year given"""
        self.max_completed_year = max(self.max_completed_year, year)

    def update_name(self, name):
        """Set the league's name to the given string"""
        self.name = name


class Matchup:
    outcome: GameOutcome
    roster: set[Player]
    team: Team
    type: GameType
    week: int

    def __init__(self, team):
        self.team = team


class Member:
    id: str
    joined_year: int
    league: FantasyLeague
    left_year: int
    name: str
    teams: dict[int, Team]

    def __init__(self, league, member_id, name):
        self.id = member_id
        self.joined_year = 99999
        self.league = league
        self.left_year = 0
        self.name = name
        self.teams = dict()

    def same(self, other):
        """Basically Member.__eq__ but without overriding so Member.__hash__ remains untouched"""
        if isinstance(other, Member):
            return self.id == other.id and self.name == other.name
        return False

    def update_joined_year(self, year):
        """Set the member's joined year to be the smaller of the current joined year and the year given"""
        self.joined_year = min(self.joined_year, year)

    def update_left_year(self, year):
        """Set the member's left year to be the larger of the current left year and the year given"""
        self.left_year = max(self.left_year, year)


class Player:
    name: str
    points: int
    position: PlayerPosition

    def __init__(self, name, points, position):
        self.name = name
        self.points = points
        self.position = position


class Team:
    id: int
    name: str
    matchups: set[Matchup]
    member: Member

    def __init__(self, name, member):
        self.name = name
        self.member = member
