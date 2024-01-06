import configparser
import json
import os
import pickle
from flask import Flask, render_template
from flask_bootstrap import Bootstrap

from fantasy_enums import GameOutcome

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f"{dir_path}/config.ini")

S2 = config["ESPN"]["s2"]
SWID = config["ESPN"]["swid"]
LEAGUE_ID = int(config["ESPN"]["league_id"])
FIRST_YEAR = int(config["ESPN"]["league_founded"])
LEAGUE_NAME = config["WEBSITE"]["league_name"].replace('"', '')
LEAGUE_ABBREVIATION = config["WEBSITE"]["league_abbreviation"].replace('"', '')
MEET_THE_MANAGERS_ASSETS = os.path.join("static/meet_the_managers")
MANAGER_BIOS_PATH = os.path.join(MEET_THE_MANAGERS_ASSETS, "manager_bios.json")

league_pickle_filename = f"{dir_path}/{LEAGUE_NAME}.pickle"
if os.path.exists(league_pickle_filename):
    with open(league_pickle_filename, "rb") as f:
        fantasy_league = pickle.load(f)
else:
    print(f"Could not find pickled league instance at {league_pickle_filename}")
    exit(1)
    
snapshot_json_filename = f"{dir_path}/Playoff Snapshot.json"
if os.path.exists(snapshot_json_filename):
    with open(snapshot_json_filename, "r") as f:
        standings_snapshot = json.load(f)
else:
    print(f"Could not find the regular season snapshot list at {snapshot_json_filename}")
    exit(1)

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


@app.context_processor
def handle_context():
    return dict(os=os)


@app.route("/")
def index():
    return render_template("index.html",
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Home",
                           welcome_message=f"Welcome to the {LEAGUE_NAME} online record book",
                           members=SORTED_MANAGERS)


@app.route("/snapshot")
def snapshot():
    return render_template('snapshot.html',
                           title_prefix=LEAGUE_ABBREVIATION,
                           records=standings_snapshot[:len(list(fantasy_league.teams_in_active_year()))],
                           record_name="Current playoff snapshot",
                           seeds=standings_snapshot,
                           owners=SORTED_MANAGERS)


@app.route("/championships")
def championships():
    records = [{"member": format_member_for_display(member),
                "value": member.championship_wins(), }
               for member in
               sorted(fantasy_league.members_with_championship(), key=lambda member: member.championship_wins(), reverse=True)]
    return render_template("table_minimal.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Championships",
                           members=SORTED_MANAGERS)


@app.route("/total_regular_season_points")
def total_regular_season_points():
    records = [{"member": format_member_for_display(member),
                "value": member.regular_season_points(),
                "average": member.regular_season_average_points(), }
               for member in sorted((member for member in fantasy_league.members), key=lambda member: member.regular_season_points(), reverse=True)]
    return render_template("table_with_average.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="All time regular season points",
                           members=SORTED_MANAGERS)


@app.route("/total_playoff_points")
def total_playoff_points():
    records = [{"member": format_member_for_display(member),
                "value": member.playoff_points(),
                "average": member.playoff_average_points(), }
               for member in
               sorted((member for member in fantasy_league.members_with_playoff_appearances()), key=lambda member: member.playoff_points(), reverse=True)]
    return render_template("table_with_average.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="All time playoff points",
                           members=SORTED_MANAGERS)


@app.route("/win_percent")
def win_percents():
    records = [{"member": format_member_for_display(member),
                "value": member.regular_season_win_percentage(), }
               for member in
               sorted(fantasy_league.members, key=lambda member: member.regular_season_win_percentage(), reverse=True)]
    return render_template("table_minimal.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Win percentage",
                           percent="%",
                           members=SORTED_MANAGERS)


@app.route("/playoff_appearances")
def playoff_appearances():
    records = [{"member": format_member_for_display(member),
                "value": member.playoff_appearances(), }
               for member in sorted((member for member in fantasy_league.members if member.playoff_appearances()),
                                    key=lambda member: member.playoff_appearances(), reverse=True)]
    return render_template("table_minimal.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Playoff appearances",
                           members=SORTED_MANAGERS)


@app.route("/highest_regular_season")
def highest_regular_seasons():
    records = [{"member": format_member_for_display(team.member),
                "team": team.name,
                "value": team.regular_season_points_scored(),
                "year": team.year, }
               for team in fantasy_league.teams_by_regular_season_points_for()[:10]]
    return render_template("table_no_week.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Most points in one season",
                           members=SORTED_MANAGERS)


@app.route("/lowest_regular_season")
def lowest_regular_seasons():
    records = [{"member": format_member_for_display(team.member),
                "team": team.name,
                "value": team.regular_season_points_scored(),
                "year": team.year, }
               for team in fantasy_league.teams_by_regular_season_points_for()[:-10:-1]]
    return render_template("table_no_week.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Least points in one season",
                           members=SORTED_MANAGERS)


@app.route("/best_defense")
def best_defenses():
    records = [{"member": format_member_for_display(team.member),
                "team": team.name,
                "value": team.regular_season_points_against(),
                "year": team.year, }
               for team in fantasy_league.teams_by_regular_season_points_against()[:-10:-1]]
    return render_template("table_no_week.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Least points against in one season",
                           members=SORTED_MANAGERS)


@app.route("/worst_defense")
def worst_defenses():
    records = [{"member": format_member_for_display(team.member),
                "team": team.name,
                "value": team.regular_season_points_against(),
                "year": team.year, }
               for team in fantasy_league.teams_by_regular_season_points_against()[:10]]
    return render_template("table_no_week.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Most points against in one season",
                           members=SORTED_MANAGERS)


@app.route("/highest_week")
def highest_weeks():
    records = [{"member": format_member_for_display(matchup.team.member),
                "team": matchup.team.name,
                "value": matchup.points_for,
                "week": matchup.week,
                "year": matchup.team.year, }
               for matchup in fantasy_league.matchups_by_points_for()[:10]]
    return render_template("table_full.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Most points in one week",
                           members=SORTED_MANAGERS)


@app.route("/lowest_week")
def lowest_weeks():
    records = [{"member": format_member_for_display(matchup.team.member),
                "team": matchup.team.name,
                "value": matchup.points_for,
                "week": matchup.week,
                "year": matchup.team.year, }
               for matchup in fantasy_league.matchups_by_points_for()[:-10:-1]]
    return render_template("table_full.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Least points in one week",
                           members=SORTED_MANAGERS)


@app.route("/lowest_win")
def lowest_wins():
    matchups = sorted((matchup for matchup in fantasy_league.matchup_superset() if matchup.outcome == GameOutcome.WIN),
                      key=lambda matchup: matchup.points_for)
    records = [{"member": format_member_for_display(matchup.team.member),
                "team": matchup.team.name,
                "value": matchup.points_for,
                "week": matchup.week,
                "year": matchup.team.year}
               for matchup in matchups][:10]
    return render_template("table_full.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Least points that still won",
                           members=SORTED_MANAGERS)


@app.route("/highest_loss")
def highest_losses():
    matchups = sorted((matchup for matchup in fantasy_league.matchup_superset() if matchup.outcome == GameOutcome.LOSS),
                      key=lambda matchup: matchup.points_for, reverse=True)
    records = [{"member": format_member_for_display(matchup.team.member),
                "team": matchup.team.name,
                "value": matchup.points_for,
                "week": matchup.week,
                "year": matchup.team.year}
               for matchup in matchups][:10]
    return render_template("table_full.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name="Most points that still lost",
                           members=SORTED_MANAGERS)


@app.route("/head-to-head/<member_name>")
def head_to_head(member_name):
    member_name = member_name.strip().title()
    if member_name is None:
        return render_template("index.html",
                               title_prefix=LEAGUE_ABBREVIATION,
                               record_name="Home",
                               welcome_message=f"Welcome to the {LEAGUE_NAME} online record book",
                               members=SORTED_MANAGERS)
    winrates = []
    for member in fantasy_league.members:
        if member.name == member_name:
            matchups = member.matchup_superset()
            for opponent in fantasy_league.members:
                if opponent.id == member.id:
                    continue
                games_against = [matchup for matchup in matchups if matchup.opponent.member.name == opponent.name]
                wins = len([game for game in games_against if game.outcome == GameOutcome.WIN])
                try:
                    winrate = round(wins * 100 / len(games_against), 2)
                    winrates.append({
                        "member": format_member_for_display(opponent),
                        "value": winrate
                    })
                except ZeroDivisionError:
                    continue

    records = sorted(winrates, key=lambda x: x.get("value"), reverse=True)

    return render_template("table_minimal.html",
                           records=records,
                           title_prefix=LEAGUE_ABBREVIATION,
                           record_name=f"Win percentages for {member_name}",
                           percent="%",
                           members=SORTED_MANAGERS)


@app.route("/meet_the_managers")
def meet_the_managers():
    managers = []
    for name in sorted(member.name for member in fantasy_league.members if member.left_year == fantasy_league.active_year):
        managers.append(
            {"display_name": name, "key_name": name.lower().replace(" ", "")}
        )

    with open(MANAGER_BIOS_PATH, "r") as g:
        bios = json.loads(g.read())

    return render_template("meet_the_managers.html",
                           title_prefix=LEAGUE_ABBREVIATION,
                           managers=managers,
                           record_name=f"Meet the members",
                           bios=bios,
                           meet_the_managers_assets=MEET_THE_MANAGERS_ASSETS,
                           members=SORTED_MANAGERS)


if __name__ == "__main__":
    # For testing
    app.run(debug=True)
    # For real
    # app.run(host="0.0.0.0")
