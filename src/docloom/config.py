"""Чтение docloom.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProjectConfig:
    """Настройки одного проекта-источника."""

    project: str
    version: str | None
    language: str
    theme: str
    guides: str | None
    python_roots: tuple[str, ...]
    openapi: tuple[str, ...]
    exclude: tuple[str, ...]
    versions_from: tuple[str, ...]
    search: bool
    llms: bool
    root: Path

    @classmethod
    def load(cls, path: Path) -> ProjectConfig:
        path = Path(path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict) or not raw.get("project"):
            raise ValueError(f"в {path} нет поля project")
        sources = raw.get("sources") or {}
        publish = raw.get("publish") or {}
        return cls(
            project=str(raw["project"]),
            version=None if raw.get("version") is None else str(raw["version"]),
            language=str(raw.get("language") or "en"),
            theme=str(raw.get("theme") or "gitbook"),
            guides=None if sources.get("guides") is None else str(sources["guides"]),
            python_roots=_as_tuple(sources.get("python")),
            openapi=_as_tuple(sources.get("openapi")),
            exclude=_as_tuple(raw.get("exclude")),
            versions_from=_as_tuple(publish.get("versions_from")),
            search=bool(raw.get("search", True)),
            llms=bool(raw.get("llms", True)),
            root=path.parent.resolve(),
        )


def _as_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    raise ValueError(f"ожидался список путей, получено {type(value).__name__}")
