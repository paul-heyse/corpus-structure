"""Maintain existing native leases across long operation-owned inference."""
from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from threading import Event, Thread

from sqlalchemy import Engine

from .operation_results import ClaimedTask
from .operations import renew_claim


@contextmanager
def maintained_claims(engine: Engine,claims: Sequence[ClaimedTask],holder: str,*,interval: float=30) -> Generator[Callable[[],None]]:
    """Yield the existing lease authority check to long-running private computation.

    Renewal alone touches PostgreSQL. Polling observes its retained failure immediately,
    allowing the inference owner to stop stale work before terminal publication.
    """
    if interval<=0:
        raise ValueError('claim renewal interval must be positive')
    stop=Event()
    failed=Event()
    failures: list[Exception]=[]
    def check_active()->None:
        if failed.is_set():
            raise failures[0]
    def renew()->None:
        while not stop.wait(interval):
            try:
                with engine.begin() as conn:
                    for claim in claims:
                        renew_claim(conn,task_id=claim.task_id,attempt=claim.attempt,holder=holder)
            except Exception as error:
                failures.append(error)
                failed.set()
                return
    thread=Thread(target=renew,name='corpus-claim-renewal',daemon=True)
    thread.start()
    try:
        yield check_active
        check_active()
    finally:
        stop.set()
        thread.join()
