"""SQLite: проекты, билды, версии. Очередь без Redis."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                git_url TEXT,
                local_path TEXT,
                webhook_secret TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS builds (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                ref TEXT NOT NULL,
                version_name TEXT NOT NULL,
                sha TEXT,
                status TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                log_path TEXT,
                artifact_path TEXT,
                warnings TEXT
            );
            CREATE TABLE IF NOT EXISTS versions (
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                build_id INTEGER NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (project_id, name)
            );
            """
        )
        self.conn.commit()

    def create_project(
        self,
        *,
        name: str,
        git_url: str | None,
        local_path: str | None,
        webhook_secret: str | None,
    ) -> dict[str, object]:
        with self._lock:
            cursor = self.conn.execute(
                """
                INSERT INTO projects (name, git_url, local_path, webhook_secret, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, git_url, local_path, webhook_secret, utcnow()),
            )
            self.conn.commit()
            project_id = int(cursor.lastrowid)
        return self.public_project(self.get_project(project_id))

    def list_projects(self) -> list[dict[str, object]]:
        rows = self.conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
        return [self.public_project(row) for row in rows]

    def get_project(self, project_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(project_id)
        return row

    def find_project(
        self,
        *,
        name: str | None,
        clone_url: str | None = None,
        clone_urls: tuple[str, ...] | list[str] | None = None,
    ) -> sqlite3.Row | None:
        from docloom.source import normalize_git_url

        wanted = {normalize_git_url(item) for item in (clone_urls or ()) if item}
        if clone_url:
            wanted.add(normalize_git_url(clone_url))
        wanted.discard("")
        rows = self.conn.execute("SELECT * FROM projects").fetchall()
        if wanted:
            for row in rows:
                if row["git_url"] and normalize_git_url(str(row["git_url"])) in wanted:
                    return row
        if name:
            for row in rows:
                if row["name"] == name:
                    return row
        return None

    def enqueue(
        self,
        project_id: int,
        ref: str,
        version_name: str,
        sha: str | None = None,
    ) -> dict[str, object]:
        with self._lock:
            cursor = self.conn.execute(
                """
                INSERT INTO builds (project_id, ref, version_name, sha, status)
                VALUES (?, ?, ?, ?, 'queued')
                """,
                (project_id, ref, version_name, sha),
            )
            self.conn.commit()
            build_id = int(cursor.lastrowid)
        return self.public_build(self.get_build(build_id))

    def mark_running(self, build_id: int) -> bool:
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute("SELECT * FROM builds WHERE id = ?", (build_id,)).fetchone()
            if row is None or row["status"] not in {"queued", "running"}:
                self.conn.rollback()
                return False
            conflict = self.conn.execute(
                """
                SELECT 1 FROM builds
                WHERE project_id = ? AND version_name = ? AND status = 'running' AND id != ?
                """,
                (row["project_id"], row["version_name"], build_id),
            ).fetchone()
            if conflict is not None:
                self.conn.rollback()
                return False
            if row["status"] == "queued":
                self.conn.execute(
                    "UPDATE builds SET status = 'running', started_at = ? WHERE id = ?",
                    (utcnow(), build_id),
                )
            self.conn.commit()
            return True

    def claim_next(self) -> dict[str, object] | None:
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                """
                SELECT * FROM builds
                WHERE status = 'queued'
                  AND NOT EXISTS (
                    SELECT 1 FROM builds AS running
                    WHERE running.project_id = builds.project_id
                      AND running.version_name = builds.version_name
                      AND running.status = 'running'
                  )
                ORDER BY id
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                self.conn.execute("ROLLBACK")
                return None
            self.conn.execute(
                "UPDATE builds SET status = 'running', started_at = ? WHERE id = ?",
                (utcnow(), row["id"]),
            )
            self.conn.commit()
            build_id = int(row["id"])
        return self.public_build(self.get_build(build_id))

    def finish(
        self,
        build_id: int,
        *,
        status: str,
        sha: str | None,
        warnings_json: str,
        log_path: str,
        artifact_path: str | None,
    ) -> None:
        with self._lock:
            build = self.get_build(build_id)
            self.conn.execute(
                """
                UPDATE builds
                SET status = ?, sha = COALESCE(?, sha), warnings = ?, finished_at = ?, log_path = ?, artifact_path = ?
                WHERE id = ?
                """,
                (status, sha, warnings_json, utcnow(), log_path, artifact_path, build_id),
            )
            if status in {"success", "success_with_warnings"} and artifact_path:
                self.conn.execute(
                    """
                    INSERT INTO versions (project_id, name, build_id, is_default)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(project_id, name) DO UPDATE SET
                        build_id = excluded.build_id,
                        is_default = excluded.is_default
                    """,
                    (
                        build["project_id"],
                        build["version_name"],
                        build_id,
                        1 if build["version_name"] == "latest" else 0,
                    ),
                )
            self.conn.commit()

    def get_build(self, build_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM builds WHERE id = ?", (build_id,)).fetchone()
        if row is None:
            raise KeyError(build_id)
        return row

    def has_active(self, project_id: int, version_name: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1 FROM builds
            WHERE project_id = ? AND version_name = ? AND status IN ('queued', 'running')
            LIMIT 1
            """,
            (project_id, version_name),
        ).fetchone()
        return row is not None

    def latest_sha(self, project_id: int, version_name: str) -> str | None:
        row = self.conn.execute(
            """
            SELECT sha FROM builds
            WHERE project_id = ? AND version_name = ?
              AND status IN ('success', 'success_with_warnings')
              AND sha IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (project_id, version_name),
        ).fetchone()
        if row is None or not row["sha"]:
            return None
        return str(row["sha"])

    def version_names(self, project_id: int) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM versions WHERE project_id = ? ORDER BY name",
            (project_id,),
        ).fetchall()
        return [str(row["name"]) for row in rows]

    @staticmethod
    def public_project(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "name": row["name"],
            "git_url": row["git_url"],
            "local_path": row["local_path"],
            "created_at": row["created_at"],
        }

    @staticmethod
    def public_build(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "ref": row["ref"],
            "version": row["version_name"],
            "sha": row["sha"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "log_path": row["log_path"],
            "artifact_path": row["artifact_path"],
            "warnings": _load_warnings(row["warnings"]),
        }


def _load_warnings(value: str | None) -> object:
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
