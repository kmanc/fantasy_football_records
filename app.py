import configparser
import json
import os
from flask import Flask, render_template

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')

league_name = config["WEBSITE"]["league_name"].replace('"', '')
league_abbreviation = config["WEBSITE"]["league_abbreviation"].replace('"', '')

app = Flask(__name__)


@app.route("/")
def index():
    return f"<p>Welcome to the {league_name}</p>"


@app.route("/championships")
def championships():
    with open("records/championships.json") as f:
        records = json.load(f)
    columns = ["owner", "value"]
    return render_template('championships.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/total_points")
def total_points():
    with open("records/total_points.json") as f:
        records = json.load(f)
    columns = ["owner", "value"]
    return render_template('total_points.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/win_percents")
def win_percents():
    with open("records/win_percents.json") as f:
        records = json.load(f)
    columns = ["owner", "value"]
    return render_template('win_percents.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/playoff_appearances")
def playoff_appearances():
    with open("records/playoff_appearances.json") as f:
        records = json.load(f)
    columns = ["owner", "value"]
    return render_template('playoff_appearances.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/highest_regular_seasons")
def highest_regular_seasons():
    with open("records/highest_regular_seasons.json") as f:
        records = json.load(f)
    columns = ["owner", "team", "year", "value"]
    return render_template('highest_regular_seasons.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/lowest_regular_seasons")
def lowest_regular_seasons():
    with open("records/lowest_regular_seasons.json") as f:
        records = json.load(f)
    columns = ["owner", "team", "year", "value"]
    return render_template('lowest_regular_seasons.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/highest_weeks")
def highest_weeks():
    with open("records/highest_weeks.json") as f:
        records = json.load(f)
    columns = ["owner", "team", "year", "week", "value"]
    return render_template('highest_weeks.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/lowest_weeks")
def lowest_weeks():
    with open("records/lowest_weeks.json") as f:
        records = json.load(f)
    columns = ["owner", "team", "year", "week", "value"]
    return render_template('lowest_weeks.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/lowest_wins")
def lowest_wins():
    with open("records/lowest_wins.json") as f:
        records = json.load(f)
    columns = ["owner", "team", "year", "week", "value"]
    return render_template('lowest_wins.html', records=records, colnames=columns, title_prefix=league_abbreviation)


@app.route("/highest_losses")
def highest_losses():
    with open("records/highest_losses.json") as f:
        records = json.load(f)
    columns = ["owner", "team", "year", "week", "value"]
    return render_template('highest_losses.html', records=records, colnames=columns, title_prefix=league_abbreviation)


if __name__ == "__main__":
    app.run(debug=True)
