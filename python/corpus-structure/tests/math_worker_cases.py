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
