import type { FantasyLeague } from "../domain/model";

export interface RenderContext {
  league: FantasyLeague;
  titlePrefix: string;
  members: string[];
}
