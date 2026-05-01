"""
response_tags.py — Response-tag utilities for Shadow.

Every response from the dispatcher must start with a recognised bracket tag
so that the TTS engine, HUD, and log system can route it correctly.

Recognised tags
───────────────
  [ACTION]  — something was done (file opened, volume changed …)
  [INFO]    — factual answer / read-out
  [WARN]    — something went wrong or needs clarification
  [REMIND]  — reminder / timer confirmation
  [EXCITED] — enthusiastic response (maps to excited TTS pitch)
"""

import re

_VALID_TAGS = frozenset([
    "[ACTION]", "[INFO]", "[WARN]", "[REMIND]",
    "[HAPPY]", "[EXCITED]", "[SAD]", "[ANGRY]", "[CURIOUS]", "[CALM]",
])

_TAG_RE = re.compile(r"^\s*\[([A-Z]+)\]", re.IGNORECASE)


def has_action_tag(text: str) -> bool:
    """Return True if *text* already starts with a recognised bracket tag."""
    if not text:
        return False
    m = _TAG_RE.match(text)
    return m is not None and f"[{m.group(1).upper()}]" in _VALID_TAGS


def ensure_action_tag(text: str, default: str = "INFO") -> str:
    """
    If *text* doesn't already start with a recognised tag, prepend
    ``[default]``.  Handles generators by draining them to a single string.

    Parameters
    ----------
    text:    Response string (or generator — will be joined).
    default: Tag name WITHOUT brackets (e.g. ``"ACTION"``, ``"INFO"``).
    """
    # Drain generators produced by streaming AI responses
    if hasattr(text, "__iter__") and not isinstance(text, str):
        text = "".join(str(chunk) for chunk in text)

    if not text:
        return text  # type: ignore[return-value]

    if has_action_tag(text):
        return text

    tag = f"[{default.upper()}]"
    return f"{tag} {text.lstrip()}"
