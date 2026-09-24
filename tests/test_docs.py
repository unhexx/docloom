"""Оглавление документации ссылается на файлы, которые есть в репозитории."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_points_at_docs_and_release() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://img.shields.io/github/v/release/unhexx/docloom" in readme
    assert "https://img.shields.io/github/license/unhexx/docloom" in readme
    assert "python-3.11" in readme
    assert "badge/API-FastAPI" in readme
    assert "badge/queue-SQLite" in readme
    assert "(docs/index.md)" in readme
    assert "(docs/architecture.md)" in readme
    assert "(docs/bitbucket.md)" in readme


def test_doc_index_has_the_same_badges() -> None:
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    assert "https://img.shields.io/github/v/release/unhexx/docloom" in index
    assert "python-3.11" in index
    assert "(../LICENSE)" in index
    assert "(architecture.md)" in index
    assert "(bitbucket.md)" in index


def test_bitbucket_retries_a_failed_build() -> None:
    text = (ROOT / "docs" / "bitbucket.md").read_text(encoding="utf-8")
    assert "Неуспешный билд SHA не сохраняет" in text
    operations = (ROOT / "docs" / "operations.md").read_text(encoding="utf-8")
    assert "300 секунд" in operations


def test_relative_doc_links_exist() -> None:
    pages = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    link = re.compile(r"\]\(([^)\s]+)\)")
    fence = re.compile(r"```.*?```", re.DOTALL)
    checked = 0
    for page in pages:
        text = fence.sub("", page.read_text(encoding="utf-8"))
        for target in link.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path = (page.parent / target.split("#", 1)[0]).resolve()
            assert path.is_file(), f"{page.relative_to(ROOT)} -> {target}"
            checked += 1
    assert checked > 20
