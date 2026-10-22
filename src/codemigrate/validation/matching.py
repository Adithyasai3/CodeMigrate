"""Deterministic symbol <-> KB entry matching shared by the validator, offline rules and metrics."""

from __future__ import annotations

from codemigrate.kb.schema import KBEntry


def normalize(symbol: str) -> str:
    s = symbol.strip().strip("`").removesuffix("()").lstrip("~")
    if s.startswith("django.conf.settings."):
        s = "settings." + s[len("django.conf.settings.") :]
    return s


def symbol_matches(symbol: str, entry: KBEntry) -> bool:
    """True if ``symbol`` (from code or from a model's claim) denotes ``entry``'s API.

    Accepts: an exact name/alias; a longer path under a name (``utc.tzname`` under ``utc``);
    a bare setting name; and a member reached through a subclass or unknown receiver
    (``django.test.TestCase.assertFormsetError`` / ``*.assertFormsetError``).
    """
    s = normalize(symbol)
    if not s:
        return False
    names = entry.all_names()
    if s in names or f"settings.{s}" in names or f"template:{s}" in names:
        return True
    if any(s.startswith(n + ".") and n.count(".") >= 2 for n in names):
        return True
    parts = s.split(".")
    member = parts[-1]
    if len(parts) >= 2 and (parts[-2] == "*" or parts[-2][:1].isupper()):
        for n in names:
            np_ = n.split(".")
            if len(np_) >= 2 and np_[-1] == member and np_[-2][:1].isupper():
                return True
    return False
