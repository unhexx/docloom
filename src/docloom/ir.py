"""Промежуточное представление страницы книги."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLoc:
    file: str
    line: int


@dataclass(frozen=True)
class Page:
    id: str
    kind: str
    title: str
    path: str
    anchors: tuple[str, ...]
    source: SourceLoc | None
    text: str

    def to_dict(self) -> dict[str, object]:
        source = None
        if self.source is not None:
            source = {"file": self.source.file, "line": self.source.line}
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "path": self.path,
            "anchors": list(self.anchors),
            "source": source,
            "text": self.text,
        }


@dataclass(frozen=True)
class WarningItem:
    code: str
    symbol: str
    file: str
    line: int
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "code": self.code,
            "symbol": self.symbol,
            "file": self.file,
            "line": self.line,
        }
        if self.message:
            data["message"] = self.message
        return data
