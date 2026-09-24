"""Пустой исходник и битый контракт не роняют сборку."""

from __future__ import annotations

from pathlib import Path

from docloom.book import build_book


def test_empty_src_and_broken_spec(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "intro.md").write_text("# Пустой пакет\n\nСправочника нет.\n", encoding="utf-8")
    (tmp_path / "SUMMARY.md").write_text("* [Пустой пакет](docs/intro.md)\n", encoding="utf-8")
    (tmp_path / "docloom.yml").write_text(
        "project: empty\nlanguage: ru\nsources:\n  guides: docs\n  python: [src]\n  openapi: [openapi.yaml]\n",
        encoding="utf-8",
    )
    (tmp_path / "openapi.yaml").write_text("openapi: [\n", encoding="utf-8")
    book = build_book(tmp_path)
    assert book.status == "success_with_warnings"
    assert any(page.kind == "guide" and page.title == "Пустой пакет" for page in book.pages)
    assert not any(page.kind.startswith("python.") for page in book.pages)
    diagnostics = next(page for page in book.pages if page.kind == "diagnostics")
    assert "invalid_openapi" in diagnostics.text
