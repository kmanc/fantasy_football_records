import { GameOutcome } from "../../domain/enums";
import type { Matchup } from "../../domain/model";
import type { RenderContext } from "../context";
import { renderTable, td, tr } from "../components/tables";
import { formatMemberForDisplay } from "../format-member";
import { escapeHtml, formatPoints } from "../html";
import { renderPage } from "../layout";
import { bottom9Reversed, top10 } from "../slicing";

function renderWeekTable(ctx: RenderContext, currentPath: string, recordName: string, matchups: Matchup[]): string {
  const rows = matchups.map((matchup) =>
    tr([
      td(escapeHtml(formatMemberForDisplay(ctx.league, matchup.team.member))),
      td(escapeHtml(matchup.team.name)),
      td(String(matchup.team.year), true),
      td(String(matchup.week), true),
      td(formatPoints(matchup.pointsFor), true),
    ]),
  );
  const content = renderTable(
    [
      { label: "Member" },
      { label: "Team Name" },
      { label: "Year", numeric: true },
      { label: "Week", numeric: true },
      { label: "Points", numeric: true },
    ],
    rows,
  );
  return renderPage({ titlePrefix: ctx.titlePrefix, recordName, currentPath, members: ctx.members, content });
}

export function renderHighestWeek(ctx: RenderContext): string {
  return renderWeekTable(ctx, "/highest_week", "Most points in one week", top10(ctx.league.matchupsByPointsFor()));
}

export function renderLowestWeek(ctx: RenderContext): string {
  return renderWeekTable(ctx, "/lowest_week", "Least points in one week", bottom9Reversed(ctx.league.matchupsByPointsFor()));
}

export function renderLowestWin(ctx: RenderContext): string {
  const matchups = [...ctx.league.matchupSuperset()]
    .filter((m) => m.outcome === GameOutcome.WIN)
    .sort((a, b) => a.pointsFor - b.pointsFor)
    .slice(0, 10);
  return renderWeekTable(ctx, "/lowest_win", "Least points that still won", matchups);
}

export function renderHighestLoss(ctx: RenderContext): string {
  const matchups = [...ctx.league.matchupSuperset()]
    .filter((m) => m.outcome === GameOutcome.LOSS)
    .sort((a, b) => b.pointsFor - a.pointsFor)
    .slice(0, 10);
  return renderWeekTable(ctx, "/highest_loss", "Most points that still lost", matchups);
}
