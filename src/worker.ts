import { buildLeague } from "./domain/build-league";
import { computePlayoffSnapshot } from "./domain/playoff-snapshot";
import { titleCase } from "./domain/utility";
import { renderAllPages } from "./routes";

export interface Env {
  WAFFL_LEAGUE_KV: KVNamespace;
  ESPN_S2: string;
  ESPN_SWID: string;
  LEAGUE_ID: number;
  LEAGUE_FOUNDED: number;
  LEAGUE_NAME: string;
  LEAGUE_ABBREVIATION: string;
  /** TEMPORARY: lets `/__admin/trigger-update` run the weekly rebuild over HTTP while Cron
   * Triggers are being debugged. Remove this + the route in worker.ts once cron works. */
  ADMIN_TRIGGER_KEY: string;
}

const HEAD_TO_HEAD_PREFIX = "/head-to-head/";

/** Mirrors the old Flask route's `member_name.strip().title()` normalization, so a request with
 * different whitespace/casing still resolves to the same pre-rendered page. */
function normalizePath(pathname: string): string {
  if (!pathname.startsWith(HEAD_TO_HEAD_PREFIX)) return pathname;
  const raw = decodeURIComponent(pathname.slice(HEAD_TO_HEAD_PREFIX.length));
  return HEAD_TO_HEAD_PREFIX + encodeURIComponent(titleCase(raw.trim()));
}

async function runWeeklyUpdate(env: Env): Promise<void> {
  const creds = { leagueId: env.LEAGUE_ID, espnS2: env.ESPN_S2, swid: env.ESPN_SWID };
  const currentCalendarYear = new Date().getFullYear();

  const { league, currentWeek } = await buildLeague(env.WAFFL_LEAGUE_KV, creds, env.LEAGUE_FOUNDED, currentCalendarYear);
  const playoffSnapshot = computePlayoffSnapshot(league, currentWeek);
  const pages = renderAllPages({
    league,
    leagueName: env.LEAGUE_NAME,
    leagueAbbreviation: env.LEAGUE_ABBREVIATION,
    playoffSnapshot,
  });

  await Promise.all([...pages.entries()].map(([path, html]) => env.WAFFL_LEAGUE_KV.put(`page:${path}`, html)));
  console.log(`Weekly update complete: wrote ${pages.size} pages.`);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/__admin/trigger-update") {
      if (url.searchParams.get("key") !== env.ADMIN_TRIGGER_KEY) {
        return new Response("Not found", { status: 404 });
      }
      try {
        await runWeeklyUpdate(env);
        return new Response("OK\n");
      } catch (err) {
        return new Response(`Error: ${err instanceof Error ? err.stack : String(err)}\n`, { status: 500 });
      }
    }

    const html = await env.WAFFL_LEAGUE_KV.get(`page:${normalizePath(url.pathname)}`);
    if (html === null) {
      return new Response("Not found", { status: 404 });
    }
    return new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } });
  },

  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(runWeeklyUpdate(env));
  },
} satisfies ExportedHandler<Env>;
