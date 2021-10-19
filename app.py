import configparser
import json
import os
from flask import Flask, render_template
from flask_bootstrap import Bootstrap

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')

league_name = config["WEBSITE"]["league_name"].replace('"', '')
league_abbreviation = config["WEBSITE"]["league_abbreviation"].replace('"', '')

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
    with open("records/championships.json") as f:
        records = json.load(f)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Championships")


@app.route("/total_regular_season_points")
def total_regular_season_points():
    with open("records/total_regular_season_points.json") as f:
        records = json.load(f)
    for record in records:
        record['value'] = round(record.get("value"), 2)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="All time regular season points")


@app.route("/total_points")
def total_points():
    with open("records/total_points.json") as f:
        records = json.load(f)
    for record in records:
        record['value'] = round(record.get("value"), 2)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="All time points")


@app.route("/win_percent")
def win_percents():
    with open("records/win_percents.json") as f:
        records = json.load(f)
    for record in records:
        record['value'] = f"{str(round(record.get('value'), 3) * 100)[:4]}%"
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Win percentage")


@app.route("/playoff_appearances")
def playoff_appearances():
    with open("records/playoff_appearances.json") as f:
        records = json.load(f)
    return render_template('table_minimal.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Playoff appearances")


@app.route("/highest_regular_season")
def highest_regular_seasons():
    with open("records/highest_regular_seasons.json") as f:
        records = json.load(f)
    return render_template('table_no_week.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Most points in one season")


@app.route("/lowest_regular_season")
def lowest_regular_seasons():
    with open("records/lowest_regular_seasons.json") as f:
        records = json.load(f)
    return render_template('table_no_week.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Least points in one season")


@app.route("/highest_week")
def highest_weeks():
    with open("records/highest_weeks.json") as f:
        records = json.load(f)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Most points in one week")


@app.route("/lowest_week")
def lowest_weeks():
    with open("records/lowest_weeks.json") as f:
        records = json.load(f)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Least points in one week")


@app.route("/lowest_win")
def lowest_wins():
    with open("records/lowest_wins.json") as f:
        records = json.load(f)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Least points that still won")


@app.route("/highest_loss")
def highest_losses():
    with open("records/highest_losses.json") as f:
        records = json.load(f)
    return render_template('table_full.html',
                           records=records,
                           title_prefix=league_abbreviation,
                           record_name="Most points that still lost")


if __name__ == "__main__":
    # For testing
    app.run(debug=True)
    # For real
    #app.run(host="0.0.0.0")
