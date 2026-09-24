"""Опрос одного удалённого репозитория и постановка билда, когда сменился коммит."""

from __future__ import annotations

import time
from urllib.parse import urlsplit

from docloom.db import Store, utcnow
from docloom.jobs import execute_build
from docloom.settings import Settings
from docloom.source import GitAuth, SourceError, remote_sha, version_from_ref


def poll_once(settings: Settings, *, url: str, ref: str) -> int:
    if not url:
        return 0
    version_name = version_from_ref(ref)
    auth = GitAuth(token=settings.git_token, ssl_verify=settings.git_ssl_verify)
    sha = remote_sha(url, version_name, auth)
    store = Store(settings.data_dir / "docloom.sqlite")
    project = store.find_project(name=None, clone_urls=(url,))
    if project is None:
        created = store.create_project(
            name=_slug(url),
            git_url=url,
            local_path=None,
            webhook_secret=None,
        )
        project_id = int(created["id"])
    else:
        project_id = int(project["id"])
    if store.has_active(project_id, version_name):
        return 0
    if store.latest_sha(project_id, version_name) == sha:
        return 0
    build = store.enqueue(project_id, version_name, version_name)
    if settings.sync_builds:
        execute_build(store, settings, int(build["id"]))
    return 1


def serve(settings: Settings, *, url: str, ref: str, once: bool) -> None:
    beat = settings.data_dir / "watch-heartbeat"
    beat.parent.mkdir(parents=True, exist_ok=True)
    while True:
        beat.write_text(utcnow() + "\n", encoding="utf-8")
        if url:
            try:
                poll_once(settings, url=url, ref=ref)
            except (SourceError, OSError) as exc:
                text = str(exc)
                if settings.git_token:
                    text = text.replace(settings.git_token, "***")
                print(f"watch: {text}", flush=True)
        if once:
            return
        time.sleep(settings.watch_interval)


def _slug(url: str) -> str:
    path = urlsplit(url).path.strip("/")
    if not path and ":" in url and "://" not in url:
        path = url.split(":", 1)[1].strip("/")
    name = path.split("/")[-1] if path else "repo"
    if name.endswith(".git"):
        name = name[:-4]
    safe = "".join(char if char.isalnum() or char in "._-" else "-" for char in name)
    return safe[:80] or "repo"
