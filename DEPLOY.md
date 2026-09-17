# Deploying to Cloudflare (free tier)

This walks through getting `fantasy-football-records` live on Cloudflare Workers from
scratch, assuming you've never used Cloudflare before. It expands on the condensed
version in [README.md](README.md#deploying-for-real-cloudflare-free-tier) with every
step spelled out.

Everything here fits inside Cloudflare's free tier: the Worker gets ~100k
requests/day free, Workers KV gets 100k reads + 1k writes/day free, and Cron Triggers
cost nothing extra. This site is low-traffic and only writes to KV once a week, so
you won't come close to any of those limits.

## 1. Create a Cloudflare account

1. Go to https://dash.cloudflare.com/sign-up and create a free account (email + password).
2. Verify your email if prompted.
3. You don't need to add a domain, a payment method, or pick a plan for anything below —
   the free "Workers Paid" upsell screens can be skipped/dismissed.

## 2. Install project dependencies

From the project root:

```
bun install
```

This pulls in `wrangler` (Cloudflare's CLI, already listed in `package.json`), so you
don't need to install anything globally — every command below is run via `bunx`.

## 3. Log in to Cloudflare from the CLI

```
bunx wrangler login
```

This opens a browser tab asking you to authorize Wrangler against your Cloudflare
account. Click **Allow**. Once it redirects back and the terminal says
`Successfully logged in`, you're done with this step.

## 4. Create the KV namespace

The Worker stores every rendered page in one Workers KV namespace. Create it:

```
bunx wrangler kv namespace create WAFFL_LEAGUE_KV
```

This prints something like:

```
[[kv_namespaces]]
binding = "WAFFL_LEAGUE_KV"
id = "a1b2c3d4e5f6..."
```

Copy that `id` value and paste it into `wrangler.toml`, replacing the placeholder:

```toml
[[kv_namespaces]]
binding = "WAFFL_LEAGUE_KV"
id = "a1b2c3d4e5f6..."   # <- the id wrangler printed
```

## 5. Back-fill the season cache

Every already-completed season gets cached in KV forever, so a normal weekly run only needs to
fetch the current, still-in-progress season fresh from ESPN. Priming that cache requires making
hundreds of requests to ESPN (one league fetch, one scoreboard fetch, and two per-week roster
fetches for every past season) - too many for a single Workers invocation's ~50-request budget,
so this runs locally instead, straight into the KV namespace you just created:

```
bun run backfill-cache
```

You'll need `.dev.vars` filled in first (see [Local development](README.md#local-development) in
the README) since this reads your ESPN credentials from there. It prints one line per season and
takes a while - this is a one-time step (safe to re-run later; already-cached seasons are
skipped).

## 6. Set the ESPN credentials as secrets

The Worker needs your ESPN `espn_s2` and `SWID` cookie values in production. You
already have these in your local `.dev.vars` file (used for `wrangler dev`) — use the
same two values here. Each command will prompt you to paste the value:

```
bunx wrangler secret put ESPN_S2
bunx wrangler secret put ESPN_SWID
```

These are stored encrypted on Cloudflare's side and are separate from `.dev.vars`
(which is gitignored and only used for local dev).

If you don't already have these values, see the
[README's "Getting ESPN credentials" section](README.md#getting-espn-credentials).

## 7. Deploy the Worker

```
bunx wrangler deploy
```

Wrangler will build and upload the Worker, and print a URL like:

```
https://fantasy-football-records.<your-subdomain>.workers.dev
```

Don't visit it yet — KV is still empty, so every page would 404 or look broken.

## 8. Populate KV with the first build

The Worker only rebuilds its pages when the weekly Cron Trigger fires (Tuesday
12:00 UTC) or when you trigger it manually. Do that once now so the site has
content.

The normal way is the dashboard's manual trigger:

1. Go to the [Cloudflare dashboard](https://dash.cloudflare.com/) → **Workers & Pages**.
2. Click into the `fantasy-football-records` worker.
3. Go to the **Triggers** tab.
4. Under **Cron Triggers**, find the `0 12 * * TUE` schedule and click **Trigger
   cron** (the exact label may read "Trigger event" depending on dashboard version).
5. Wait 10-20 seconds — it fetches the current season from ESPN and writes every page to KV.

You can confirm it worked by checking **Logs** (Real-time Logs) in the same dashboard, or by
just visiting the `workers.dev` URL from step 7 after waiting.

**If that button does nothing** (no toast/confirmation, and KV stays empty): as of September
2026 Cloudflare has an active platform bug where Cron Triggers on new accounts don't fire at
all - neither the real schedule nor this manual button
([community reports](https://community.cloudflare.com/t/newly-created-workers-cron-triggers-not-firing/392501)).
As a workaround, `src/worker.ts` has a temporary route that does the same thing over a plain
HTTP request:

1. Set a random secret for it (any long random string works, e.g. from `openssl rand -hex 24`):
   ```
   bunx wrangler secret put ADMIN_TRIGGER_KEY
   ```
2. Hit the route with that value as the `key` query param:
   ```
   curl "https://fantasy-football-records.<your-subdomain>.workers.dev/__admin/trigger-update?key=<the value you just set>"
   ```
   A response of `OK` means it worked; an `Error: ...` body means something failed (the response
   includes the stack trace).

Once Cloudflare's Cron Triggers are confirmed working again (try the dashboard button, or just
wait for the next real Tuesday firing), remove the `/__admin/trigger-update` route and the
`ADMIN_TRIGGER_KEY` secret from `src/worker.ts` - it's only meant to exist as long as the
platform bug does.

## 9. Verify it's live

Visit the `https://fantasy-football-records.<your-subdomain>.workers.dev` URL from
step 7. You should see the site fully rendered — browse a few pages to confirm CSS
and manager photos (served from `public/`) are loading correctly.

## 10. Point your real domain at it (optional)

If `walpolefantasyfootball.com` isn't on Cloudflare yet:

1. In the dashboard, click **Add a domain** and enter `walpolefantasyfootball.com`.
2. Cloudflare will scan your existing DNS records and give you two nameservers
   (something like `xxx.ns.cloudflare.com`).
3. Go to wherever the domain is registered (e.g. GoDaddy, Namecheap) and change the
   domain's nameservers to the two Cloudflare gave you. This can take anywhere from a
   few minutes to ~24 hours to propagate.
4. Back in Cloudflare, wait until the dashboard shows the domain as **Active**.

Once the domain is active on Cloudflare:

1. Go to **Workers & Pages** → `fantasy-football-records` → **Settings** → **Domains
   & Routes**.
2. Click **Add** → **Custom Domain**, enter `walpolefantasyfootball.com` (and
   `www.walpolefantasyfootball.com` if you want both), and confirm.
3. Cloudflare provisions an SSL certificate automatically — this usually takes a few
   minutes. Once done, the real domain serves the Worker directly.

## You're done

From here, the site updates itself automatically every Tuesday morning via the Cron
Trigger — no further action needed (once the Cloudflare cron bug from step 8 is resolved; until
then, re-run the `/__admin/trigger-update` curl from step 8 each Tuesday). For future code
changes, redeploy with:

```
bunx wrangler deploy
```

If you ever need to check on it: **Workers & Pages** → `fantasy-football-records` in
the Cloudflare dashboard shows request counts, errors, and logs, all within the free
tier's usage graphs.
