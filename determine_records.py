import configparser
import heapq
import json
import os
from collections import Counter
from datetime import date

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')


first_year = int(config["ESPN"]["league_founded"])
current_year = date.today().year
champ_list = []
playoff_appearances = []
win_percents = {}
all_games = {}
all_wins = {}
all_losses = {}
yearly_totals = {}
single_regular_season = {}


def is_champ(owner_data, data_year):
	if data_year <= 2020 and owner_data.get("week_16", {}).get("result") == "win":
		return True
	if owner_data.get("week_17", {}).get("result") == "win":
		return True


def in_playoffs(owner_data, data_year):
	if data_year == 2014 or data_year > 2020:
		if owner_data.get("week_15"):
			return True
	if owner_data.get("week_14"):
		return True


def win_counts(owner_data):
	ws = 0
	total = 0
	for game in owner_data.values():
		try:
			result = game.get("result")
		except AttributeError:
			continue
		if result == "win":
			ws += 1
			total += 1
		elif result in ["loss", "tie"]:
			total += 1

	return ws, total


def flatten_all(owner_name, owner_data, data_year):
	flat_all = {}
	flat_wins = {}
	flat_losses = {}
	team_name = owner_data.get("team_name")
	for week, game in owner_data.items():
		if "week" in week:
			combined_key = f"{owner_name}||{team_name}||{data_year}||{week.title().replace('_', ' ')}"
			flat_all[combined_key] = game.get("score")
			if game.get('result') == "win":
				flat_wins[combined_key] = game.get("score")
			elif game.get('result') == "loss":
				flat_losses[combined_key] = game.get("score")

	return flat_all, flat_wins, flat_losses


def calculate_percent(in_dict):
	return in_dict.get("wins") / in_dict.get("games")


def process_key(combined_key):
	split_key = combined_key.split("||")
	return {"owner": split_key[0], "team": split_key[1], "year": split_key[2], "week": split_key[3]}


def sum_points(owner_data, data_year):
	total_points = []
	regular_season_points = []
	for week, game in owner_data.items():
		if "week" in week:
			total_points.append(game.get("score"))
			regular_season_end = 13
			if data_year == 2014 or data_year > 2020:
				regular_season_end = 14
			this_week = int(week.split("_")[-1])
			if "week" in week and this_week <= regular_season_end:
				regular_season_points.append(game.get("score"))

	total_points = sum(total_points)
	regular_season_points = sum(regular_season_points)
	playoff_points = total_points - regular_season_points

	return total_points, regular_season_points, playoff_points


for year in range(first_year, current_year + 1):
	try:
		with open(f"past_years/{year}.json") as f:
			file_data = json.loads(f.read())
			for owner, data in file_data.items():
				if is_champ(data, year):
					champ_list.append(owner)
				if in_playoffs(data, year):
					playoff_appearances.append(owner)
				tot_points, reg_points, play_points = sum_points(data, year)
				if owner in yearly_totals:
					yearly_totals[owner][year] = {"total": tot_points, "regular_season": reg_points, "playoff": play_points, "name": data.get("team_name")}
				else:
					yearly_totals[owner] = {year: {"total": tot_points, "regular_season": reg_points, "playoff": play_points, "name": data.get("team_name")}}
				wins, played = win_counts(data)
				if owner in win_percents:
					win_percents[owner]["wins"] += wins
					win_percents[owner]["games"] += played
				else:
					win_percents[owner] = {"wins": wins, "games": played}
				any_game, win_game, loss_game = flatten_all(owner, data, year)
				all_games.update(any_game)
				all_wins.update(win_game)
				all_losses.update(loss_game)
	except FileNotFoundError:
		pass


for owner, years_data in yearly_totals.items():
	for year, year_data in years_data.items():
		if year == current_year:
			continue
		single_regular_season[year_data.get("regular_season")] = {"year": year, "owner": owner, "team_name": year_data.get("name")}


with open("records/championships.json", "w") as f:
	champs = []
	champs_count = Counter(champ_list)
	most_champs = heapq.nlargest(10, champs_count, key=champs_count.get)
	for owner in most_champs:
		champs.append({"owner": owner, "value": champs_count.get(owner)})
	f.write(json.dumps(champs))


with open("records/playoff_appearances.json", "w") as f:
	playoffs = []
	playoffs_count = Counter(playoff_appearances)
	most_playoffs = heapq.nlargest(10, playoffs_count, key=playoffs_count.get)
	for owner in most_playoffs:
		playoffs.append({"owner": owner, "value": playoffs_count.get(owner)})
	f.write(json.dumps(playoffs))


with open("records/win_percents.json", "w") as f:
	ordered = sorted(win_percents, key=lambda x: calculate_percent(win_percents.get(x)), reverse=True)
	actual_percents = [{"owner": name, "value": calculate_percent(win_percents.get(name))} for name in ordered]
	f.write(json.dumps(actual_percents))


with open("records/highest_weeks.json", "w") as f:
	highest_weeks = heapq.nlargest(10, all_games, key=all_games.get)
	actual_highest = []
	for key in highest_weeks:
		entry = process_key(key)
		entry["value"] = all_games.get(key)
		actual_highest.append(entry)
	f.write(json.dumps(actual_highest))


with open("records/lowest_weeks.json", "w") as f:
	lowest_weeks = heapq.nsmallest(10, all_games, key=all_games.get)
	actual_lowest = []
	for key in lowest_weeks:
		entry = process_key(key)
		entry["value"] = all_games.get(key)
		actual_lowest.append(entry)
	f.write(json.dumps(actual_lowest))


with open("records/highest_losses.json", "w") as f:
	highest_losses = heapq.nlargest(10, all_losses, key=all_losses.get)
	actual_highest = []
	for key in highest_losses:
		entry = process_key(key)
		entry["value"] = all_losses.get(key)
		actual_highest.append(entry)
	f.write(json.dumps(actual_highest))


with open("records/lowest_wins.json", "w") as f:
	lowest_wins = heapq.nsmallest(10, all_wins, key=all_wins.get)
	actual_lowest = []
	for key in lowest_wins:
		entry = process_key(key)
		entry["value"] = all_wins.get(key)
		actual_lowest.append(entry)
	f.write(json.dumps(actual_lowest))


with open("records/total_points.json", "w") as f:
	all_time_points = {}
	for owner, seasons in yearly_totals.items():
		all_time_points[owner] = sum(season.get("total") for season in seasons.values())
	highest_all_time_points = heapq.nlargest(10, all_time_points, key=all_time_points.get)
	actual_highest = []
	for key in highest_all_time_points:
		actual_highest.append({"owner": key, "value": all_time_points.get(key)})
	f.write(json.dumps(actual_highest))


with open("records/highest_regular_seasons.json", "w") as f:
	highest_seasons = heapq.nlargest(10, single_regular_season)
	actual_highest = []
	for key in highest_seasons:
		record_holder = single_regular_season.get(key)
		record_owner = record_holder.get("owner")
		record_year = record_holder.get("year")
		record_team = record_holder.get("team_name")
		actual_highest.append({"owner": record_owner, "value": key, "year": record_year, "team": record_team})
	f.write(json.dumps(actual_highest))

with open("records/lowest_regular_seasons.json", "w") as f:
	lowest_seasons = heapq.nsmallest(10, single_regular_season)
	actual_lowest = []
	for key in lowest_seasons:
		record_holder = single_regular_season.get(key)
		record_owner = record_holder.get("owner")
		record_year = record_holder.get("year")
		record_team = record_holder.get("team_name")
		actual_lowest.append({"owner": record_owner, "value": key, "year": record_year, "team": record_team})
	f.write(json.dumps(actual_lowest))
