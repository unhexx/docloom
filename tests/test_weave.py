"""Гайды, OpenAPI и порядок разделов в SUMMARY."""

from __future__ import annotations

from pathlib import Path

from docloom.book import build_book

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "samples" / "demo-lib"


def test_demo_summary_order_and_operation() -> None:
    first = build_book(DEMO)
    second = build_book(DEMO)
    assert first.summary == second.summary
    assert first.status == "success_with_warnings"
    summary = first.summary
    assert summary.index("## Руководства") < summary.index("## Справочник")
    assert summary.index("### Python") < summary.index("### HTTP")
    assert "* [Введение](docs/intro.md)" in summary
    assert "* [Понятия](docs/concepts.md)" in summary
    operation = next(page for page in first.pages if page.title == "GET /widgets")
    assert operation.kind == "openapi.operation"
    assert operation.path == "generated/http/get-widgets.md"
    assert "listWidgets" in operation.text
    assert "limit" in operation.text
    assert "apiKey" in operation.text
    assert f"* [{operation.title}]({operation.path})" in summary
    assert any(page.kind == "python.class" and page.title == "Client" for page in first.pages)
    assert any(page.kind == "diagnostics" for page in first.pages)


def test_broken_spec_does_not_abort(tmp_path: Path) -> None:
    (tmp_path / "docloom.yml").write_text(
        "project: broken\nlanguage: ru\nsources:\n  guides: docs\n  openapi: [openapi.yaml]\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "intro.md").write_text("# Введение\n\nТекст.\n", encoding="utf-8")
    (tmp_path / "SUMMARY.md").write_text("* [Введение](docs/intro.md)\n", encoding="utf-8")
    (tmp_path / "openapi.yaml").write_text("openapi: [", encoding="utf-8")
    book = build_book(tmp_path)
    assert book.status == "success_with_warnings"
    diagnostics = next(page for page in book.pages if page.kind == "diagnostics")
    assert "invalid_openapi" in diagnostics.text
    assert any(page.kind == "guide" for page in book.pages)
    assert not any(page.kind == "openapi.operation" for page in book.pages)
