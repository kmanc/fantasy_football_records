import configparser
import os
import pickle
import weakref
from datetime import date
from espn_api.football import League
from espn_api.requests.espn_requests import ESPNInvalidLeague

import utility
from new_fantasy_classes import FantasyLeague, Matchup, Member, Team
from new_fantasy_enums import GameOutcome, GameType

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

# Placeholders for BYE weeks
PLACEHOLDER_LEAGUE = FantasyLeague("", "", 99999, 99999)
PLACEHOLDER_MEMBER = Member(weakref.proxy(PLACEHOLDER_LEAGUE), "", "")
PLACEHOLDER_TEAM = Team(99999, 99999, "", weakref.proxy(PLACEHOLDER_MEMBER), 99999)

# Create a new instance of a league from the config values
fantasy_league = FantasyLeague(S2, SWID, FIRST_YEAR, LEAGUE_ID)

# Override the new instance if one is already saved on disk
pickle_filename = f"TEST.pickle"
if os.path.exists(pickle_filename):
    with open(pickle_filename, "rb") as f:
        print("LOADING FROM DISK")
        fantasy_league = pickle.load(f)


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
        member_object = Member(weakref.proxy(fantasy_league), member_id, name)
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
            if any(member.id == utility.clean_user_id(team_owner) for team_owner in team.owners):
                # Use the ESPN team ID and year to generate a true team ID
                team_id = utility.generate_team_id(espn_id, api_year.year)
                # If the owner already has a record of that team, update the record
                for existing_team in member.teams:
                    if existing_team.id == team_id:
                        existing_team.update_losses(team.losses)
                        existing_team.update_ties(team.ties)
                        existing_team.update_wins(team.wins)
                        break
                # If the loop completed without a break (IE there was no match to an existing member's teams)
                # Add the new team to the member
                else:
                    team_name = utility.clean_team_name(member.name, api_year.year, team.team_name)
                    team_object = Team(team.division_id, espn_id, team_name, weakref.proxy(member), api_year.year)
                    team_object.update_losses(team.losses)
                    team_object.update_ties(team.ties)
                    team_object.update_wins(team.wins)
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
                if team.id == home_team_id:
                    # If there was no away team, throw in a placeholder
                    if away_team_id is None:
                        opponent = PLACEHOLDER_TEAM
                    # If there was an away team, find it
                    else:
                        opponent = [opponent for opponent in this_years_teams if opponent.id == away_team_id][0]
                    # Set the outcome to a win
                    outcome = GameOutcome.WIN
                    # Change it to a loss if the away team scored more points
                    if matchup.home_score < matchup.away_score:
                        outcome = GameOutcome.LOSS
                    # Or change it to a tie if the teams had the same amount of points
                    elif matchup.home_score == matchup.away_score:
                        outcome = GameOutcome.TIE
                    # Create a matchup object based on the information gathered
                    matchup_object = Matchup(opponent, outcome, matchup.away_score,
                                             matchup.home_score, team, matchup_type, week)
                    # If this matchup is not already in the matchup set for a given team, add it
                    if not any(matchup_object.same(existing) for existing in team.matchups):
                        team.add_matchup(matchup_object)
                elif team.id == away_team_id:
                    # If there was no away team, throw in a placeholder
                    if home_team_id is None:
                        opponent = PLACEHOLDER_TEAM
                    # If there was a home team, find it
                    else:
                        opponent = [opponent for opponent in this_years_teams if opponent.id == home_team_id][0]
                    # Set the outcome to a win
                    outcome = GameOutcome.WIN
                    # Change it to a loss if the home team scored more points
                    if matchup.home_score > matchup.away_score:
                        outcome = GameOutcome.LOSS
                    # Or change it to a tie if the teams had the same amount of points
                    elif matchup.home_score == matchup.away_score:
                        outcome = GameOutcome.TIE
                    # Create a matchup object based on the information gathered
                    matchup_object = Matchup(opponent, outcome, matchup.home_score,
                                             matchup.away_score, team, matchup_type, week)
                    # If this matchup is not already in the matchup set for a given team, add it
                    if not any(matchup_object.same(existing) for existing in team.matchups):
                        team.add_matchup(matchup_object)


with open(pickle_filename, "wb") as f:
    pickle.dump(fantasy_league, f)

from pprint import pprint
# Number of people in the league
print(len(fantasy_league.members), "|| should be 14")
# Maximum completed year for the league
print(fantasy_league.max_completed_year, "|| should be 2023")
# Number of games each member has played
for member in fantasy_league.members:
    print(member.name, "-", len(member.matchup_superset()))
# My all-time points for
pts = 0
for member in fantasy_league.members:
    if "C487AA1C-6659-4FF7-B681-E33F72523AAD" == member.id:
        for team in member.teams:
            for matchup in team.matchups:
                if matchup.type == GameType.REGULAR_SEASON:
                    pts += matchup.points_for
print(pts)
# My 2023 team
for member in fantasy_league.members:
    if "C487AA1C-6659-4FF7-B681-E33F72523AAD" == member.id:
        for team in member.teams:
            if team.year == 2023:
                pprint(vars(team))

