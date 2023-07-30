from enum import Enum, auto


class GameOutcome(Enum):
	WIN = auto()
	LOSS = auto()
	TIE = auto()

	def __repr__(self):
		return self.name


class GameType(Enum):
	REGULAR_SEASON = auto()
	PLAYOFF = auto()

	def __repr__(self):
		return self.name


class Matchup:
	opponent_owner_name: str
	owner_name: str
	outcome: GameOutcome
	score: int
	team_name: str
	type: GameType
	week: int
	year: int

	def __init__(self, owner, team, year, week, matchup):
		if matchup.data.get("playoffTierType") == "WINNERS_BRACKET":
			self.type = GameType.PLAYOFF
		else:
			self.type = GameType.REGULAR_SEASON
		self.owner_name = owner
		self.team_name = team
		self.week = week
		self.year = year
		if owner == matchup.home_team.owner:
			self.score = matchup.home_score
			self.opponent_owner_name = matchup.away_team.owner
			if matchup.data.get("winner") == "HOME":
				self.outcome = GameOutcome.WIN
			elif matchup.data.get("winner") == "AWAY":
				self.outcome = GameOutcome.LOSS
			elif matchup.data.get("winner") == "UNDECIDED" and self.opponent_owner_name == "BYE":
				self.outcome = GameOutcome.WIN
			else:
				self.outcome = GameOutcome.TIE
		else:
			self.score = matchup.away_score
			self.opponent_owner_name = matchup.home_team.owner
			if matchup.data.get("winner") == "HOME":
				self.outcome = GameOutcome.LOSS
			elif matchup.data.get("winner") == "AWAY":
				self.outcome = GameOutcome.WIN
			else:
				self.outcome = GameOutcome.TIE
