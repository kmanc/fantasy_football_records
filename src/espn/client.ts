import type {
  EspnLeaguePayload,
  EspnMatchupRosterEntry,
  EspnMatchupRosterPayload,
  EspnRosterPayload,
  EspnScoreboardPayload,
} from "./types";

/**
 * ESPN's real responses carry far more than these interfaces declare (full per-player stat
 * breakdowns, projections, ownership%, draft info, ...). A TypeScript cast doesn't strip any of
 * that at runtime, so every fetch is trimmed down to exactly the declared shape here - otherwise
 * anything that serializes these payloads (e.g. the season cache) bloats hugely for no reason.
 */
function trimLeaguePayload(raw: EspnLeaguePayload): EspnLeaguePayload {
  return {
    scoringPeriodId: raw.scoringPeriodId,
    status: {
      currentMatchupPeriod: raw.status.currentMatchupPeriod,
      scoringPeriodId: raw.status.scoringPeriodId,
      firstScoringPeriod: raw.status.firstScoringPeriod,
      finalScoringPeriod: raw.status.finalScoringPeriod,
    },
    settings: {
      name: raw.settings.name,
      scheduleSettings: {
        matchupPeriodCount: raw.settings.scheduleSettings.matchupPeriodCount,
        playoffTeamCount: raw.settings.scheduleSettings.playoffTeamCount,
        matchupPeriods: raw.settings.scheduleSettings.matchupPeriods,
      },
    },
    members: raw.members.map((m) => ({ id: m.id, firstName: m.firstName, lastName: m.lastName })),
    teams: raw.teams.map((t) => ({
      id: t.id,
      divisionId: t.divisionId,
      name: t.name,
      location: t.location,
      nickname: t.nickname,
      owners: t.owners,
      record: {
        overall: { wins: t.record.overall.wins, losses: t.record.overall.losses, ties: t.record.overall.ties },
      },
    })),
  };
}

function trimScoreboardPayload(raw: EspnScoreboardPayload): EspnScoreboardPayload {
  return {
    schedule: raw.schedule.map((m) => ({
      matchupPeriodId: m.matchupPeriodId,
      playoffTierType: m.playoffTierType,
      home: m.home ? { teamId: m.home.teamId, totalPoints: m.home.totalPoints } : undefined,
      away: m.away ? { teamId: m.away.teamId, totalPoints: m.away.totalPoints } : undefined,
    })),
  };
}

function trimRosterPayload(raw: EspnRosterPayload): EspnRosterPayload {
  return {
    teams: raw.teams.map((t) => ({
      id: t.id,
      roster: { entries: t.roster.entries.map((e) => ({ playerId: e.playerId, lineupSlotId: e.lineupSlotId })) },
    })),
  };
}

function trimMatchupRosterEntry(e: EspnMatchupRosterEntry): EspnMatchupRosterEntry {
  return {
    playerId: e.playerId,
    playerPoolEntry: {
      player: { fullName: e.playerPoolEntry.player.fullName },
      appliedStatTotal: e.playerPoolEntry.appliedStatTotal,
    },
  };
}

function trimMatchupRosterPayload(raw: EspnMatchupRosterPayload): EspnMatchupRosterPayload {
  return {
    schedule: raw.schedule.map((game) => ({
      home: game.home?.rosterForCurrentScoringPeriod
        ? { rosterForCurrentScoringPeriod: { entries: game.home.rosterForCurrentScoringPeriod.entries.map(trimMatchupRosterEntry) } }
        : undefined,
      away: game.away?.rosterForCurrentScoringPeriod
        ? { rosterForCurrentScoringPeriod: { entries: game.away.rosterForCurrentScoringPeriod.entries.map(trimMatchupRosterEntry) } }
        : undefined,
    })),
  };
}

const FANTASY_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl";

export class EspnInvalidLeagueError extends Error {}
export class EspnAccessDeniedError extends Error {}
export class EspnUnknownError extends Error {}

export interface EspnCredentials {
  leagueId: number;
  espnS2: string;
  swid: string;
}

function cookieHeader(creds: EspnCredentials): string {
  return `espn_s2=${creds.espnS2}; SWID=${creds.swid}`;
}

/** ESPN stores pre-2018 seasons at a different endpoint shape than modern seasons. */
function leagueEndpoint(creds: EspnCredentials, year: number, modern: boolean): string {
  return modern
    ? `${FANTASY_BASE}/seasons/${year}/segments/0/leagues/${creds.leagueId}`
    : `${FANTASY_BASE}/leagueHistory/${creds.leagueId}?seasonId=${year}`;
}

async function requestJson(url: string, creds: EspnCredentials): Promise<{ status: number; body: unknown }> {
  const response = await fetch(url, { headers: { Cookie: cookieHeader(creds) } });
  const body = response.status === 200 ? await response.json() : undefined;
  return { status: response.status, body };
}

function appendParams(url: string, params: Record<string, string | string[]>): string {
  const u = new URL(url);
  for (const [key, value] of Object.entries(params)) {
    for (const v of Array.isArray(value) ? value : [value]) {
      u.searchParams.append(key, v);
    }
  }
  return u.toString();
}

/**
 * GETs a league-scoped endpoint for a given year, matching espn_api's behavior of
 * trying the modern endpoint shape first (or the legacy one for pre-2018 seasons)
 * and falling back to the other shape on a 401, since ESPN moved older seasons
 * behind the legacy `leagueHistory` path at some point.
 */
async function leagueGet<T>(
  creds: EspnCredentials,
  year: number,
  params: Record<string, string | string[]>,
): Promise<T> {
  const modernFirst = year >= 2018;
  const primaryUrl = appendParams(leagueEndpoint(creds, year, modernFirst), params);
  let { status, body } = await requestJson(primaryUrl, creds);

  if (status === 401) {
    const fallbackUrl = appendParams(leagueEndpoint(creds, year, !modernFirst), params);
    ({ status, body } = await requestJson(fallbackUrl, creds));
  }

  if (status === 404) {
    throw new EspnInvalidLeagueError(`League ${creds.leagueId} does not exist for ${year}`);
  }
  if (status === 401) {
    throw new EspnAccessDeniedError(`League ${creds.leagueId} cannot be accessed with the provided credentials`);
  }
  if (status !== 200) {
    throw new EspnUnknownError(`ESPN returned an HTTP ${status} for ${year}`);
  }

  return (Array.isArray(body) ? body[0] : body) as T;
}

export async function getLeaguePayload(creds: EspnCredentials, year: number): Promise<EspnLeaguePayload> {
  const payload = await leagueGet<EspnLeaguePayload>(creds, year, {
    view: ["mTeam", "mRoster", "mMatchup", "mSettings", "mStandings"],
  });
  return trimLeaguePayload(payload);
}

/** ESPN returns the whole season's schedule regardless of any per-week param, so this is fetched once per year. */
export async function getScoreboard(creds: EspnCredentials, year: number): Promise<EspnScoreboardPayload> {
  const scoreboard = await leagueGet<EspnScoreboardPayload>(creds, year, { view: "mMatchupScore" });
  return trimScoreboardPayload(scoreboard);
}

/** Player data is only available for 2018+ and always lives at the modern endpoint shape. */
export async function getWeeklyRoster(creds: EspnCredentials, year: number, week: number): Promise<EspnRosterPayload> {
  const url = appendParams(leagueEndpoint(creds, year, true), { view: "mRoster", scoringPeriodId: String(week) });
  const { status, body } = await requestJson(url, creds);
  if (status !== 200) {
    throw new EspnUnknownError(`ESPN returned an HTTP ${status} fetching ${year} week ${week} roster`);
  }
  return trimRosterPayload(body as EspnRosterPayload);
}

export async function getWeeklyMatchupRosters(
  creds: EspnCredentials,
  year: number,
  week: number,
): Promise<EspnMatchupRosterPayload> {
  const url = appendParams(leagueEndpoint(creds, year, true), { view: "mMatchup", scoringPeriodId: String(week) });
  const { status, body } = await requestJson(url, creds);
  if (status !== 200) {
    throw new EspnUnknownError(`ESPN returned an HTTP ${status} fetching ${year} week ${week} matchup rosters`);
  }
  return trimMatchupRosterPayload(body as EspnMatchupRosterPayload);
}
