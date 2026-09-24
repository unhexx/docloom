"""Python autodoc: стабильный Markdown из AST, без импорта пакета."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from docloom.config import ProjectConfig
from docloom.generators.python_ast import extract_python
from docloom.ignore import is_excluded

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "samples" / "demo-lib"


def test_config_reads_demo() -> None:
    config = ProjectConfig.load(DEMO / "docloom.yml")
    assert config.project == "demo-lib"
    assert config.language == "ru"
    assert config.python_roots == ("src",)
    assert config.openapi == ("openapi.yaml",)
    assert config.root == DEMO.resolve()


def test_exclude_glob() -> None:
    assert is_excluded("src/demo_lib/tests/test_client.py", ("**/tests/**",))
    assert is_excluded("tests/test_client.py", ("**/tests/**",))
    assert not is_excluded("src/demo_lib/client.py", ("**/tests/**",))


def test_demo_has_client_class_and_identical_rerun() -> None:
    before = {name for name in sys.modules if name == "demo_lib" or name.startswith("demo_lib.")}
    first = extract_python(DEMO)
    second = extract_python(DEMO)
    after = {name for name in sys.modules if name == "demo_lib" or name.startswith("demo_lib.")}
    assert after == before
    assert [(page.path, page.text) for page in first.pages] == [
        (page.path, page.text) for page in second.pages
    ]
    assert [item.to_dict() for item in first.warnings] == [item.to_dict() for item in second.warnings]

    client = next(page for page in first.pages if page.kind == "python.class" and page.title == "Client")
    assert client.source is not None
    assert client.source.file == "src/demo_lib/client.py"
    source_line = (DEMO / client.source.file).read_text(encoding="utf-8").splitlines()[
        client.source.line - 1
    ]
    assert source_line.startswith("class Client")
    assert "class Client" in client.text

    connect = next(page for page in first.pages if page.title == "Client.connect")
    assert connect.kind == "python.method"
    assert "def connect(self, timeout: float = 5.0) -> bool" in connect.text
    assert "parameters" in connect.anchors
    assert connect.to_dict()["source"]["file"] == "src/demo_lib/client.py"
    assert all("_hidden" not in page.title for page in first.pages)
    assert any(
        item.code == "missing_docstring" and item.symbol.endswith("helper") for item in first.warnings
    )
    assert not any("hidden" in item.symbol for item in first.warnings)


def test_all_and_signature_edges(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (tmp_path / "docloom.yml").write_text(
        "project: edges\nlanguage: en\nsources:\n  python: [pkg]\n",
        encoding="utf-8",
    )
    (package / "mod.py").write_text(
        textwrap.dedent(
            '''
            """Module."""

            __all__ = ["shown", "Child"]

            def shown(a, /, b: int, *rest: str, flag: bool = False, **kw: int) -> int:
                """Visible."""
                return b

            def hidden_public(x: int) -> int:
                """Kept out by __all__."""
                return x

            class Child(shown):
                """Child class."""

                async def run(self, *, retry: int = 1) -> None:
                    """Run."""
                    return None
            '''
        ).lstrip(),
        encoding="utf-8",
    )
    extracted = extract_python(tmp_path)
    titles = {page.title for page in extracted.pages}
    assert "shown" in titles
    assert "hidden_public" not in titles
    assert "Child.run" in titles
    shown = next(page for page in extracted.pages if page.title == "shown")
    assert "def shown(a, /, b: int, *rest: str, flag: bool = False, **kw: int) -> int" in shown.text
    run = next(page for page in extracted.pages if page.title == "Child.run")
    assert "async def run(self, *, retry: int = 1) -> None" in run.text
    child = next(page for page in extracted.pages if page.kind == "python.class")
    assert "class Child(shown)" in child.text


def test_syntax_error_is_warning(tmp_path: Path) -> None:
    (tmp_path / "docloom.yml").write_text(
        "project: bad\nsources:\n  python: [src]\n",
        encoding="utf-8",
    )
    source = tmp_path / "src"
    source.mkdir()
    (source / "broken.py").write_text("def (\n", encoding="utf-8")
    extracted = extract_python(tmp_path)
    assert extracted.pages == ()
    assert extracted.warnings[0].code == "syntax_error"
