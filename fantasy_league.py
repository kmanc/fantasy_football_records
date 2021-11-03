import heapq
import pickle
from collections import defaultdict
from datetime import date
from espn_api.football import League
from fantasy_owner import Owner


class FantasyLeague:
	espn_objects: dict
	espn_s2: str
	espn_swid: str
	founded: int
	league_id: int
	name: str
	owners: dict

	def matchup_by_outcome_generator(self, outcome=None):
		""" Yields any matchup with the given outcome (or all matchups) """
		for owner in self.owners.values():
			for matchups in owner.matchups.values():
				for matchup in matchups:
					if outcome is None:
						yield matchup
					elif matchup.outcome.name == outcome:
						yield matchup

	def season_generator(self, season_type="REGULAR_SEASON", omit_current=False):
		"""
			Yields a dict containing the owner's name, team name, year, and total points scored in that season type
			Defaults to regular season but can also be PLAYOFF
		"""
		for owner in self.owners.values():
			for year, matchups in owner.matchups.items():
				if omit_current and year == max(self.espn_objects):
					continue
				yield {"owner": owner.name, "team": owner.teams.get(year), "year": year, "points": sum(matchup.score for matchup in matchups if matchup.type.name == season_type)}

	def calculate_highest_loss_points(self, number=10):
		""" Returns the {number} highest scores in games that were lost """
		games = self.matchup_by_outcome_generator(outcome="LOSS")

		return [vars(record) for record in heapq.nlargest(number, games, key=lambda x: x.score)]

	def calculate_highest_playoff_season_points(self, number=10):
		""" Returns the {number} highest point totals in a single year's playoffs """
		seasons = self.season_generator(season_type="PLAYOFF")

		return heapq.nlargest(number, seasons, key=lambda x: x.get("points"))

	def calculate_highest_regular_season_points(self, number=10):
		""" Returns the {number} highest point totals in a single year's regular season """
		seasons = self.season_generator()

		return heapq.nlargest(number, seasons, key=lambda x: x.get("points"))

	def calculate_highest_single_week_points(self, number=10):
		""" Returns the {number} highest scores in a single week """
		games = self.matchup_by_outcome_generator()

		return [vars(record) for record in heapq.nlargest(number, games, key=lambda x: x.score)]

	def calculate_lowest_regular_season_points(self, number=10):
		""" Returns the {number} lowest point totals in a single year's regular season """
		seasons = self.season_generator(omit_current=True)

		return heapq.nsmallest(number, seasons, key=lambda x: x.get("points"))

	def calculate_lowest_single_week_points(self, number=10):
		""" Returns the {number} lowest scores in a single week """
		games = self.matchup_by_outcome_generator()

		return [vars(record) for record in heapq.nsmallest(number, games, key=lambda x: x.score)]

	def calculate_lowest_win_points(self, number=10):
		""" Returns the {number} lowest scores in games that were won """
		games = self.matchup_by_outcome_generator(outcome="WIN")

		return [vars(record) for record in heapq.nsmallest(number, games, key=lambda x: x.score)]

	def get_active_owners(self):
		""" Returns active league owners """
		owner_names = set()
		for team in self.espn_objects.get(max(self.espn_objects)).teams:
			owner_names.add(team.owner.replace("  ", " ").strip().title())

		return owner_names

	def get_all_matchups(self):
		""" Returns a dict where the keys are owners. Values are dicts where keys are years and values are matchup lists """
		owners_matchups = defaultdict(lambda: defaultdict(list))
		for year, espn_object in self.espn_objects.items():
			max_week = min(len(espn_object.settings.matchup_periods), espn_object.current_week)
			for week in range(1, max_week + 1):
				scoreboard = espn_object.scoreboard(week)
				if all(game.home_score == 0 for game in scoreboard) and all(game.away_score == 0 for game in scoreboard):
					continue
				for matchup in scoreboard:
					try:
						home_owner = matchup.home_team.owner.replace("  ", " ").strip().title()
					except AttributeError:
						home_owner = "BYE"
					try:
						away_owner = matchup.away_team.owner.replace("  ", " ").strip().title()
					except AttributeError:
						away_owner = "BYE"
					owners_matchups[home_owner][year].append(matchup)
					owners_matchups[away_owner][year].append(matchup)
		del owners_matchups["BYE"]

		return owners_matchups

	def get_all_owners(self):
		""" Returns all owners who have participated in the league """
		owner_names = set()
		for espn_object in self.espn_objects.values():
			for team in espn_object.teams:
				owner_names.add(team.owner.replace("  ", " ").strip().title())

		return owner_names

	def get_fantasy_year(self, year):
		""" Returns an ESPN_API object for the given year """
		return League(league_id=self.league_id, year=year, espn_s2=self.espn_s2, swid=self.espn_swid)

	def get_owners_teams(self, owner_name):
		""" Returns a dict where the keys are years and the values are the name of that owner's team in that year """
		owners_teams = {}
		for year, espn_object in self.espn_objects.items():
			for team in espn_object.teams:
				if owner_name == team.owner.replace("  ", " ").strip().title():
					owners_teams[year] = team.team_name.replace("  ", " ").strip()

		return owners_teams

	def save_to_file(self, filename=None):
		""" Saves the entire class to a pickled file """
		if filename is None:
			filename = f"{self.name}.pickle"
		with open(filename, "wb") as f:
			pickle.dump(self, f)

	def update_espn_objects(self):
		""" Updates the self.espn_objects dict with all missing ESPN_API data """
		all_league_years = range(self.founded, date.today().year + 1)
		needs_update = []
		new_objects_dict = {}
		for year in all_league_years:
			try:
				years_data = self.espn_objects.get(year)
			except AttributeError:
				needs_update.append(year)
				continue
			if years_data is None:
				needs_update.append(year)
			elif years_data.current_week != len(years_data.settings.matchup_periods):
				needs_update.append(year)
		for year in needs_update:
			candidate_object = self.get_fantasy_year(year)
			if candidate_object is not None:
				new_objects_dict[year] = candidate_object

		self.espn_objects = new_objects_dict

	def __init__(self, espn_s2, espn_swid, founded_year, league_id):
		self.espn_s2 = espn_s2
		self.espn_swid = espn_swid
		self.founded = founded_year
		self.league_id = league_id
		self.update_espn_objects()
		self.name = self.espn_objects.get(max(self.espn_objects)).settings.name
		all_owners = self.get_all_owners()
		active_owners = self.get_active_owners()
		all_matchups = self.get_all_matchups()
		owner_objects = {}
		for owner in all_owners:
			owner_matchups = all_matchups.get(owner)
			owner_teams = self.get_owners_teams(owner)
			owner_active = owner in active_owners
			owner_objects[owner] = (Owner(owner_name=owner, owner_matchups=owner_matchups, owner_teams=owner_teams, owner_active=owner_active))
		self.owners = owner_objects
