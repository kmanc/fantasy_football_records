import type { PlayoffPictureEntry } from "../../domain/playoff-snapshot";
import type { RenderContext } from "../context";
import { cell, renderTable, type TableCell } from "../components/tables";
import { escapeHtml } from "../html";
import { renderPage } from "../layout";

/** playoff-snapshot.ts encodes the clinch marker and its label together, e.g. "* (clinched division)"
 * or "** (clinched bye)"; the bracket/table just need the marker, the legend spells out what it means. */
function clinchMark(clinched: string | undefined): string {
  return clinched?.split(" ")[0] ?? "";
}

function teamLabel(entry: PlayoffPictureEntry | undefined): string {
  if (!entry?.name) return "";
  const mark = clinchMark(entry.clinched);
  const markHtml = mark ? ` <span class="clinch-mark">${escapeHtml(mark)}</span>` : "";
  return `${escapeHtml(entry.name)}${markHtml}`;
}

function isWinner(entry: PlayoffPictureEntry | undefined, advancedTo: PlayoffPictureEntry | undefined): boolean {
  return Boolean(entry?.name && advancedTo?.name && entry.name === advancedTo.name);
}

function teamDiv(entry: PlayoffPictureEntry | undefined, advancedTo: PlayoffPictureEntry | undefined): string {
  const winnerClass = isWinner(entry, advancedTo) ? " winner" : "";
  return `<div class="team${winnerClass}">${teamLabel(entry)}</div>`;
}

function renderBracket(seeds: PlayoffPictureEntry[]): string {
  const s = seeds;
  return `<div class="bracket">
    <ul class="round round-1" data-label="Wildcard">
        <li class="game">
            ${teamDiv(s[0], s[12])}
            <div class="team bye-slot">BYE</div>
        </li>
        <li class="game">
            ${teamDiv(s[4], s[14])}
            ${teamDiv(s[3], s[14])}
        </li>
        <li class="game">
            ${teamDiv(s[5], s[15])}
            ${teamDiv(s[2], s[15])}
        </li>
        <li class="game">
            <div class="team bye-slot">BYE</div>
            ${teamDiv(s[1], s[13])}
        </li>
    </ul>
    <ul class="round round-2" data-label="Semifinals">
        <li class="game">
            ${teamDiv(s[12], s[16])}
            ${teamDiv(s[14], s[16])}
        </li>
        <li class="game">
            ${teamDiv(s[15], s[17])}
            ${teamDiv(s[13], s[17])}
        </li>
    </ul>
    <ul class="round round-3" data-label="Championship">
        <li class="game">
            ${teamDiv(s[16], s[18])}
            ${teamDiv(s[17], s[18])}
        </li>
    </ul>
    <ul class="round round-4 round-final" data-label="Champion">
        <li class="game">
            <div class="team champ">${escapeHtml(s[18]?.name ?? "")}</div>
        </li>
    </ul>
</div>`;
}

export function renderSnapshot(ctx: RenderContext, seeds: PlayoffPictureEntry[], teamCount: number): string {
  const records = seeds.slice(0, teamCount);
  const rows: TableCell[][] = records.map((record) => {
    const mark = clinchMark(record.clinched);
    const nameHtml = mark
      ? `${escapeHtml(record.name)} <span class="clinch-mark">${escapeHtml(mark)}</span>`
      : escapeHtml(record.name);
    return [
      cell(record.seed !== undefined ? escapeHtml(String(record.seed)) : "—", true),
      cell(nameHtml),
      cell(`${record.wins ?? ""}–${record.losses ?? ""}`, true),
      cell(record.pointsFor !== undefined ? String(record.pointsFor) : "", true),
      cell(record.pointsOut !== undefined ? String(record.pointsOut) : "—", true),
    ];
  });
  const table = renderTable(
    [
      { label: "Seed", numeric: true },
      { label: "Team", kind: "team" },
      { label: "Record", numeric: true },
      { label: "Points For", numeric: true },
      { label: "Points Out", numeric: true },
    ],
    rows,
  );

  const content = `<section class="hero-snapshot">
    <div class="wrap">
        <h1>${ctx.league.activeYear} playoff picture</h1>
        <p>Standings if the season ended today.</p>
    </div>
</section>

<div class="wrap">
    <section class="bracket-section">
        ${renderBracket(seeds)}
        <ul class="legend">
            <li><span class="clinch-mark">*</span> Clinched division</li>
            <li><span class="clinch-mark">**</span> Clinched first-round bye</li>
        </ul>
    </section>

    <section class="standings-section">
        <h2>Full standings</h2>
        ${table}
    </section>
</div>`;

  return renderPage({
    titlePrefix: ctx.titlePrefix,
    recordName: "Current playoff snapshot",
    currentPath: "/snapshot",
    members: ctx.members,
    content,
    heading: false,
    extraHeadLinks: ["/static/bracket.css"],
  });
}
