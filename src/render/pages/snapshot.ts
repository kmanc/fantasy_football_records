import type { PlayoffPictureEntry } from "../../domain/playoff-snapshot";
import type { RenderContext } from "../context";
import { renderTable, td, tr } from "../components/tables";
import { escapeHtml } from "../html";
import { renderPage } from "../layout";

function teamCell(entry: PlayoffPictureEntry | undefined): string {
  return escapeHtml(entry?.name ?? "");
}

function isWinner(entry: PlayoffPictureEntry | undefined, advancedTo: PlayoffPictureEntry | undefined): boolean {
  return Boolean(entry?.name && advancedTo?.name && entry.name === advancedTo.name);
}

function teamDiv(entry: PlayoffPictureEntry | undefined, advancedTo: PlayoffPictureEntry | undefined, extraClass = ""): string {
  const winnerClass = isWinner(entry, advancedTo) ? " winner" : "";
  return `<div class="team${winnerClass}${extraClass}">${teamCell(entry)}</div>`;
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
            <div class="team champ">${teamCell(s[18])}</div>
        </li>
    </ul>
</div>`;
}

export function renderSnapshot(ctx: RenderContext, seeds: PlayoffPictureEntry[], teamCount: number): string {
  const records = seeds.slice(0, teamCount);
  const rows = records.map((record) =>
    tr([
      td(record.seed !== undefined ? escapeHtml(String(record.seed)) : "", true),
      td(`${escapeHtml(record.name)}${escapeHtml(record.clinched ?? "")}`),
      td(`${record.wins ?? ""} - ${record.losses ?? ""}`, true),
      td(record.pointsFor !== undefined ? String(record.pointsFor) : "", true),
      td(record.pointsOut !== undefined ? String(record.pointsOut) : "", true),
    ]),
  );
  const table = renderTable(
    [
      { label: "Seed", numeric: true },
      { label: "Team Name" },
      { label: "Record", numeric: true },
      { label: "Points For", numeric: true },
      { label: "Points Out", numeric: true },
    ],
    rows,
  );

  const content = `${renderBracket(seeds)}
<div>
    ${table}
</div>`;

  return renderPage({
    titlePrefix: ctx.titlePrefix,
    recordName: "Current playoff snapshot",
    currentPath: "/snapshot",
    members: ctx.members,
    content,
    extraHeadLinks: ["/static/bracket.css"],
  });
}
