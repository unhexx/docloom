"""Статический сайт: заголовок, ссылка на символ, индекс, llms и манифест."""

from __future__ import annotations

import json
from pathlib import Path

from docloom.book import build_book
from docloom.publisher import publish

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "samples" / "demo-lib"


def test_publish_demo_site(tmp_path: Path) -> None:
    book = build_book(DEMO)
    dest = tmp_path / "latest"
    manifest = publish(book, dest, sha="deadbeef", built_at="2026-09-24T00:00:00Z")
    index = (dest / "index.html").read_text(encoding="utf-8")
    assert "demo-lib" in index
    assert 'class="brand"' in index
    client_pages = list(dest.glob("generated/python/**/Client.html"))
    assert client_pages
    client_href = client_pages[0].relative_to(dest).as_posix()
    assert client_href in index
    client_html = client_pages[0].read_text(encoding="utf-8")
    assert "Client" in client_html
    assert 'class="highlight"' in client_html
    assert "class Client" in client_pages[0].with_suffix(".md").read_text(encoding="utf-8")

    documents = json.loads((dest / "search-index.json").read_text(encoding="utf-8"))
    assert documents
    assert any("connect" in item["title"] or "connect" in item["body"] for item in documents)
    assert (dest / "llms.txt").read_text(encoding="utf-8").startswith("# demo-lib")
    assert "GET /widgets" in (dest / "llms-full.txt").read_text(encoding="utf-8")
    assert (dest / "404.html").read_text(encoding="utf-8").count("Страница не найдена") >= 1
    assert manifest["source_sha"] == "deadbeef"
    assert manifest["search_documents"] == len(documents)
    saved = json.loads((dest / "build.json").read_text(encoding="utf-8"))
    assert saved["status"] == "success_with_warnings"
    assert saved["docstring_coverage"]["missing"] >= 1

    nested = next(dest.glob("generated/http/*.html"))
    nested_html = nested.read_text(encoding="utf-8")
    assert "DOCLOOM_ROOT" in nested_html
    assert "../" in nested_html
