import type { EspnCredentials } from "../espn/client";
import { isSeasonFinal, loadOrFetchSeason, type FetchedSeasonData, type SeasonCacheStore } from "../espn/season-cache";
import type { EspnMatchupRosterPayload, EspnRosterPayload } from "../espn/types";
import { GameOutcome, GameType, type PlayerPosition } from "./enums";
import { FantasyLeague, Matchup, Member, Player, Team } from "./model";
import { cleanMemberName, cleanTeamName, cleanUserId, generateTeamId } from "./utility";

const CONSOLATION_MATCHUP_TYPES = new Set(["LOSERS_CONSOLATION_LADDER", "WINNERS_CONSOLATION_LADDER"]);

/** Player rosters/points are only available for 2018+ and only for weeks season-cache actually fetched. */
function mergePlayerData(
  rosterPayload: EspnRosterPayload | undefined,
  matchupRosterPayload: EspnMatchupRosterPayload | undefined,
): Map<number, Player[]> {
  const output = new Map<number, Player[]>();
  if (!rosterPayload || !matchupRosterPayload) return output;

  const scheduledEntries = matchupRosterPayload.schedule.flatMap((game) => [
    ...(game.home?.rosterForCurrentScoringPeriod?.entries ?? []),
    ...(game.away?.rosterForCurrentScoringPeriod?.entries ?? []),
  ]);
  const scheduledByPlayerId = new Map(scheduledEntries.map((entry) => [entry.playerId, entry]));

  for (const team of rosterPayload.teams) {
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

export async function buildLeague(
  store: SeasonCacheStore,
  creds: EspnCredentials,
  foundedYear: number,
  currentCalendarYear: number,
): Promise<BuildLeagueResult> {
  const league = new FantasyLeague(foundedYear, creds.leagueId);
  const teamsByKey = new Map<string, Team>();
  const placeholderMember = new Member("__bye__", "");
  const placeholderTeam = new Team({ division: -1, espnId: -1, name: "", member: placeholderMember, schedule: [], year: -1 });

  interface FetchedYear {
    year: number;
    data: FetchedSeasonData;
  }
  const fetchedYears: FetchedYear[] = [];

  for (let year = foundedYear; year <= currentCalendarYear; year++) {
    // Completed seasons are cached forever in KV; only an in-progress season is fetched from ESPN
    // fresh every run (keeps this well under the Workers-free-tier subrequest cap per invocation).
    const data = await loadOrFetchSeason(store, creds, year);
    // A null result most likely just means the fantasy football year hasn't started for this
    // calendar year yet.
    if (!data) continue;

    league.updateActiveYear(year);
    if (isSeasonFinal(data)) {
      league.updateMaxCompletedYear(year);
    }
    fetchedYears.push({ year, data });
  }

  const lastYear = fetchedYears.at(-1);
  if (!lastYear) {
    throw new Error(`No seasons could be fetched for league ${creds.leagueId} from ${foundedYear} onward`);
  }
  league.activeYearPlayoffSlots = lastYear.data.payload.settings.scheduleSettings.playoffTeamCount;
  league.activeYearRegularSeasonLength = lastYear.data.payload.settings.scheduleSettings.matchupPeriodCount;
  league.name = lastYear.data.payload.settings.name;

  for (const { year, data } of fetchedYears) {
    const { payload, scoreboard, currentWeek, totalMatchupPeriods, weeklyRosters, weeklyMatchupRosters } = data;
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

    for (let week = 1; week <= maxWeek; week++) {
      const weekMatchups = scoreboard.schedule.filter((m) => m.matchupPeriodId === week);
      if (weekMatchups.length === 0) continue;
      const allZero = weekMatchups.every((m) => (m.home?.totalPoints ?? 0) === 0 && (m.away?.totalPoints ?? 0) === 0);
      if (allZero) continue;

      const playerData = mergePlayerData(weeklyRosters[week], weeklyMatchupRosters[week]);

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

  return { league, currentWeek: lastYear.data.currentWeek };
}
