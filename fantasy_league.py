import heapq
import pickle
from collections import defaultdict, OrderedDict
from datetime import date

from espn_api.football import League
from espn_api.requests.espn_requests import ESPNInvalidLeague

from fantasy_owner import Owner
from utility import clean_name, clean_team


class FantasyLeague:
    current_active_year: int
    espn_objects: dict
    espn_s2: str
    espn_swid: str
    founded: int
    league_id: int
    name: str
    owners: dict
    max_completed_year: int

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
                if omit_current and year == self.current_active_year:
                    continue
                yield {"owner": owner, "team_name": owner.teams.get(year), "year": year,
                       "points": sum(matchup.score for matchup in matchups if matchup.type.name == season_type)}

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
        league_max = self.founded
        for owner_data in self.owners.values():
            their_max = max(owner_data.matchups.keys())
            league_max = max(league_max, their_max)
        needs_omit = league_max > self.max_completed_year
        seasons = self.season_generator(omit_current=needs_omit)

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
        for team in self.espn_objects.get(self.current_active_year).teams:
            for owner_id in team.owners:
                for member in self.espn_objects.get(self.current_active_year).members:
                    if owner_id == member.get("id"):
                        owner_names.add(clean_name(f"{member.get('firstName')} {member.get('lastName')}"))

        return owner_names

    def get_all_matchups(self):
        """
            Returns a dict where the keys are owners.
            Values are dicts where keys are years and values are matchup lists
        """
        owners_matchups = defaultdict(lambda: defaultdict(list))
        for year, espn_object in self.espn_objects.items():
            lookup_dict = {}
            for member in espn_object.members:
                lookup_dict[member.get("id")] = clean_name(f"{member.get('firstName')} {member.get('lastName')}")
            max_week = min(len(espn_object.settings.matchup_periods), espn_object.current_week)
            for week in range(1, max_week + 1):
                scoreboard = espn_object.scoreboard(week)
                if all(game.home_score == 0 for game in scoreboard) and all(
                        game.away_score == 0 for game in scoreboard):
                    continue
                for matchup in scoreboard:
                    try:
                        home_owner = lookup_dict.get(matchup.home_team.owners[0])
                    except AttributeError:
                        home_owner = "BYE"
                        matchup.home_team = type('', (object,), {})()
                    try:
                        away_owner = lookup_dict.get(matchup.away_team.owners[0])
                    except AttributeError:
                        away_owner = "BYE"
                        matchup.away_team = type('', (object,), {})()
                    matchup.home_team.owner = home_owner
                    matchup.away_team.owner = away_owner
                    owners_matchups[home_owner][year].append(matchup)
                    owners_matchups[away_owner][year].append(matchup)
        owners_matchups.pop("BYE", None)

        return owners_matchups

    def get_all_owners(self):
        """ Returns all owners who have participated in the league """
        owner_names = set()
        for espn_object in self.espn_objects.values():
            for team in espn_object.teams:
                for owner_id in team.owners:
                    for member in espn_object.members:
                        if owner_id == member.get("id"):
                            owner_names.add(clean_name(f"{member.get('firstName')} {member.get('lastName')}"))

        return owner_names

    def get_fantasy_year(self, year):
        """ Returns an ESPN_API object for the given year """
        return League(league_id=self.league_id, year=year, espn_s2=self.espn_s2, swid=self.espn_swid)

    def get_owners_teams(self, owner_name):
        """ Returns a dict where the keys are years and the values are the name of that owner's team in that year """
        owners_teams = {}
        for year, espn_object in self.espn_objects.items():
            for team in espn_object.teams:
                for member in espn_object.members:
                    if any(member.get("id") == team_owner for team_owner in team.owners) and (clean_name(f"{member.get('firstName')} {member.get('lastName')}") == owner_name):
                        owners_teams[year] = clean_team(owner_name, year, team.team_name)

        return owners_teams

    def get_wffl_playoff_picture(self):
        """ Returns an ordered playoff projection with the help of _get_wffl_standings """
        """
            Once the standings are sorted, divisional winners are seeded by total wins
                Tiebreaker 1 - total points scored
            Then wildcard spots are determined by total points for
                Tiebreaker 1 - total wins
            The remaining teams are re-sorted by total wins
                Tiebreaker 1 - total points scored
            Teams who are not currently playoff teams have their total-points-needed for a wildcard spot calculated
        """
        playoff_picture = OrderedDict()
        division_standings, flat_standings = self._get_wffl_standings()
        number_of_playoff_teams = self.espn_objects.get(self.current_active_year).settings.playoff_team_count

        unsorted_division_winners = {}
        for division_data in division_standings.values():
            winner = division_data.popitem(last=False)
            unsorted_division_winners[winner[0]] = winner[1]

        sorted_division_winners = OrderedDict(sorted(unsorted_division_winners.items(),
                                                     key=lambda item: (
                                                         item[1].get("total_wins"),
                                                         item[1].get("total_points_scored")
                                                     ), reverse=True))

        for winner, winner_data in sorted_division_winners.items():
            playoff_picture[winner] = winner_data
            flat_standings.pop(winner, None)

        sorted_wildcard_winners = OrderedDict([
            flat_standings.popitem(last=False),
            flat_standings.popitem(last=False)
        ])

        for wildcard, wildcard_data in sorted_wildcard_winners.items():
            playoff_picture[wildcard] = wildcard_data

        low_wildcard = list(sorted_wildcard_winners.keys())[-1]
        wildcard_points_needed = sorted_wildcard_winners[low_wildcard].get('total_points_scored')

        sorted_rest_of_league = OrderedDict(sorted(flat_standings.items(),
                                                   key=lambda item: (
                                                       item[1].get("total_wins"),
                                                       item[1].get("total_points_scored")
                                                   ), reverse=True))

        for rest, rest_data in sorted_rest_of_league.items():
            rest_data["points_out"] = round(wildcard_points_needed - rest_data.get('total_points_scored'), 2)
            playoff_picture[rest] = rest_data

        seed = 1
        for team, team_data in playoff_picture.items():
            if seed <= number_of_playoff_teams:
                team_data["seed"] = seed
            elif seed >= len(playoff_picture) - 1:
                team_data["seed"] = "P"
            playoff_picture[team] = team_data
            seed += 1

        return playoff_picture

    def _get_wffl_standings(self):
        """ Gets the data required to determine what the standings are in accordance with the WFFL rules, then sorts it"""
        """
        WFFL rules state that divisional standings are determined as follows:
            Overall record
            Tiebreaker 1 - divisional record
            Tiebreaker 2 - total points scored
        Wildcard playoff teams are then determined by:
            Total points for
            Tiebreaker 1 - overall record
            Tiebreaker 2 - divisional record
        """
        divisional_standings = defaultdict(dict)
        flat_standings = defaultdict(dict)

        for team in self.espn_objects.get(self.current_active_year).teams:
            team_data = {
                "division_losses": 0,
                "division_wins": 0,
                "total_losses": 0,
                "total_points_scored": round(team.points_for, 2),
                "total_wins": 0,
            }
            for win_loss, opponent in zip(team.outcomes, team.schedule):
                if win_loss == "W" and team.division_id == opponent.division_id:
                    team_data["division_wins"] += 1
                    team_data["total_wins"] += 1
                elif win_loss == "W" and team.division_id != opponent.division_id:
                    team_data["total_wins"] += 1
                elif win_loss == "L" and team.division_id == opponent.division_id:
                    team_data["division_losses"] += 1
                    team_data["total_losses"] += 1
                elif win_loss == "L" and team.division_id != opponent.division_id:
                    team_data["total_losses"] += 1

            divisional_standings[team.division_name][team.team_name] = team_data
            flat_standings[team.team_name] = team_data

        for division, division_data in divisional_standings.items():
            divisional_standings[division] = OrderedDict(sorted(division_data.items(),
                                                                key=lambda item: (
                                                                    item[1].get("total_wins"),
                                                                    item[1].get("division_wins"),
                                                                    item[1].get("total_points_scored")
                                                                ), reverse=True))

        flat_standings = OrderedDict(sorted(flat_standings.items(),
                                            key=lambda item: (
                                                item[1].get("total_points_scored"),
                                                item[1].get("total_wins"),
                                                item[1].get("division_wins")
                                            ), reverse=True))

        return divisional_standings, flat_standings

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
            try:
                candidate_object = self.get_fantasy_year(year)
            except ESPNInvalidLeague:
                continue
            if candidate_object is not None:
                self.espn_objects[year] = candidate_object

        return

    def update_max_completed_year(self):
        """ Updates the self.max_completed_year to the most recent year that is complete """
        last_game_dict = defaultdict(list)
        for owner_data in self.owners.values():
            for year, year_data in owner_data.matchups.items():
                last_game = year_data[-1]
                if last_game.outcome.name == "WIN" and last_game.type.name == "PLAYOFF":
                    last_game_dict[year].append(last_game)

        completed = (year for year, games in last_game_dict.items() if len(games) == 1)

        return max(completed)

    def __init__(self, espn_s2, espn_swid, founded_year, league_id):
        self.espn_s2 = espn_s2
        self.espn_swid = espn_swid
        self.founded = founded_year
        self.league_id = league_id
        self.espn_objects = {}
        self.update_espn_objects()
        self.current_active_year = max(self.espn_objects)
        self.name = self.espn_objects.get(self.current_active_year).settings.name
        all_owners = self.get_all_owners()
        active_owners = self.get_active_owners()
        all_matchups = self.get_all_matchups()
        owner_objects = {}
        for owner in all_owners:
            owner_matchups = all_matchups.get(owner)
            owner_teams = self.get_owners_teams(owner)
            owner_start_year = min(owner_teams)
            owner_active = owner in active_owners
            owner_objects[owner] = (
                Owner(owner_joined=owner_start_year, owner_name=owner, owner_matchups=owner_matchups,
                      owner_teams=owner_teams, owner_active=owner_active))
        self.owners = owner_objects
        self.max_completed_year = self.update_max_completed_year()
