"""Справочник Python из AST. Пользовательский код не импортируется и не исполняется."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from docloom.config import ProjectConfig
from docloom.ignore import is_excluded
from docloom.ir import Page, SourceLoc, WarningItem
from docloom.textfmt import md_label

_LABELS = {
    "ru": {
        "params": "Параметры",
        "returns": "Возвращает",
        "source": "Исходник",
        "members": "Состав",
        "methods": "Методы",
        "name": "Имя",
        "type": "Тип",
        "default": "По умолчанию",
        "empty": "—",
        "missing_return": "не указан",
        "reexport": "Повторный экспорт",
    },
    "en": {
        "params": "Parameters",
        "returns": "Returns",
        "source": "Source",
        "members": "Members",
        "methods": "Methods",
        "name": "Name",
        "type": "Type",
        "default": "Default",
        "empty": "—",
        "missing_return": "not annotated",
        "reexport": "Re-exports",
    },
}


@dataclass(frozen=True)
class PythonExtraction:
    pages: tuple[Page, ...]
    warnings: tuple[WarningItem, ...]


def extract_python(project_root: Path) -> PythonExtraction:
    root = Path(project_root)
    config = ProjectConfig.load(root / "docloom.yml")
    labels = _LABELS["ru"] if config.language.lower().startswith("ru") else _LABELS["en"]
    pages: list[Page] = []
    warnings: list[WarningItem] = []
    for py_root in config.python_roots:
        base = root / py_root
        if not base.is_dir():
            warnings.append(
                WarningItem("missing_python_root", py_root, py_root.replace("\\", "/"), 1)
            )
            continue
        files = sorted(path for path in base.rglob("*.py") if path.is_file())
        for path in files:
            rel = path.relative_to(root).as_posix()
            if is_excluded(rel, config.exclude):
                continue
            rel_mod = path.relative_to(base).as_posix()
            if _private_module(rel_mod):
                continue
            file_pages, file_warnings = _extract_file(path, rel, rel_mod, labels)
            pages.extend(file_pages)
            warnings.extend(file_warnings)
    pages.sort(key=lambda page: page.path)
    warnings.sort(key=lambda item: (item.file, item.line, item.symbol, item.code))
    return PythonExtraction(tuple(pages), tuple(warnings))


def _private_module(rel_mod: str) -> bool:
    parts = PurePosixPath(rel_mod).parts
    for part in parts:
        name = part[:-3] if part.endswith(".py") else part
        if name == "__init__":
            continue
        if name.startswith("_"):
            return True
    return False


def _extract_file(
    path: Path,
    rel: str,
    rel_mod: str,
    labels: dict[str, str],
) -> tuple[list[Page], list[WarningItem]]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], [WarningItem("unreadable_file", rel, rel, 1, str(exc))]
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        return [], [WarningItem("syntax_error", rel, rel, exc.lineno or 1, exc.msg or "")]

    module_name = _module_name(rel_mod)
    exported = _all_names(tree)
    pages: list[Page] = []
    warnings: list[WarningItem] = []
    defined: set[str] = set()

    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _public_name(node.name)
    ]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and _public_name(node.name)]
    if exported is not None:
        functions = [node for node in functions if node.name in exported]
        classes = [node for node in classes if node.name in exported]
    defined.update(node.name for node in functions)
    defined.update(node.name for node in classes)

    members: list[tuple[str, str]] = []
    for node in functions:
        qual = _join(module_name, node.name)
        page, missing = _function_page(node, qual, node.name, "python.function", rel, labels)
        pages.append(page)
        members.append((node.name, page.path))
        if missing:
            warnings.append(missing)
    for node in classes:
        qual = _join(module_name, node.name)
        class_page, method_pages, class_warnings, method_links = _class_pages(
            node, qual, rel, labels
        )
        pages.append(class_page)
        pages.extend(method_pages)
        warnings.extend(class_warnings)
        members.append((node.name, class_page.path))
        members.extend(method_links)

    reexports = []
    if exported is not None:
        reexports = [name for name in exported if name not in defined]
    module_doc = ast.get_docstring(tree, clean=True)
    if not module_doc:
        warnings.append(WarningItem("missing_docstring", module_name or rel, rel, 1))
    pages.append(
        _module_page(module_name or rel, rel, module_doc or "", members, reexports, labels)
    )
    return pages, warnings


def _class_pages(
    node: ast.ClassDef,
    qual: str,
    rel: str,
    labels: dict[str, str],
) -> tuple[Page, list[Page], list[WarningItem], list[tuple[str, str]]]:
    warnings: list[WarningItem] = []
    methods: list[Page] = []
    links: list[tuple[str, str]] = []
    docstring = ast.get_docstring(node, clean=True)
    if not docstring:
        warnings.append(WarningItem("missing_docstring", qual, rel, node.lineno))
    for child in node.body:
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _public_name(child.name):
            continue
        method_qual = f"{qual}.{child.name}"
        title = f"{node.name}.{child.name}"
        page, missing = _function_page(child, method_qual, title, "python.method", rel, labels)
        methods.append(page)
        links.append((title, page.path))
        if missing:
            warnings.append(missing)
    methods.sort(key=lambda page: (page.source.line if page.source else 0, page.path))
    class_path = _page_path(qual, "python.class")
    method_lines = [_member_table(labels["methods"], links, class_path, labels)]
    text = _render_block(
        title=node.name,
        signature=_class_signature(node),
        decorators=_decorators(node),
        docstring=docstring or "",
        extra="".join(method_lines),
        source_file=rel,
        source_line=node.lineno,
        labels=labels,
    )
    page = Page(
        id=f"python:{qual}",
        kind="python.class",
        title=node.name,
        path=class_path,
        anchors=("methods",),
        source=SourceLoc(rel, node.lineno),
        text=text,
    )
    return page, methods, warnings, links


def _function_page(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    qual: str,
    title: str,
    kind: str,
    rel: str,
    labels: dict[str, str],
) -> tuple[Page, WarningItem | None]:
    docstring = ast.get_docstring(node, clean=True)
    missing = None
    if not docstring:
        missing = WarningItem("missing_docstring", qual, rel, node.lineno)
    params = _param_rows(node.args)
    returns = ast.unparse(node.returns) if node.returns is not None else ""
    extra = _param_table(params, labels) + _returns_block(returns, labels)
    text = _render_block(
        title=title,
        signature=_function_signature(node),
        decorators=_decorators(node),
        docstring=docstring or "",
        extra=extra,
        source_file=rel,
        source_line=node.lineno,
        labels=labels,
    )
    page = Page(
        id=f"python:{qual}",
        kind=kind,
        title=title,
        path=_page_path(qual, kind),
        anchors=("parameters", "returns"),
        source=SourceLoc(rel, node.lineno),
        text=text,
    )
    return page, missing


def _module_page(
    module_name: str,
    rel: str,
    docstring: str,
    members: list[tuple[str, str]],
    reexports: list[str],
    labels: dict[str, str],
) -> Page:
    path = _page_path(module_name, "python.module")
    extra = _member_table(labels["members"], members, path, labels)
    if reexports:
        items = "\n".join(f"- `{name}`" for name in reexports)
        extra += f'<a id="reexports"></a>\n\n## {labels["reexport"]}\n\n{items}\n'
    text = _render_block(
        title=module_name,
        signature="",
        decorators=[],
        docstring=docstring,
        extra=extra,
        source_file=rel,
        source_line=1,
        labels=labels,
    )
    return Page(
        id=f"python:{module_name}",
        kind="python.module",
        title=module_name,
        path=path,
        anchors=("members",),
        source=SourceLoc(rel, 1),
        text=text,
    )


def _render_block(
    *,
    title: str,
    signature: str,
    decorators: list[str],
    docstring: str,
    extra: str,
    source_file: str,
    source_line: int,
    labels: dict[str, str],
) -> str:
    lines = [f"# {md_label(title)}", ""]
    if signature or decorators:
        lines.append("```python")
        lines.extend(decorators)
        if signature:
            lines.append(signature)
        lines.append("```")
        lines.append("")
    if docstring:
        lines.append(docstring)
        lines.append("")
    lines.append(extra.rstrip())
    lines.append("")
    lines.append(f'<a id="source"></a>')
    lines.append("")
    lines.append(f"## {labels['source']}")
    lines.append("")
    lines.append(f"`{source_file}:{source_line}`")
    lines.append("")
    return "\n".join(lines)


def _member_table(
    heading: str,
    members: list[tuple[str, str]],
    from_path: str,
    labels: dict[str, str],
) -> str:
    anchor = "methods" if heading == labels["methods"] else "members"
    if not members:
        return f'<a id="{anchor}"></a>\n\n## {heading}\n\n{labels["empty"]}\n'
    rows = [f'<a id="{anchor}"></a>', "", f"## {heading}", ""]
    for name, target in members:
        href = _relative(from_path, target)
        rows.append(f"- [{md_label(name)}]({href})")
    rows.append("")
    return "\n".join(rows)


def _param_table(params: list[tuple[str, str, str]], labels: dict[str, str]) -> str:
    lines = ['<a id="parameters"></a>', "", f"## {labels['params']}", ""]
    if not params:
        lines.append(labels["empty"])
        lines.append("")
        return "\n".join(lines)
    lines.append(f"| {labels['name']} | {labels['type']} | {labels['default']} |")
    lines.append("| --- | --- | --- |")
    for name, annotation, default in params:
        lines.append(
            f"| `{name}` | {annotation or labels['empty']} | {default or labels['empty']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _returns_block(annotation: str, labels: dict[str, str]) -> str:
    shown = f"`{annotation}`" if annotation else labels["missing_return"]
    return f'<a id="returns"></a>\n\n## {labels["returns"]}\n\n{shown}\n'


def _relative(from_path: str, to_path: str) -> str:
    origin = PurePosixPath(from_path).parent
    return PurePosixPath(_relpath(origin, to_path)).as_posix()


def _relpath(origin: PurePosixPath, target: str) -> str:
    origin_parts = list(origin.parts)
    target_parts = list(PurePosixPath(target).parts)
    common = 0
    for left, right in zip(origin_parts, target_parts):
        if left != right:
            break
        common += 1
    up = [".."] * (len(origin_parts) - common)
    return "/".join(up + target_parts[common:]) or target_parts[-1]


def _page_path(qualname: str, kind: str) -> str:
    parts = [part for part in qualname.split(".") if part]
    if kind == "python.module":
        return "generated/python/" + "/".join(parts) + "/index.md"
    return "generated/python/" + "/".join(parts) + ".md"


def _module_name(rel_mod: str) -> str:
    parts = list(PurePosixPath(rel_mod).parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    elif parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    return ".".join(parts)


def _join(module_name: str, name: str) -> str:
    return f"{module_name}.{name}" if module_name else name


def _public_name(name: str) -> bool:
    if name.startswith("__") and name.endswith("__"):
        return name == "__init__"
    return not name.startswith("_")


def _all_names(tree: ast.AST) -> list[str] | None:
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                return _string_elts(node.value)
    return None


def _string_elts(node: ast.AST) -> list[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    names: list[str] = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            names.append(elt.value)
            continue
        return None
    return names


def _decorators(node: ast.AST) -> list[str]:
    found = getattr(node, "decorator_list", [])
    return [f"@{ast.unparse(item)}" for item in found]


def _class_signature(node: ast.ClassDef) -> str:
    pieces = [ast.unparse(base) for base in node.bases]
    for keyword in node.keywords:
        if keyword.arg is None:
            pieces.append("**" + ast.unparse(keyword.value))
        else:
            pieces.append(f"{keyword.arg}={ast.unparse(keyword.value)}")
    if not pieces:
        return f"class {node.name}"
    return f"class {node.name}({', '.join(pieces)})"


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    rendered = _render_arguments(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({rendered}){returns}"


def _render_arguments(args: ast.arguments) -> str:
    pieces: list[str] = []
    positional = list(args.posonlyargs) + list(args.args)
    first_default = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        default = args.defaults[index - first_default] if index >= first_default else None
        pieces.append(_format_arg(arg, default))
        if args.posonlyargs and index == len(args.posonlyargs) - 1:
            pieces.append("/")
    if args.vararg is not None:
        pieces.append(_format_arg(args.vararg, None, "*"))
    elif args.kwonlyargs:
        pieces.append("*")
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        pieces.append(_format_arg(arg, default))
    if args.kwarg is not None:
        pieces.append(_format_arg(args.kwarg, None, "**"))
    return ", ".join(pieces)


def _format_arg(arg: ast.arg, default: ast.expr | None, star: str = "") -> str:
    text = f"{star}{arg.arg}"
    if arg.annotation is not None:
        text += ": " + ast.unparse(arg.annotation)
    if default is not None:
        text += " = " + ast.unparse(default)
    return text


def _param_rows(args: ast.arguments) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    positional = list(args.posonlyargs) + list(args.args)
    first_default = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        if arg.arg in {"self", "cls"}:
            continue
        default = args.defaults[index - first_default] if index >= first_default else None
        rows.append(_row(arg, default))
    if args.vararg is not None:
        rows.append(_row(args.vararg, None, "*"))
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        rows.append(_row(arg, default))
    if args.kwarg is not None:
        rows.append(_row(args.kwarg, None, "**"))
    return rows


def _row(arg: ast.arg, default: ast.expr | None, star: str = "") -> tuple[str, str, str]:
    annotation = ast.unparse(arg.annotation) if arg.annotation is not None else ""
    shown_default = ast.unparse(default) if default is not None else ""
    return (f"{star}{arg.arg}", annotation, shown_default)
