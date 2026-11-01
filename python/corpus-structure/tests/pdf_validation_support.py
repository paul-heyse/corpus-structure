"""Importable spawn target for the PDF validation child ownership control."""

from pathlib import Path
from time import sleep


def hold_validation(capture, projection, result):
    Path(projection).write_text("running")
    sleep(60)
    result.close()
