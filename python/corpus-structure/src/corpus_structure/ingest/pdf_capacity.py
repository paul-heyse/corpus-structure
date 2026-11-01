"""Finite GPU handoff with the dedicated local Nemotron service, without process ownership."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from urllib.parse import urlsplit

import httpx


@contextmanager
def native_before_nemotron(
    endpoint: str,
    *,
    model: str = "nemotron-parse",
    timeout_seconds: float = 30.0,
    check_active: Callable[[], None] | None = None,
) -> Iterator[None]:
    """Level-one sleep releases weights/KV; restore on success, error or cancellation.

    This endpoint is dedicated to this source operation. vLLM must be launched with
    --enable-sleep-mode and VLLM_SERVER_DEV_MODE=1. No unrelated service is stopped,
    launched or reconfigured. The enclosing method closes its native child before exit.
    """
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.path.rstrip("/") != "/v1"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("GPU handoff requires the dedicated local Nemotron /v1 endpoint")
    if not 0 < timeout_seconds <= 60:
        raise ValueError("GPU handoff timeout must be positive and at most sixty seconds")
    base = endpoint.rstrip("/")[:-3]
    primary: BaseException | None = None
    requested = False
    with httpx.Client(timeout=timeout_seconds) as client:
        if check_active is not None:
            check_active()
        try:
            reply = client.get(base + "/v1/models")
            reply.raise_for_status()
            models = reply.json().get("data", [])
            if len(models) != 1 or models[0].get("id") != model:
                raise ValueError("GPU handoff endpoint does not serve the dedicated Nemotron model")
            requested = True
            reply = client.post(base + "/sleep", params={"level": 1, "mode": "wait"})
            reply.raise_for_status()
            reply = client.get(base + "/is_sleeping")
            reply.raise_for_status()
            if reply.json().get("is_sleeping") is not True:
                raise RuntimeError("Nemotron did not acknowledge GPU release")
            if check_active is not None:
                check_active()
            yield
        except BaseException as error:
            primary = error
            if isinstance(error, httpx.HTTPError):
                error.add_note(
                    "Dedicated vLLM needs --enable-sleep-mode and VLLM_SERVER_DEV_MODE=1; "
                    "the Standard phase cannot overlap its reserved GPU memory."
                )
            raise
        finally:
            if requested:
                try:
                    reply = client.post(base + "/wake_up")
                    reply.raise_for_status()
                    reply = client.get(base + "/is_sleeping")
                    reply.raise_for_status()
                    if reply.json().get("is_sleeping") is not False:
                        raise RuntimeError("Nemotron did not acknowledge GPU restoration")
                except BaseException as cleanup:
                    if primary is None:
                        raise
                    primary.add_note("Nemotron GPU restoration failed: " + str(cleanup)[:1800])
