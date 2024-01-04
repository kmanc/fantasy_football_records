import configparser
import os
import requests

from new_fantasy_classes import Player

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')

S2 = config["ESPN"]["s2"]
SWID = config["ESPN"]["swid"]
LEAGUE_ID = int(config["ESPN"]["league_id"])

cookies = {
    'swid': SWID,
    'espn_s2': S2
}

temp_player = {
    "name": "",
    "on_team": 0,
    "player_id": 0,
    "points": 0,
    "position_id": 0,
}

from pprint import pprint

for year in range(2014, 2024):
    endpoint = f"https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{LEAGUE_ID}"
    if year <= 2017:
        endpoint = f"https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{LEAGUE_ID}?seasonId={year}"
    for week in range(1, 16):
        # Rostered players that week
        rostered = []
        params = {
            "view": "mRoster",
            "scoringPeriodId": week,
        }
        r = requests.get(endpoint, params=params, cookies=cookies)
        if r.status_code != 200:
            print("year: ", year, "week: ", week, "returned an HTTP", r.status_code)

        if year <= 2017:
            result = r.json()[0]
            # Loop over the teams' rosters
            for team in result.get("teams"):
                for entry in team.get("roster").get("entries"):
                    # Add the data that can be pulled from this endpoint
                    rostered.append({
                        "name": None,
                        "on_team": team.get("id"),
                        "player_id": entry.get("playerId"),
                        "points": None,
                        "position_id": entry.get("lineupSlotId"),
                    })
        else:
            result = r.json()
            # Loop over the teams' rosters
            for team in result.get("teams"):
                for entry in team.get("roster").get("entries"):
                    # Add the data that can be pulled from this endpoint
                    rostered.append({
                        "name": None,
                        "on_team": team.get("id"),
                        "player_id": entry.get("playerId"),
                        "points": None,
                        "position_id": entry.get("lineupSlotId"),
                    })

        params = {
            "view": "mBoxscore",
            "scoringPeriodId": week
        }
        r = requests.get(endpoint, params=params, cookies=cookies)
        if r.status_code != 200:
            print("year: ", year, "week: ", week, "returned an HTTP", r.status_code)

        scheduled = []
        if year <= 2017:
            result = r.json()[0]
            for game in result.get("schedule"):
                try:
                    scheduled.extend(game.get("home").get("rosterForMatchupPeriod").get("entries"))
                except AttributeError:
                    continue
                try:
                    scheduled.extend(game.get("away").get("rosterForMatchupPeriod").get("entries"))
                except AttributeError:
                    continue
        else:
            result = r.json()
            for game in result.get("schedule"):
                try:
                    scheduled.extend(game.get("home").get("rosterForMatchupPeriod").get("entries"))
                except AttributeError:
                    pass
                try:
                    scheduled.extend(game.get("away").get("rosterForMatchupPeriod").get("entries"))
                except AttributeError:
                    pass

        rids = {player.get("player_id") for player in rostered}
        sids = {player.get("playerId") for player in scheduled}
        print("RIDS: ", len(rids), "SIDS: ", len(sids))
        print("RIDS - SIDS: ", len(rids - sids))
        print("SIDS - RIDS: ", len(sids - rids))
        exit(0)

        for rostered_player in rostered:
            for scheduled_player in scheduled:
                if scheduled_player.get("playerId") == rostered_player.get("player_id"):
                    rostered_player["name"] = scheduled_player.get("playerPoolEntry").get("player").get("fullName")
                    rostered_player["points"] = scheduled_player.get("playerPoolEntry").get("appliedStatTotal")

        #print(rostered[0])
        less = [player for player in rostered if player.get("name") is None or player.get("points") is None]
        print(len(rostered), "|", len(less))
        #for player in rostered:
        #    print(player)
        #print(len(scheduled))
        #exit(0)


"""
for year in range(2014, 2024):
    endpoint = f"https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{LEAGUE_ID}"
    if year <= 2017:
        endpoint = f"https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{LEAGUE_ID}?seasonId={year}"
    for week in range(1, 16):
        score = 0
        params = {
            "view": "mMatchup",
            "scoringPeriodId": week
        }
        r = requests.get(endpoint, params=params, cookies=cookies)
        if r.status_code != 200:
            print("year: ", year, "week: ", week, "returned an HTTP", r.status_code)

        if year <= 2017:
            result = r.json()[0]
            # Players actuve in that week
            weeks_players = []
            # Schedule has the players points value and what team they played for
            for game in result.get("schedule"):
                # Add the home team's players
                try:
                    home_roster = game.get("home").get("rosterForMatchupPeriod").get("entries")
                except AttributeError:
                    continue
                for entry in home_roster:
                    weeks_players.append({
                        "name": entry.get("playerPoolEntry").get("player").get("fullName"),
                        "on_team": game.get("home").get("teamId"),
                        "player_id": entry.get("playerId"),
                        "points": entry.get("playerPoolEntry").get("appliedStatTotal"),
                        "position_id": 0,
                    })
                # Add the away team's players
                try:
                    away_roster = game.get("away").get("rosterForMatchupPeriod").get("entries")
                except AttributeError:
                    continue
                for entry in away_roster:
                    weeks_players.append({
                        "name": entry.get("playerPoolEntry").get("player").get("fullName"),
                        "on_team": game.get("away").get("teamId"),
                        "player_id": entry.get("playerId"),
                        "points": entry.get("playerPoolEntry").get("appliedStatTotal"),
                        "position_id": 0,
                    })
            for team in result.get("teams"):
                for entry in team.get("roster").get("entries"):
                    for player in weeks_players:
                        if entry.get("playerId") == player.get("player_id"):
                            player["position_id"] = entry.get("lineupSlotId")
            #pprint(weeks_players)
            for player in weeks_players:
                if player.get("on_team") == 1:
                    print(player)
            exit(0)
        else:
            result = r.json()
            teams = result.get("teams")
            my_team = teams[6]
            print(my_team)
            exit(0)
            my_roster = my_team.get("roster").get("entries")
        for player in my_roster:
            pprint(player)
            #print(player.get("playerPoolEntry").get("player").get("fullName"), "-", player.get("playerPoolEntry").get("appliedStatTotal"))
            if player.get("lineupSlotId") not in [20, 21]:
                score += player.get("playerPoolEntry").get("appliedStatTotal")
        print(year, "|", week, "|", score)
"""




"""
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