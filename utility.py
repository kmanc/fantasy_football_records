MANAGER_ALIASES = {
	"Joe Guidoboni" : "Joe",
	"Brendan Shea" : "Durgan",
}

def clean_name(name: str) -> str:
    """Cleans up a manager's name str and fetches its alias, if present"""
    cleaned = name.replace("  ", " ").strip().title()
    return MANAGER_ALIASES.get(cleaned, cleaned)
