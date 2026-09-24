"""Воркер забирает очередь SQLite и собирает книги по одной."""

from __future__ import annotations

import time

from docloom.db import Store
from docloom.jobs import execute_build
from docloom.settings import Settings


def drain(settings: Settings, *, limit: int = 100) -> int:
    store = Store(settings.data_dir / "docloom.sqlite")
    done = 0
    while done < limit:
        job = store.claim_next()
        if job is None:
            return done
        execute_build(store, settings, int(job["id"]))
        done += 1
    return done


def serve(settings: Settings, *, poll: float = 1.0) -> None:
    while True:
        if drain(settings, limit=1) == 0:
            time.sleep(poll)
