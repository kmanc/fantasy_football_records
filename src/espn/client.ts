import type {
  EspnLeaguePayload,
  EspnMatchupRosterPayload,
  EspnRosterPayload,
  EspnScoreboardPayload,
} from "./types";

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
  return leagueGet<EspnLeaguePayload>(creds, year, {
    view: ["mTeam", "mRoster", "mMatchup", "mSettings", "mStandings"],
  });
}

/** ESPN returns the whole season's schedule regardless of any per-week param, so this is fetched once per year. */
export async function getScoreboard(creds: EspnCredentials, year: number): Promise<EspnScoreboardPayload> {
  return leagueGet<EspnScoreboardPayload>(creds, year, { view: "mMatchupScore" });
}

/** Player data is only available for 2018+ and always lives at the modern endpoint shape. */
export async function getWeeklyRoster(creds: EspnCredentials, year: number, week: number): Promise<EspnRosterPayload> {
  const url = appendParams(leagueEndpoint(creds, year, true), { view: "mRoster", scoringPeriodId: String(week) });
  const { status, body } = await requestJson(url, creds);
  if (status !== 200) {
    throw new EspnUnknownError(`ESPN returned an HTTP ${status} fetching ${year} week ${week} roster`);
  }
  return body as EspnRosterPayload;
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
  return body as EspnMatchupRosterPayload;
}
