import configparser
import os
import requests

from enum import IntEnum, auto

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')

S2 = config["ESPN"]["s2"]
SWID = config["ESPN"]["swid"]
LEAGUE_ID = int(config["ESPN"]["league_id"])


url = f"https://fantasy.espn.com/apis/v3/games/ffl/seasons/#2/segments/0/leagues/{LEAGUE_ID}?view=mMatchup&view=mMatchupScore&scoringPeriodId=#3"
headers = {
    'swid': SWID,
    'espn_s2': S2
}

a = requests.get(url, headers=headers)

from pprint import pprint
pprint(a.json())


# OLDER THAN 2018
u = "https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/86591?seasonId=2017"
# 2018 OR NEWER
u = "https://fantasy.espn.com/apis/v3/games/ffl/seasons/2023/segments/0/leagues/86591"
views = [
    "mMatchup",
    "mTeam",
    "mBoxscore",
    "mRoster",
    "mSettings",
    "kona_player_info",
    "player_wl",
    "mSchedule",
]

"""
class PlayerStatus(IntEnum):
    QB = 0
    RB = 2
    WR = 4
    TE = 6
    FLEX = 23
    DEFENSE = 16
    KICKER = 17
    BENCH = 20
    IR = 21

    def __repr__(self):
        return self.name
"""


# https://fantasy.espn.com/apis/v3/games/ffl/seasons/2023/segments/0/leagues/86591?view=mMatchup&scoringPeriodId={WEEK}