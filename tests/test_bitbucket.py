"""Bitbucket сам ставит билд, а опрос не повторяет уже собранный коммит."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from docloom.api import create_app
from docloom.book import build_book
from docloom.settings import Settings
from docloom.source import normalize_git_url
from docloom.watch import poll_once

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "samples" / "demo-lib"


def _settings(tmp_path: Path, **overrides) -> Settings:
    values = dict(
        data_dir=tmp_path / "data",
        publish_dir=tmp_path / "publish",
        sources_dir=tmp_path / "sources",
        source_roots=(ROOT, tmp_path),
        sync_builds=True,
        webhook_secret="topsecret",
        host="127.0.0.1",
        port=8000,
    )
    values.update(overrides)
    return Settings(**values)


def test_bitbucket_url_points_at_project_and_slug() -> None:
    from docloom.source import _bitbucket_repo, _doc_path

    assert _bitbucket_repo("https://git.example.com/scm/in/agentic-box.git") == (
        "git.example.com",
        "IN",
        "agentic-box",
    )
    assert _bitbucket_repo("file:///tmp/origin") is None
    assert _doc_path("docs/quickstart-ru.md")
    assert _doc_path("README.md")
    assert not _doc_path("pkglists/base-offline.txt")


def test_normalize_drops_user_and_git_suffix() -> None:
    left = normalize_git_url("https://user@git.example.com/scm/in/agentic-box.git")
    right = normalize_git_url("https://git.example.com/scm/in/agentic-box")
    assert left == right


def test_repo_without_config_still_builds(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Глава\n\nТекст.\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Про проект\n\nОписание.\n", encoding="utf-8")
    book = build_book(tmp_path)
    titles = [page.title for page in book.pages]
    assert "Про проект" in titles
    assert "Глава" in titles
    assert book.project == tmp_path.name


def test_bitbucket_server_push_queues_build(tmp_path: Path) -> None:
    settings = _settings(tmp_path, sync_builds=False)
    client = TestClient(create_app(settings))
    created = client.post(
        "/api/projects",
        json={
            "name": "agentic-box",
            "git_url": "https://git.example.com/scm/in/agentic-box.git",
            "local_path": str(DEMO),
        },
    )
    assert created.status_code == 201
    payload = {
        "eventKey": "repo:refs_changed",
        "repository": {
            "slug": "agentic-box",
            "links": {
                "clone": [
                    {"href": "https://ci@git.example.com/scm/in/agentic-box.git", "name": "http"}
                ]
            },
        },
        "changes": [
            {
                "ref": {"id": "refs/heads/master", "type": "BRANCH"},
                "toHash": "a" * 40,
                "type": "UPDATE",
            }
        ],
    }
    raw = json.dumps(payload).encode()
    denied = client.post("/hooks/git", content=raw, headers={"content-type": "application/json"})
    assert denied.status_code == 401
    signature = "sha256=" + hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()
    accepted = client.post(
        "/hooks/git",
        content=raw,
        headers={"content-type": "application/json", "X-Hub-Signature": signature},
    )
    assert accepted.status_code == 202
    assert accepted.json()["build"]["version"] == "master"
    delete_payload = {
        "eventKey": "repo:refs_changed",
        "repository": {"slug": "agentic-box"},
        "changes": [{"ref": {"id": "refs/heads/old"}, "type": "DELETE", "toHash": "0" * 40}],
    }
    raw_delete = json.dumps(delete_payload).encode()
    signature = "sha256=" + hmac.new(b"topsecret", raw_delete, hashlib.sha256).hexdigest()
    ignored = client.post(
        "/hooks/git",
        content=raw_delete,
        headers={"content-type": "application/json", "X-Hub-Signature": signature},
    )
    assert ignored.status_code == 200
    assert ignored.json()["ignored"] == "no-changes"


def test_watch_builds_once_until_commit_changes(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    (origin / "docs").mkdir(parents=True)
    (origin / "docs" / "intro.md").write_text("# Из наблюдения\n", encoding="utf-8")
    _git(origin, "init", "-b", "master")
    _git(origin, "add", ".")
    _git(origin, "-c", "user.email=dev@example.com", "-c", "user.name=Dev", "commit", "-m", "init")
    settings = _settings(tmp_path)
    assert poll_once(settings, url=origin.as_uri(), ref="master") == 1
    assert poll_once(settings, url=origin.as_uri(), ref="master") == 0
    (origin / "docs" / "intro.md").write_text("# Из наблюдения\n\nВторая редакция.\n", encoding="utf-8")
    _git(origin, "add", ".")
    _git(origin, "-c", "user.email=dev@example.com", "-c", "user.name=Dev", "commit", "-m", "edit")
    assert poll_once(settings, url=origin.as_uri(), ref="master") == 1
    page = next((tmp_path / "publish").rglob("index.html"))
    assert "Из наблюдения" in page.read_text(encoding="utf-8")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
