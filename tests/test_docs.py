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
    assert "(docs/index.md)" in readme


def test_doc_index_targets_exist() -> None:
    index = ROOT / "docs" / "index.md"
    text = index.read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)]+)\)", text)
    assert links
    for target in links:
        path = (index.parent / target).resolve()
        assert path.is_file(), target
