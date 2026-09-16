/** Raw ESPN response shapes, limited to the fields this project actually reads. */

export interface EspnMember {
  id: string;
  firstName?: string;
  lastName?: string;
}

export interface EspnTeamRecord {
  wins: number;
  losses: number;
  ties: number;
}

export interface EspnTeam {
  id: number;
  divisionId: number;
  name?: string;
  location?: string;
  nickname?: string;
  owners: string[];
  record: { overall: EspnTeamRecord };
}

export interface EspnScheduleSettings {
  matchupPeriodCount: number;
  playoffTeamCount: number;
  matchupPeriods: Record<string, number[]>;
}

export interface EspnSettings {
  name: string;
  scheduleSettings: EspnScheduleSettings;
}

export interface EspnStatus {
  currentMatchupPeriod: number;
  scoringPeriodId: number;
  firstScoringPeriod: number;
  finalScoringPeriod: number;
}

export interface EspnLeaguePayload {
  scoringPeriodId: number;
  status: EspnStatus;
  settings: EspnSettings;
  members: EspnMember[];
  teams: EspnTeam[];
}

export interface EspnMatchupTeam {
  teamId: number;
  totalPoints: number;
}

export interface EspnScoreboardMatchup {
  matchupPeriodId: number;
  playoffTierType?: string;
  home?: EspnMatchupTeam;
  away?: EspnMatchupTeam;
}

export interface EspnScoreboardPayload {
  schedule: EspnScoreboardMatchup[];
}

export interface EspnRosterEntry {
  playerId: number;
  lineupSlotId: number;
}

export interface EspnRosterTeam {
  id: number;
  roster: { entries: EspnRosterEntry[] };
}

export interface EspnRosterPayload {
  teams: EspnRosterTeam[];
}

export interface EspnMatchupRosterEntry {
  playerId: number;
  playerPoolEntry: {
    player: { fullName: string };
    appliedStatTotal: number;
  };
}

export interface EspnMatchupScheduleGame {
  home?: { rosterForCurrentScoringPeriod?: { entries: EspnMatchupRosterEntry[] } };
  away?: { rosterForCurrentScoringPeriod?: { entries: EspnMatchupRosterEntry[] } };
}

export interface EspnMatchupRosterPayload {
  schedule: EspnMatchupScheduleGame[];
}
