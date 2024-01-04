from __future__ import annotations
from itertools import chain

import utility
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

    def player_superset(self):
        """Gets all players from all matchups from all teams from all members in a league"""
        return set(chain.from_iterable((member.player_superset() for member in self.members)))

    def matchup_superset(self):
        """Gets all matchups from all teams from all members in a league"""
        return set(chain.from_iterable((member.matchup_superset() for member in self.members)))

    def team_superset(self):
        """Gets all teams from all members in a league"""
        return set(chain.from_iterable((member.teams for member in self.members)))

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
    points_against: int
    points_for: int
    team: Team
    type: GameType
    week: int

    def __init__(self, opponent, outcome, points_against, points_for, team, game_type, week):
        self.lineup = set()
        self.opponent = opponent
        self.outcome = outcome
        self.points_against = points_against
        self.points_for = points_for
        self.team = team
        self.type = game_type
        self.week = week

    def add_player(self, player):
        """Add a player to the matchup's lineup"""
        self.lineup.add(player)

    def same(self, other):
        """Basically Matchup.__eq__ but without overriding so Matchup.__hash__ remains untouched"""
        if isinstance(other, Matchup):
            me = hash(f"{self.team.name} vs {self.opponent.name} week {self.week}")
            it = hash(f"{other.team.name} vs {other.opponent.name} week {other.week}")
            return me == it
        return False


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

    def matchup_superset(self):
        """Gets all matchups from all teams for a member"""
        return set(chain.from_iterable((team.matchups for team in self.teams)))

    def player_superset(self):
        """Gets all players from all matchups from all teams for a member"""
        return set(chain.from_iterable((team.player_superset() for team in self.teams)))

    def update_joined_year(self, year):
        """Set the member's joined year to be the smaller of the current joined year and the year given"""
        self.joined_year = min(self.joined_year, year)

    def update_left_year(self, year):
        """Set the member's left year to be the larger of the current left year and the year given"""
        self.left_year = max(self.left_year, year)


class Player:
    id: int
    name: str
    points: int
    position: PlayerPosition

    def __init__(self, espn_id, name, points, position):
        self.id = espn_id
        self.name = name
        self.points = round(points, ndigits=2)
        self.position = PlayerPosition(position)


class Team:
    division: int
    id: int
    espn_id: int
    losses: int
    name: str
    matchups: set[Matchup]
    member: Member
    ties: int
    wins: int
    year: int

    def __init__(self, division, espn_id, name, member, year):
        self.division = division
        self.id = utility.generate_team_id(espn_id, year)
        self.espn_id = espn_id
        self.name = name
        self.matchups = set()
        self.member = member
        self.year = year

    def add_matchup(self, matchup):
        """Adds a matchup to the team"""
        self.matchups.add(matchup)

    def player_superset(self):
        """Gets all players from all matchups in a team"""
        return set(chain.from_iterable((matchup.lineup for matchup in self.matchups)))

    def update_losses(self, losses):
        """Set the team's losses"""
        self.losses = losses

    def update_ties(self, ties):
        """Set the team's ties"""
        self.ties = ties

    def update_wins(self, wins):
        """Set the team's wins"""
        self.wins = wins
