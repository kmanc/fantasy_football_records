import { GameOutcome, GameType } from "./enums";
import { round2 } from "./math";
import type { FantasyLeague, Team } from "./model";

const FULL_BRACKET_SLOTS = 19;

interface TeamStats {
  name: string;
  wins: number;
  losses: number;
  ties: number;
  pointsFor: number;
  divisionalWins: number;
  divisionalLosses: number;
}

export interface PlayoffPictureEntry extends Partial<TeamStats> {
  name: string;
  seed?: number | "P";
  pointsOut?: number;
  clinched?: string;
}

function descendingComparator<T>(...keys: Array<(item: T) => number>): (a: T, b: T) => number {
  return (a, b) => {
    for (const key of keys) {
      const diff = key(b) - key(a);
      if (diff !== 0) return diff;
    }
    return 0;
  };
}

/**
 * WFFL rules state that divisional standings are determined as follows:
 *   Overall record
 *   Tiebreaker 1 - divisional record
 *   Tiebreaker 2 - total points scored
 */
const divisionComparator = descendingComparator<TeamStats>((t) => t.wins, (t) => t.divisionalWins, (t) => t.pointsFor);
function sortDivision(teams: TeamStats[]): TeamStats[] {
  return [...teams].sort(divisionComparator);
}

/**
 * WFFL rules state that wildcard standings are determined as follows:
 *   Total points for
 *   Tiebreaker 1 - overall record
 *   Tiebreaker 2 - divisional record
 */
function sortWildcard(teams: TeamStats[]): TeamStats[] {
  return [...teams].sort(descendingComparator<TeamStats>((t) => t.pointsFor, (t) => t.wins, (t) => t.divisionalWins));
}

/**
 * Once the standings are sorted, divisional winners are seeded by total wins
 *   Tiebreaker 1 - total points scored
 * (The same rule seeds the non-division-leader field once wildcard spots are pulled out.)
 */
function sortByWinsThenPoints(teams: TeamStats[]): TeamStats[] {
  return [...teams].sort(descendingComparator<TeamStats>((t) => t.wins, (t) => t.pointsFor));
}

/** Finds the active-year team with this name and, if it played in `week`, returns the winner's snapshot entry. */
function appendMatchupWinner(
  picture: PlayoffPictureEntry[],
  activeTeams: Team[],
  seedEntry: PlayoffPictureEntry,
  week: number,
  onWin: PlayoffPictureEntry,
  onLoss: PlayoffPictureEntry,
): void {
  const team = activeTeams.find((t) => t.name === seedEntry.name);
  if (!team) return;
  const matchup = team.matchups.find(
    (m) => m.week === week && (m.outcome === GameOutcome.WIN || m.outcome === GameOutcome.LOSS),
  );
  if (!matchup) return;
  picture.push({ ...(matchup.outcome === GameOutcome.WIN ? onWin : onLoss) });
}

/**
 * Builds the current-season playoff picture: standings with seeds/points-out, a projected bracket
 * (using real results for rounds that have already happened), and division/bye clinch markers.
 *
 * `currentWeek` should be the current-week value already computed for the active year during the
 * league build (see build-league.ts) - there's no need to hit ESPN again just to find out what week it is.
 */
export function computePlayoffSnapshot(league: FantasyLeague, currentWeek: number): PlayoffPictureEntry[] {
  const activeTeams = [...league.teamsInActiveYear()];

  // Create a dict {division_id: list[team_id_in_division]}
  const divisions = new Map<number, number[]>();
  for (const team of activeTeams) {
    const list = divisions.get(team.division) ?? [];
    list.push(team.espnId);
    divisions.set(team.division, list);
  }

  // Create two collections containing the data needed to calculate standings
  //     divisionalRawData - data required to figure out who is winning a division
  //     flatRawData - data required to figure out who is winning the points-for wildcard race
  const divisionalRawData = new Map<number, TeamStats[]>();
  const flatRawData: TeamStats[] = [];

  for (const team of activeTeams) {
    // Calculate how many in-division wins/losses a team has
    let divisionalWins = 0;
    let divisionalLosses = 0;
    const divisionOpponents = divisions.get(team.division) ?? [];
    for (const matchup of team.matchups) {
      if (matchup.type !== GameType.REGULAR_SEASON || !divisionOpponents.includes(matchup.opponent.espnId)) {
        continue;
      }
      if (matchup.outcome === GameOutcome.WIN) divisionalWins += 1;
      else if (matchup.outcome === GameOutcome.LOSS) divisionalLosses += 1;
    }

    const teamStats: TeamStats = {
      name: team.name,
      wins: team.regularSeasonWins,
      losses: team.regularSeasonLosses,
      ties: team.regularSeasonTies,
      pointsFor: team.regularSeasonPointsScored(),
      divisionalWins,
      divisionalLosses,
    };
    const divisionList = divisionalRawData.get(team.division) ?? [];
    divisionList.push(teamStats);
    divisionalRawData.set(team.division, divisionList);
    flatRawData.push(teamStats);
  }

  // Now sort the raw divisional data so that each key contains a sorted list representing the standings for that division
  const divisionalStandings = new Map<number, TeamStats[]>();
  for (const [division, data] of divisionalRawData) {
    divisionalStandings.set(division, sortDivision(data));
  }

  // And sort the raw flat data so that it is a list representing the wildcard standings
  let wildcardStandings = sortWildcard(flatRawData);

  // Determine who is leading each division
  const unsortedDivisionLeaders = [...divisionalStandings.values()].map((standings) => standings[0]!);
  const sortedDivisionLeaders = sortByWinsThenPoints(unsortedDivisionLeaders);

  // Then wildcard spots are determined by total points for, tiebreaker total wins
  for (const leader of sortedDivisionLeaders) {
    wildcardStandings = wildcardStandings.filter((team) => team !== leader);
  }
  const sortedWildcardLeaders = wildcardStandings.slice(0, 2);

  // The remaining teams are re-sorted by total wins, tiebreaker total points scored
  const sortedRestOfLeague = sortByWinsThenPoints(wildcardStandings.slice(2));

  // Playoff teams are given their seed.
  // Teams on the outside of the playoffs looking in have their total-points-needed for a wildcard spot calculated.
  // Pooper bowl teams are given their seed.
  const fullPlayoffPicture: PlayoffPictureEntry[] = [];
  const orderedField = [...sortedDivisionLeaders, ...sortedWildcardLeaders, ...sortedRestOfLeague];
  let seed = 1;
  for (const teamStats of orderedField) {
    const entry: PlayoffPictureEntry = { ...teamStats };
    if (seed <= league.activeYearPlayoffSlots) {
      entry.seed = seed;
    } else {
      const lowestWildcard = sortedWildcardLeaders.at(-1)!;
      entry.pointsOut = round2(lowestWildcard.pointsFor - teamStats.pointsFor);
    }
    if (seed >= orderedField.length - 1) {
      entry.seed = "P";
    }
    fullPlayoffPicture.push(entry);
    seed += 1;
  }

  // Get the regular season games played by the first place person (should be the same as everyone else)
  const first = fullPlayoffPicture[0]!;
  const regularSeasonGamesPlayed = (first.losses ?? 0) + (first.ties ?? 0) + (first.wins ?? 0);

  // First seed gets a bye, so they win game 1
  fullPlayoffPicture.push({ ...fullPlayoffPicture[0]! });
  // Second seed gets a bye, so they win game 2
  fullPlayoffPicture.push({ ...fullPlayoffPicture[1]! });
  // Who won the 4 vs 5 matchup?
  appendMatchupWinner(fullPlayoffPicture, activeTeams, fullPlayoffPicture[3]!, regularSeasonGamesPlayed + 1, fullPlayoffPicture[3]!, fullPlayoffPicture[4]!);
  // Who won the 3 vs 6 matchup?
  appendMatchupWinner(fullPlayoffPicture, activeTeams, fullPlayoffPicture[2]!, regularSeasonGamesPlayed + 1, fullPlayoffPicture[2]!, fullPlayoffPicture[5]!);
  // Who won the round 2 high seed matchup?
  appendMatchupWinner(fullPlayoffPicture, activeTeams, fullPlayoffPicture[0]!, regularSeasonGamesPlayed + 2, fullPlayoffPicture[0]!, fullPlayoffPicture.at(-2)!);
  // Who won the round 2 low seed matchup?
  appendMatchupWinner(fullPlayoffPicture, activeTeams, fullPlayoffPicture[1]!, regularSeasonGamesPlayed + 2, fullPlayoffPicture[1]!, fullPlayoffPicture.at(-2)!);
  // Who won the championship?
  appendMatchupWinner(fullPlayoffPicture, activeTeams, fullPlayoffPicture.at(-2)!, regularSeasonGamesPlayed + 3, fullPlayoffPicture.at(-2)!, fullPlayoffPicture.at(-1)!);

  // If there are less than a full bracket's worth of teams, the season isn't complete yet, so add blanks
  while (fullPlayoffPicture.length < FULL_BRACKET_SLOTS) {
    fullPlayoffPicture.push({ name: "" });
  }

  const remainingGames = league.activeYearRegularSeasonLength - regularSeasonGamesPlayed;

  // Now see if anyone has clinched a playoff berth: pessimize each division leader (assume they lose
  // out) and optimize the rest of their division (assume they win out); if the leader still wins the
  // division under that worst case, they've clinched it.
  const simulatedBerth = structuredClone(divisionalStandings);
  for (const simDivisionData of simulatedBerth.values()) {
    const leader = simDivisionData.shift()!;
    const leaderName = leader.name;
    leader.losses += remainingGames;
    leader.pointsFor = -1;
    for (const other of simDivisionData) {
      other.wins += remainingGames;
      other.divisionalWins = 4 - other.divisionalLosses;
    }
    simDivisionData.push(leader);
    const simulatedLeader = sortDivision(simDivisionData)[0]!;
    if (simulatedLeader.name === leaderName) {
      for (const currentLead of fullPlayoffPicture.slice(0, 4)) {
        if (currentLead.name === simulatedLeader.name) {
          currentLead.clinched = "* (clinched division)";
        }
      }
    }
  }

  // Now see if anyone has clinched a bye: pessimize the two current bye holders and optimize
  // everyone else, then check whether the same two teams still come out on top.
  const byeHolderNames = new Set(sortedDivisionLeaders.slice(0, 2).map((t) => t.name));
  const simulatedBye = structuredClone(divisionalStandings);
  for (const simDivisionData of simulatedBye.values()) {
    const leader = simDivisionData.shift()!;
    if (byeHolderNames.has(leader.name)) {
      leader.losses += remainingGames;
      leader.pointsFor = -1;
    } else {
      leader.wins += remainingGames;
      leader.divisionalWins = 4 - leader.divisionalLosses;
    }
    for (const other of simDivisionData) {
      other.wins += remainingGames;
      other.divisionalWins = 4 - other.divisionalLosses;
    }
    simDivisionData.push(leader);
    simDivisionData.sort(divisionComparator);
  }

  const simUnsortedDivisionLeaders = [...simulatedBye.values()].map((data) => data[0]!);
  const simSortedDivisionLeaders = sortByWinsThenPoints(simUnsortedDivisionLeaders);
  const simByeHolderNames = new Set(simSortedDivisionLeaders.slice(0, 2).map((t) => t.name));

  for (const currentLead of fullPlayoffPicture.slice(0, 2)) {
    if (currentWeek > league.activeYearRegularSeasonLength || simByeHolderNames.has(currentLead.name!)) {
      currentLead.clinched = "** (clinched bye)";
    }
  }

  return fullPlayoffPicture;
}
