"""Гайды из Markdown и SUMMARY.md. Текст не переписывается, только порядок."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import yaml

from docloom.config import ProjectConfig
from docloom.ir import Page, SourceLoc, WarningItem

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_guides(project_root: Path, config: ProjectConfig | None = None) -> tuple[tuple[Page, ...], tuple[WarningItem, ...]]:
    root = Path(project_root)
    config = config or ProjectConfig.load(root / "docloom.yml")
    if not config.guides:
        return (), ()
    guide_root = root / config.guides
    warnings: list[WarningItem] = []
    pages: list[Page] = []
    seen: set[str] = set()
    summary_path = root / "SUMMARY.md"
    entries: list[tuple[str, str]] = []
    if summary_path.is_file():
        entries = _summary_entries(summary_path.read_text(encoding="utf-8"))
    else:
        warnings.append(WarningItem("missing_summary", "SUMMARY.md", "SUMMARY.md", 1))

    for title, href in entries:
        rel = href.split("#", 1)[0].strip()
        if rel.startswith(("http://", "https://", "mailto:")):
            warnings.append(WarningItem("external_summary_link", title, "SUMMARY.md", 1, rel))
            continue
        path = _inside(root, rel)
        if path is None or not path.is_file():
            warnings.append(WarningItem("missing_guide", title, rel or href, 1))
            continue
        rel_posix = path.relative_to(root).as_posix()
        if rel_posix in seen:
            continue
        seen.add(rel_posix)
        pages.append(_guide_page(path, rel_posix, title))

    if guide_root.is_dir():
        for path in sorted(guide_root.rglob("*.md")):
            rel_posix = path.relative_to(root).as_posix()
            if rel_posix in seen or not path.is_file():
                continue
            seen.add(rel_posix)
            warnings.append(WarningItem("unlisted_guide", rel_posix, rel_posix, 1))
            pages.append(_guide_page(path, rel_posix, _fallback_title(path)))
    return tuple(pages), tuple(warnings)


def _summary_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("-", "*", "+")):
            continue
        match = _LINK.search(stripped)
        if match:
            entries.append((match.group(1).strip(), match.group(2).strip()))
    return entries


def _guide_page(path: Path, rel: str, title: str) -> Page:
    raw = path.read_text(encoding="utf-8")
    meta, body = _front_matter(raw)
    if isinstance(meta.get("title"), str) and meta["title"].strip():
        title = meta["title"].strip()
    else:
        heading = _first_heading(body)
        if heading and title == _fallback_title(path):
            title = heading
    body = body.strip()
    if not body.startswith("#"):
        body = f"# {title}\n\n{body}".strip()
    text = body + "\n"
    return Page(
        id=f"guide:{rel}",
        kind="guide",
        title=title,
        path=rel,
        anchors=(),
        source=SourceLoc(rel, 1),
        text=text,
    )


def _front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    loaded = yaml.safe_load(parts[1]) or {}
    if not isinstance(loaded, dict):
        return {}, parts[2].lstrip("\n")
    return loaded, parts[2].lstrip("\n")


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _fallback_title(path: Path) -> str:
    stem = path.stem.replace("-", " ").replace("_", " ").strip()
    return stem[:1].upper() + stem[1:] if stem else path.name


def _inside(root: Path, rel: str) -> Path | None:
    if not rel or rel.startswith(("/", "\\")):
        return None
    if ".." in PurePosixPath(rel).parts:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate
