"""Importable spawn target for the PDF validation child ownership control."""

import os
from pathlib import Path
from time import sleep


def hold_validation(capture, projection, result):
    Path(projection).write_text("running")
    sleep(60)
    result.close()


def acknowledge_then_exit_nonzero(capture, projection, result):
    Path(projection).write_text(str(os.getpid()))
    result.send((True, None))
    result.close()
    os._exit(17)


def acknowledge_then_hold(capture, projection, result):
    result.send((True, None))
    result.close()
    # This marker cannot be observed before the acknowledgement was sent.
    Path(projection).write_text(str(os.getpid()))
    sleep(60)
