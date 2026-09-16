export const MANAGER_ALIASES: Record<string, string> = {
  "Joe Guidoboni": "Joe",
  "Brendan Shea": "Durgan",
};

export const MANAGER_DUPLICATES: Record<string, string> = {
  "7B1424F4-143B-4EB5-BA40-08B7A978921F": "BC7D0741-6090-4ABA-9F23-1590DCDC6434",
};

export const REDACTED_TEAM_YEARS: Record<string, number[]> = {
  "Billy Heanue": [2017, 2018],
};

/** Matches Python's str.title(): capitalizes each maximal run of letters. */
export function titleCase(value: string): string {
  return value.replace(/[A-Za-z]+/g, (word) => word[0]!.toUpperCase() + word.slice(1).toLowerCase());
}

/** Cleans up a manager's name string and fetches its alias, if present */
export function cleanMemberName(name: string): string {
  const cleaned = titleCase(name.replaceAll("  ", " ").trim());
  return MANAGER_ALIASES[cleaned] ?? cleaned;
}

/** Cleans up a team's name string and fetches its alias, if needed */
export function cleanTeamName(owner: string, year: number, name: string): string {
  const cleaned = name.replaceAll("  ", " ").trim();
  if (REDACTED_TEAM_YEARS[owner]?.includes(year)) {
    return "Redacted";
  }
  return cleaned;
}

/** Cleans up a manager's id string and fetches its duplicate, if present */
export function cleanUserId(userId: string): string {
  const cleaned = userId.replaceAll("'", "").replaceAll("{", "").replaceAll("}", "").trim();
  return MANAGER_DUPLICATES[cleaned] ?? cleaned;
}

/** Deterministic key identifying a team within a season (replaces Python's hash-based id). */
export function generateTeamId(espnId: number | string, year: number): string {
  return `${year}-${espnId}`;
}
