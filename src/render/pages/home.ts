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

export function renderHome(ctx: RenderContext, leagueName: string): string {
  const timelineHtml = TIMELINE_ITEMS.map(
    (item) => `<li class="timeline-item">
    <time datetime="${item.year}" class="timeline-year">${item.year}</time>
    <div class="timeline-body">
        <h5>${item.title}</h5>
        <p>${item.body}</p>
    </div>
</li>`,
  ).join("\n");

  const content = `<div class="welcome-message">
    <b>Welcome to the ${escapeHtml(leagueName)} online record book</b>
</div>

<section class="league-timeline-wrap">
    <h2 class="league-timeline-heading">League timeline</h2>
    <ol class="timeline">
        ${timelineHtml}
    </ol>
</section>`;

  return renderPage({
    titlePrefix: ctx.titlePrefix,
    recordName: "Home",
    currentPath: "/",
    members: ctx.members,
    content,
    extraHeadLinks: ["/static/index.css"],
  });
}
