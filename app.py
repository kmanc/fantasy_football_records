import configparser
import os
import pickle
from copy import deepcopy
from fantasy_league import FantasyLeague
from flask import Flask, render_template
from flask_bootstrap import Bootstrap

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')

s2 = config["ESPN"]["s2"]
swid = config["ESPN"]["swid"]
league_id = int(config["ESPN"]["league_id"])
first_year = int(config["ESPN"]["league_founded"])
league_name = config["WEBSITE"]["league_name"].replace('"', '')
league_abbreviation = config["WEBSITE"]["league_abbreviation"].replace('"', '')

pickle_filename = f"{dir_path}/{league_name}.pickle"
if os.path.exists(pickle_filename):
    with open(pickle_filename, "rb") as f:
        league_instance = pickle.load(f)
    league_instance.update_espn_objects()
    league_instance.save_to_file(pickle_filename)
else:
    league_instance = FantasyLeague(s2, swid, first_year, league_id)
    league_instance.save_to_file(pickle_filename)

app = Flask(__name__)
Bootstrap(app)


def determine_bye_clinches(playoff_obj):
    simulation = deepcopy(league_instance)
    number_of_byes = 2
    current_byes = list(playoff_obj.keys())[:number_of_byes]

    for team in simulation.espn_objects.get(max(simulation.espn_objects)).teams:
        if team.team_name in current_byes:
            team.points_for = -1
        for outcome_index, outcome in enumerate(team.outcomes):
            if outcome == "U" and team.team_name in current_byes:
                team.outcomes[outcome_index] = "L"
            elif outcome == "U" and team.team_name not in current_byes:
                team.outcomes[outcome_index] = "W"

    simulation_picture = simulation.get_wffl_playoff_picture()
    simulation_byes = list(simulation_picture.keys())[:number_of_byes]

    for current_bye in current_byes:
        if current_bye in simulation_byes:
            playoff_obj[current_bye]["clinched"] = "** (clinched bye)"

    # I don't know if this is necessary but I'm trying to prevent carrying around large copied objects
    del simulation

    return playoff_obj


def determine_division_clinches(playoff_obj):
    simulation = deepcopy(league_instance)
    number_of_divisions = len(simulation.espn_objects.get(max(simulation.espn_objects)).settings.division_map)
    current_leads = list(playoff_obj.keys())[:number_of_divisions]

    for team in simulation.espn_objects.get(max(simulation.espn_objects)).teams:
        if team.team_name in current_leads:
            team.points_for = -1
        for outcome_index, outcome in enumerate(team.outcomes):
            if outcome == "U" and team.team_name in current_leads:
                team.outcomes[outcome_index] = "L"
            elif outcome == "U" and team.team_name not in current_leads:
                team.outcomes[outcome_index] = "W"

    simulation_picture = simulation.get_wffl_playoff_picture()
    simulation_leads = list(simulation_picture.keys())[:number_of_divisions]

    for current_lead in current_leads:
        if current_lead in simulation_leads:
            playoff_obj[current_lead]["clinched"] = "* (clinched division)"

    # I don't know if this is necessary but I'm trying to prevent carrying around large copied objects
    del simulation

    return playoff_obj


def format_owner_for_display(owner_obj):
    if owner_obj.active and owner_obj.joined == league_instance.founded:
        return owner_obj.name
    elif owner_obj.active:
        return f"{owner_obj.name}\N{ASTERISK} (Joined {owner_obj.joined})"
    return f"{owner_obj.name}\N{ASTERISK} ({owner_obj.joined} - {max(owner_obj.teams)})"


def format_weekly_records_for_display(records_obj):
    formatted = deepcopy(records_obj)
    for record in formatted:
        record["value"] = round(record.get("score"), 2)
        record["owner_name"] = format_owner_for_display(league_instance.owners.get(record.get("owner_name")))

    return formatted


def format_season_records_for_display(records_obj):
    formatted = deepcopy(records_obj)
    for record in formatted:
        record["value"] = round(record.get("points"), 2)
        record["owner_name"] = format_owner_for_display(record.get("owner"))

    return formatted


def format_lifetime_records_for_display(records_obj, percent=False):
    formatted = deepcopy(records_obj)
    for record in formatted:
        if percent:
            record["value"] = round(record.get("value") * 100, 2)
        else:
            record["value"] = round(record.get("value"), 2)
        record["owner_name"] = format_owner_for_display(record.get("owner"))

    return formatted


@app.route("/")
def index():
    return render_template('index.html',
                           title_prefix=league_abbreviation,
                           record_name="Home",
                           welcome_message=f"Welcome to the {league_name} online record book",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/snapshot")
def snapshot():
    playoff_picture = league_instance.get_wffl_playoff_picture()
    playoff_picture = determine_division_clinches(playoff_picture)
    playoff_picture = determine_bye_clinches(playoff_picture)
    number_of_playoff_teams = league_instance.espn_objects.get(league_instance.current_active_year).settings.playoff_team_count
    seeds_as_list = list(playoff_picture.keys())[:number_of_playoff_teams]
    return render_template('snapshot.html',
                           title_prefix=league_abbreviation,
                           records=playoff_picture,
                           record_name="Current playoff snapshot",
                           seeds=seeds_as_list,
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/championships")
def championships():
    records = sorted(({"owner": owner, "value": owner.calculate_championship_wins(league_instance.max_completed_year)}
                      for owner in league_instance.owners.values() if owner.calculate_championship_wins() > 0),
                     key=lambda x: x.get("value"), reverse=True)
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Championships",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/total_regular_season_points")
def total_regular_season_points():
    records = sorted(({"owner": owner, "value": owner.calculate_lifetime_regular_season_points()} for owner in
                      league_instance.owners.values()), key=lambda x: x.get("value"), reverse=True)
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="All time regular season points",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/total_playoff_points")
def total_playoff_points():
    records = sorted(({"owner": owner, "value": owner.calculate_lifetime_playoff_points()} for owner in
                      league_instance.owners.values() if owner.calculate_lifetime_playoff_points() > 0),
                     key=lambda x: x.get("value"), reverse=True)
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="All time playoff points",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/win_percent")
def win_percents():
    records = sorted(({"owner": owner, "value": owner.calculate_lifetime_win_percent()} for owner in
                      league_instance.owners.values()), key=lambda x: x.get("value"), reverse=True)
    records_for_display = format_lifetime_records_for_display(records, percent=True)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Win percentage",
                           percent="%",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/playoff_appearances")
def playoff_appearances():
    records = sorted(({"owner": owner, "value": owner.calculate_playoff_appearances()} for owner in
                      league_instance.owners.values() if owner.calculate_playoff_appearances() > 0),
                     key=lambda x: x.get("value"), reverse=True)
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Playoff appearances",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/highest_regular_season")
def highest_regular_seasons():
    records = league_instance.calculate_highest_regular_season_points()
    records_for_display = format_season_records_for_display(records)
    return render_template('table_no_week.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Most points in one season",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/lowest_regular_season")
def lowest_regular_seasons():
    records = league_instance.calculate_lowest_regular_season_points()
    records_for_display = format_season_records_for_display(records)
    return render_template('table_no_week.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Least points in one season",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/highest_week")
def highest_weeks():
    records = league_instance.calculate_highest_single_week_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Most points in one week",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/lowest_week")
def lowest_weeks():
    records = league_instance.calculate_lowest_single_week_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Least points in one week",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/lowest_win")
def lowest_wins():
    records = league_instance.calculate_lowest_win_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Least points that still won",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/highest_loss")
def highest_losses():
    records = league_instance.calculate_highest_loss_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name="Most points that still lost",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/head-to-head/<owner>")
def head_to_head(owner):
    owner = league_instance.owners.get(owner.strip().title())
    if owner is None:
        return render_template('index.html',
                               title_prefix=league_abbreviation,
                               record_name="Home",
                               welcome_message=f"Welcome to the {league_name} online record book",
                               owners=sorted((owner for owner in league_instance.owners)))
    records = sorted(({"owner": opponent, "value": owner.calculate_lifetime_win_percent_against(opponent.name)}
                      for opponent in league_instance.owners.values() if opponent.name != owner.name),
                     key=lambda x: x.get("value"), reverse=True)
    records_for_display = format_lifetime_records_for_display(records, percent=True)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=league_abbreviation,
                           record_name=f"Win percentages for {owner.name}",
                           percent="%",
                           owners=sorted(owner for owner in league_instance.owners))


@app.route("/meet_the_owners")
def meet_the_owners():
    active_owners = sorted(owner for owner in league_instance.owners if league_instance.owners.get(owner).active)
    return render_template('meet_the_owners.html',
                           title_prefix=league_abbreviation,
                           owners=sorted(owner for owner in league_instance.owners),
                           active=active_owners)


if __name__ == "__main__":
    # For testing
    app.run(debug=True)
    # For real
    #app.run(host="0.0.0.0")
