from collections import defaultdict
from datetime import date

from fantasy_matchup import Matchup


class Owner:
    active: bool
    joined: int
    matchups: defaultdict[list]
    name: str
    teams: dict

    def matchup_by_type_generator(self, game_type=None):
        """ Yields any matchup with the given game type (or all matchups) """
        for years_matchups in self.matchups.values():
            for matchup in years_matchups:
                if game_type is None:
                    yield matchup
                elif matchup.type.name == game_type:
                    yield matchup

    def calculate_championship_wins(self, max_year=date.today().year):
        """ Returns the number of championships the owner has won """
        return sum(
            matchup[-1].type.name == "PLAYOFF" and matchup[-1].outcome.name == "WIN" and matchup[-1].year <= max_year
            for matchup in self.matchups.values())

    def calculate_lifetime_playoff_points(self):
        """ Returns the total points the owner has scored in playoff games """
        return sum(matchup.score for matchup in self.matchup_by_type_generator("PLAYOFF"))

    def calculate_lifetime_regular_season_points(self):
        """ Returns the total points the owner has scored in regular season games """
        return sum(matchup.score for matchup in self.matchup_by_type_generator("REGULAR_SEASON"))

    def calculate_lifetime_win_percent(self):
        """ Returns the owner's career win percentage """
        wins = 0
        games = 0
        for years_matchups in self.matchups.values():
            for matchup in years_matchups:
                games += 1
                if matchup.outcome.name == "WIN":
                    wins += 1

        return wins / games

    def calculate_lifetime_win_percent_against(self, opponent_name):
        """ Returns the owner's career win percentage against the given opponent """
        wins = 0
        games = 0
        for years_matchups in self.matchups.values():
            for matchup in years_matchups:
                if matchup.opponent_owner_name == opponent_name:
                    games += 1
                    if matchup.outcome.name == "WIN":
                        wins += 1

        try:
            return wins / games
        except ZeroDivisionError:
            return 0.0

    def calculate_playoff_appearances(self):
        """ Returns the number of times the owner has made the playoffs """
        appearances = 0
        for years_matchups in self.matchups.values():
            if years_matchups[-1].type.name == "PLAYOFF":
                appearances += 1

        return appearances

    def __init__(self, owner_joined, owner_name, owner_matchups, owner_teams, owner_active):
        self.joined = owner_joined
        self.name = owner_name
        self.teams = owner_teams
        self.active = owner_active
        parsed_matchups = defaultdict(list)
        for year, matchups in owner_matchups.items():
            for week, matchup in enumerate(matchups):
                if matchup.matchup_type in ["LOSERS_CONSOLATION_LADDER", "WINNERS_CONSOLATION_LADDER"]:
                    continue
                parsed_matchups[year].append(Matchup(self.name, self.teams.get(year), year, week + 1, matchup))
        self.matchups = parsed_matchups
