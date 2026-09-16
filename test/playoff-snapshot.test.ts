import { describe, expect, test } from "bun:test";
import { GameOutcome, GameType } from "../src/domain/enums";
import { FantasyLeague, Matchup, Member, Team } from "../src/domain/model";
import { computePlayoffSnapshot } from "../src/domain/playoff-snapshot";

interface TeamSpec {
  name: string;
  division: number;
  espnId: number;
  wins: number;
  losses: number;
  pointsFor: number;
}

/**
 * Builds a 2-division, 12-team, fully-completed regular season (no playoff games played yet).
 * Every team plays a single same-division matchup, just so `regularSeasonPointsScored()` and
 * divisional win/loss counting have something to derive from - `wins`/`losses` themselves are
 * set directly, mirroring how build-league.ts populates them straight from ESPN's team record.
 */
function buildFixtureLeague(specs: TeamSpec[]): FantasyLeague {
  const league = new FantasyLeague(2024, 1);
  const teams = new Map<string, Team>();

  for (const spec of specs) {
    const member = new Member(spec.name, spec.name);
    league.addMember(member);
    const team = new Team({ division: spec.division, espnId: spec.espnId, name: spec.name, member, schedule: [], year: 2024 });
    team.regularSeasonWins = spec.wins;
    team.regularSeasonLosses = spec.losses;
    team.regularSeasonTies = 0;
    member.addTeam(team);
    teams.set(spec.name, team);
  }

  // Pair each team with the next team in the same division for a single scored matchup.
  for (const spec of specs) {
    const team = teams.get(spec.name)!;
    if (team.matchups.length > 0) continue;
    const partnerSpec = specs.find((s) => s.division === spec.division && s.name !== spec.name && teams.get(s.name)!.matchups.length === 0);
    const partner = partnerSpec ? teams.get(partnerSpec.name)! : team;
    team.addMatchup(new Matchup({ team, opponent: partner, outcome: GameOutcome.WIN, pointsFor: spec.pointsFor, pointsAgainst: 0, gameType: GameType.REGULAR_SEASON, week: 1 }));
    if (partner !== team) {
      partner.addMatchup(new Matchup({ team: partner, opponent: team, outcome: GameOutcome.LOSS, pointsFor: partnerSpec!.pointsFor, pointsAgainst: spec.pointsFor, gameType: GameType.REGULAR_SEASON, week: 1 }));
    }
  }

  league.updateActiveYear(2024);
  league.activeYearPlayoffSlots = 6;
  league.activeYearRegularSeasonLength = 3;
  return league;
}

const SPECS: TeamSpec[] = [
  { name: "A", division: 0, espnId: 1, wins: 3, losses: 0, pointsFor: 300 },
  { name: "B", division: 0, espnId: 2, wins: 2, losses: 1, pointsFor: 250 },
  { name: "C", division: 0, espnId: 3, wins: 1, losses: 2, pointsFor: 200 },
  { name: "D", division: 0, espnId: 4, wins: 1, losses: 2, pointsFor: 190 },
  { name: "E", division: 0, espnId: 5, wins: 0, losses: 3, pointsFor: 150 },
  { name: "F", division: 0, espnId: 6, wins: 0, losses: 3, pointsFor: 140 },
  { name: "G", division: 1, espnId: 7, wins: 3, losses: 0, pointsFor: 280 },
  { name: "H", division: 1, espnId: 8, wins: 2, losses: 1, pointsFor: 260 },
  { name: "I", division: 1, espnId: 9, wins: 1, losses: 2, pointsFor: 210 },
  { name: "J", division: 1, espnId: 10, wins: 1, losses: 2, pointsFor: 195 },
  { name: "K", division: 1, espnId: 11, wins: 0, losses: 3, pointsFor: 160 },
  { name: "L", division: 1, espnId: 12, wins: 0, losses: 3, pointsFor: 130 },
];

describe("computePlayoffSnapshot seeding", () => {
  test("seeds division leaders first, then wildcard leaders, then the rest by wins/points", () => {
    const league = buildFixtureLeague(SPECS);
    const snapshot = computePlayoffSnapshot(league, 4);
    const names = snapshot.slice(0, 12).map((e) => e.name);
    expect(names).toEqual(["A", "G", "H", "B", "I", "C", "J", "D", "K", "E", "F", "L"]);
  });

  test("assigns numeric seeds only to playoff slots, and 'P' to the bottom two", () => {
    const league = buildFixtureLeague(SPECS);
    const snapshot = computePlayoffSnapshot(league, 4);
    expect(snapshot.slice(0, 6).map((e) => e.seed)).toEqual([1, 2, 3, 4, 5, 6]);
    expect(snapshot[6]!.seed).toBeUndefined();
    expect(snapshot[9]!.seed).toBeUndefined();
    expect(snapshot[10]!.seed).toBe("P");
    expect(snapshot[11]!.seed).toBe("P");
  });

  test("computes points-out relative to the lower of the two wildcard leaders", () => {
    const league = buildFixtureLeague(SPECS);
    const snapshot = computePlayoffSnapshot(league, 4);
    // Lowest wildcard leader is B at 250 points.
    expect(snapshot[6]!.pointsOut).toBe(55); // J: 250 - 195
    expect(snapshot[7]!.pointsOut).toBe(60); // D: 250 - 190
    expect(snapshot[11]!.pointsOut).toBe(120); // L: 250 - 130 (also seeded "P")
  });

  test("pads the bracket portion with blanks when playoff games haven't been played yet", () => {
    const league = buildFixtureLeague(SPECS);
    const snapshot = computePlayoffSnapshot(league, 4);
    expect(snapshot).toHaveLength(19);
    // Byes are asserted unconditionally regardless of whether the game has been played.
    expect(snapshot[12]!.name).toBe("A");
    expect(snapshot[13]!.name).toBe("G");
    // Everything after the (unplayed) bye slots is blank.
    expect(snapshot.slice(14)).toEqual(new Array(5).fill(null).map(() => ({ name: "" })));
  });
});

describe("computePlayoffSnapshot clinches", () => {
  test("marks a division clinched once the leader can't be caught even in the worst case", () => {
    const league = buildFixtureLeague(SPECS);
    // Regular season is already over (0 games left), so both division leaders have clinched no matter what.
    const snapshot = computePlayoffSnapshot(league, 4);
    expect(snapshot[0]!.clinched).toBe("** (clinched bye)"); // A: division clinch is overwritten by bye clinch
    expect(snapshot[1]!.clinched).toBe("** (clinched bye)"); // G: same
    expect(snapshot[2]!.clinched).toBeUndefined(); // H is a wildcard seed, not a division leader
    expect(snapshot[3]!.clinched).toBeUndefined(); // B: same
  });

  test("marks the top two seeds bye-clinched once the season has moved past the regular season", () => {
    const league = buildFixtureLeague(SPECS);
    const snapshotMidSeason = computePlayoffSnapshot(league, 2); // currentWeek <= regular season length
    // Still clinched here because the simulation itself proves it (0 games remain either way).
    expect(snapshotMidSeason[0]!.clinched).toBe("** (clinched bye)");
    expect(snapshotMidSeason[1]!.clinched).toBe("** (clinched bye)");
  });

  test("does not mark a division clinched if a rival could still catch up", () => {
    // Division 0's leader (A) only leads by 1 win with 2 games left - either chaser could pass them
    // in the worst case. Division 1's leader (G) leads by 3 wins with 2 games left - unassailable.
    const closeRaceSpecs: TeamSpec[] = [
      { name: "A", division: 0, espnId: 1, wins: 2, losses: 1, pointsFor: 200 },
      { name: "B", division: 0, espnId: 2, wins: 1, losses: 2, pointsFor: 190 },
      { name: "C", division: 0, espnId: 3, wins: 1, losses: 2, pointsFor: 180 },
      { name: "D", division: 0, espnId: 4, wins: 0, losses: 3, pointsFor: 170 },
      { name: "E", division: 0, espnId: 5, wins: 0, losses: 3, pointsFor: 160 },
      { name: "F", division: 0, espnId: 6, wins: 0, losses: 3, pointsFor: 150 },
      { name: "G", division: 1, espnId: 7, wins: 3, losses: 0, pointsFor: 280 },
      { name: "H", division: 1, espnId: 8, wins: 0, losses: 3, pointsFor: 260 },
      { name: "I", division: 1, espnId: 9, wins: 0, losses: 3, pointsFor: 210 },
      { name: "J", division: 1, espnId: 10, wins: 0, losses: 3, pointsFor: 195 },
      { name: "K", division: 1, espnId: 11, wins: 0, losses: 3, pointsFor: 140 },
      { name: "L", division: 1, espnId: 12, wins: 0, losses: 3, pointsFor: 130 },
    ];
    const league = buildFixtureLeague(closeRaceSpecs);
    league.activeYearRegularSeasonLength = 5; // 2 games remain beyond the 3 already played
    const snapshot = computePlayoffSnapshot(league, 4);

    expect(snapshot[0]!.name).toBe("G");
    expect(snapshot[0]!.clinched).toBe("** (clinched bye)");
    expect(snapshot[1]!.name).toBe("A");
    expect(snapshot[1]!.clinched).toBeUndefined();
  });
});
