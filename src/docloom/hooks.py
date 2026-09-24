"""Разбор push-событий GitHub и Bitbucket в одну постановку билда."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookEvent:
    action: str
    reason: str
    name: str | None
    clone_urls: tuple[str, ...]
    refs: tuple[str, ...]


def parse_hook(payload: dict) -> HookEvent:
    if payload.get("zen") and payload.get("hook_id"):
        return _ignore("ping")
    if payload.get("eventKey"):
        return _bitbucket_server(payload)
    if isinstance(payload.get("push"), dict) and isinstance(payload.get("repository"), dict):
        return _bitbucket_cloud(payload)
    return _github(payload)


def _ignore(reason: str) -> HookEvent:
    return HookEvent("ignore", reason, None, (), ())


def _github(payload: dict) -> HookEvent:
    after = str(payload.get("after") or "")
    if payload.get("deleted") or after == "0" * 40:
        return _ignore("delete")
    repository = payload.get("repository") if isinstance(payload.get("repository"), dict) else {}
    name = repository.get("name") if isinstance(repository.get("name"), str) else None
    clone = repository.get("clone_url") if isinstance(repository.get("clone_url"), str) else None
    ref = payload.get("ref")
    if not isinstance(ref, str) or not ref:
        return _ignore("no-changes")
    return HookEvent("build", "", name, ((clone,) if clone else ()), (ref,))


def _bitbucket_server(payload: dict) -> HookEvent:
    event = str(payload.get("eventKey") or "")
    if event != "repo:refs_changed":
        return _ignore(event or "unknown")
    repository = payload.get("repository") if isinstance(payload.get("repository"), dict) else {}
    name = repository.get("slug") if isinstance(repository.get("slug"), str) else None
    if name is None and isinstance(repository.get("name"), str):
        name = repository["name"]
    clones = _clone_hrefs(repository)
    refs: list[str] = []
    changes = payload.get("changes") if isinstance(payload.get("changes"), list) else []
    for change in changes:
        if not isinstance(change, dict) or change.get("type") == "DELETE":
            continue
        to_hash = str(change.get("toHash") or "")
        if to_hash == "0" * 40:
            continue
        ref_obj = change.get("ref") if isinstance(change.get("ref"), dict) else {}
        ref = ref_obj.get("id") if isinstance(ref_obj.get("id"), str) else change.get("refId")
        if isinstance(ref, str) and ref:
            refs.append(ref)
    if not refs:
        return HookEvent("ignore", "no-changes", name, clones, ())
    return HookEvent("build", "", name, clones, tuple(refs))


def _bitbucket_cloud(payload: dict) -> HookEvent:
    repository = payload["repository"]
    name = repository.get("name") if isinstance(repository.get("name"), str) else None
    clones = _clone_hrefs(repository)
    refs: list[str] = []
    changes = payload["push"].get("changes") if isinstance(payload["push"].get("changes"), list) else []
    for change in changes:
        if not isinstance(change, dict):
            continue
        new = change.get("new")
        if not isinstance(new, dict):
            continue
        branch = new.get("name")
        kind = new.get("type") or "branch"
        if not isinstance(branch, str) or not branch:
            continue
        prefix = "refs/tags/" if kind == "tag" else "refs/heads/"
        refs.append(prefix + branch)
    if not refs:
        return HookEvent("ignore", "no-changes", name, clones, ())
    return HookEvent("build", "", name, clones, tuple(refs))


def _clone_hrefs(repository: dict) -> tuple[str, ...]:
    links = repository.get("links") if isinstance(repository.get("links"), dict) else {}
    raw = links.get("clone") if isinstance(links.get("clone"), list) else []
    found: list[str] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("href"), str):
            found.append(item["href"])
        elif isinstance(item, str):
            found.append(item)
    return tuple(found)
