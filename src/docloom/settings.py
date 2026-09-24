"""Настройки процесса. Секреты только из окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    publish_dir: Path
    sources_dir: Path
    source_roots: tuple[Path, ...]
    sync_builds: bool
    webhook_secret: str
    host: str
    port: int


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("DOCLOOM_DATA", "data"))
    publish_dir = Path(os.environ.get("DOCLOOM_PUBLISH", "publish"))
    sources_dir = Path(os.environ.get("DOCLOOM_SOURCES", str(data_dir / "sources")))
    configured = [Path(item) for item in os.environ.get("DOCLOOM_SOURCE_ROOTS", "").split(":") if item]
    roots = (sources_dir, *configured) if configured else (sources_dir, Path.cwd())
    return Settings(
        data_dir=data_dir,
        publish_dir=publish_dir,
        sources_dir=sources_dir,
        source_roots=tuple(roots),
        sync_builds=os.environ.get("DOCLOOM_SYNC_BUILDS", "0") == "1",
        webhook_secret=os.environ.get("DOCLOOM_WEBHOOK_SECRET", ""),
        host=os.environ.get("DOCLOOM_HOST", "127.0.0.1"),
        port=int(os.environ.get("DOCLOOM_PORT", "8000")),
    )
