import re


# Commands that are explicitly allowed.
ALLOWED_PATTERNS = [
    r"^npm\s+(test|run\s+(test|build|lint|check))(\s+.*)?$",
    r"^node\s+[\w./\\-]+(\s+.*)?$",
    r"^python\s+(-m\s+[\w.-]+|[\w./\\-]+)(\s+.*)?$",
    r"^pytest(\s+.*)?$",
    r"^git\s+(status|diff|log)(\s+.*)?$",
]


# Dangerous commands / patterns.
BLOCKED_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+-r",
    r"del\s+/[sq]",
    r"rmdir\s+/[sq]",
    r"format\s+[a-zA-Z]:",
    r"shutdown",
    r"restart-computer",
    r"stop-computer",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-fd",
    r"git\s+push\s+.*--force",
    r"drop\s+database",
    r"drop\s+table",
    r"truncate\s+table",
    r"powershell\s+-enc",
    r"invoke-expression",
    r"iex\s+",
]


def normalize(command: str) -> str:
    return " ".join(command.strip().split())


def is_blocked(command: str) -> bool:

    normalized = normalize(command).lower()

    for pattern in BLOCKED_PATTERNS:

        if re.search(pattern, normalized):
            return True

    return False


def is_allowed(command: str) -> bool:

    normalized = normalize(command)

    if is_blocked(normalized):
        return False

    for pattern in ALLOWED_PATTERNS:

        if re.match(pattern, normalized, re.IGNORECASE):
            return True

    return False


def validate_command(command: str) -> tuple[bool, str]:

    if not command or not command.strip():
        return False, "Command is empty."

    normalized = normalize(command)

    if is_blocked(normalized):
        return False, "Command matches a blocked dangerous pattern."

    if not is_allowed(normalized):
        return False, "Command is not on the AutoCoder allowlist."

    return True, "Command is allowed."