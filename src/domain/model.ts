import { GameOutcome, GameType, type PlayerPosition } from "./enums";
import { round2 } from "./math";

export class Player {
  readonly id: number;
  readonly name: string;
  readonly points: number;
  readonly position: PlayerPosition;

  constructor(espnId: number, name: string, points: number, position: PlayerPosition) {
    this.id = espnId;
    this.name = name;
    this.points = round2(points);
    this.position = position;
  }
}

export interface MatchupInit {
  opponent: Team;
  outcome: GameOutcome;
  pointsAgainst: number;
  pointsFor: number;
  team: Team;
  gameType: GameType;
  week: number;
}

export class Matchup {
  readonly lineup: Player[] = [];
  readonly opponent: Team;
  readonly outcome: GameOutcome;
  readonly pointsAgainst: number;
  readonly pointsFor: number;
  readonly team: Team;
  readonly type: GameType;
  readonly week: number;

  constructor(init: MatchupInit) {
    this.opponent = init.opponent;
    this.outcome = init.outcome;
    this.pointsAgainst = init.pointsAgainst;
    this.pointsFor = init.pointsFor;
    this.team = init.team;
    this.type = init.gameType;
    this.week = init.week;
  }

  addPlayer(player: Player): void {
    this.lineup.push(player);
  }

  /** Identifies this team/opponent/week combination, for de-duping within a single build run. */
  key(): string {
    return `${this.team.espnId}-${this.opponent.espnId}-${this.week}`;
  }
}

export interface TeamInit {
  division: number;
  espnId: number;
  name: string;
  member: Member;
  schedule: number[];
  year: number;
}

export class Team {
  readonly division: number;
  readonly espnId: number;
  readonly name: string;
  readonly matchups: Matchup[] = [];
  readonly member: Member;
  playoffWinsForChamp = 0;
  regularSeasonLosses = 0;
  regularSeasonTies = 0;
  regularSeasonWins = 0;
  readonly schedule: number[];
  readonly year: number;

  constructor(init: TeamInit) {
    this.division = init.division;
    this.espnId = init.espnId;
    this.name = init.name;
    this.member = init.member;
    this.schedule = init.schedule;
    this.year = init.year;
  }

  /** Adds a matchup, ignoring a duplicate add of the same team/opponent/week. */
  addMatchup(matchup: Matchup): void {
    if (!this.matchups.some((existing) => existing.key() === matchup.key())) {
      this.matchups.push(matchup);
    }
  }

  madePlayoffs(): boolean {
    return this.matchups.some((matchup) => matchup.type === GameType.PLAYOFF);
  }

  playerSuperset(): Player[] {
    const seen = new Map<number, Player>();
    for (const matchup of this.matchups) {
      for (const player of matchup.lineup) {
        seen.set(player.id, player);
      }
    }
    return [...seen.values()];
  }

  playoffPointsScored(): number {
    return round2(sumBy(this.matchups.filter((m) => m.type === GameType.PLAYOFF), (m) => m.pointsFor));
  }

  regularSeasonPointsAgainst(): number {
    return round2(sumBy(this.matchups.filter((m) => m.type === GameType.REGULAR_SEASON), (m) => m.pointsAgainst));
  }

  regularSeasonPointsScored(): number {
    return round2(sumBy(this.matchups.filter((m) => m.type === GameType.REGULAR_SEASON), (m) => m.pointsFor));
  }

  wonChampionship(): boolean {
    const playoffWins = this.matchups.filter(
      (m) => m.type === GameType.PLAYOFF && m.outcome !== GameOutcome.LOSS,
    ).length;
    return playoffWins === this.playoffWinsForChamp;
  }
}

export class Member {
  readonly id: string;
  joinedYear = Number.POSITIVE_INFINITY;
  leftYear = 0;
  readonly name: string;
  readonly teams: Team[] = [];

  constructor(id: string, name: string) {
    this.id = id;
    this.name = name;
  }

  addTeam(team: Team): void {
    this.teams.push(team);
  }

  updateJoinedYear(year: number): void {
    this.joinedYear = Math.min(this.joinedYear, year);
  }

  updateLeftYear(year: number): void {
    this.leftYear = Math.max(this.leftYear, year);
  }

  championshipWins(): number {
    return this.teams.filter((team) => team.wonChampionship()).length;
  }

  matchupSuperset(): Matchup[] {
    return this.teams.flatMap((team) => team.matchups);
  }

  playerSuperset(): Player[] {
    const seen = new Map<number, Player>();
    for (const team of this.teams) {
      for (const player of team.playerSuperset()) {
        seen.set(player.id, player);
      }
    }
    return [...seen.values()];
  }

  playoffAppearances(): number {
    return this.teams.filter((team) => team.madePlayoffs()).length;
  }

  playoffMatchups(): Matchup[] {
    return this.matchupSuperset().filter((m) => m.type === GameType.PLAYOFF);
  }

  playoffPoints(): number {
    return round2(sumBy(this.playoffMatchups(), (m) => m.pointsFor));
  }

  playoffAveragePoints(): number {
    const matchups = this.playoffMatchups();
    if (matchups.length === 0) return 0;
    return round2(this.playoffPoints() / matchups.length);
  }

  playoffWins(): number {
    return this.playoffMatchups().filter((m) => m.outcome === GameOutcome.WIN).length;
  }

  playoffWinPercentage(): number {
    const matchups = this.playoffMatchups();
    if (matchups.length === 0) return 0;
    return round2((this.playoffWins() * 100) / matchups.length);
  }

  regularSeasonMatchups(): Matchup[] {
    return this.matchupSuperset().filter((m) => m.type === GameType.REGULAR_SEASON);
  }

  regularSeasonPoints(): number {
    return round2(sumBy(this.regularSeasonMatchups(), (m) => m.pointsFor));
  }

  regularSeasonAveragePoints(): number {
    const matchups = this.regularSeasonMatchups();
    if (matchups.length === 0) return 0;
    return round2(this.regularSeasonPoints() / matchups.length);
  }

  regularSeasonWins(): number {
    return this.regularSeasonMatchups().filter((m) => m.outcome === GameOutcome.WIN).length;
  }

  regularSeasonWinPercentage(): number {
    const matchups = this.regularSeasonMatchups();
    if (matchups.length === 0) return 0;
    return round2((this.regularSeasonWins() * 100) / matchups.length);
  }
}

export class FantasyLeague {
  activeYear = 0;
  activeYearPlayoffSlots = 0;
  activeYearRegularSeasonLength = 0;
  readonly foundedYear: number;
  readonly id: number;
  maxCompletedYear = 0;
  readonly members = new Map<string, Member>();
  name = "";

  constructor(foundedYear: number, id: number) {
    this.foundedYear = foundedYear;
    this.id = id;
  }

  addMember(member: Member): void {
    this.members.set(member.id, member);
  }

  membersList(): Member[] {
    return [...this.members.values()];
  }

  membersWithChampionship(): Member[] {
    return this.membersList().filter((member) => member.championshipWins() > 0);
  }

  membersWithPlayoffAppearances(): Member[] {
    return this.membersList().filter((member) => member.playoffAppearances() > 0);
  }

  matchupSuperset(): Matchup[] {
    return this.membersList().flatMap((member) => member.matchupSuperset());
  }

  matchupsByPointsFor(): Matchup[] {
    return this.matchupSuperset()
      .filter((matchup) => matchup.pointsFor !== 0)
      .sort((a, b) => b.pointsFor - a.pointsFor);
  }

  teamSuperset(): Team[] {
    return this.membersList().flatMap((member) => member.teams);
  }

  teamsInActiveYear(): Team[] {
    return this.teamSuperset().filter((team) => team.year === this.activeYear);
  }

  teamsByRegularSeasonPointsAgainst(excludeCurrent = false): Team[] {
    const activeIds = new Set(this.teamsInActiveYear());
    const teams = excludeCurrent
      ? this.teamSuperset().filter((team) => !activeIds.has(team))
      : this.teamSuperset();
    return teams.sort((a, b) => b.regularSeasonPointsAgainst() - a.regularSeasonPointsAgainst());
  }

  teamsByRegularSeasonPointsFor(excludeCurrent = false): Team[] {
    const activeIds = new Set(this.teamsInActiveYear());
    const teams = excludeCurrent
      ? this.teamSuperset().filter((team) => !activeIds.has(team))
      : this.teamSuperset();
    return teams.sort((a, b) => b.regularSeasonPointsScored() - a.regularSeasonPointsScored());
  }

  updateActiveYear(year: number): void {
    this.activeYear = Math.max(this.activeYear, year);
  }

  updateMaxCompletedYear(year: number): void {
    this.maxCompletedYear = Math.max(this.maxCompletedYear, year);
  }
}

function sumBy<T>(items: T[], fn: (item: T) => number): number {
  return items.reduce((total, item) => total + fn(item), 0);
}
