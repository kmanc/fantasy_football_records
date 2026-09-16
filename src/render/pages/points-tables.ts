import type { RenderContext } from "../context";
import { cell, rankCell, RANK_COLUMN, renderTable } from "../components/tables";
import { formatMemberForDisplay } from "../format-member";
import { escapeHtml, formatPoints } from "../html";
import { renderPage } from "../layout";

interface PointsRecord {
  member: string;
  value: number;
  average: number;
}

function renderPointsTable(ctx: RenderContext, currentPath: string, recordName: string, records: PointsRecord[]): string {
  const rows = records.map((r, i) => [
    rankCell(i + 1),
    cell(escapeHtml(r.member)),
    cell(formatPoints(r.value), true),
    cell(formatPoints(r.average), true),
  ]);
  const content = renderTable(
    [RANK_COLUMN, { label: "Member", kind: "member" }, { label: "Value", numeric: true }, { label: "PPG", numeric: true }],
    rows,
  );
  return renderPage({ titlePrefix: ctx.titlePrefix, recordName, currentPath, members: ctx.members, content });
}

export function renderTotalRegularSeasonPoints(ctx: RenderContext): string {
  const records = [...ctx.league.membersList()]
    .sort((a, b) => b.regularSeasonPoints() - a.regularSeasonPoints())
    .map((member) => ({
      member: formatMemberForDisplay(ctx.league, member, true),
      value: member.regularSeasonPoints(),
      average: member.regularSeasonAveragePoints(),
    }));
  return renderPointsTable(ctx, "/total_regular_season_points", "All time regular season points", records);
}

export function renderTotalPlayoffPoints(ctx: RenderContext): string {
  const records = [...ctx.league.membersWithPlayoffAppearances()]
    .sort((a, b) => b.playoffPoints() - a.playoffPoints())
    .map((member) => ({
      member: formatMemberForDisplay(ctx.league, member, true),
      value: member.playoffPoints(),
      average: member.playoffAveragePoints(),
    }));
  return renderPointsTable(ctx, "/total_playoff_points", "All time playoff points", records);
}
