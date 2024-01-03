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
    lineup: set[Player]
    opponent: Team
    outcome: GameOutcome
    team: Team
    type: GameType
    week: int

    def __init__(self, opponent, outcome, team, game_type, week):
        self.opponent = opponent
        self.outcome = outcome
        self.team = team
        self.type = game_type
        self.week = week

    def add_player(self, player):
        """Add a player to the matchup's lineup"""
        self.lineup.add(player)


class Member:
    id: str
    joined_year: int
    league: FantasyLeague
    left_year: int
    name: str
    teams: set[Team]

    def __init__(self, league, member_id, name):
        self.id = member_id
        self.joined_year = 99999
        self.league = league
        self.left_year = 0
        self.name = name
        self.teams = set()

    def add_team(self, team):
        """Add a new team to the member"""
        self.teams.add(team)

    def same(self, other):
        """Basically Member.__eq__ but without overriding so Member.__hash__ remains untouched"""
        if isinstance(other, Member):
            return self.id == other.id
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
    division: int
    id: int
    losses: int
    name: str
    matchups: set[Matchup]
    member: Member
    ties: int
    wins: int
    year: int

    def __init__(self, division, team_id, name, member, year):
        self.division = division
        self.id = team_id
        self.name = name
        self.member = member
        self.year = year

    def add_matchup(self, matchup):
        """Adds a matchup to the team"""
        self.matchups.add(matchup)

    def update_losses(self, losses):
        """Set the team's losses"""
        self.losses = losses

    def update_ties(self, ties):
        """Set the team's ties"""
        self.ties = ties

    def update_wins(self, wins):
        """Set the team's wins"""
        self.wins = wins
