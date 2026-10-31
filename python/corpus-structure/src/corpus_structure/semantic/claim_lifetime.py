"""Maintain existing native leases across long operation-owned inference."""
from __future__ import annotations

from contextlib import contextmanager
from threading import Event, Thread

from .operations import renew_claim


@contextmanager
def maintained_claims(engine,claims,holder: str,*,interval: float=30):
    stop=Event()
    failures=[]
    def renew():
        while not stop.wait(interval):
            try:
                with engine.begin() as conn:
                    for claim in claims:
                        renew_claim(conn,task_id=claim.task_id,attempt=claim.attempt,holder=holder)
            except Exception as error:
                failures.append(error)
                return
    thread=Thread(target=renew,name='corpus-claim-renewal',daemon=True)
    thread.start()
    try:
        yield
        if failures:
            raise failures[0]
    finally:
        stop.set()
        thread.join()
