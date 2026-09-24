"""Один билд: исходник, книга, каталог публикации, лог."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from docloom.book import build_book
from docloom.db import Store, utcnow
from docloom.publisher import publish
from docloom.settings import Settings
from docloom.source import GitAuth, SourceError, checkout_git, ensure_allowed, fingerprint


def execute_build(store: Store, settings: Settings, build_id: int) -> None:
    if not store.mark_running(build_id):
        return
    build = store.get_build(build_id)
    project = store.get_project(int(build["project_id"]))
    log_path = settings.data_dir / "logs" / f"{build_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"build {build_id} project={project['name']} ref={build['ref']}"]
    try:
        root, sha = _resolve(project, settings, str(build["version_name"]))
        book = build_book(root, version=str(build["version_name"]))
        known = set(store.version_names(int(project["id"])))
        known.add(str(build["version_name"]))
        dest = settings.publish_dir / str(project["name"]) / str(build["version_name"])
        manifest = publish(book, dest, sha=sha, built_at=utcnow(), versions=sorted(known))
        store.finish(
            build_id,
            status=str(manifest["status"]),
            sha=sha,
            warnings_json=json.dumps(manifest["warnings"], ensure_ascii=False),
            log_path=str(log_path),
            artifact_path=str(dest),
        )
        lines.append(f"status={manifest['status']} sha={sha} pages={manifest['docstring_coverage']}")
    except Exception as exc:
        message = str(exc)
        trace = traceback.format_exc()
        if settings.git_token:
            message = message.replace(settings.git_token, "***")
            trace = trace.replace(settings.git_token, "***")
        lines.append(f"failed: {message}")
        lines.append(trace)
        store.finish(
            build_id,
            status="failed",
            sha=None,
            warnings_json="[]",
            log_path=str(log_path),
            artifact_path=None,
        )
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve(project, settings: Settings, version_name: str) -> tuple[Path, str]:
    local = project["local_path"]
    auth = GitAuth(token=settings.git_token, ssl_verify=settings.git_ssl_verify)
    if local:
        root = ensure_allowed(Path(str(local)), settings.source_roots)
        return root, fingerprint(root)
    git_url = project["git_url"]
    if not git_url:
        raise SourceError("у проекта нет local_path и git_url")
    dest = settings.sources_dir / str(project["name"]) / version_name
    ensure_allowed(dest, (settings.sources_dir,))
    sha = checkout_git(str(git_url), dest, version_name, auth)
    return dest, sha
