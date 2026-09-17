import type { FantasyLeague } from "./domain/model";
import type { PlayoffPictureEntry } from "./domain/playoff-snapshot";
import type { RenderContext } from "./render/context";
import { renderChampionships, renderHeadToHead, renderPlayoffAppearances, renderWinPercent } from "./render/pages/minimal-tables";
import { renderHome } from "./render/pages/home";
import { renderMeetTheManagers } from "./render/pages/meet-the-managers";
import { renderTotalPlayoffPoints, renderTotalRegularSeasonPoints } from "./render/pages/points-tables";
import { renderBestDefense, renderHighestRegularSeason, renderLowestRegularSeason, renderWorstDefense } from "./render/pages/season-tables";
import { renderSnapshot } from "./render/pages/snapshot";
import { renderHighestLoss, renderHighestWeek, renderLowestWeek, renderLowestWin } from "./render/pages/week-tables";

export interface RenderAllOptions {
  league: FantasyLeague;
  leagueName: string;
  leagueAbbreviation: string;
  playoffSnapshot: PlayoffPictureEntry[];
}

/** Renders every page of the site up front, keyed by request path, for storage in KV. */
export function renderAllPages(opts: RenderAllOptions): Map<string, string> {
  const sortedMembers = opts.league
    .membersList()
    .map((m) => m.name)
    .sort();
  const ctx: RenderContext = { league: opts.league, titlePrefix: opts.leagueAbbreviation, members: sortedMembers };

  const pages = new Map<string, string>();
  pages.set("/", renderHome(ctx, opts.leagueName));
  pages.set("/snapshot", renderSnapshot(ctx, opts.playoffSnapshot, opts.league.teamsInActiveYear().length));
  pages.set("/championships", renderChampionships(ctx));
  pages.set("/total_regular_season_points", renderTotalRegularSeasonPoints(ctx));
  pages.set("/total_playoff_points", renderTotalPlayoffPoints(ctx));
  pages.set("/win_percent", renderWinPercent(ctx));
  pages.set("/playoff_appearances", renderPlayoffAppearances(ctx));
  pages.set("/highest_regular_season", renderHighestRegularSeason(ctx));
  pages.set("/lowest_regular_season", renderLowestRegularSeason(ctx));
  pages.set("/best_defense", renderBestDefense(ctx));
  pages.set("/worst_defense", renderWorstDefense(ctx));
  pages.set("/highest_week", renderHighestWeek(ctx));
  pages.set("/lowest_week", renderLowestWeek(ctx));
  pages.set("/lowest_win", renderLowestWin(ctx));
  pages.set("/highest_loss", renderHighestLoss(ctx));
  pages.set("/meet_the_managers", renderMeetTheManagers(ctx));

  for (const memberName of sortedMembers) {
    pages.set(`/head-to-head/${encodeURIComponent(memberName)}`, renderHeadToHead(ctx, memberName));
  }

  return pages;
}
