"""Статический сайт книги: своя тема, без рендерера GitBook."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from pygments.formatters import HtmlFormatter

from docloom.book import Book
from docloom.ir import Page

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_MD_LINK = re.compile(r"\]\(([^)\s]+?)\.md(#[^)\s]*)?\)")


def publish(
    book: Book,
    dest: Path,
    *,
    sha: str,
    built_at: str,
    versions: list[str] | None = None,
) -> dict[str, object]:
    """Пишет HTML, индекс поиска, llms.txt и build.json в каталог версии."""
    target = Path(dest)
    target.mkdir(parents=True, exist_ok=True)
    assets = target / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "theme.css").write_text((_TEMPLATE_DIR / "theme.css").read_text(encoding="utf-8"), encoding="utf-8")
    (assets / "search.js").write_text((_TEMPLATE_DIR / "search.js").read_text(encoding="utf-8"), encoding="utf-8")
    (assets / "pygments.css").write_text(_pygments_css(), encoding="utf-8")
    (target / "SUMMARY.md").write_text(book.summary, encoding="utf-8")

    version_names = versions or [book.version]
    groups = _groups(book)
    flat = [(page, _html_path(page.path)) for page in book.pages]
    env = _env()
    template = env.get_template("page.html")
    search_docs: list[dict[str, object]] = []
    full_chunks: list[str] = []

    for index, (page, href) in enumerate(flat):
        html_body, toc = _render_markdown(page.text)
        _write_page(
            template,
            target / href,
            root=target,
            book=book,
            page=page,
            href=href,
            content=html_body,
            toc=toc,
            groups=groups,
            versions=version_names,
            prev=_neighbor(flat, index - 1),
            next_page=_neighbor(flat, index + 1),
        )
        (target / page.path).parent.mkdir(parents=True, exist_ok=True)
        (target / page.path).write_text(page.text, encoding="utf-8")
        search_docs.append(
            {
                "title": page.title,
                "headings": _headings(page.text),
                "body": _plain(page.text),
                "path": href,
            }
        )
        full_chunks.append(page.text.rstrip() + "\n")

    first = flat[0]
    first_body, first_toc = _render_markdown(first[0].text)
    _write_page(
        template,
        target / "index.html",
        root=target,
        book=book,
        page=first[0],
        href=first[1],
        content=first_body,
        toc=first_toc,
        groups=groups,
        versions=version_names,
        prev=None,
        next_page=_neighbor(flat, 1),
        active=first[1],
    )
    _write_page(
        template,
        target / "404.html",
        root=target,
        book=book,
        page=Page("404", "meta", _ui(book)["missing"], "404.html", (), None, ""),
        href="404.html",
        content=f"<h1>{_ui(book)['missing']}</h1><p>{_ui(book)['missing_hint']}</p>",
        toc="",
        groups=groups,
        versions=version_names,
        prev=None,
        next_page=None,
        active="",
    )
    (target / "search-index.json").write_text(
        json.dumps(search_docs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (target / "llms.txt").write_text(_llms(book, groups), encoding="utf-8")
    (target / "llms-full.txt").write_text("\n".join(full_chunks), encoding="utf-8")
    manifest = _manifest(book, sha, built_at, search_docs)
    (target / "build.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _write_page(
    template,
    destination: Path,
    *,
    root: Path,
    book: Book,
    page: Page,
    href: str,
    content: str,
    toc: str,
    groups: list[dict[str, object]],
    versions: list[str],
    prev: dict[str, str] | None,
    next_page: dict[str, str] | None,
    active: str | None = None,
) -> None:
    placed = destination.resolve().relative_to(root.resolve()).as_posix()
    prefix = _asset_prefix(placed)
    ui = _ui(book)
    search_href = f"{prefix}search-index.json"
    rendered_groups = []
    for group in groups:
        items = group["items"]
        assert isinstance(items, list)
        rendered_groups.append({"title": group["title"], "items": items})
    html = template.render(
        language=book.language,
        project=book.project,
        version=book.version,
        versions=versions,
        page_title=page.title,
        content=Markup(content),
        toc=Markup(toc or ""),
        groups=rendered_groups,
        asset_prefix=prefix,
        active=href if active is None else active,
        prev=prev,
        next=next_page,
        search_enabled=True,
        search_href=search_href,
        ui=ui,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _render_markdown(text: str) -> tuple[str, str]:
    converter = markdown.Markdown(
        extensions=["fenced_code", "codehilite", "tables", "toc", "sane_lists"],
        extension_configs={"codehilite": {"css_class": "highlight"}},
    )
    html = converter.convert(_MD_LINK.sub(r"](\1.html\2)", text))
    return html, converter.toc or ""


def _groups(book: Book) -> list[dict[str, object]]:
    ui = _ui(book)
    buckets = [
        (ui["guides"], [page for page in book.pages if page.kind == "guide"]),
        ("Python", [page for page in book.pages if page.kind.startswith("python.") and page.kind != "python.method"]),
        ("HTTP", [page for page in book.pages if page.kind == "openapi.operation"]),
        (ui["meta"], [page for page in book.pages if page.kind == "diagnostics"]),
    ]
    groups: list[dict[str, object]] = []
    for title, pages in buckets:
        if not pages:
            continue
        groups.append(
            {
                "title": title,
                "items": [{"title": page.title, "href": _html_path(page.path)} for page in pages],
            }
        )
    return groups


def _neighbor(flat: list[tuple[Page, str]], index: int) -> dict[str, str] | None:
    if index < 0 or index >= len(flat):
        return None
    page, href = flat[index]
    return {"title": page.title, "href": href}


def _html_path(path: str) -> str:
    if path.endswith(".md"):
        return path[:-3] + ".html"
    return path


def _asset_prefix(html_path: str) -> str:
    depth = len(PurePosixPath(html_path).parent.parts)
    return "../" * depth


def _headings(text: str) -> list[str]:
    return [line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#")]


def _plain(text: str) -> str:
    without_code = re.sub(r"```.*?```", " ", text, flags=re.S)
    without_marks = re.sub(r"[#>*`|_\[\]()]", " ", without_code)
    return re.sub(r"\s+", " ", without_marks).strip()


def _llms(book: Book, groups: list[dict[str, object]]) -> str:
    lines = [f"# {book.project}", "", f"> {book.project} {book.version}", ""]
    for group in groups:
        lines.append(f"## {group['title']}")
        lines.append("")
        items = group["items"]
        assert isinstance(items, list)
        for item in items:
            lines.append(f"- [{item['title']}]({item['href']})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _manifest(book: Book, sha: str, built_at: str, search_docs: list[dict[str, object]]) -> dict[str, object]:
    python_pages = [page for page in book.pages if page.kind.startswith("python.")]
    missing = {item.symbol for item in book.warnings if item.code == "missing_docstring"}
    documented = 0
    for page in python_pages:
        symbol = page.id.removeprefix("python:")
        if symbol not in missing:
            documented += 1
    total = len(python_pages)
    skipped = [
        item.to_dict()
        for item in book.warnings
        if item.code in {"syntax_error", "unreadable_file", "missing_guide", "missing_openapi", "invalid_openapi"}
    ]
    return {
        "project": book.project,
        "version": book.version,
        "source_sha": sha,
        "built_at": built_at,
        "status": book.status,
        "pages": [
            {"id": page.id, "path": _html_path(page.path), "title": page.title, "kind": page.kind}
            for page in book.pages
        ],
        "warnings": [item.to_dict() for item in book.warnings],
        "docstring_coverage": {
            "documented": documented,
            "missing": len(missing),
            "total": total,
            "ratio": round(documented / total, 4) if total else 1.0,
        },
        "search_documents": len(search_docs),
        "skipped": skipped,
    }


def _pygments_css() -> str:
    light = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    dark = HtmlFormatter(style="monokai").get_style_defs(':root[data-theme="dark"] .highlight')
    return light + "\n" + dark + "\n"


def _ui(book: Book) -> dict[str, str]:
    if book.language.lower().startswith("ru"):
        return {
            "menu": "Меню",
            "versions": "Версия",
            "search": "Поиск",
            "theme": "Тема",
            "on_page": "На странице",
            "guides": "Руководства",
            "meta": "Служебное",
            "missing": "Страница не найдена",
            "missing_hint": "В этой версии книги такой страницы нет.",
        }
    return {
        "menu": "Menu",
        "versions": "Version",
        "search": "Search",
        "theme": "Theme",
        "on_page": "On this page",
        "guides": "Guides",
        "meta": "Meta",
        "missing": "Page not found",
        "missing_hint": "This version of the book has no such page.",
    }
