from collections import defaultdict
from fantasy_matchup import Matchup


class Owner:
	active: bool
	matchups: defaultdict[list]
	name: str
	teams: dict

	def matchup_by_type_generator(self, game_type=None):
		for years_matchups in self.matchups.values():
			for matchup in years_matchups:
				if game_type is None:
					yield matchup
				elif matchup.type.name == game_type:
					yield matchup

	def calculate_championship_wins(self):
		return sum(matchup[-1].type.name == "PLAYOFF" and matchup[-1].outcome.name == "WIN" for matchup in self.matchups.values())

	def calculate_lifetime_playoff_points(self):
		return sum(matchup.score for matchup in self.matchup_by_type_generator("PLAYOFF"))

	def calculate_lifetime_regular_season_points(self):
		return sum(matchup.score for matchup in self.matchup_by_type_generator("REGULAR_SEASON"))

	def calculate_lifetime_win_percent(self):
		wins = 0
		games = 0
		for years_matchups in self.matchups.values():
			for matchup in years_matchups:
				games += 1
				if matchup.outcome.name == "WIN":
					wins += 1

		return wins / games

	def calculate_lifetime_win_percent_against(self, opponent_name):
		wins = 0
		games = 0
		for years_matchups in self.matchups.values():
			for matchup in years_matchups:
				if matchup.opponent_owner_name == opponent_name:
					games += 1
					if matchup.outcome.name == "WIN":
						wins += 1

		return wins / games

	def calculate_playoff_appearances(self):
		appearances = 0
		for years_matchups in self.matchups.values():
			if years_matchups[-1].type.name == "PLAYOFF":
				appearances += 1

		return appearances

	def __init__(self, owner_name, owner_matchups, owner_teams, owner_active):
		self.name = owner_name
		self.teams = owner_teams
		self.active = owner_active
		parsed_matchups = defaultdict(list)
		for year, matchups in owner_matchups.items():
			for week, matchup in enumerate(matchups):
				if matchup.data.get("playoffTierType") in ["LOSERS_CONSOLATION_LADDER", "WINNERS_CONSOLATION_LADDER"]:
					continue
				parsed_matchups[year].append(Matchup(self.name, self.teams.get(year), year, week + 1, matchup))
		self.matchups = parsed_matchups
