MANAGER_ALIASES = {
    "Joe Guidoboni": "Joe",
    "Brendan Shea": "Durgan",
}

REDACTED_TEAM_YEARS = {
    "Billy Heanue": [2017, 2018],
}


def clean_name(name: str) -> str:
    """Cleans up a manager's name str and fetches its alias, if present"""
    cleaned = name.replace("  ", " ").strip().title()
    return MANAGER_ALIASES.get(cleaned, cleaned)


def clean_team(owner: str, year: int, name: str) -> str:
    """Cleans up a team's name str and fetches its alias, if needed"""
    cleaned = name.replace("  ", " ").strip()
    if year in REDACTED_TEAM_YEARS.get(owner, []):
        return "Redacted"
    return cleaned
