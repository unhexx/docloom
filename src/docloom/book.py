"""Склейка гайдов и сгенерированного справочника в одну книгу."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docloom.config import ProjectConfig
from docloom.generators.guides import extract_guides
from docloom.generators.openapi import extract_openapi
from docloom.generators.python_ast import extract_python
from docloom.ir import Page, WarningItem


@dataclass(frozen=True)
class Book:
    project: str
    version: str
    language: str
    pages: tuple[Page, ...]
    summary: str
    warnings: tuple[WarningItem, ...]
    status: str


def build_book(project_root: Path, *, version: str | None = None) -> Book:
    root = Path(project_root).resolve()
    config = ProjectConfig.load(root / "docloom.yml")
    guides, guide_warnings = extract_guides(root, config)
    python = extract_python(root)
    http_pages, http_warnings = extract_openapi(root, config)
    warnings = tuple(sorted(
        (*guide_warnings, *python.warnings, *http_warnings),
        key=lambda item: (item.file, item.line, item.symbol, item.code),
    ))
    diagnostics = _diagnostics(warnings, config.language) if warnings else None
    pages: list[Page] = list(guides)
    pages.extend(python.pages)
    pages.extend(http_pages)
    if diagnostics is not None:
        pages.append(diagnostics)
    chosen = version or config.version or "latest"
    return Book(
        project=config.project,
        version=chosen,
        language=config.language,
        pages=tuple(pages),
        summary=_summary(config, guides, python.pages, http_pages, diagnostics),
        warnings=warnings,
        status="success_with_warnings" if warnings else "success",
    )


def _summary(
    config: ProjectConfig,
    guides: tuple[Page, ...],
    python_pages: tuple[Page, ...],
    http_pages: tuple[Page, ...],
    diagnostics: Page | None,
) -> str:
    ru = config.language.lower().startswith("ru")
    guides_title = "Руководства" if ru else "Guides"
    reference = "Справочник" if ru else "Reference"
    service = "Служебное" if ru else "Meta"
    lines = ["# Summary", ""]
    lines.extend(_section(guides_title, guides))
    visible_python = tuple(page for page in python_pages if page.kind != "python.method")
    lines.append(f"## {reference}")
    lines.append("")
    lines.extend(_section("Python", visible_python, level=3))
    lines.extend(_section("HTTP", http_pages, level=3))
    if diagnostics is not None:
        diag_title = "Диагностика" if ru else "Diagnostics"
        renamed = Page(
            id=diagnostics.id,
            kind=diagnostics.kind,
            title=diag_title,
            path=diagnostics.path,
            anchors=diagnostics.anchors,
            source=diagnostics.source,
            text=diagnostics.text,
        )
        lines.extend(_section(service, (renamed,)))
    return "\n".join(lines).rstrip() + "\n"


def _section(title: str, pages: tuple[Page, ...], *, level: int = 2) -> list[str]:
    lines = [f"{'#' * level} {title}", ""]
    if not pages:
        lines.append("- —")
        lines.append("")
        return lines
    for page in pages:
        lines.append(f"* [{page.title}]({page.path})")
    lines.append("")
    return lines


def _diagnostics(warnings: tuple[WarningItem, ...], language: str) -> Page:
    ru = language.lower().startswith("ru")
    title = "Диагностика" if ru else "Diagnostics"
    intro = (
        "Сборка дошла до конца. Ниже замечания, которые не остановили книгу."
        if ru
        else "The build finished. These notes did not stop the book."
    )
    lines = [f"# {title}", "", intro, "", "| code | symbol | file | line |", "| --- | --- | --- | --- |"]
    for item in warnings:
        lines.append(f"| `{item.code}` | `{item.symbol}` | `{item.file}` | {item.line} |")
    lines.append("")
    return Page(
        id="diagnostics",
        kind="diagnostics",
        title=title,
        path="generated/diagnostics.md",
        anchors=(),
        source=None,
        text="\n".join(lines),
    )
