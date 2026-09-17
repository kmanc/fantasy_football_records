#!/usr/bin/env bun
/**
 * One-time backfill: primes the Workers KV season cache directly from a local Bun process, which
 * has no Workers-style per-invocation subrequest cap. Run this once after creating the KV
 * namespace and before (or right after) the first `wrangler deploy` - otherwise the Worker's own
 * first run would try to fetch the league's entire multi-year history from ESPN in one invocation
 * and hit that cap. Safe to re-run later (already-cached seasons are skipped); only needed again
 * if you ever wipe the KV namespace.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { EspnCredentials } from "../src/espn/client";
import { EspnInvalidLeagueError } from "../src/espn/client";
import {
  fetchSeasonData,
  isSeasonFinal,
  readSeasonCache,
  writeSeasonCache,
  type FetchedSeasonData,
  type SeasonCacheStore,
} from "../src/espn/season-cache";

const KV_BINDING = "WAFFL_LEAGUE_KV";
const PROJECT_ROOT = join(import.meta.dir, "..");

function parseDevVars(path: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const match = line.match(/^([A-Z0-9_]+)\s*=\s*"(.*)"\s*$/);
    if (match) out[match[1]!] = match[2]!;
  }
  return out;
}

function parseWranglerNumberVar(path: string, name: string): number {
  const text = readFileSync(path, "utf8");
  const match = text.match(new RegExp(`^${name}\\s*=\\s*(\\d+)`, "m"));
  if (!match) throw new Error(`Could not find ${name} in ${path}`);
  return Number(match[1]);
}

class RemoteKvStore implements SeasonCacheStore {
  async get(key: string): Promise<string | null> {
    const result = await Bun.$`bunx wrangler kv key get ${key} --binding=${KV_BINDING} --remote`.quiet().nothrow();
    if (result.exitCode !== 0) return null;
    const text = result.stdout.toString().trim();
    return text.length > 0 ? text : null;
  }

  async put(key: string, value: string): Promise<void> {
    const tmpPath = join(PROJECT_ROOT, `season-cache-${key.replace(/[^a-z0-9-]/gi, "_")}.json`);
    await Bun.write(tmpPath, value);
    try {
      await Bun.$`bunx wrangler kv key put ${key} --binding=${KV_BINDING} --remote --path=${tmpPath}`.quiet();
    } finally {
      await Bun.$`rm ${tmpPath}`.quiet();
    }
  }
}

async function main(): Promise<void> {
  const devVars = parseDevVars(join(PROJECT_ROOT, ".dev.vars"));
  const wranglerToml = join(PROJECT_ROOT, "wrangler.toml");
  if (!devVars.ESPN_S2 || !devVars.ESPN_SWID) {
    throw new Error("ESPN_S2 / ESPN_SWID not found in .dev.vars - copy .dev.vars.sample and fill them in first.");
  }

  const creds: EspnCredentials = {
    leagueId: parseWranglerNumberVar(wranglerToml, "LEAGUE_ID"),
    espnS2: devVars.ESPN_S2,
    swid: devVars.ESPN_SWID,
  };
  const foundedYear = parseWranglerNumberVar(wranglerToml, "LEAGUE_FOUNDED");
  const currentCalendarYear = new Date().getFullYear();
  const store = new RemoteKvStore();

  for (let year = foundedYear; year <= currentCalendarYear; year++) {
    if (await readSeasonCache(store, year)) {
      console.log(`${year}: already cached, skipping`);
      continue;
    }

    let data: FetchedSeasonData;
    try {
      data = await fetchSeasonData(creds, year);
    } catch (err) {
      if (err instanceof EspnInvalidLeagueError) {
        console.log(`${year}: league did not exist yet, skipping`);
        continue;
      }
      throw err;
    }

    if (!isSeasonFinal(data)) {
      console.log(`${year}: season still in progress, leaving for the Worker to fetch live each run`);
      continue;
    }

    await writeSeasonCache(store, year, data);
    console.log(`${year}: fetched and cached`);
  }

  console.log("Backfill complete.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
