import type { Team } from "../../domain/model";
import type { RenderContext } from "../context";
import { renderTable, td, tr } from "../components/tables";
import { formatMemberForDisplay } from "../format-member";
import { escapeHtml, formatPoints } from "../html";
import { renderPage } from "../layout";
import { bottom9Reversed, top10 } from "../slicing";

function renderSeasonTable(
  ctx: RenderContext,
  currentPath: string,
  recordName: string,
  teams: Team[],
  value: (team: Team) => number,
): string {
  const rows = teams.map((team) =>
    tr([
      td(escapeHtml(formatMemberForDisplay(ctx.league, team.member))),
      td(escapeHtml(team.name)),
      td(String(team.year), true),
      td(formatPoints(value(team)), true),
    ]),
  );
  const content = renderTable(
    [{ label: "Member" }, { label: "Team Name" }, { label: "Year", numeric: true }, { label: "Points", numeric: true }],
    rows,
  );
  return renderPage({ titlePrefix: ctx.titlePrefix, recordName, currentPath, members: ctx.members, content });
}

export function renderHighestRegularSeason(ctx: RenderContext): string {
  const teams = top10(ctx.league.teamsByRegularSeasonPointsFor());
  return renderSeasonTable(ctx, "/highest_regular_season", "Most points in one season", teams, (t) => t.regularSeasonPointsScored());
}

export function renderLowestRegularSeason(ctx: RenderContext): string {
  const teams = bottom9Reversed(ctx.league.teamsByRegularSeasonPointsFor(true));
  return renderSeasonTable(ctx, "/lowest_regular_season", "Least points in one season", teams, (t) => t.regularSeasonPointsScored());
}

export function renderBestDefense(ctx: RenderContext): string {
  const teams = bottom9Reversed(ctx.league.teamsByRegularSeasonPointsAgainst(true));
  return renderSeasonTable(ctx, "/best_defense", "Least points against in one season", teams, (t) => t.regularSeasonPointsAgainst());
}

export function renderWorstDefense(ctx: RenderContext): string {
  const teams = top10(ctx.league.teamsByRegularSeasonPointsAgainst());
  return renderSeasonTable(ctx, "/worst_defense", "Most points against in one season", teams, (t) => t.regularSeasonPointsAgainst());
}
