"""Controlled native children: no model provider claim."""

import os
import time

from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.methods.gliner_worker import _Reply


def controlled_child(connection, profile):
    try:
        while (request := connection.recv()) is not None:
            mode = request.inputs[0].text
            if mode == "crash":
                os._exit(7)
            if mode == "hang":
                time.sleep(60)
            if mode == "error":
                connection.send(_Reply(request.serial, error="controlled inference failure"))
                return
            reports = tuple(
                GlinerReport(
                    item.context_id,
                    item.context_digest,
                    "computation",
                    profile.fingerprint,
                    request.pack.fingerprint,
                    GlinerPreparation(item.text, "", 1, 2, len(item.text.encode())),
                    "{}",
                    "{}",
                    0.01,
                    False,
                )
                for item in request.inputs
            )
            if mode == "oversized-preparation":
                from dataclasses import replace

                reports = (
                    replace(reports[0], preparation=GlinerPreparation("x" * 10000, "", 1, 2, 1)),
                )
            elif mode == "oversized-metadata":
                from dataclasses import replace

                reports = (replace(reports[0], context_id="x" * 10000),)
            connection.send(_Reply(request.serial + (mode == "stale"), reports=reports))
    finally:
        connection.close()
