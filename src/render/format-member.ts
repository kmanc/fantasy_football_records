import type { FantasyLeague, Member } from "../domain/model";

/** Appends a tenure note (joined late / left early) to a member's display name, when relevant. */
export function formatMemberForDisplay(league: FantasyLeague, member: Member, affectedByTenure = false): string {
  const isFoundingAndActive = member.joinedYear === league.foundedYear && member.leftYear === league.activeYear;
  if (isFoundingAndActive) {
    return member.name;
  }
  if (affectedByTenure) {
    const isFoundingButInactive = member.joinedYear === league.foundedYear && member.leftYear < league.activeYear;
    if (isFoundingButInactive) {
      return `${member.name}* (Left ${member.leftYear})`;
    }
    if (member.leftYear === league.activeYear) {
      return `${member.name}* (Joined ${member.joinedYear})`;
    }
    return `${member.name}* (${member.joinedYear} - ${member.leftYear})`;
  }
  return member.name;
}
