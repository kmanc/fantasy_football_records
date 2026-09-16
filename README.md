# fantasy_football_records

[We're live!!](https://walpolefantasyfootball.com/)

A TypeScript site running on Cloudflare Workers. Once a week (Tuesday morning) a Cron Trigger
fetches the season from ESPN's fantasy API, recomputes every record, and writes fully-rendered
HTML for every page into Workers KV. Every other request is just a KV read - no database, no
per-request computation, no separate build/deploy pipeline.

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
bunx wrangler kv namespace create LEAGUE_KV
# paste the printed id into wrangler.toml's [[kv_namespaces]] id field
bunx wrangler secret put ESPN_S2
bunx wrangler secret put ESPN_SWID
bunx wrangler deploy
```

Then, once, trigger the scheduled handler manually (Cloudflare dashboard -> Workers -> this
worker -> Triggers -> "Trigger cron" for the schedule, or `wrangler triggers`) so KV is
populated before anyone visits. After that it updates itself every Tuesday morning per the
`crons` schedule in `wrangler.toml`.

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
