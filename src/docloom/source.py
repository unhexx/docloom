"""Откуда брать исходники билда и как посчитать отпечаток дерева."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

_REF = re.compile(r"[A-Za-z0-9._-]{1,100}")


class SourceError(Exception):
    """Исходник нельзя безопасно прочитать."""


@dataclass(frozen=True)
class GitAuth:
    token: str = ""
    ssl_verify: bool = True


def normalize_git_url(url: str) -> str:
    """Сравнивает clone URL без пользователя, порта по умолчанию и суффикса .git."""
    raw = url.strip()
    if not raw:
        return ""
    if "://" not in raw and ":" in raw:
        host, path = raw.split(":", 1)
        host = host.split("@")[-1].lower()
        return _ssh(host, None, path)
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    path = parts.path
    if parts.scheme in {"ssh", "git"}:
        return _ssh(host, parts.port, path)
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme.lower()}://{host}{port}{_clean_path(path)}"


def remote_sha(url: str, ref: str, auth: GitAuth | None = None, *, timeout: int = 300) -> str:
    version_from_ref(ref)
    auth = auth or GitAuth()
    completed = _run(
        [*_git_prefix(auth), "ls-remote", url, f"refs/heads/{ref}"],
        timeout,
        auth,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        completed = _run(
            [*_git_prefix(auth), "ls-remote", url, f"refs/tags/{ref}"],
            timeout,
            auth,
        )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise SourceError(f"на удалённой стороне нет {ref}")
    sha = lines[0].split()[0]
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise SourceError("неожиданный ответ ls-remote")
    return sha.lower()


def _ssh(host: str, port: int | None, path: str) -> str:
    suffix = f":{port}" if port else ""
    return f"ssh://{host}{suffix}{_clean_path(path)}"


def _clean_path(path: str) -> str:
    cleaned = "/" + path.strip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned or "/"


def _git_prefix(auth: GitAuth) -> list[str]:
    args = ["git", "-c", "http.version=HTTP/1.1"]
    if not auth.ssl_verify:
        args.extend(["-c", "http.sslVerify=false"])
    if auth.token:
        args.extend(["-c", f"http.extraHeader=Authorization: Bearer {auth.token}"])
    return args


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


def checkout_git(
    url: str,
    dest: Path,
    ref: str,
    auth: GitAuth | None = None,
    *,
    timeout: int = 300,
) -> str:
    """Клонирует ref в dest и возвращает SHA. ref — ветка или тег, не произвольная команда."""
    version_from_ref(ref)
    auth = auth or GitAuth()
    if auth.token and _bitbucket_repo(url) is not None:
        return _checkout_bitbucket_docs(url, dest, ref, auth, timeout)
    dest.parent.mkdir(parents=True, exist_ok=True)
    prefix = _git_prefix(auth)
    if not (dest / ".git").is_dir():
        _run([*prefix, "clone", "--depth", "1", "--branch", ref, url, str(dest)], timeout, auth)
    else:
        _run([*prefix, "-C", str(dest), "fetch", "--depth", "1", "origin", ref], timeout, auth)
        _run([*prefix, "-C", str(dest), "checkout", "--detach", "FETCH_HEAD"], timeout, auth)
    completed = _run([*prefix, "-C", str(dest), "rev-parse", "HEAD"], timeout, auth)
    return completed.stdout.strip()


def _run(args: list[str], timeout: int, auth: GitAuth | None = None) -> subprocess.CompletedProcess[str]:
    auth = auth or GitAuth()
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
        raise SourceError(_scrub(message, auth.token)) from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceError("превышено время ожидания git") from exc


def _bitbucket_repo(url: str) -> tuple[str, str, str] | None:
    parts = urlsplit(url)
    pieces = [item for item in parts.path.split("/") if item]
    if len(pieces) < 3 or pieces[0] != "scm":
        return None
    slug = pieces[2]
    if slug.endswith(".git"):
        slug = slug[:-4]
    if not parts.hostname or not slug or not pieces[1]:
        return None
    return parts.hostname, pieces[1].upper(), slug


def _doc_path(rel: str) -> bool:
    name = rel.replace("\\", "/").lstrip("./")
    lower = name.lower()
    if lower in {"readme.md", "summary.md", "docloom.yml", "openapi.yaml", "openapi.yml"}:
        return True
    if lower.startswith("docs/") and lower.endswith(".md"):
        return True
    return name.startswith("src/") and lower.endswith(".py")


def _checkout_bitbucket_docs(url: str, dest: Path, ref: str, auth: GitAuth, timeout: int) -> str:
    """Берёт только файлы книги. Полный clone на этом сервере зависает на pack."""
    host, project, slug = _bitbucket_repo(url) or ("", "", "")
    sha = remote_sha(url, ref, auth, timeout=min(timeout, 60))
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    at = urllib.parse.quote(f"refs/heads/{ref}", safe="")
    paths = _bitbucket_paths(host, project, slug, at, auth, timeout)
    chosen = [item for item in paths if _doc_path(item)]
    if not chosen:
        raise SourceError("в ревизии нет README, docs или docloom.yml")
    for rel in chosen:
        quoted = "/".join(urllib.parse.quote(part) for part in rel.split("/"))
        payload = _bitbucket_get(
            host,
            f"/rest/api/1.0/projects/{urllib.parse.quote(project)}/repos/{urllib.parse.quote(slug)}/raw/{quoted}?at={at}",
            auth,
            timeout,
        )
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return sha


def _bitbucket_paths(host: str, project: str, slug: str, at: str, auth: GitAuth, timeout: int) -> list[str]:
    found: list[str] = []
    start = 0
    while True:
        query = f"/rest/api/1.0/projects/{urllib.parse.quote(project)}/repos/{urllib.parse.quote(slug)}/files?at={at}&limit=200&start={start}"
        payload = json.loads(_bitbucket_get(host, query, auth, timeout).decode("utf-8"))
        found.extend(str(item) for item in payload.get("values", []))
        if payload.get("isLastPage", True):
            break
        start = int(payload.get("nextPageStart") or start + 200)
    return found


def _bitbucket_get(host: str, path: str, auth: GitAuth, timeout: int) -> bytes:
    context = ssl.create_default_context() if auth.ssl_verify else ssl._create_unverified_context()
    request = urllib.request.Request(
        f"https://{host}{path}",
        headers={"Authorization": f"Bearer {auth.token}"},
    )
    try:
        with urllib.request.urlopen(request, context=context, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise SourceError(f"Bitbucket ответил {exc.code} на {path.split('?')[0]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SourceError("Bitbucket не отдал файл документации") from exc


def _scrub(message: str, token: str) -> str:
    if token:
        return message.replace(token, "***")
    return message
