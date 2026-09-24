"""Страницы операций из OpenAPI 3. Спецификация только читается, не исполняется."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from docloom.config import ProjectConfig
from docloom.ir import Page, SourceLoc, WarningItem

_METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "trace")
_SLUG = re.compile(r"[^a-z0-9]+")


def extract_openapi(
    project_root: Path,
    config: ProjectConfig | None = None,
) -> tuple[tuple[Page, ...], tuple[WarningItem, ...]]:
    root = Path(project_root)
    config = config or ProjectConfig.load(root / "docloom.yml")
    labels = _labels(config.language)
    pages: list[Page] = []
    warnings: list[WarningItem] = []
    for rel in config.openapi:
        spec_path = root / rel
        if not spec_path.is_file():
            warnings.append(WarningItem("missing_openapi", rel, rel, 1))
            continue
        try:
            raw_text = spec_path.read_text(encoding="utf-8")
            loaded = yaml.safe_load(raw_text)
        except (OSError, yaml.YAMLError) as exc:
            warnings.append(WarningItem("invalid_openapi", rel, rel, 1, str(exc).splitlines()[0]))
            continue
        file_pages, file_warnings = _operations(loaded, rel, raw_text, labels)
        pages.extend(file_pages)
        warnings.extend(file_warnings)
    pages.sort(key=lambda page: page.path)
    return tuple(pages), tuple(warnings)


def _operations(
    loaded: object,
    rel: str,
    raw_text: str,
    labels: dict[str, str],
) -> tuple[list[Page], list[WarningItem]]:
    if not isinstance(loaded, dict):
        return [], [WarningItem("invalid_openapi", rel, rel, 1, "корень спецификации не объект")]
    version = str(loaded.get("openapi") or "")
    if not version.startswith("3."):
        return [], [WarningItem("invalid_openapi", rel, rel, 1, f"нужен OpenAPI 3, получено {version or 'пусто'}")]
    paths = loaded.get("paths")
    if not isinstance(paths, dict):
        return [], [WarningItem("invalid_openapi", rel, rel, 1, "нет объекта paths")]
    pages: list[Page] = []
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method in _METHODS:
            operation = item.get(method)
            if not isinstance(operation, dict):
                continue
            pages.append(_operation_page(method, str(path), operation, rel, raw_text, labels))
    return pages, []


def _operation_page(
    method: str,
    path: str,
    operation: dict[str, object],
    rel: str,
    raw_text: str,
    labels: dict[str, str],
) -> Page:
    verb = method.upper()
    title = f"{verb} {path}"
    slug = _slug(method, path)
    summary = str(operation.get("summary") or operation.get("description") or "").strip()
    op_id = operation.get("operationId")
    lines = [f"# {title}", ""]
    if summary:
        lines.extend([summary, ""])
    if isinstance(op_id, str) and op_id:
        lines.extend([f"`operationId: {op_id}`", ""])
    lines.append(_parameters(operation.get("parameters"), labels))
    lines.append(_request(operation.get("requestBody"), labels))
    lines.append(_responses(operation.get("responses"), labels))
    lines.append(_security(operation.get("security"), labels))
    text = "\n".join(part.rstrip() for part in lines if part is not None).rstrip() + "\n"
    return Page(
        id=f"openapi:{method}:{path}",
        kind="openapi.operation",
        title=title,
        path=f"generated/http/{slug}.md",
        anchors=("parameters", "request", "responses"),
        source=SourceLoc(rel, _line_of(raw_text, path)),
        text=text,
    )


def _parameters(value: object, labels: dict[str, str]) -> str:
    lines = ['<a id="parameters"></a>', "", f"## {labels['params']}", ""]
    if not isinstance(value, list) or not value:
        lines.append(labels["empty"])
        return "\n".join(lines) + "\n"
    lines.append(f"| {labels['name']} | {labels['in']} | {labels['type']} | {labels['required']} |")
    lines.append("| --- | --- | --- | --- |")
    for item in value:
        if not isinstance(item, dict):
            continue
        schema = item.get("schema") if isinstance(item.get("schema"), dict) else {}
        assert isinstance(schema, dict)
        type_name = str(schema.get("type") or item.get("type") or labels["empty"])
        required = labels["yes"] if item.get("required") else labels["no"]
        lines.append(
            f"| `{item.get('name', '')}` | {item.get('in', '')} | {type_name} | {required} |"
        )
    return "\n".join(lines) + "\n"


def _request(value: object, labels: dict[str, str]) -> str:
    lines = ['<a id="request"></a>', "", f"## {labels['request']}", ""]
    if not isinstance(value, dict):
        lines.append(labels["empty"])
        return "\n".join(lines) + "\n"
    required = labels["yes"] if value.get("required") else labels["no"]
    lines.append(f"{labels['required']}: {required}")
    lines.append("")
    content = value.get("content")
    if isinstance(content, dict):
        for mime, body in content.items():
            lines.append(f"### `{mime}`")
            lines.append("")
            if isinstance(body, dict) and "example" in body:
                lines.append(_fence(body["example"]))
    return "\n".join(lines).rstrip() + "\n"


def _responses(value: object, labels: dict[str, str]) -> str:
    lines = ['<a id="responses"></a>', "", f"## {labels['responses']}", ""]
    if not isinstance(value, dict) or not value:
        lines.append(labels["empty"])
        return "\n".join(lines) + "\n"
    for status, item in value.items():
        description = ""
        if isinstance(item, dict):
            description = str(item.get("description") or "")
        lines.append(f"### {status}")
        lines.append("")
        if description:
            lines.append(description)
            lines.append("")
        if isinstance(item, dict) and isinstance(item.get("content"), dict):
            for mime, body in item["content"].items():
                lines.append(f"`{mime}`")
                lines.append("")
                if isinstance(body, dict) and "example" in body:
                    lines.append(_fence(body["example"]))
    return "\n".join(lines).rstrip() + "\n"


def _security(value: object, labels: dict[str, str]) -> str:
    lines = ['<a id="security"></a>', "", f"## {labels['security']}", ""]
    if not isinstance(value, list) or not value:
        lines.append(labels["empty"])
        return "\n".join(lines) + "\n"
    for item in value:
        if isinstance(item, dict):
            for name in item:
                lines.append(f"- `{name}`")
    return "\n".join(lines).rstrip() + "\n"


def _fence(value: object) -> str:
    if isinstance(value, str):
        rendered = value
    else:
        rendered = json.dumps(value, ensure_ascii=False, indent=2)
    return f"```json\n{rendered}\n```\n"


def _slug(method: str, path: str) -> str:
    raw = f"{method}-{path.strip('/')}"
    slug = _SLUG.sub("-", raw.lower()).strip("-")
    return slug or method


def _line_of(text: str, path: str) -> int:
    needle = f"{path}:"
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line.replace(" ", ""):
            return index
    return 1


def _labels(language: str) -> dict[str, str]:
    if language.lower().startswith("ru"):
        return {
            "params": "Параметры",
            "request": "Тело запроса",
            "responses": "Ответы",
            "security": "Безопасность",
            "name": "Имя",
            "in": "Где",
            "type": "Тип",
            "required": "Обязательно",
            "yes": "да",
            "no": "нет",
            "empty": "—",
        }
    return {
        "params": "Parameters",
        "request": "Request body",
        "responses": "Responses",
        "security": "Security",
        "name": "Name",
        "in": "In",
        "type": "Type",
        "required": "Required",
        "yes": "yes",
        "no": "no",
        "empty": "—",
    }
