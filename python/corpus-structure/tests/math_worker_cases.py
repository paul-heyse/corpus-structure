"""Importable subprocess targets for the math worker lifecycle controls."""

import multiprocessing
import os
import time


def probe(page: str) -> tuple[str, int, str]:
    if page == "hang":
        time.sleep(60)
    if page == "error":
        raise ValueError("deliberate page error")
    if page == "exit":
        os._exit(23)
    if page == "interrupt":
        raise KeyboardInterrupt("deliberate interruption")
    return page, os.getpid(), multiprocessing.get_start_method()


def reading_positions(readings):
    """Observe every nested token field after a parent-to-worker handoff."""
    from lark import Token

    return [
        [
            (t.type, str(t), t.start_pos, t.line, t.column, t.end_line, t.end_column, t.end_pos)
            for t in reading.result.tree.scan_values(lambda value: isinstance(value, Token))
            if isinstance(t, Token)
        ]
        if reading.result.tree is not None else []
        for reading in readings
    ]
