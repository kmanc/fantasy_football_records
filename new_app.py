import configparser
import json
import os
import pickle
import weakref
from copy import deepcopy
from datetime import date

from espn_api.football import League
from espn_api.requests.espn_requests import ESPNInvalidLeague

import utility
from new_fantasy_classes import FantasyLeague, Member

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

# Instantiate the league object
fantasy_league = FantasyLeague(S2, SWID, FIRST_YEAR, LEAGUE_ID)


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
        name = utility.clean_name(f'{member.get("firstName")} {member.get("lastName")}')
        member_id = member.get("id").replace("'", "").replace("{", "").replace("}", "")
        member_object = Member(weakref.proxy(fantasy_league), member_id, name)
        # If those identifiers match an existing league member, update the data for that member
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

    # Chances are the name hasn't changed, but on the off chance it has, update that
    fantasy_league.update_name(api_year.settings.name)


print(len(fantasy_league.members))
print(fantasy_league.active_year)
print(fantasy_league.max_completed_year)
from pprint import pprint
#pprint(vars(fantasy_league))
for member in fantasy_league.members:
    pprint(vars(member))


#print(vars(api_year.teams[0]))
#for m in fantasy_league.members:
#    print(m.name)
#print(vars(test.box_scores(3)))
#team_one = test.teams[0]
#print(vars(team_one))
#print(team_one)
