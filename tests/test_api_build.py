"""API ставит билд, worker пишет книгу, одна версия не собирается параллельно."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from docloom.api import create_app
from docloom.db import Store
from docloom.settings import Settings
from docloom.worker import drain

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "samples" / "demo-lib"


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        publish_dir=tmp_path / "publish",
        sources_dir=tmp_path / "sources",
        source_roots=(ROOT, tmp_path),
        sync_builds=False,
        webhook_secret="topsecret",
        host="127.0.0.1",
        port=8000,
    )


def test_same_version_is_serialized(tmp_path: Path) -> None:
    store = Store(tmp_path / "db.sqlite")
    project = store.create_project(name="p", git_url=None, local_path=str(DEMO), webhook_secret=None)
    assert "webhook_secret" not in project
    project_id = int(project["id"])
    store.enqueue(project_id, "latest", "latest")
    store.enqueue(project_id, "latest", "latest")
    store.enqueue(project_id, "v1", "v1")
    first = store.claim_next()
    second = store.claim_next()
    assert first is not None and second is not None
    assert first["version"] == "latest"
    assert second["version"] == "v1"
    assert store.claim_next() is None
    store.finish(
        int(first["id"]),
        status="success",
        sha="abc",
        warnings_json="[]",
        log_path="log",
        artifact_path=str(tmp_path / "out"),
    )
    third = store.claim_next()
    assert third is not None and third["version"] == "latest"


def test_demo_build_publishes_files(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    client = TestClient(create_app(settings))
    assert client.get("/health").json() == {"status": "ok"}
    denied = client.post("/api/projects", json={"name": "nope", "local_path": "/etc"})
    assert denied.status_code == 400
    created = client.post("/api/projects", json={"name": "demo-lib", "local_path": str(DEMO)})
    assert created.status_code == 201
    project_id = created.json()["id"]
    queued = client.post(f"/api/projects/{project_id}/builds", json={"ref": "latest"})
    assert queued.status_code == 202
    assert queued.json()["status"] == "queued"
    assert drain(settings) == 1
    body = client.get(f"/api/projects/{project_id}/builds/{queued.json()['id']}").json()
    assert body["status"] == "success_with_warnings"
    artifact = Path(body["artifact_path"])
    assert (artifact / "index.html").is_file()
    assert "demo-lib" in (artifact / "index.html").read_text(encoding="utf-8")
    assert Path(body["log_path"]).is_file()
    assert body["sha"]


def test_clean_tree_is_success(tmp_path: Path) -> None:
    project = tmp_path / "clean"
    (project / "docs").mkdir(parents=True)
    (project / "docloom.yml").write_text(
        "project: clean\nlanguage: ru\nsources:\n  guides: docs\n",
        encoding="utf-8",
    )
    (project / "docs" / "intro.md").write_text("# Введение\n\nТолько гайд.\n", encoding="utf-8")
    (project / "SUMMARY.md").write_text("* [Введение](docs/intro.md)\n", encoding="utf-8")
    settings = _settings(tmp_path)
    client = TestClient(create_app(settings))
    project_id = client.post("/api/projects", json={"name": "clean", "local_path": str(project)}).json()["id"]
    build_id = client.post(f"/api/projects/{project_id}/builds", json={"ref": "latest"}).json()["id"]
    assert drain(settings) == 1
    body = client.get(f"/api/projects/{project_id}/builds/{build_id}").json()
    assert body["status"] == "success"


def test_webhook_queues_build(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    client = TestClient(create_app(settings))
    project_id = client.post(
        "/api/projects",
        json={"name": "demo-lib", "local_path": str(DEMO)},
    ).json()["id"]
    payload = {
        "ref": "refs/heads/main",
        "after": "a" * 40,
        "repository": {"name": "demo-lib", "clone_url": "https://example.com/demo-lib.git"},
    }
    raw = json.dumps(payload).encode("utf-8")
    bad = client.post("/hooks/git", content=raw, headers={"content-type": "application/json"})
    assert bad.status_code == 401
    signature = "sha256=" + hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()
    accepted = client.post(
        "/hooks/git",
        content=raw,
        headers={"content-type": "application/json", "X-Hub-Signature-256": signature},
    )
    assert accepted.status_code == 202
    build = accepted.json()["build"]
    assert build["version"] == "main"
    assert build["project_id"] == project_id
    assert drain(settings) == 1
    done = client.get(f"/api/projects/{project_id}/builds/{build['id']}").json()
    assert done["status"].startswith("success")
    assert (Path(done["artifact_path"]) / "index.html").is_file()


def test_git_url_checkout(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    (origin / "docs").mkdir(parents=True)
    (origin / "docloom.yml").write_text(
        "project: gitdemo\nlanguage: ru\nsources:\n  guides: docs\n",
        encoding="utf-8",
    )
    (origin / "docs" / "intro.md").write_text("# Из git\n", encoding="utf-8")
    (origin / "SUMMARY.md").write_text("* [Из git](docs/intro.md)\n", encoding="utf-8")
    _git(origin, "init", "-b", "main")
    _git(origin, "add", ".")
    _git(origin, "-c", "user.email=dev@example.com", "-c", "user.name=Dev", "commit", "-m", "init")
    settings = _settings(tmp_path)
    client = TestClient(create_app(settings))
    created = client.post("/api/projects", json={"name": "gitdemo", "git_url": origin.as_uri()})
    assert created.status_code == 201
    project_id = created.json()["id"]
    build_id = client.post(f"/api/projects/{project_id}/builds", json={"ref": "main"}).json()["id"]
    assert drain(settings) == 1
    body = client.get(f"/api/projects/{project_id}/builds/{build_id}").json()
    assert body["status"] == "success"
    assert len(body["sha"]) == 40
    page = Path(body["artifact_path"]) / "index.html"
    assert "Из git" in page.read_text(encoding="utf-8")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
