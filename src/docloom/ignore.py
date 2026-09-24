"""Сопоставление путей с масками exclude из docloom.yml."""

from __future__ import annotations

import re


def is_excluded(rel_posix: str, patterns: tuple[str, ...] | list[str]) -> bool:
    normalized = rel_posix.replace("\\", "/").lstrip("./")
    return any(_match(normalized, pattern) for pattern in patterns)


def _match(path: str, pattern: str) -> bool:
    pattern = pattern.replace("\\", "/").strip()
    if not pattern:
        return False
    return _compile(pattern).fullmatch(path) is not None


def _compile(pattern: str) -> re.Pattern[str]:
    parts: list[str] = ["^"]
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
            continue
        if pattern.startswith("**", i):
            parts.append(".*")
            i += 2
            continue
        char = pattern[i]
        if char == "*":
            parts.append("[^/]*")
        elif char == "?":
            parts.append("[^/]")
        else:
            parts.append(re.escape(char))
        i += 1
    parts.append("$")
    return re.compile("".join(parts))
