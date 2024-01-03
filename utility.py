MANAGER_ALIASES = {
    "Joe Guidoboni": "Joe",
    "Brendan Shea": "Durgan",
}

MANAGER_DUPLICATES = {
    "7B1424F4-143B-4EB5-BA40-08B7A978921F": "BC7D0741-6090-4ABA-9F23-1590DCDC6434",
}

REDACTED_TEAM_YEARS = {
    "Billy Heanue": [2017, 2018],
}


def clean_member_name(name: str) -> str:
    """Cleans up a manager's name str and fetches its alias, if present"""
    cleaned = name.replace("  ", " ").strip().title()
    return MANAGER_ALIASES.get(cleaned, cleaned)


def clean_team_name(owner: str, year: int, name: str) -> str:
    """Cleans up a team's name str and fetches its alias, if needed"""
    cleaned = name.replace("  ", " ").strip()
    if year in REDACTED_TEAM_YEARS.get(owner, []):
        return "Redacted"
    return cleaned


def clean_user_id(user_id: str) -> str:
    """Cleans up a manager's id str and fetches its duplicate, if present"""
    cleaned = user_id.replace("'", "").replace("{", "").replace("}", "").strip()
    return MANAGER_DUPLICATES.get(cleaned, cleaned)


def generate_team_id(espn_team_id: int, year: int) -> int:
    return hash(f"{year}-{espn_team_id}")
