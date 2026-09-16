import { GameOutcome } from "../../domain/enums";
import { titleCase } from "../../domain/utility";
import type { RenderContext } from "../context";
import { renderTable, td, tr } from "../components/tables";
import { formatMemberForDisplay } from "../format-member";
import { escapeHtml, formatCount, formatPoints } from "../html";
import { renderPage } from "../layout";

interface MinimalRecord {
  member: string;
  value: number;
}

function renderMinimalTable(ctx: RenderContext, currentPath: string, recordName: string, records: MinimalRecord[], asPercent: boolean): string {
  const rows = records.map((r) =>
    tr([td(escapeHtml(r.member)), td(asPercent ? `${formatPoints(r.value)}%` : formatCount(r.value), true)]),
  );
  const content = renderTable([{ label: "Member" }, { label: "Value", numeric: true }], rows);
  return renderPage({ titlePrefix: ctx.titlePrefix, recordName, currentPath, members: ctx.members, content });
}

export function renderChampionships(ctx: RenderContext): string {
  const records = [...ctx.league.membersWithChampionship()]
    .sort((a, b) => b.championshipWins() - a.championshipWins())
    .map((member) => ({ member: formatMemberForDisplay(ctx.league, member, true), value: member.championshipWins() }));
  return renderMinimalTable(ctx, "/championships", "Championships", records, false);
}

export function renderWinPercent(ctx: RenderContext): string {
  const records = [...ctx.league.membersList()]
    .sort((a, b) => b.regularSeasonWinPercentage() - a.regularSeasonWinPercentage())
    .map((member) => ({ member: formatMemberForDisplay(ctx.league, member), value: member.regularSeasonWinPercentage() }));
  return renderMinimalTable(ctx, "/win_percent", "Win percentage", records, true);
}

export function renderPlayoffAppearances(ctx: RenderContext): string {
  const records = [...ctx.league.membersList()]
    .filter((member) => member.playoffAppearances() > 0)
    .sort((a, b) => b.playoffAppearances() - a.playoffAppearances())
    .map((member) => ({ member: formatMemberForDisplay(ctx.league, member, true), value: member.playoffAppearances() }));
  return renderMinimalTable(ctx, "/playoff_appearances", "Playoff appearances", records, false);
}

export function renderHeadToHead(ctx: RenderContext, requestedName: string): string {
  const memberName = titleCase(requestedName.trim());
  const member = ctx.league.membersList().find((m) => m.name === memberName);
  const records: MinimalRecord[] = [];
  if (member) {
    const matchups = member.matchupSuperset();
    for (const opponent of ctx.league.membersList()) {
      if (opponent.id === member.id) continue;
      const gamesAgainst = matchups.filter((m) => m.opponent.member.name === opponent.name);
      if (gamesAgainst.length === 0) continue;
      const wins = gamesAgainst.filter((m) => m.outcome === GameOutcome.WIN).length;
      records.push({
        member: formatMemberForDisplay(ctx.league, opponent, true),
        value: Math.round(((wins * 100) / gamesAgainst.length) * 100) / 100,
      });
    }
  }
  records.sort((a, b) => b.value - a.value);
  return renderMinimalTable(ctx, `/head-to-head/${encodeURIComponent(memberName)}`, `Win percentages for ${memberName}`, records, true);
}
