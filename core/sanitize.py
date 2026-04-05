# core/sanitize.py
"""
Redaction and sanitization utilities for EgoVault.

redact_sensitive() — strips API keys and sensitive field values from strings.
sanitize_error() — produces safe error messages without system paths or keys.

Applied BEFORE writing to logs/DB. Irreversible by design.
"""

import re
from pathlib import PurePosixPath, PureWindowsPath

# API key patterns — sk-xxx with 20+ alphanumeric chars
_KEY_PATTERN = re.compile(r"sk-[a-zA-Z0-9_-]{20,}")
# Covers sk-* family. Extend for other provider key prefixes as needed.

# JSON field names whose values should be redacted
_SENSITIVE_FIELDS = re.compile(
    r'"(api_key|secret|token|password|authorization|openai_api_key|anthropic_api_key)'
    r'"\s*:\s*"[^"]*"',
    re.IGNORECASE,
)

# Absolute paths — Unix or Windows
_ABS_PATH_UNIX = re.compile(r"/(?:home|usr|tmp|etc|var|opt|root)/[^\s,;\"')\]]+")
# Common Unix paths. Extend if needed.
_ABS_PATH_WIN = re.compile(r"[A-Z]:\\[^\s,;\"')\]]+", re.IGNORECASE)
# Covers drive-letter paths (C:\...). Does not cover UNC paths (\\server\share).

_REDACTED = "sk-***REDACTED***"


def redact_sensitive(text: str | None) -> str | None:
    """
    Remove API keys and sensitive JSON field values from a string.
    Returns None if input is None.
    """
    if text is None:
        return None
    if not text:
        return text

    # Redact bare API key patterns first (so sk-*** appears in JSON fields too)
    result = _KEY_PATTERN.sub(_REDACTED, text)

    # Redact JSON fields with sensitive names (catches non-sk-* values like passwords)
    # Skip fields whose value already contains REDACTED (set by _KEY_PATTERN above)
    def _redact_field(match: re.Match) -> str:
        if "REDACTED" in match.group(0):
            return match.group(0)
        field_name = match.group(1)
        return f'"{field_name}": "***REDACTED***"'

    result = _SENSITIVE_FIELDS.sub(_redact_field, result)
    return result


def sanitize_error(err: Exception) -> str:
    """
    Produce a safe error string: ErrorType: message.
    Strips absolute paths (keeps basename only) and redacts API keys.
    """
    msg = str(err)

    # Replace absolute paths with basename
    def _basename_unix(match: re.Match) -> str:
        return PurePosixPath(match.group(0)).name

    def _basename_win(match: re.Match) -> str:
        return PureWindowsPath(match.group(0)).name

    msg = _ABS_PATH_WIN.sub(_basename_win, msg)
    msg = _ABS_PATH_UNIX.sub(_basename_unix, msg)

    # Redact API keys
    msg = redact_sensitive(msg) or msg

    return f"{type(err).__name__}: {msg}"
