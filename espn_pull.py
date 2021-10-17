import configparser
import json
import os
from datetime import date
from espn_api.football import League

config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
config.read(f'{dir_path}/config.ini')

s2 = config["ESPN"]["s2"]
swid = config["ESPN"]["swid"]
league_id = int(config["ESPN"]["league_id"])
first_year = int(config["ESPN"]["league_founded"])

current_year = date.today().year
home_game_result_transform = {
	"HOME": "win",
	"AWAY": "loss",
	"TIE": "tie"
}
away_game_result_transform = {
	"HOME": "loss",
	"AWAY": "win",
	"TIE": "tie"
}


def process_year(league_year):
	league = League(league_id=league_id, year=league_year, espn_s2=s2, swid=swid)
	max_week = 16
	if league_year > 2020:
		max_week = 17

	owners_to_teams_dict = {}
	for team in league.teams:
		owners_to_teams_dict[team.owner.title()] = team.team_name.replace("  ", " ").strip()

	owners_to_weeks_dict = {}
	for owner, team_name in owners_to_teams_dict.items():
		owners_to_weeks_dict[owner] = {}
		owners_to_weeks_dict[owner][f"team_name"] = team_name
	for week in range(1, max_week + 1):
		scoreboard = league.scoreboard(week)
		# Week hasn't happened yet
		if scoreboard[0].data.get("winner") == "UNDECIDED" and scoreboard[0].data.get("playoffTierType") != "WINNERS_BRACKET":
			break
		for matchup in scoreboard:
			skip_away = False
			game_result = matchup.data.get("winner")

			# Not really in the playoffs
			if matchup.data.get("playoffTierType") in ["LOSERS_CONSOLATION_LADDER", "WINNERS_CONSOLATION_LADDER"]:
				continue

			# Home team has a bye in playoffs
			if matchup.away_team == 0:
				game_result = "HOME"
				skip_away = True

			# Home team score and win result
			owners_to_weeks_dict[matchup.home_team.owner.title()][f"week_{week}"] = {
				"score": matchup.home_score,
				"result": home_game_result_transform.get(game_result)
			}

			# Had to record the home team's win and points before skipping
			if skip_away:
				continue

			# Away team score and win result
			owners_to_weeks_dict[matchup.away_team.owner.title()][f"week_{week}"] = {
				"score": matchup.away_score,
				"result": away_game_result_transform.get(game_result)
			}

	return owners_to_weeks_dict


def main():
	for year in range(first_year, current_year + 1):
		try:
			with open(f"past_years/{year}.json") as f:
				file_data = json.loads(f.read())
				weeks_there = set()
				for key, value in file_data.items():
					weeks_there.update(value.keys())
				if "week_16" in weeks_there and year <= 2020:
					print(f"{year} already stored locally")
					continue
				elif "week_17" in weeks_there and year > 2020:
					print(f"{year} already stored locally")
					continue
		except FileNotFoundError:
			pass
		print(f"Working on {year}")
		ff_year = process_year(league_year=year)
		with open(f"past_years/{year}.json", "w") as f:
			f.write(json.dumps(ff_year))


if __name__ == "__main__":
	main()
