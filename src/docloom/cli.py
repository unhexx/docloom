"""Команды docloom build, serve и worker."""

from __future__ import annotations

import argparse
from pathlib import Path

from docloom.book import build_book
from docloom.db import utcnow
from docloom.publisher import publish
from docloom.settings import load_settings
from docloom.source import fingerprint


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docloom")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="собрать книгу в каталог")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--version", default=None)

    serve = commands.add_parser("serve", help="HTTP API")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    commands.add_parser("worker", help="разбирать очередь билдов")
    watch = commands.add_parser("watch", help="опрашивать один git и ставить билд")
    watch.add_argument("--url", default=None)
    watch.add_argument("--ref", default=None)
    watch.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "build":
        return _build(args.root, args.out, args.version)
    if args.command == "serve":
        return _serve(args.host, args.port)
    if args.command == "worker":
        return _worker()
    if args.command == "watch":
        return _watch(args.url, args.ref, args.once)
    return 2


def _build(root: Path, out: Path, version: str | None) -> int:
    book = build_book(root, version=version)
    publish(book, out, sha=fingerprint(root.resolve()), built_at=utcnow())
    print(out)
    return 0


def _serve(host: str | None, port: int | None) -> int:
    import uvicorn

    from docloom.api import create_app

    settings = load_settings()
    uvicorn.run(
        create_app(settings),
        host=host or settings.host,
        port=port or settings.port,
    )
    return 0


def _worker() -> int:
    from docloom.worker import serve

    serve(load_settings())
    return 0


def _watch(url: str | None, ref: str | None, once: bool) -> int:
    from docloom.watch import serve

    settings = load_settings()
    serve(
        settings,
        url=url if url is not None else settings.watch_url,
        ref=ref if ref is not None else settings.watch_ref,
        once=once,
    )
    return 0
