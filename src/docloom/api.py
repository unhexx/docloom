"""Control plane: проекты, билды и webhook push."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from docloom.db import Store
from docloom.hooks import parse_hook
from docloom.jobs import execute_build
from docloom.settings import Settings, load_settings
from docloom.source import SourceError, ensure_allowed, version_from_ref

_NAME = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


class ProjectIn(BaseModel):
    name: str
    git_url: str | None = None
    local_path: str | None = None
    webhook_secret: str | None = Field(default=None, max_length=200)


class BuildIn(BaseModel):
    ref: str = "latest"


def create_app(settings: Settings | None = None) -> FastAPI:
    current = settings or load_settings()
    app = FastAPI(title="Docloom", version="0.1.0")
    app.state.settings = current
    app.state.store = Store(current.data_dir / "docloom.sqlite")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/projects")
    def list_projects() -> list[dict[str, object]]:
        return app.state.store.list_projects()

    @app.post("/api/projects", status_code=201)
    def create_project(body: ProjectIn) -> dict[str, object]:
        if not _NAME.fullmatch(body.name):
            raise HTTPException(status_code=400, detail="недопустимое имя проекта")
        if not body.local_path and not body.git_url:
            raise HTTPException(status_code=400, detail="нужен local_path или git_url")
        local_path = body.local_path
        if local_path:
            try:
                local_path = str(ensure_allowed(Path(local_path), current.source_roots))
            except SourceError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            return app.state.store.create_project(
                name=body.name,
                git_url=body.git_url,
                local_path=local_path,
                webhook_secret=body.webhook_secret,
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="проект уже есть") from exc

    @app.post("/api/projects/{project_id}/builds", status_code=202)
    def create_build(project_id: int, body: BuildIn) -> JSONResponse:
        try:
            app.state.store.get_project(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="проект не найден") from exc
        try:
            version_name = version_from_ref(body.ref)
        except SourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        build = app.state.store.enqueue(project_id, body.ref, version_name)
        if current.sync_builds:
            execute_build(app.state.store, current, int(build["id"]))
            build = app.state.store.public_build(app.state.store.get_build(int(build["id"])))
        return JSONResponse(build, status_code=202)

    @app.get("/api/projects/{project_id}/builds/{build_id}")
    def get_build(project_id: int, build_id: int) -> dict[str, object]:
        try:
            row = app.state.store.get_build(build_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="билд не найден") from exc
        if int(row["project_id"]) != project_id:
            raise HTTPException(status_code=404, detail="билд не найден")
        return app.state.store.public_build(row)

    @app.post("/hooks/git", status_code=202)
    async def git_hook(request: Request) -> JSONResponse:
        body = await request.body()
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="ожидался JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="ожидался объект")
        event = parse_hook(payload)
        project = app.state.store.find_project(name=event.name, clone_urls=event.clone_urls)
        secret = ""
        if project is not None and project["webhook_secret"]:
            secret = str(project["webhook_secret"])
        elif current.webhook_secret:
            secret = current.webhook_secret
        if secret and not _signature_ok(secret, body, request.headers):
            raise HTTPException(status_code=401, detail="подпись webhook не сошлась")
        if event.action == "ignore":
            return JSONResponse({"ok": True, "ignored": event.reason})
        if project is None:
            raise HTTPException(status_code=404, detail="проект не найден")
        builds = []
        for ref in event.refs:
            try:
                version_name = version_from_ref(ref)
            except SourceError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            build = app.state.store.enqueue(int(project["id"]), ref, version_name)
            if current.sync_builds:
                execute_build(app.state.store, current, int(build["id"]))
                build = app.state.store.public_build(app.state.store.get_build(int(build["id"])))
            builds.append(build)
        return JSONResponse({"ok": True, "build": builds[0], "builds": builds}, status_code=202)

    return app


def _signature_ok(secret: str, body: bytes, headers) -> bool:
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    presented = [
        headers.get("x-hub-signature-256", ""),
        headers.get("x-hub-signature", ""),
    ]
    return any(item and _same(expected, item) for item in presented)


def _same(expected: str, presented: str) -> bool:
    try:
        return hmac.compare_digest(expected, presented)
    except ValueError:
        return False
