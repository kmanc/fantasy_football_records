from __future__ import annotations
import itertools

import utility
from fantasy_enums import GameType, GameOutcome, PlayerPosition


class FantasyLeague:
    active_year: int
    active_year_playoff_slots: int
    active_year_regular_season_length: int
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
        self.playoff_team_size = 0

    def add_member(self, member):
        """Add a new member to the league"""
        self.members.add(member)

    def player_superset(self):
        """Gets all players from all matchups from all teams from all members in a league"""
        return set(itertools.chain.from_iterable((member.player_superset() for member in self.members)))

    def members_with_championship(self):
        """Returns members who have won a championship"""
        return (member for member in self.members if member.championship_wins())

    def members_with_playoff_appearances(self):
        """Returns members who have made the playoffs at least once"""
        return (member for member in self.members if member.playoff_appearances())

    def matchup_superset(self):
        """Gets all matchups from all teams from all members in a league"""
        return set(itertools.chain.from_iterable((member.matchup_superset() for member in self.members)))

    def matchups_by_points_for(self):
        """Sorts all matchups by points scored"""
        return sorted(self.matchup_superset(), key=lambda matchup: matchup.points_for, reverse=True)

    def team_superset(self):
        """Gets all teams from all members in a league"""
        return set(itertools.chain.from_iterable((member.teams for member in self.members)))

    def teams_in_active_year(self):
        """Gets all teams for the active year"""
        return set(team for team in self.team_superset() if team.year == self.active_year)

    def teams_by_regular_season_points_against(self, exclude_current=False):
        """Sorts all teams in league by points_against"""
        if exclude_current:
            return sorted([team for team in self.team_superset() if team not in self.teams_in_active_year()], key=lambda team: team.regular_season_points_against(), reverse=True)
        return sorted(self.team_superset(), key=lambda team: team.regular_season_points_against(), reverse=True)

    def teams_by_regular_season_points_for(self, exclude_current=False):
        """Sorts all teams in league by points_for"""
        if exclude_current:
            return sorted([team for team in self.team_superset() if team not in self.teams_in_active_year()], key=lambda team: team.regular_season_points_scored(), reverse=True)
        return sorted(self.team_superset(), key=lambda team: team.regular_season_points_scored(), reverse=True)

    def update_active_year(self, year):
        """Set the league's active year to be the larger of the current active year and the year given"""
        self.active_year = max(self.active_year, year)

    def update_max_completed_year(self, year):
        """Set the league's max completed year to be the larger of the current max completed year and the year given"""
        self.max_completed_year = max(self.max_completed_year, year)

    def update_name(self, name):
        """Set the league's name to the given string"""
        self.name = name

    def update_active_year_playoff_slots(self, size):
        """Set the league's playoff team size to the given integer"""
        self.active_year_playoff_slots = size

    def update_active_year_regular_season_length(self, size):
        """Set the league's regular season length to the given integer"""
        self.active_year_regular_season_length = size


class Matchup:
    id: int
    lineup: set[Player]
    opponent: Team
    outcome: GameOutcome
    points_against: int
    points_for: int
    team: Team
    type: GameType
    week: int

    def __init__(self, opponent, outcome, points_against, points_for, team, game_type, week):
        self.id = utility.generate_matchup_id(team.id, opponent.id, week)
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
            return self.id == other.id
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

    def championship_wins(self):
        """Calculates the number of championship wins for a member"""
        return len(list(team for team in self.teams if team.won_championship()))

    def same(self, other):
        """Basically Member.__eq__ but without overriding so Member.__hash__ remains untouched"""
        if isinstance(other, Member):
            return self.id == other.id
        return False

    def matchup_superset(self):
        """Gets all matchups from all teams for a member"""
        return set(itertools.chain.from_iterable((team.matchups for team in self.teams)))

    def player_superset(self):
        """Gets all players from all matchups from all teams for a member"""
        return set(itertools.chain.from_iterable((team.player_superset() for team in self.teams)))

    def playoff_appearances(self):
        """Calculates the playoff appearances for a member"""
        return len([team for team in self.teams if team.made_playoffs()])

    def playoff_average_points(self):
        """Calculates the average points scored per playoff game for a member"""
        return round(self.playoff_points() / len(list(self.playoff_matchups())), 2)

    def playoff_matchups(self):
        """Gets all playoff matchups for a member"""
        return (matchup for matchup in self.matchup_superset() if matchup.type == GameType.PLAYOFF)

    def playoff_points(self):
        """Calculates the all-time playoff points for a member"""
        return round(sum(matchup.points_for for matchup in self.playoff_matchups()), 2)

    def playoff_win_percentage(self):
        """Calculates the playoff win percentage for a member"""
        return round(self.playoff_wins() * 100 / len(list(self.playoff_matchups())), 2)

    def playoff_wins(self):
        """Calculates the number of playoff wins for a member"""
        return len(list(matchup for matchup in self.playoff_matchups() if matchup.outcome == GameOutcome.WIN))

    def regular_season_average_points(self):
        """Calculates the average points scored per regular season game for a member"""
        return round(self.regular_season_points() / len(list(self.regular_season_matchups())), 2)

    def regular_season_matchups(self):
        """Gets all regular season matchups for a member"""
        return (matchup for matchup in self.matchup_superset() if matchup.type == GameType.REGULAR_SEASON)

    def regular_season_points(self):
        """Calculates the all-time regular season points for a member"""
        return round(sum(matchup.points_for for matchup in self.regular_season_matchups()), 2)

    def regular_season_win_percentage(self):
        """Calculates the regular season win percentage for a member"""
        try:
            return round(self.regular_season_wins() * 100 / len(list(self.regular_season_matchups())), 2)
        except ZeroDivisionError:
            return 0

    def regular_season_wins(self):
        """Calculates the number of regular season wins for a member"""
        return len(list(matchup for matchup in self.regular_season_matchups() if matchup.outcome == GameOutcome.WIN))

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
    name: str
    matchups: set[Matchup]
    member: Member
    schedule: list[int]
    regular_season_losses: int
    regular_season_ties: int
    regular_season_wins: int
    year: int

    def __init__(self, division, espn_id, name, member, schedule, year):
        self.division = division
        self.id = utility.generate_team_id(espn_id, year)
        self.espn_id = espn_id
        self.name = name
        self.matchups = set()
        self.member = member
        self.schedule = schedule
        self.year = year

    def add_matchup(self, matchup):
        """Adds a matchup to the team"""
        self.matchups.add(matchup)

    def made_playoffs(self):
        """Returns a boolean representing whether the team made the playoffs"""
        return any(matchup.type == GameType.PLAYOFF for matchup in self.matchups)

    def player_superset(self):
        """Gets all players from all matchups in a team"""
        return set(itertools.chain.from_iterable((matchup.lineup for matchup in self.matchups)))

    def playoff_points_scored(self):
        """Calculates the playoff points scored for a team"""
        return round(sum(matchup.points_for for matchup in self.matchups if matchup.type == GameType.PLAYOFF), 2)

    def regular_season_points_against(self):
        """Calculates the regular season points scored for a team"""
        return round(sum(matchup.points_against for matchup in self.matchups if matchup.type == GameType.REGULAR_SEASON), 2)

    def regular_season_points_scored(self):
        """Calculates the regular season points scored for a team"""
        return round(sum(matchup.points_for for matchup in self.matchups if matchup.type == GameType.REGULAR_SEASON), 2)

    def update_regular_season_losses(self, losses):
        """Set the team's regular season losses"""
        self.regular_season_losses = losses

    def update_regular_season_ties(self, ties):
        """Set the team's regular season ties"""
        self.regular_season_ties = ties

    def update_regular_season_wins(self, wins):
        """Set the team's regular season wins"""
        self.regular_season_wins = wins

    def won_championship(self):
        """Returns a boolean representing whether the team won the championship"""
        if self.year <= self.member.league.max_completed_year:
            last_game = sorted(self.matchups, key=lambda matchup: matchup.week, reverse=True)[0]
            return last_game.type == GameType.PLAYOFF and last_game.outcome == GameOutcome.WIN
        else:
            return False
