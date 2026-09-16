import type { RenderContext } from "../context";
import { escapeHtml } from "../html";
import { renderPage } from "../layout";

const TIMELINE_ITEMS: Array<{ year: string; title: string; body: string }> = [
  { year: "2012", title: "Founding", body: "The league was founded. Due to unknown reasons, all data before 2014 has been lost." },
  { year: "2015", title: "Keeper era", body: "The keeper era began this year." },
  {
    year: "2018",
    title: "Scoring &amp; stats overhaul",
    body: ".5 PPR scoring was introduced, and player-specific stats became available from this point onward.",
  },
  { year: "2021", title: "17-game season", body: "The NFL expanded to a 17-game regular season." },
  { year: "2022", title: "Kickers retired", body: "Kickers were removed from the league." },
];

/** The league's own seal (public/favicon.svg), inlined so it can sit large and crisp in the hero
 * without an extra network request for what's otherwise a small favicon-sized asset. */
const SEAL_MARK = `<svg class="home-hero-mark" viewBox="0 0 504 352" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="WaFFL seal">
    <rect x="0" y="0" width="504" height="352" fill="#ffffff"/>
    <path d="M9,40 C50,14 110,1 172,4 C205,5 225,11 250,18 C275,11 295,5 328,4 C390,1 450,14 493,40 L493,335 C493,341 489,345 483,345 L19,345 C13,345 9,341 9,335 Z" fill="#ffffff" stroke="#000000" stroke-width="3" stroke-linejoin="round"/>
    <path d="M9,40 C50,14 110,1 172,4 C205,5 225,11 250,18 C275,11 295,5 328,4 C390,1 450,14 493,40 L493,54 C450,28 390,15 328,18 C295,19 275,25 250,32 C225,25 205,19 172,18 C110,15 50,28 9,54 Z" fill="#cccccc" stroke="#000000" stroke-width="2" stroke-linejoin="round"/>
    <defs>
        <path id="archPath" d="M92,135 A 450,450 0 0 1 412,135"/>
        <clipPath id="melonClip"><ellipse cx="251" cy="200" rx="38" ry="25"/></clipPath>
    </defs>
    <text font-size="64" font-weight="normal" fill="#000000" font-family="Arial, Helvetica, sans-serif" letter-spacing="2">
        <textPath href="#archPath" startOffset="50%" text-anchor="middle">Entering</textPath>
    </text>
    <g>
        <path d="M 266.01,129.98 L 269.54,139.13 L 279.32,139.65 L 271.72,145.83 L 274.24,155.31 L 266.01,149.98 L 257.78,155.31 L 260.3,145.83 L 252.7,139.65 L 262.48,139.13 Z" fill="#FFBD45" stroke="#476125" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 292.01,144.99 L 295.54,154.14 L 305.32,154.66 L 297.72,160.84 L 300.24,170.32 L 292.01,164.99 L 283.78,170.32 L 286.3,160.84 L 278.7,154.66 L 288.48,154.14 Z" fill="#FFBD45" stroke="#476125" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 307.02,170.99 L 310.55,180.14 L 320.33,180.66 L 312.73,186.84 L 315.25,196.32 L 307.02,190.99 L 298.79,196.32 L 301.31,186.84 L 293.71,180.66 L 303.49,180.14 Z" fill="#FFBD45" stroke="#476125" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 307.02,201.01 L 310.55,210.16 L 320.33,210.68 L 312.73,216.86 L 315.25,226.34 L 307.02,221.01 L 298.79,226.34 L 301.31,216.86 L 293.71,210.68 L 303.49,210.16 Z" fill="#FFBD45" stroke="#476125" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 292.01,227.01 L 295.54,236.16 L 305.32,236.68 L 297.72,242.86 L 300.24,252.34 L 292.01,247.01 L 283.78,252.34 L 286.3,242.86 L 278.7,236.68 L 288.48,236.16 Z" fill="#FFBD45" stroke="#476125" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 266.01,242.02 L 269.54,251.17 L 279.32,251.69 L 271.72,257.87 L 274.24,267.35 L 266.01,262.02 L 257.78,267.35 L 260.3,257.87 L 252.7,251.69 L 262.48,251.17 Z" fill="#FFBD45" stroke="#476125" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 235.99,242.02 L 239.52,251.17 L 249.3,251.69 L 241.7,257.87 L 244.22,267.35 L 235.99,262.02 L 227.76,267.35 L 230.28,257.87 L 222.68,251.69 L 232.46,251.17 Z" fill="#176CFF" stroke="#1a3a66" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 209.99,227.01 L 213.52,236.16 L 223.3,236.68 L 215.7,242.86 L 218.22,252.34 L 209.99,247.01 L 201.76,252.34 L 204.28,242.86 L 196.68,236.68 L 206.46,236.16 Z" fill="#176CFF" stroke="#1a3a66" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 194.98,201.01 L 198.51,210.16 L 208.29,210.68 L 200.69,216.86 L 203.21,226.34 L 194.98,221.01 L 186.75,226.34 L 189.27,216.86 L 181.67,210.68 L 191.45,210.16 Z" fill="#176CFF" stroke="#1a3a66" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 194.98,170.99 L 198.51,180.14 L 208.29,180.66 L 200.69,186.84 L 203.21,196.32 L 194.98,190.99 L 186.75,196.32 L 189.27,186.84 L 181.67,180.66 L 191.45,180.14 Z" fill="#176CFF" stroke="#1a3a66" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 209.99,144.99 L 213.52,154.14 L 223.3,154.66 L 215.7,160.84 L 218.22,170.32 L 209.99,164.99 L 201.76,170.32 L 204.28,160.84 L 196.68,154.66 L 206.46,154.14 Z" fill="#176CFF" stroke="#1a3a66" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M 235.99,129.98 L 239.52,139.13 L 249.3,139.65 L 241.7,145.83 L 244.22,155.31 L 235.99,149.98 L 227.76,155.31 L 230.28,145.83 L 222.68,139.65 L 232.46,139.13 Z" fill="#176CFF" stroke="#1a3a66" stroke-width="1.3" stroke-linejoin="round"/>
    </g>
    <g transform="rotate(-22 251 200)">
        <ellipse cx="251" cy="200" rx="38" ry="25" fill="#69B300" stroke="#000000" stroke-width="2.5"/>
        <ellipse cx="242" cy="191" rx="20" ry="10" fill="#7fc61a" opacity="0.45"/>
        <g clip-path="url(#melonClip)" fill="none" stroke="#254200" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 206.0,183 L 217.2,185 L 228.5,182 L 239.8,186 L 251.0,181 L 262.2,184 L 273.5,180 L 284.8,185 L 296.0,183"/>
            <path d="M 202.0,195 L 214.2,192 L 226.5,197 L 238.8,193 L 251.0,196 L 263.2,191 L 275.5,195 L 287.8,196 L 300.0,193"/>
            <path d="M 202.0,205 L 214.2,209 L 226.5,204 L 238.8,207 L 251.0,203 L 263.2,208 L 275.5,205 L 287.8,209 L 300.0,206"/>
            <path d="M 206.0,217 L 217.2,214 L 228.5,219 L 239.8,216 L 251.0,220 L 262.2,215 L 273.5,218 L 284.8,215 L 296.0,217"/>
            <path d="M 233,193 L 236,187" stroke-width="3"/>
        </g>
        <ellipse cx="251" cy="200" rx="38" ry="25" fill="none" stroke="#000000" stroke-width="2.5"/>
    </g>
    <text x="167" y="207" font-size="28" fill="#000000" text-anchor="end">Inc.</text>
    <text x="335" y="207" font-size="28" fill="#000000" text-anchor="start">2010</text>
    <text x="252" y="332" font-size="76" font-weight="bold" fill="#000000" text-anchor="middle" font-family="'Arial Black', Arial, Helvetica, sans-serif">WaFFL</text>
</svg>`;

export function renderHome(ctx: RenderContext, leagueName: string): string {
  const timelineHtml = TIMELINE_ITEMS.map(
    (item) => `<li class="timeline-item">
    <time datetime="${item.year}" class="timeline-year">${item.year}</time>
    <div class="timeline-body">
        <h3>${item.title}</h3>
        <p>${item.body}</p>
    </div>
</li>`,
  ).join("\n");

  const content = `<div class="wrap">
    <section class="home-hero">
        ${SEAL_MARK}
        <div class="home-hero-text">
            <h1>${escapeHtml(leagueName)}</h1>
            <p>The league's online record book &mdash; every championship, every blowout, every Pooper Bowl, since 2014.</p>
            <a class="btn btn-primary" href="/snapshot">See this week's playoff picture</a>
        </div>
    </section>

    <section class="timeline-section">
        <h2>League history</h2>
        <ol class="timeline">
            ${timelineHtml}
        </ol>
    </section>
</div>`;

  return renderPage({
    titlePrefix: ctx.titlePrefix,
    recordName: "Home",
    currentPath: "/",
    members: ctx.members,
    content,
    heading: false,
    extraHeadLinks: ["/static/index.css"],
  });
}
