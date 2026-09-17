# fantasy_football_records

[We're live!!](https://walpolefantasyfootball.com/)

A TypeScript site running on Cloudflare Workers. Once a week (Tuesday morning) a Cron Trigger
fetches the season from ESPN's fantasy API, recomputes every record, and writes fully-rendered
HTML for every page into Workers KV. Every other request is just a KV read - no database, no
per-request computation, no separate build/deploy pipeline.

Completed seasons are cached in KV forever (`src/espn/season-cache.ts`) so a normal run only
re-fetches the current, still-in-progress season from ESPN - otherwise a full rebuild would need
far more than the ~50 ESPN requests a single Workers-free-tier invocation is allowed to make.

### Local development

This project uses [Bun](https://bun.sh) for local dev/tests and [Wrangler](https://developers.cloudflare.com/workers/wrangler/)
to run/deploy the actual Worker (Cloudflare Workers run on their own `workerd` runtime, not Bun -
Bun is just the fast local tool here).

```
bun install
bun test              # unit tests for the scoring/standings/tiebreaker logic
bunx tsc --noEmit      # type-check
```

To run the whole thing locally (Miniflare-emulated KV, no Cloudflare account needed):

1. Copy `.dev.vars.sample` to `.dev.vars` and fill in real ESPN credentials (see below).
2. `bun run dev` (runs `wrangler dev --test-scheduled`).
3. Trigger the weekly update once so KV has something to serve: visit
   `http://localhost:8787/__scheduled` in a browser (it responds quickly but keeps building in
   the background - give it 10-20 seconds before loading other pages the first time).
4. Browse `http://localhost:8787`.

### Deploying for real (Cloudflare free tier)

```
bunx wrangler login
bunx wrangler kv namespace create WAFFL_LEAGUE_KV
# paste the printed id into wrangler.toml's [[kv_namespaces]] id field
bun run backfill-cache   # one-time: primes the KV cache for every already-completed season
bunx wrangler secret put ESPN_S2
bunx wrangler secret put ESPN_SWID
bunx wrangler deploy
```

Then, once, trigger the scheduled handler manually so KV is populated before anyone visits (the
Cloudflare dashboard's Workers -> this worker -> Triggers -> "Trigger cron" button is the normal
way to do this - see the note below if it doesn't work). After that it updates itself every
Tuesday morning per the `crons` schedule in `wrangler.toml`.

**Known issue:** as of September 2026, Cloudflare has an active platform bug where Cron Triggers
on new accounts don't fire - neither the real schedule nor the dashboard's manual "Trigger cron"
button ([community reports](https://community.cloudflare.com/t/newly-created-workers-cron-triggers-not-firing/392501)).
If that's still the case, `src/worker.ts` has a temporary `/__admin/trigger-update?key=...`
route (guarded by an `ADMIN_TRIGGER_KEY` secret you set the same way as the ESPN secrets above)
that runs the same rebuild over a plain HTTP request as a workaround. Remove that route and
secret once Cloudflare's Cron Triggers are confirmed working again.

To put it on the real domain, add a Custom Domain / Route for `walpolefantasyfootball.com` to
this Worker in the Cloudflare dashboard once DNS for that domain is on Cloudflare.

### Getting ESPN credentials

Get access to private leagues that you are a member of with the instructions on
[cwendt94's awesome ESPN API repo](https://github.com/cwendt94/espn-api) (this project only
borrows the two cookie values, `espn_s2` and `SWID` - it doesn't depend on that package).

### Project layout

- `src/domain/` - the league data model, ESPN response parsing, and the standings/playoff/tiebreaker logic
- `src/espn/` - a minimal ESPN fantasy API client (just the endpoints this project actually needs)
- `src/render/` - hand-rolled HTML templates (no framework), matching the site's existing look
- `src/worker.ts` - the Worker's `fetch` (serve a page from KV) and `scheduled` (weekly rebuild) handlers
- `public/` - static assets (CSS, manager photos), served directly by Workers Static Assets
