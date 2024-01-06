import configparser
import os
import pickle
import requests
from collections import defaultdict
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

"""
Once the standings are sorted, divisional winners are seeded by total wins
    Tiebreaker 1 - total points scored
Then wildcard spots are determined by total points for
    Tiebreaker 1 - total wins
The remaining teams are re-sorted by total wins
    Tiebreaker 1 - total points scored
Teams who are not currently playoff teams have their total-points-needed for a wildcard spot calculated
"""
