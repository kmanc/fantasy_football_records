import type { EspnCredentials } from "../espn/client";
import { EspnInvalidLeagueError, getLeaguePayload, getScoreboard, getWeeklyMatchupRosters, getWeeklyRoster } from "../espn/client";
import type { EspnLeaguePayload, EspnMatchupRosterEntry } from "../espn/types";
import { GameOutcome, GameType, type PlayerPosition } from "./enums";
import { FantasyLeague, Matchup, Member, Player, Team } from "./model";
import { cleanMemberName, cleanTeamName, cleanUserId, generateTeamId } from "./utility";

const CONSOLATION_MATCHUP_TYPES = new Set(["LOSERS_CONSOLATION_LADDER", "WINNERS_CONSOLATION_LADDER"]);

function computeCurrentWeek(year: number, payload: EspnLeaguePayload): number {
  if (year < 2018) return payload.scoringPeriodId;
  return payload.scoringPeriodId <= payload.status.finalScoringPeriod
    ? payload.scoringPeriodId
    : payload.status.finalScoringPeriod;
}

/** Player rosters/points are only available for 2018+; a fetch failure degrades to "no lineup data" rather than failing the whole build. */
async function fetchPlayerData(creds: EspnCredentials, year: number, week: number): Promise<Map<number, Player[]>> {
  const output = new Map<number, Player[]>();
  if (year < 2018) return output;

  let scheduledEntries: EspnMatchupRosterEntry[];
  let rosterTeams: Awaited<ReturnType<typeof getWeeklyRoster>>["teams"];
  try {
    const [rosterPayload, matchupRosterPayload] = await Promise.all([
      getWeeklyRoster(creds, year, week),
      getWeeklyMatchupRosters(creds, year, week),
    ]);
    rosterTeams = rosterPayload.teams;
    scheduledEntries = matchupRosterPayload.schedule.flatMap((game) => [
      ...(game.home?.rosterForCurrentScoringPeriod?.entries ?? []),
      ...(game.away?.rosterForCurrentScoringPeriod?.entries ?? []),
    ]);
  } catch (err) {
    console.warn(`Failed to fetch player data for ${year} week ${week}:`, err);
    return output;
  }

  const scheduledByPlayerId = new Map(scheduledEntries.map((entry) => [entry.playerId, entry]));

  for (const team of rosterTeams) {
    const players: Player[] = [];
    for (const entry of team.roster.entries) {
      const scheduled = scheduledByPlayerId.get(entry.playerId);
      if (!scheduled) continue;
      players.push(
        new Player(
          entry.playerId,
          scheduled.playerPoolEntry.player.fullName,
          scheduled.playerPoolEntry.appliedStatTotal,
          entry.lineupSlotId as PlayerPosition,
        ),
      );
    }
    output.set(team.id, players);
  }
  return output;
}

/**
 * Rebuilds the entire league from ESPN, from scratch, every time it's called.
 *
 * The original Python version could optionally reuse a previously-pickled instance and merge new
 * data into it; the production cron job never actually used that path (it always rebuilt from
 * scratch), so this port only implements the always-rebuild behavior. That also means
 * joined/left year can just be min/max over the years fetched in this run, rather than merged
 * incrementally across runs.
 */
export interface BuildLeagueResult {
  league: FantasyLeague;
  /** current-week value for the active season, needed by the playoff snapshot's clinch checks */
  currentWeek: number;
}

export async function buildLeague(creds: EspnCredentials, foundedYear: number, currentCalendarYear: number): Promise<BuildLeagueResult> {
  const league = new FantasyLeague(foundedYear, creds.leagueId);
  const teamsByKey = new Map<string, Team>();
  const placeholderMember = new Member("__bye__", "");
  const placeholderTeam = new Team({ division: -1, espnId: -1, name: "", member: placeholderMember, schedule: [], year: -1 });

  interface FetchedYear {
    year: number;
    payload: EspnLeaguePayload;
    currentWeek: number;
    totalMatchupPeriods: number;
  }
  const fetchedYears: FetchedYear[] = [];

  for (let year = foundedYear; year <= currentCalendarYear; year++) {
    let payload: EspnLeaguePayload;
    try {
      payload = await getLeaguePayload(creds, year);
    } catch (err) {
      // Most likely just means the fantasy football year hasn't started for this calendar year yet.
      if (err instanceof EspnInvalidLeagueError) continue;
      throw err;
    }

    const currentWeek = computeCurrentWeek(year, payload);
    const totalMatchupPeriods = Object.keys(payload.settings.scheduleSettings.matchupPeriods).length;

    league.updateActiveYear(year);
    if (currentWeek >= totalMatchupPeriods) {
      league.updateMaxCompletedYear(year);
    }
    fetchedYears.push({ year, payload, currentWeek, totalMatchupPeriods });
  }

  const lastYear = fetchedYears.at(-1);
  if (!lastYear) {
    throw new Error(`No seasons could be fetched for league ${creds.leagueId} from ${foundedYear} onward`);
  }
  league.activeYearPlayoffSlots = lastYear.payload.settings.scheduleSettings.playoffTeamCount;
  league.activeYearRegularSeasonLength = lastYear.payload.settings.scheduleSettings.matchupPeriodCount;
  league.name = lastYear.payload.settings.name;

  for (const { year, payload, currentWeek, totalMatchupPeriods } of fetchedYears) {
    // Members
    for (const rawMember of payload.members) {
      const name = cleanMemberName(`${rawMember.firstName ?? ""} ${rawMember.lastName ?? ""}`);
      const id = cleanUserId(rawMember.id);
      const existing = league.members.get(id);
      if (existing) {
        existing.updateJoinedYear(year);
        existing.updateLeftYear(year);
      } else {
        const member = new Member(id, name);
        member.updateJoinedYear(year);
        member.updateLeftYear(year);
        league.addMember(member);
      }
    }

    const playoffWinsForChamp = totalMatchupPeriods - payload.settings.scheduleSettings.matchupPeriodCount;

    // Teams
    const thisYearsTeams: Team[] = [];
    for (const rawTeam of payload.teams) {
      const owner = league.membersList().find((member) => rawTeam.owners.some((ownerId) => cleanUserId(ownerId) === member.id));
      if (!owner) continue;

      const teamKey = generateTeamId(rawTeam.id, year);
      let team = teamsByKey.get(teamKey);
      if (team) {
        team.regularSeasonWins = rawTeam.record.overall.wins;
        team.regularSeasonLosses = rawTeam.record.overall.losses;
        team.regularSeasonTies = rawTeam.record.overall.ties;
        team.playoffWinsForChamp = playoffWinsForChamp;
      } else {
        const rawName = rawTeam.name;
        const fallbackName = `${rawTeam.location ?? "Unknown"} ${rawTeam.nickname ?? "Unknown"}`;
        const teamName = cleanTeamName(owner.name, year, !rawName || rawName === "Unknown" ? fallbackName : rawName);
        team = new Team({ division: rawTeam.divisionId, espnId: rawTeam.id, name: teamName, member: owner, schedule: [], year });
        team.regularSeasonWins = rawTeam.record.overall.wins;
        team.regularSeasonLosses = rawTeam.record.overall.losses;
        team.regularSeasonTies = rawTeam.record.overall.ties;
        team.playoffWinsForChamp = playoffWinsForChamp;
        owner.addTeam(team);
        teamsByKey.set(teamKey, team);
      }
      thisYearsTeams.push(team);
    }

    // Matchups
    const maxWeek = Math.min(totalMatchupPeriods, currentWeek);
    const scoreboard = await getScoreboard(creds, year);

    for (let week = 1; week <= maxWeek; week++) {
      const weekMatchups = scoreboard.schedule.filter((m) => m.matchupPeriodId === week);
      if (weekMatchups.length === 0) continue;
      const allZero = weekMatchups.every((m) => (m.home?.totalPoints ?? 0) === 0 && (m.away?.totalPoints ?? 0) === 0);
      if (allZero) continue;

      const playerData = await fetchPlayerData(creds, year, week);

      for (const rawMatchup of weekMatchups) {
        const tierType = rawMatchup.playoffTierType ?? "NONE";
        if (CONSOLATION_MATCHUP_TYPES.has(tierType)) continue;
        const gameType = tierType === "WINNERS_BRACKET" ? GameType.PLAYOFF : GameType.REGULAR_SEASON;

        const homeKey = rawMatchup.home ? generateTeamId(rawMatchup.home.teamId, year) : null;
        const awayKey = rawMatchup.away ? generateTeamId(rawMatchup.away.teamId, year) : null;
        const homePoints = rawMatchup.home?.totalPoints ?? 0;
        const awayPoints = rawMatchup.away?.totalPoints ?? 0;

        for (const team of thisYearsTeams) {
          const teamKey = generateTeamId(team.espnId, year);
          if (teamKey === homeKey) {
            const opponent = awayKey ? (teamsByKey.get(awayKey) ?? placeholderTeam) : placeholderTeam;
            const outcome = homePoints < awayPoints ? GameOutcome.LOSS : homePoints === awayPoints ? GameOutcome.TIE : GameOutcome.WIN;
            const matchup = new Matchup({ team, opponent, outcome, pointsFor: homePoints, pointsAgainst: awayPoints, gameType, week });
            for (const player of playerData.get(rawMatchup.home!.teamId) ?? []) matchup.addPlayer(player);
            team.addMatchup(matchup);
          } else if (teamKey === awayKey) {
            const opponent = homeKey ? (teamsByKey.get(homeKey) ?? placeholderTeam) : placeholderTeam;
            const outcome = awayPoints < homePoints ? GameOutcome.LOSS : awayPoints === homePoints ? GameOutcome.TIE : GameOutcome.WIN;
            const matchup = new Matchup({ team, opponent, outcome, pointsFor: awayPoints, pointsAgainst: homePoints, gameType, week });
            for (const player of playerData.get(rawMatchup.away!.teamId) ?? []) matchup.addPlayer(player);
            team.addMatchup(matchup);
          }
        }
      }
    }
  }

  return { league, currentWeek: lastYear.currentWeek };
}
