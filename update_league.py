import configparser
import itertools
import json
import os
import pickle
import requests
from collections import defaultdict
from copy import deepcopy
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
FULL_BRACKET_SLOTS = 19
LEAGUE_NAME = config["WEBSITE"]["league_name"].replace('"', '')
LEAGUE_ABBREVIATION = config["WEBSITE"]["league_abbreviation"].replace('"', '')
MEET_THE_MANAGERS_ASSETS = os.path.join('static/meet_the_managers')
MANAGER_BIOS_PATH = os.path.join(MEET_THE_MANAGERS_ASSETS, 'manager_bios.json')

# Placeholders for BYE weeks
PLACEHOLDER_LEAGUE = FantasyLeague(espn_s2="", espn_swid="", founded_year=99999, league_id=99999)
PLACEHOLDER_MEMBER = Member(member_id="", league=PLACEHOLDER_LEAGUE, name="")
PLACEHOLDER_TEAM = Team(division=99999, espn_id=99999, name="", member=PLACEHOLDER_MEMBER, schedule=[], year=99999)

# Create a new instance of a league from the config values
fantasy_league = FantasyLeague(espn_s2=S2, espn_swid=SWID, founded_year=FIRST_YEAR, league_id=LEAGUE_ID)

# Override the new instance if one is already saved on disk
league_pickle_filename = f"{dir_path}/{LEAGUE_NAME}.pickle"
if os.path.exists(league_pickle_filename):
    with open(league_pickle_filename, "rb") as f:
        fantasy_league = pickle.load(f)


def fetch_player_data(league_id, espn_s2, espn_swid, fetch_year, fetch_week):
    """Gets name, points, position_id, and team for players in the given year/week combination.
    Data not available prior to 2018. Returns data as a defaultdict[week: list[Player]]"""

    # Start a defaultdict for the results
    output_data = defaultdict(list)
    # This data is not available prior to 2018
    if fetch_year < 2018:
        return output_data

    endpoint = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{fetch_year}/segments/0/leagues/{league_id}"
    params = {
        "view": "mRoster",
        "scoringPeriodId": fetch_week,
    }
    cookies = {
        'swid': espn_swid,
        'espn_s2': espn_s2
    }
    # Rostered players that week
    rostered = []
    r = requests.get(endpoint, params=params, cookies=cookies)
    if r.status_code != 200:
        print("year: ", fetch_year, "week: ", fetch_week, "returned an HTTP", r.status_code)
        return output_data

    result = r.json()
    # Loop over the teams' rosters
    for fetch_team in result.get("teams"):
        for entry in fetch_team.get("roster").get("entries"):
            # Add the data that can be pulled from this endpoint
            rostered.append({
                "name": None,
                "on_team": fetch_team.get("id"),
                "player_id": entry.get("playerId"),
                "points": None,
                "position_id": entry.get("lineupSlotId"),
            })

    params = {
        "view": "mMatchup",
        "scoringPeriodId": fetch_week,
    }
    r = requests.get(endpoint, params=params, cookies=cookies)
    if r.status_code != 200:
        print("year: ", fetch_year, "week: ", fetch_week, "returned an HTTP", r.status_code)
        return output_data

    # Create a list of scheduled players
    scheduled = []
    # Get players who were played and players who were benched
    result = r.json()
    for game in result.get("schedule"):
        scheduled.extend(game.get("home", {}).get("rosterForCurrentScoringPeriod", {}).get("entries", []))
        scheduled.extend(game.get("away", {}).get("rosterForCurrentScoringPeriod", {}).get("entries", []))

    # Enrich the rostered players with the scheduled players (only fully works in 2018 or later)
    for rostered_player in rostered:
        for scheduled_player in scheduled:
            if scheduled_player.get("playerId") == rostered_player.get("player_id"):
                rostered_player["name"] = scheduled_player.get("playerPoolEntry").get("player").get("fullName")
                rostered_player["points"] = scheduled_player.get("playerPoolEntry").get("appliedStatTotal")

    # Use the data we put together to create a player object
    for rostered_player in rostered:
        if rostered_player.get("name"):
            player_object = Player(espn_id=rostered_player.get("player_id"),
                                   name=rostered_player.get("name"),
                                   points=rostered_player.get("points"),
                                   position=rostered_player.get("position_id"))
            output_data[rostered_player.get("on_team")].append(player_object)

    return output_data


def get_year_from_api(query_year):
    """ Returns an ESPN_API object for the given year """
    return League(league_id=fantasy_league.id, year=query_year, espn_s2=fantasy_league.espn_s2, swid=fantasy_league.espn_swid)


# Get all years that the league could have existed
all_league_years = range(fantasy_league.founded_year, date.today().year + 1)

# Loop over years the league could have existed
api_years = []
for year in all_league_years:
    # Try to get the data for the league for that year
    try:
        api_year = get_year_from_api(year)
        # If the year of gathered data is newer than the newest active year, the league needs to be updated
        if fantasy_league.active_year < year:
            api_years.append(api_year)
            fantasy_league.update_active_year(year)
            fantasy_league.update_active_year_playoff_slots(api_year.settings.playoff_team_count)
            fantasy_league.update_active_year_regular_season_length(api_year.settings.reg_season_count)
        # If the year of gathered data has not yet completed, the league needs to be updated
        if api_year.current_week < len(api_year.settings.matchup_periods):
            api_years.append(api_year)
        # If the year of gathered data has completed, the maximum completed year should be updated
        else:
            fantasy_league.update_max_completed_year(year)
    # If it fails, that's ok
    # It most likely just means that the fantasy football year hasn't started for the calendar year
    except ESPNInvalidLeague:
        continue

# Now loop over the data that needs to be integrated into the league instance
for api_year in api_years:
    # Loop over the members of the league that year and grab a few of their identifiers
    for member in api_year.members:
        name = utility.clean_member_name(f'{member.get("firstName")} {member.get("lastName")}')
        member_id = utility.clean_user_id(member.get("id"))
        member_object = Member(league=fantasy_league, member_id=member_id, name=name)
        # If the id matches an existing league member, update the data for that member
        for existing in fantasy_league.members:
            if member_object.same(existing):
                # update existing members
                existing.update_joined_year(api_year.year)
                existing.update_left_year(api_year.year)
                break
        # If the loop completed without a break (IE there was no match to an existing league member)
        # Add the new member to the league
        else:
            member_object.update_joined_year(api_year.year)
            fantasy_league.add_member(member_object)

    # Chances are the name hasn't changed but on the off chance it has, update it
    fantasy_league.update_name(api_year.settings.name)

    # Loop over the teams of the league that year and grab a few of their stats
    for team in api_year.teams:
        # Get the ESPN-assigned team ID
        espn_id = team.team_id
        # Loop over the league members to find its owner
        for member in fantasy_league.members:
            # Match on the owner
            if any(member.id == utility.clean_user_id(team_owner.get("id")) for team_owner in team.owners):
                # Use the ESPN team ID and year to generate a true team ID
                team_id = utility.generate_team_id(espn_id, api_year.year)
                # If the owner already has a record of that team, update the record
                for existing_team in member.teams:
                    if utility.generate_team_id(existing_team.espn_id, existing_team.year) == team_id:
                        existing_team.update_regular_season_losses(team.losses)
                        existing_team.update_regular_season_ties(team.ties)
                        existing_team.update_regular_season_wins(team.wins)
                        break
                # If the loop completed without a break (IE there was no match to an existing member's teams)
                # Add the new team to the member
                else:
                    team_name = utility.clean_team_name(member.name, api_year.year, team.team_name)
                    schedule_ids = [opponent.team_id for opponent in team.schedule]
                    team_object = Team(division=team.division_id, espn_id=espn_id, name=team_name,
                                       member=member, schedule=schedule_ids, year=api_year.year)
                    team_object.update_regular_season_losses(team.losses)
                    team_object.update_regular_season_ties(team.ties)
                    team_object.update_regular_season_wins(team.wins)
                    member.add_team(team_object)

    # Figure out how far into the season we are
    max_week = min(len(api_year.settings.matchup_periods), api_year.current_week)

    # Get the teams from the league for the given year
    this_years_teams = {team for team in fantasy_league.team_superset() if team.year == api_year.year}

    # Loop over the weeks of the season that have happened or are in progress
    for week in range(1, max_week + 1):
        # Get the scoreboard for that week
        scoreboard = api_year.scoreboard(week)
        # If nobody has any points, the ESPN API doesn't have data for that week, so skip it
        if all(game.home_score == 0 for game in scoreboard) and all(game.away_score == 0 for game in scoreboard):
            continue
        # Get the custom-built player data for that week
        player_data = fetch_player_data(fantasy_league.id, fantasy_league.espn_s2, fantasy_league.espn_swid, api_year.year, week)
        # Loop over the matchups for the week's scoreboard
        for matchup in scoreboard:
            # Skip "fake" playoff games
            if matchup.matchup_type in ["LOSERS_CONSOLATION_LADDER", "WINNERS_CONSOLATION_LADDER"]:
                continue
            # Set the game to be a regular season game
            matchup_type = GameType.REGULAR_SEASON
            # Switch it to a playoff game if it matches the "real" playoff game type
            if matchup.matchup_type == "WINNERS_BRACKET":
                matchup_type = GameType.PLAYOFF
            # Get the home team's ID
            try:
                home_team_id = utility.generate_team_id(matchup.home_team.team_id, api_year.year)
            # Or set it to None, denoting a BYE
            except AttributeError:
                home_team_id = None
            # Get the away team's ID
            try:
                away_team_id = utility.generate_team_id(matchup.away_team.team_id, api_year.year)
            # Or set it to None, denoting a BYE
            except AttributeError:
                away_team_id = None
            for team in this_years_teams:
                if utility.generate_team_id(team.espn_id, team.year) == home_team_id:
                    # If there was no away team, throw in a placeholder
                    if away_team_id is None:
                        opponent = PLACEHOLDER_TEAM
                    # If there was an away team, find it
                    else:
                        opponent = [opponent for opponent in this_years_teams if utility.generate_team_id(opponent.espn_id, opponent.year) == away_team_id][0]
                    # Set the outcome to a win
                    outcome = GameOutcome.WIN
                    # Change it to a loss if the away team scored more points
                    if matchup.home_score < matchup.away_score:
                        outcome = GameOutcome.LOSS
                    # Or change it to a tie if the teams had the same amount of points
                    elif matchup.home_score == matchup.away_score:
                        outcome = GameOutcome.TIE
                    # Create a matchup object based on the information gathered
                    matchup_object = Matchup(opponent=opponent, outcome=outcome, points_against=matchup.away_score,
                                             points_for=matchup.home_score, team=team, game_type=matchup_type,
                                             week=week)
                    # Add the players for the team into the matchup object IF IT EXISTS
                    # Remember that prior to 2018 this data doesn't exist
                    if player_data:
                        for player in player_data.get(matchup.home_team.team_id):
                            matchup_object.add_player(player)
                    # If this matchup is not already in the matchup set for a given team, add it
                    if not any(matchup_object.same(existing) for existing in team.matchups):
                        team.add_matchup(matchup_object)
                elif utility.generate_team_id(team.espn_id, team.year) == away_team_id:
                    # If there was no away team, throw in a placeholder
                    if home_team_id is None:
                        opponent = PLACEHOLDER_TEAM
                    # If there was a home team, find it
                    else:
                        opponent = [opponent for opponent in this_years_teams if utility.generate_team_id(opponent.espn_id, opponent.year) == home_team_id][0]
                    # Set the outcome to a win
                    outcome = GameOutcome.WIN
                    # Change it to a loss if the home team scored more points
                    if matchup.home_score > matchup.away_score:
                        outcome = GameOutcome.LOSS
                    # Or change it to a tie if the teams had the same amount of points
                    elif matchup.home_score == matchup.away_score:
                        outcome = GameOutcome.TIE
                    # Create a matchup object based on the information gathered
                    matchup_object = Matchup(opponent=opponent, outcome=outcome, points_against=matchup.home_score,
                                             points_for=matchup.away_score, team=team, game_type=matchup_type,
                                             week=week)
                    # Add the players for the team into the matchup object IF IT EXISTS
                    # Remember that prior to 2018 this data doesn't exist
                    if player_data:
                        for player in player_data.get(matchup.away_team.team_id):
                            matchup_object.add_player(player)
                    # If this matchup is not already in the matchup set for a given team, add it
                    if not any(matchup_object.same(existing) for existing in team.matchups):
                        team.add_matchup(matchup_object)


with open(league_pickle_filename, "wb") as f:
    pickle.dump(fantasy_league, f, protocol=pickle.HIGHEST_PROTOCOL)


# Now do stuff for the playoffs
# Create a dict {division_id: list[team_id_in_division]}
divisions = defaultdict(list)
for team in fantasy_league.teams_in_active_year():
    divisions[team.division].append(team.espn_id)


# Create two dicts containing the data needed to calculate standings
#     divisional_raw_data - data required to figure out who is winning a division
#     flat_raw_data - data required to figure out who is winning the points-for wildcard race
divisional_raw_data = defaultdict(list)
flat_raw_data = []

for team in fantasy_league.teams_in_active_year():
    # Calculate how many in-division wins a team has
    divisional_wins = 0
    divisional_losses = 0
    for matchup in team.matchups:
        if (matchup.type == GameType.REGULAR_SEASON and
                matchup.outcome == GameOutcome.WIN and
                matchup.opponent.espn_id in divisions.get(team.division)):
            divisional_wins += 1
        elif (matchup.type == GameType.REGULAR_SEASON and
              matchup.outcome == GameOutcome.LOSS and
              matchup.opponent.espn_id in divisions.get(team.division)):
            divisional_losses += 1

    team_stats = {
        "divisional_losses": divisional_losses,
        "divisional_wins": divisional_wins,
        "losses": team.regular_season_losses,
        "name": team.name,
        "points_for": team.regular_season_points_scored(),
        "ties": team.regular_season_ties,
        "wins": team.regular_season_wins,
    }
    # Store the raw data in the dict split by division
    divisional_raw_data[team.division].append(team_stats)
    # Store it again in the dict not split by division
    flat_raw_data.append(team_stats)

"""
WFFL rules state that divisional standings are determined as follows:
    Overall record
    Tiebreaker 1 - divisional record
    Tiebreaker 2 - total points scored
"""

# Now sort the raw divisional data so that each key contains a sorted list representing the standings for that division
divisional_standings = {}

for division, division_data in divisional_raw_data.items():
    divisional_standings[division] = sorted(division_data, key=lambda team_data: (
        team_data.get("wins"),
        team_data.get("divisional_wins"),
        team_data.get("points_for"),
    ), reverse=True)

"""
WFFL rules state that wildcard standings are determined as follows:
    Total points for
    Tiebreaker 1 - overall record
    Tiebreaker 2 - divisional record
"""

# And sort the raw flat data so that it is a list representing the wildcard standings
wildcard_standings = sorted(flat_raw_data,
                            key=lambda team_data: (
                                team_data.get("points_for"),
                                team_data.get("wins"),
                                team_data.get("divisional_wins"),
                            ), reverse=True)


# Determine who is leading each division and store them in a dict {division_id: team_data}
unsorted_division_leaders = {}
for division, division_data in divisional_standings.items():
    unsorted_division_leaders[division] = division_data[0]


"""
Once the standings are sorted, divisional winners are seeded by total wins
    Tiebreaker 1 - total points scored
"""


sorted_division_leaders = sorted(unsorted_division_leaders.values(),
                                 key=lambda team_data: (
                                     team_data.get("wins"),
                                     team_data.get("points_for"),
                                 ), reverse=True)

"""
Then wildcard spots are determined by total points for
    Tiebreaker 1 - total wins
"""

for leader in sorted_division_leaders:
    wildcard_standings.remove(leader)

sorted_wildcard_leaders = wildcard_standings[:2]

"""
The remaining teams are re-sorted by total wins
    Tiebreaker 1 - total points scored
"""

sorted_rest_of_league = sorted(wildcard_standings[2:],
                               key=lambda team_data: (
                                   team_data.get("wins"),
                                   team_data.get("points_for"),
                               ), reverse=True)

# Playoff teams are given their seed
# Teams on the outside of the playoffs looking in have their total-points-needed for a wildcard spot calculated
# Pooper bowl teams are given their seed
full_playoff_picture = []
seed = 1
for team_data in itertools.chain(sorted_division_leaders, sorted_wildcard_leaders, sorted_rest_of_league):
    if seed <= fantasy_league.active_year_playoff_slots:
        team_data["seed"] = seed
    else:
        team_data["points_out"] = round(sorted_wildcard_leaders[-1].get("points_for") - team_data.get("points_for"), 2)
    if seed >= len(list(fantasy_league.teams_in_active_year())) - 1:
        team_data["seed"] = "P"
    full_playoff_picture.append(team_data)
    seed += 1

# Get the regular season games played by the first place person (should be the same as everyone else)
regular_season_games_played = (int(full_playoff_picture[0].get("losses")) +
                               int(full_playoff_picture[0].get("ties")) +
                               int(full_playoff_picture[0].get("wins")))

# First seed gets a bye, so they win game 1
full_playoff_picture.append(full_playoff_picture[0])
# Second seed gets a bye, so they win game 2
full_playoff_picture.append(full_playoff_picture[1])
# Who won the 4 vs 5 matchup?
for team in fantasy_league.teams_in_active_year():
    if team.name == full_playoff_picture[3].get("name"):
        for matchup in team.matchups:
            if matchup.week == regular_season_games_played + 1 and matchup.outcome == GameOutcome.WIN:
                full_playoff_picture.append(full_playoff_picture[3])
                break
            elif matchup.week == regular_season_games_played + 1 and matchup.outcome == GameOutcome.LOSS:
                full_playoff_picture.append(full_playoff_picture[4])
                break
# Who won the 3 vs 6 matchup?
for team in fantasy_league.teams_in_active_year():
    if team.name == full_playoff_picture[2].get("name"):
        for matchup in team.matchups:
            if matchup.week == regular_season_games_played + 1 and matchup.outcome == GameOutcome.WIN:
                full_playoff_picture.append(full_playoff_picture[2])
                break
            elif matchup.week == regular_season_games_played + 1 and matchup.outcome == GameOutcome.LOSS:
                full_playoff_picture.append(full_playoff_picture[5])
                break
# Who won the round 2 high seed matchup?
for team in fantasy_league.teams_in_active_year():
    if team.name == full_playoff_picture[0].get("name"):
        for matchup in team.matchups:
            if matchup.week == regular_season_games_played + 2 and matchup.outcome == GameOutcome.WIN:
                full_playoff_picture.append(full_playoff_picture[0])
                break
            elif matchup.week == regular_season_games_played + 2 and matchup.outcome == GameOutcome.LOSS:
                full_playoff_picture.append(full_playoff_picture[-2])
                break
# Who won the round 2 low seed matchup?
for team in fantasy_league.teams_in_active_year():
    if team.name == full_playoff_picture[1].get("name"):
        for matchup in team.matchups:
            if matchup.week == regular_season_games_played + 2 and matchup.outcome == GameOutcome.WIN:
                full_playoff_picture.append(full_playoff_picture[1])
                break
            elif matchup.week == regular_season_games_played + 2 and matchup.outcome == GameOutcome.LOSS:
                full_playoff_picture.append(full_playoff_picture[-2])
                break
# Who won the championship?
for team in fantasy_league.teams_in_active_year():
    if team.name == full_playoff_picture[-2].get("name"):
        for matchup in team.matchups:
            if matchup.week == regular_season_games_played + 3 and matchup.outcome == GameOutcome.WIN:
                full_playoff_picture.append(full_playoff_picture[-2])
                break
            elif matchup.week == regular_season_games_played + 3 and matchup.outcome == GameOutcome.LOSS:
                full_playoff_picture.append(full_playoff_picture[-1])
                break

# If there are less than a full bracket's worth of teams, the season isn't complete yet, so add blanks
for _ in range(FULL_BRACKET_SLOTS - len(full_playoff_picture)):
    full_playoff_picture.append({"name": ""})

# Now see if anyone has a clinched a playoff berth
simulated_berth = deepcopy(divisional_standings)

# Loop over the divisions in the berth simulation
for sim_division_data in simulated_berth.values():
    # Set the division leader's remaining games to losses
    leader = sim_division_data.pop(0)
    leader_name = leader.get("name")
    leader["losses"] += (fantasy_league.active_year_regular_season_length - regular_season_games_played)
    leader["points_for"] = -1
    # Set the other division teams remaining games to wins
    for other_player in sim_division_data:
        other_player["wins"] += (fantasy_league.active_year_regular_season_length - regular_season_games_played)
        other_player["divisional_wins"] = 4 - other_player.get("divisional_losses")
    # Re-insert the division leader
    sim_division_data.append(leader)
    # Recalculate the division's standings
    simulated_division = sorted(sim_division_data, key=lambda team_data: (
        team_data.get("wins"),
        team_data.get("divisional_wins"),
        team_data.get("points_for"),
    ), reverse=True)
    # See if the leader has changed
    simulated_leader = simulated_division.pop(0)
    simulated_leader_name = simulated_leader.get("name")
    # If it hasn't, find them in the playoff picture and update their name to indicate a division clinch
    if simulated_leader_name == leader_name:
        for current_lead in full_playoff_picture[:4]:
            if current_lead.get("name") == simulated_leader_name:
                current_lead["clinched"] = "* (clinched division)"

# Now see if anyone has a clinched a bye
simulated_bye = deepcopy(divisional_standings)
bye_holders = [s.get("name") for s in sorted_division_leaders[:2]]

# Loop over the divisions in the bye simulation
for sim_division_data in simulated_bye.values():
    # If the division leader is already in a top-two spot, set the division leader's remaining games to losses
    leader = sim_division_data.pop(0)
    leader_name = leader.get("name")
    if leader_name in bye_holders:
        leader["losses"] += (fantasy_league.active_year_regular_season_length - regular_season_games_played)
        leader["points_for"] = -1
    # If they were not already in a top-two spot, set their remaining games to wins
    else:
        leader["wins"] += (fantasy_league.active_year_regular_season_length - regular_season_games_played)
        leader["divisional_wins"] = 4 - other_player.get("divisional_losses")
    # Set the other division teams remaining games to wins
    for other_player in sim_division_data:
        other_player["wins"] += (fantasy_league.active_year_regular_season_length - regular_season_games_played)
        other_player["divisional_wins"] = 4 - other_player.get("divisional_losses")
    # Re-insert the division leader
    sim_division_data.append(leader)
    # Recalculate the division's standings in place for use below
    sim_division_data.sort(key=lambda team_data: (
        team_data.get("wins"),
        team_data.get("divisional_wins"),
        team_data.get("points_for"),
    ), reverse=True)

# Determine who is leading each division and store them in a dict {division_id: team_data}
sim_unsorted_division_leaders = {}
for sim_division, sim_division_data in simulated_bye.items():
    sim_unsorted_division_leaders[sim_division] = sim_division_data[0]

sim_sorted_division_leaders = sorted(sim_unsorted_division_leaders.values(),
                                     key=lambda team_data: (
                                         team_data.get("wins"),
                                         team_data.get("points_for"),
                                     ), reverse=True)

sim_bye_holders = [s.get("name") for s in sim_sorted_division_leaders[:2]]

for current_lead in full_playoff_picture[:2]:
    if current_lead.get("name") in sim_bye_holders:
        current_lead["clinched"] = "** (clinched bye)"

# Save the regular season snapshot to a JSON file for use by the site
snapshot_json_filename = f"{dir_path}/Playoff Snapshot.json"
with open(snapshot_json_filename, "w") as f:
    json.dump(full_playoff_picture, f)
