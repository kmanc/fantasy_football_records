import configparser
import os
import pickle
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


@app.route("/")
def index():
    return render_template('index.html',
                           title_prefix=league_abbreviation,
                           record_name="Home",
                           welcome_message=f"Welcome to the {league_name} online record book")


@app.route("/championships")
def championships():
    records = sorted(({"owner": owner.name, "value": owner.calculate_championship_wins()} for owner in
                      league_instance.owners.values() if owner.calculate_championship_wins() > 0),
                     key=lambda x: x.get("value"), reverse=True)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Championships")


@app.route("/total_regular_season_points")
def total_regular_season_points():
    records = sorted(({"owner": owner.name, "value": owner.calculate_lifetime_regular_season_points()} for owner in
                      league_instance.owners.values()), key=lambda x: x.get("value"), reverse=True)
    for record in records:
        record['value'] = round(record.get("value"), 2)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="All time regular season points")


@app.route("/total_playoff_points")
def total_playoff_points():
    records = sorted(({"owner": owner.name, "value": owner.calculate_lifetime_playoff_points()} for owner in
                      league_instance.owners.values() if owner.calculate_lifetime_playoff_points() > 0),
                     key=lambda x: x.get("value"), reverse=True)
    for record in records:
        record['value'] = round(record.get("value"), 2)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="All time playoff points")


@app.route("/win_percent")
def win_percents():
    records = sorted(({"owner": owner.name, "value": owner.calculate_lifetime_win_percent()} for owner in
                      league_instance.owners.values()), key=lambda x: x.get("value"), reverse=True)
    for record in records:
        record['value'] = round(record.get("value"), 4) * 100
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Win percentage",
                           percent="%")


@app.route("/playoff_appearances")
def playoff_appearances():
    records = sorted(({"owner": owner.name, "value": owner.calculate_playoff_appearances()} for owner in
                      league_instance.owners.values() if owner.calculate_playoff_appearances() > 0),
                     key=lambda x: x.get("value"), reverse=True)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Playoff appearances")


@app.route("/highest_regular_season")
def highest_regular_seasons():
    records = league_instance.calculate_highest_regular_season_points()
    for record in records:
        record['value'] = round(record.get("points"), 2)
    return render_template('table_no_week.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Most points in one season")


@app.route("/lowest_regular_season")
def lowest_regular_seasons():
    records = league_instance.calculate_lowest_regular_season_points()
    for record in records:
        record['value'] = round(record.get("points"), 2)
    return render_template('table_no_week.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Least points in one season")


@app.route("/highest_week")
def highest_weeks():
    records = league_instance.calculate_highest_single_week_points()
    for record in records:
        record['value'] = round(record.get("score"), 2)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Most points in one week")


@app.route("/lowest_week")
def lowest_weeks():
    records = league_instance.calculate_lowest_single_week_points()
    for record in records:
        record['value'] = round(record.get("score"), 2)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Least points in one week")


@app.route("/lowest_win")
def lowest_wins():
    records = league_instance.calculate_lowest_win_points()
    for record in records:
        record['value'] = round(record.get("score"), 2)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Least points that still won")


@app.route("/highest_loss")
def highest_losses():
    records = league_instance.calculate_highest_loss_points()
    for record in records:
        record['value'] = round(record.get("score"), 2)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Most points that still lost")


if __name__ == "__main__":
    # For testing
    app.run(debug=True)
    # For real
    #app.run(host="0.0.0.0")
