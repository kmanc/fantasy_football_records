import {
  EspnInvalidLeagueError,
  getLeaguePayload,
  getScoreboard,
  getWeeklyMatchupRosters,
  getWeeklyRoster,
  type EspnCredentials,
} from "./client";
import type {
  EspnLeaguePayload,
  EspnMatchupRosterPayload,
  EspnRosterPayload,
  EspnScoreboardPayload,
} from "./types";

export { EspnInvalidLeagueError };

/** Minimal read/write surface both a Workers KV binding and a local backfill script can satisfy. */
export interface SeasonCacheStore {
  get(key: string): Promise<string | null>;
  put(key: string, value: string): Promise<void>;
}

export interface FetchedSeasonData {
  payload: EspnLeaguePayload;
  scoreboard: EspnScoreboardPayload;
  currentWeek: number;
  totalMatchupPeriods: number;
  /** Only populated for weeks with real (non-bye, played) matchups, and only for 2018+ seasons. */
  weeklyRosters: Record<number, EspnRosterPayload>;
  weeklyMatchupRosters: Record<number, EspnMatchupRosterPayload>;
}

function seasonCacheKey(year: number): string {
  return `espn-season-cache:${year}`;
}

export async function readSeasonCache(store: SeasonCacheStore, year: number): Promise<FetchedSeasonData | null> {
  const raw = await store.get(seasonCacheKey(year));
  return raw === null ? null : (JSON.parse(raw) as FetchedSeasonData);
}

export async function writeSeasonCache(store: SeasonCacheStore, year: number, data: FetchedSeasonData): Promise<void> {
  await store.put(seasonCacheKey(year), JSON.stringify(data));
}

export function isSeasonFinal(data: Pick<FetchedSeasonData, "currentWeek" | "totalMatchupPeriods">): boolean {
  return data.currentWeek >= data.totalMatchupPeriods;
}

/** Mirrors ESPN's own "current week" semantics, which differ for pre-2018 seasons. */
function computeCurrentWeek(year: number, payload: EspnLeaguePayload): number {
  if (year < 2018) return payload.scoringPeriodId;
  return payload.scoringPeriodId <= payload.status.finalScoringPeriod
    ? payload.scoringPeriodId
    : payload.status.finalScoringPeriod;
}

/**
 * Fetches everything buildLeague needs for one season directly from ESPN: the league payload,
 * the scoreboard, and (for 2018+ seasons) each played week's roster + matchup-roster payloads.
 * Used both for a not-yet-cached year during a normal run and by the one-time backfill script.
 */
export async function fetchSeasonData(creds: EspnCredentials, year: number): Promise<FetchedSeasonData> {
  const payload = await getLeaguePayload(creds, year);
  const currentWeek = computeCurrentWeek(year, payload);
  const totalMatchupPeriods = Object.keys(payload.settings.scheduleSettings.matchupPeriods).length;
  const scoreboard = await getScoreboard(creds, year);

  const weeklyRosters: Record<number, EspnRosterPayload> = {};
  const weeklyMatchupRosters: Record<number, EspnMatchupRosterPayload> = {};
  const maxWeek = Math.min(totalMatchupPeriods, currentWeek);

  if (year >= 2018) {
    for (let week = 1; week <= maxWeek; week++) {
      const weekMatchups = scoreboard.schedule.filter((m) => m.matchupPeriodId === week);
      if (weekMatchups.length === 0) continue;
      const allZero = weekMatchups.every((m) => (m.home?.totalPoints ?? 0) === 0 && (m.away?.totalPoints ?? 0) === 0);
      if (allZero) continue;

      try {
        const [rosterPayload, matchupRosterPayload] = await Promise.all([
          getWeeklyRoster(creds, year, week),
          getWeeklyMatchupRosters(creds, year, week),
        ]);
        weeklyRosters[week] = rosterPayload;
        weeklyMatchupRosters[week] = matchupRosterPayload;
      } catch (err) {
        // Degrades to "no lineup data" for this week rather than failing the whole season fetch.
        console.warn(`Failed to fetch player data for ${year} week ${week}:`, err);
      }
    }
  }

  return { payload, scoreboard, currentWeek, totalMatchupPeriods, weeklyRosters, weeklyMatchupRosters };
}

/**
 * Loads one season's data, preferring the cache. A cache hit means zero ESPN requests. A cache
 * miss fetches fresh from ESPN and, if the season turned out to be over, caches it so it's never
 * fetched again. Returns null if the league didn't exist yet for this year (future season).
 */
export async function loadOrFetchSeason(
  store: SeasonCacheStore,
  creds: EspnCredentials,
  year: number,
): Promise<FetchedSeasonData | null> {
  const cached = await readSeasonCache(store, year);
  if (cached) return cached;

  let data: FetchedSeasonData;
  try {
    data = await fetchSeasonData(creds, year);
  } catch (err) {
    if (err instanceof EspnInvalidLeagueError) return null;
    throw err;
  }

  if (isSeasonFinal(data)) {
    await writeSeasonCache(store, year, data);
  }
  return data;
}
