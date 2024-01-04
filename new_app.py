import configparser
import json
import os
import pickle

from flask import Flask, render_template
from flask_bootstrap import Bootstrap

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

pickle_filename = f"{dir_path}/{LEAGUE_NAME}.pickle"
if os.path.exists(pickle_filename):
    with open(pickle_filename, "rb") as f:
        fantasy_league = pickle.load(f)
else:
    print(f"Could not find pickled league instance at {pickle_filename}")
    exit(0)

app = Flask(__name__)
Bootstrap(app)
SORTED_MANAGERS = sorted(member.name for member in fantasy_league.members)


def format_member_for_display(member_obj):
    # Member was a founding member of the league and is still active
    if member_obj.joined_year == fantasy_league.founded_year and member_obj.left_year == fantasy_league.active_year:
        return member_obj.name
    # Member was a founding member of the league but is no longer active
    if member_obj.joined_year == fantasy_league.founded_year and member_obj.left_year < fantasy_league.active_year:
        return f"{member_obj.name}\N{ASTERISK} (Left {member_obj.left_year})"
    # Member joined the league after it was founded, but is still active
    elif member_obj.left_year == fantasy_league.active_year:
        return f"{member_obj.name}\N{ASTERISK} (Joined {member_obj.joined_year})"
    # Member joined the league after it was founded, and is no longer active
    return f"{member_obj.name}\N{ASTERISK} ({member_obj.joined_year} - {member_obj.left_year})"


def format_weekly_records_for_display(records_obj):
    for record in records_obj:
        record["value"] = round(record.get("score"), 2)
        record["member_name"] = format_member_for_display(fantasy_league.members.get(record.get("member_name")))

    return records_obj


def format_season_records_for_display(records_obj):
    for record in records_obj:
        record["value"] = record.get("value")
        record["member_name"] = format_member_for_display(record.get("member"))

    return records_obj


def format_lifetime_records_for_display(records_obj):
    for record in records_obj:
        record["member_name"] = format_member_for_display(record.get("member"))

    return records_obj


@app.context_processor
def handle_context():
    return dict(os=os)


@app.route("/")
def index():
    return render_template('index.html',
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Home",
                           welcome_message=f"Welcome to the {LEAGUE_NAME} online record book",
                           members=SORTED_MANAGERS)


@app.route("/championships")
def championships():
    members = sorted((member for member in fantasy_league.members if member.championship_wins()),
                     key=lambda member: member.championship_wins(), reverse=True)
    records = [{"member": member, "value": member.championship_wins()} for member in members]
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Championships",
                           members=SORTED_MANAGERS)


@app.route("/total_regular_season_points")
def total_regular_season_points():
    members = sorted((member for member in fantasy_league.members),
                     key=lambda member: member.regular_season_points(), reverse=True)
    records = [{"member": member, "value": member.regular_season_points()} for member in members]
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="All time regular season points",
                           members=SORTED_MANAGERS)


@app.route("/total_playoff_points")
def total_playoff_points():
    members = sorted((member for member in fantasy_league.members if member.playoff_points()),
                     key=lambda member: member.playoff_points(), reverse=True)
    records = [{"member": member, "value": member.playoff_points()} for member in members]
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="All time playoff points",
                           members=SORTED_MANAGERS)


@app.route("/win_percent")
def win_percents():
    members = sorted((member for member in fantasy_league.members),
                     key=lambda member: member.regular_season_win_percentage(), reverse=True)
    records = [{"member": member, "value": member.regular_season_win_percentage()} for member in members]
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Win percentage",
                           percent="%",
                           members=SORTED_MANAGERS)


@app.route("/playoff_appearances")
def playoff_appearances():
    members = sorted((member for member in fantasy_league.members if member.playoff_appearances()),
                     key=lambda member: member.playoff_appearances(), reverse=True)
    records = [{"member": member, "value": member.playoff_appearances()} for member in members]
    records_for_display = format_lifetime_records_for_display(records)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Playoff appearances",
                           members=SORTED_MANAGERS)


@app.route("/highest_regular_season")
def highest_regular_seasons():
    teams = sorted((team for team in fantasy_league.team_superset()),
                   key=lambda team: team.regular_season_points_scored(), reverse=True)
    for team in teams:
        print(vars(team.member))
        print(team.member.name)
    records = [{"member": team.member.name, "value": team.regular_season_points_scored()} for team in teams]
    records_for_display = format_season_records_for_display(records)
    return render_template('table_no_week.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Most points in one season",
                           members=SORTED_MANAGERS)


@app.route("/lowest_regular_season")
def lowest_regular_seasons():
    records = fantasy_league.calculate_lowest_regular_season_points()
    records_for_display = format_season_records_for_display(records)
    return render_template('table_no_week.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Least points in one season",
                           members=SORTED_MANAGERS)


@app.route("/highest_week")
def highest_weeks():
    records = fantasy_league.calculate_highest_single_week_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Most points in one week",
                           members=SORTED_MANAGERS)


@app.route("/lowest_week")
def lowest_weeks():
    records = fantasy_league.calculate_lowest_single_week_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Least points in one week",
                           members=SORTED_MANAGERS)


@app.route("/lowest_win")
def lowest_wins():
    records = fantasy_league.calculate_lowest_win_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Least points that still won",
                           members=SORTED_MANAGERS)


@app.route("/highest_loss")
def highest_losses():
    records = fantasy_league.calculate_highest_loss_points()
    records_for_display = format_weekly_records_for_display(records)
    return render_template('table_full.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Most points that still lost",
                           members=SORTED_MANAGERS)


@app.route("/head-to-head/<member>")
def head_to_head(member):
    member = fantasy_league.members.get(member.strip().title())
    if member is None:
        return render_template('index.html',
                               title_prefix=LEAGUE_ABBREVIATION,
                               record_name="Home",
                               welcome_message=f"Welcome to the {LEAGUE_NAME} online record book",
                               members=SORTED_MANAGERS)
    records = sorted(({"member": opponent, "value": member.calculate_lifetime_win_percent_against(opponent.name)}
                      for opponent in fantasy_league.members.values() if opponent.name != member.name),
                     key=lambda x: x.get("value"), reverse=True)
    records_for_display = format_lifetime_records_for_display(records, percent=True)
    return render_template('table_minimal.html',
                           records=records_for_display,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name=f"Win percentages for {member.name}",
                           percent="%",
                           members=SORTED_MANAGERS)


@app.route("/meet_the_managers")
def meet_the_managers():
    managers = []
    for manager in SORTED_MANAGERS:
        if fantasy_league.members.get(manager).active:
            managers.append(
                {'display_name': manager, 'key_name': manager.lower().replace(' ', '')}
            )

    with open(MANAGER_BIOS_PATH, 'r') as f:
        bios = json.loads(f.read())

    return render_template('meet_the_managers.html',
                           title_prefix=LEAGUE_ABBREVIATION,
                           managers=managers,
                           bios=bios,
                           meet_the_managers_assets=MEET_THE_MANAGERS_ASSETS,
                           members=SORTED_MANAGERS)


if __name__ == "__main__":
    # For testing
    app.run(debug=True)
    # For real
    # app.run(host="0.0.0.0")
