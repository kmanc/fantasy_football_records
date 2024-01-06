import configparser
import os
import pickle
import requests
from collections import defaultdict, OrderedDict
from datetime import date
from espn_api.football import League
from espn_api.requests.espn_requests import ESPNInvalidLeague

import utility
from fantasy_classes import FantasyLeague, Matchup, Member, Player, Team
from fantasy_enums import GameOutcome, GameType

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')

S2 = config["ESPN"]["s2"]
SWID = config["ESPN"]["swid"]
LEAGUE_ID = int(config["ESPN"]["league_id"])
FIRST_YEAR = int(config["ESPN"]["league_founded"])
LEAGUE_NAME = config["WEBSITE"]["league_name"].replace('"', '')
LEAGUE_ABBREVIATION = config["WEBSITE"]["league_abbreviation"].replace('"', '')
MEET_THE_MANAGERS_ASSETS = os.path.join('static/meet_the_managers')
MANAGER_BIOS_PATH = os.path.join(MEET_THE_MANAGERS_ASSETS, 'manager_bios.json')

# Override the new instance if one is already saved on disk
pickle_filename = f"{dir_path}/{LEAGUE_NAME}.pickle"
if os.path.exists(pickle_filename):
    with open(pickle_filename, "rb") as f:
        fantasy_league = pickle.load(f)

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

divisions = defaultdict(list)
divisional_standings = defaultdict(dict)
flat_standings = defaultdict(dict)
for team in fantasy_league.teams_in_active_year():
    divisions[team.division].append(team.espn_id)

print(divisions)

for team in fantasy_league.teams_in_active_year():
    divisional_wins = 0
    for matchup in team.matchups:
        if matchup.outcome == GameOutcome.WIN and matchup.opponent.espn_id in divisions.get(team.division):
            divisional_wins += 1
    team_stats = {
        "wins": team.wins,
        "divisional_wins": divisional_wins,
        "points_for": team.regular_season_points_scored()
    }
    divisional_standings[team.division][team.name] = team_stats
    flat_standings[team.name] = team_stats

for division, division_data in divisional_standings.items():
    divisional_standings[division] = OrderedDict(sorted(division_data.items(),
                                                        key=lambda item: (
                                                            item[1].get("wins"),
                                                            item[1].get("divisional_wins"),
                                                            item[1].get("points_for")
                                                        ), reverse=True))

flat_standings = OrderedDict(sorted(flat_standings.items(),
                                    key=lambda item: (
                                        item[1].get("points_for"),
                                        item[1].get("wins"),
                                        item[1].get("divisional_wins")
                                    ), reverse=True))

print(divisional_standings)
print()
print(flat_standings)
"""
Once the standings are sorted, divisional winners are seeded by total wins
    Tiebreaker 1 - total points scored
Then wildcard spots are determined by total points for
    Tiebreaker 1 - total wins
The remaining teams are re-sorted by total wins
    Tiebreaker 1 - total points scored
Teams who are not currently playoff teams have their total-points-needed for a wildcard spot calculated
"""
