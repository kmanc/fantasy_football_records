import { describe, expect, test } from "bun:test";
import { GameOutcome, GameType } from "../src/domain/enums";
import { FantasyLeague, Matchup, Member, Team } from "../src/domain/model";

function buildFixtureLeague(): FantasyLeague {
  const league = new FantasyLeague(2020, 1);

  const alice = new Member("alice-id", "Alice");
  const bob = new Member("bob-id", "Bob");
  alice.updateJoinedYear(2020);
  alice.updateLeftYear(2021);
  bob.updateJoinedYear(2020);
  bob.updateLeftYear(2021);
  league.addMember(alice);
  league.addMember(bob);

  const aliceTeam2020 = new Team({ division: 1, espnId: 1, name: "Alice Team", member: alice, schedule: [], year: 2020 });
  const bobTeam2020 = new Team({ division: 1, espnId: 2, name: "Bob Team", member: bob, schedule: [], year: 2020 });
  const aliceTeam2021 = new Team({ division: 1, espnId: 1, name: "Alice Team", member: alice, schedule: [], year: 2021 });
  const bobTeam2021 = new Team({ division: 1, espnId: 2, name: "Bob Team", member: bob, schedule: [], year: 2021 });

  aliceTeam2020.playoffWinsForChamp = 2;
  bobTeam2020.playoffWinsForChamp = 2;
  aliceTeam2021.playoffWinsForChamp = 2;
  bobTeam2021.playoffWinsForChamp = 2;

  alice.addTeam(aliceTeam2020);
  alice.addTeam(aliceTeam2021);
  bob.addTeam(bobTeam2020);
  bob.addTeam(bobTeam2021);

  // 2020 regular season: Alice beats Bob week 1, loses week 2
  aliceTeam2020.addMatchup(new Matchup({ team: aliceTeam2020, opponent: bobTeam2020, outcome: GameOutcome.WIN, pointsFor: 120, pointsAgainst: 100, gameType: GameType.REGULAR_SEASON, week: 1 }));
  bobTeam2020.addMatchup(new Matchup({ team: bobTeam2020, opponent: aliceTeam2020, outcome: GameOutcome.LOSS, pointsFor: 100, pointsAgainst: 120, gameType: GameType.REGULAR_SEASON, week: 1 }));
  aliceTeam2020.addMatchup(new Matchup({ team: aliceTeam2020, opponent: bobTeam2020, outcome: GameOutcome.LOSS, pointsFor: 90, pointsAgainst: 110, gameType: GameType.REGULAR_SEASON, week: 2 }));
  bobTeam2020.addMatchup(new Matchup({ team: bobTeam2020, opponent: aliceTeam2020, outcome: GameOutcome.WIN, pointsFor: 110, pointsAgainst: 90, gameType: GameType.REGULAR_SEASON, week: 2 }));

  // 2020 playoffs: Alice wins both rounds (champion), Bob wins only round 1
  aliceTeam2020.addMatchup(new Matchup({ team: aliceTeam2020, opponent: bobTeam2020, outcome: GameOutcome.WIN, pointsFor: 130, pointsAgainst: 100, gameType: GameType.PLAYOFF, week: 3 }));
  aliceTeam2020.addMatchup(new Matchup({ team: aliceTeam2020, opponent: bobTeam2020, outcome: GameOutcome.WIN, pointsFor: 140, pointsAgainst: 100, gameType: GameType.PLAYOFF, week: 4 }));
  bobTeam2020.addMatchup(new Matchup({ team: bobTeam2020, opponent: aliceTeam2020, outcome: GameOutcome.WIN, pointsFor: 105, pointsAgainst: 95, gameType: GameType.PLAYOFF, week: 3 }));
  bobTeam2020.addMatchup(new Matchup({ team: bobTeam2020, opponent: aliceTeam2020, outcome: GameOutcome.LOSS, pointsFor: 95, pointsAgainst: 130, gameType: GameType.PLAYOFF, week: 4 }));

  // 2021: only regular season, no playoffs for either
  aliceTeam2021.addMatchup(new Matchup({ team: aliceTeam2021, opponent: bobTeam2021, outcome: GameOutcome.LOSS, pointsFor: 80, pointsAgainst: 150, gameType: GameType.REGULAR_SEASON, week: 1 }));
  bobTeam2021.addMatchup(new Matchup({ team: bobTeam2021, opponent: aliceTeam2021, outcome: GameOutcome.WIN, pointsFor: 150, pointsAgainst: 80, gameType: GameType.REGULAR_SEASON, week: 1 }));

  league.updateActiveYear(2021);
  league.activeYearPlayoffSlots = 2;
  league.activeYearRegularSeasonLength = 1;
  league.updateMaxCompletedYear(2020);

  return league;
}

describe("Team.wonChampionship", () => {
  test("requires exactly playoffWinsForChamp non-loss playoff matchups", () => {
    const league = buildFixtureLeague();
    const alice = league.members.get("alice-id")!;
    const bob = league.members.get("bob-id")!;
    const aliceTeam2020 = alice.teams.find((t) => t.year === 2020)!;
    const bobTeam2020 = bob.teams.find((t) => t.year === 2020)!;

    expect(aliceTeam2020.wonChampionship()).toBe(true);
    expect(bobTeam2020.wonChampionship()).toBe(false);
  });
});

describe("Member aggregate stats", () => {
  test("championshipWins counts only championship-winning teams", () => {
    const league = buildFixtureLeague();
    expect(league.members.get("alice-id")!.championshipWins()).toBe(1);
    expect(league.members.get("bob-id")!.championshipWins()).toBe(0);
  });

  test("playoffAppearances counts teams that made the playoffs", () => {
    const league = buildFixtureLeague();
    expect(league.members.get("alice-id")!.playoffAppearances()).toBe(1);
    expect(league.members.get("bob-id")!.playoffAppearances()).toBe(1);
  });

  test("regularSeasonPoints/average/win% only include regular season matchups", () => {
    const league = buildFixtureLeague();
    const alice = league.members.get("alice-id")!;
    // 120 + 90 (2020) + 80 (2021) = 290, across 3 games
    expect(alice.regularSeasonPoints()).toBe(290);
    expect(alice.regularSeasonAveragePoints()).toBe(96.67);
    // 1 win out of 3 regular season games
    expect(alice.regularSeasonWinPercentage()).toBe(33.33);
  });

  test("playoffPoints/average/win% only include playoff matchups", () => {
    const league = buildFixtureLeague();
    const bob = league.members.get("bob-id")!;
    // 105 + 95 = 200 across 2 playoff games
    expect(bob.playoffPoints()).toBe(200);
    expect(bob.playoffAveragePoints()).toBe(100);
    expect(bob.playoffWinPercentage()).toBe(50);
  });

  test("returns 0 instead of dividing by zero when a member has no matching games", () => {
    const league = buildFixtureLeague();
    const noGames = new Member("nobody", "Nobody");
    league.addMember(noGames);
    expect(noGames.regularSeasonAveragePoints()).toBe(0);
    expect(noGames.playoffAveragePoints()).toBe(0);
    expect(noGames.regularSeasonWinPercentage()).toBe(0);
  });
});

describe("FantasyLeague aggregate queries", () => {
  test("matchupsByPointsFor sorts descending and excludes zero scores", () => {
    const league = buildFixtureLeague();
    const top = league.matchupsByPointsFor()[0]!;
    expect(top.pointsFor).toBe(150);
  });

  test("teamsInActiveYear only returns teams from the active year", () => {
    const league = buildFixtureLeague();
    const activeTeams = league.teamsInActiveYear();
    expect(activeTeams).toHaveLength(2);
    expect(activeTeams.every((team) => team.year === 2021)).toBe(true);
  });

  test("teamsByRegularSeasonPointsFor can exclude the active year", () => {
    const league = buildFixtureLeague();
    const historical = league.teamsByRegularSeasonPointsFor(true);
    expect(historical.every((team) => team.year !== 2021)).toBe(true);
    expect(historical[0]!.regularSeasonPointsScored()).toBe(210); // Alice 2020: 120 + 90
  });
});

describe("Team.addMatchup de-duplication", () => {
  test("ignores a second add of the same team/opponent/week", () => {
    const league = new FantasyLeague(2020, 1);
    const alice = new Member("alice-id", "Alice");
    const bob = new Member("bob-id", "Bob");
    league.addMember(alice);
    league.addMember(bob);
    const aliceTeam = new Team({ division: 1, espnId: 1, name: "Alice", member: alice, schedule: [], year: 2020 });
    const bobTeam = new Team({ division: 1, espnId: 2, name: "Bob", member: bob, schedule: [], year: 2020 });

    const matchup = new Matchup({ team: aliceTeam, opponent: bobTeam, outcome: GameOutcome.WIN, pointsFor: 100, pointsAgainst: 90, gameType: GameType.REGULAR_SEASON, week: 1 });
    aliceTeam.addMatchup(matchup);
    aliceTeam.addMatchup(matchup);
    expect(aliceTeam.matchups).toHaveLength(1);
  });
});
