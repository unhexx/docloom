"""Откуда брать исходники билда и как посчитать отпечаток дерева."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath

_REF = re.compile(r"[A-Za-z0-9._-]{1,100}")


class SourceError(Exception):
    """Исходник нельзя безопасно прочитать."""


def version_from_ref(ref: str) -> str:
    value = ref.strip()
    for prefix in ("refs/heads/", "refs/tags/"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    if value in {"", "HEAD"}:
        value = "latest"
    if not _REF.fullmatch(value) or value in {".", ".."}:
        raise SourceError(f"недопустимое имя версии: {ref}")
    return value


def ensure_allowed(path: Path, roots: tuple[Path, ...]) -> Path:
    resolved = path.resolve()
    for root in roots:
        base = root.resolve()
        if resolved == base or base in resolved.parents:
            return resolved
    raise SourceError(f"путь вне разрешённых корней: {path}")


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc")
    ]
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if ".git" in PurePosixPath(rel).parts:
            continue
        digest.update(rel.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def checkout_git(url: str, dest: Path, ref: str, *, timeout: int = 60) -> str:
    """Клонирует ref в dest и возвращает SHA. ref — ветка или тег, не произвольная команда."""
    version_from_ref(ref)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").is_dir():
        _run(["git", "clone", "--depth", "1", "--branch", ref, url, str(dest)], timeout)
    else:
        _run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin", ref], timeout)
        _run(["git", "-C", str(dest), "checkout", "--detach", "FETCH_HEAD"], timeout)
    completed = _run(["git", "-C", str(dest), "rev-parse", "HEAD"], timeout)
    return completed.stdout.strip()


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        message = detail[-1] if detail else "git завершился с ошибкой"
        raise SourceError(message) from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceError("превышено время ожидания git") from exc
