"""Immutable actual physical CPU execution evidence, independent of runtime setup."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from pydantic import ConfigDict, Field

from .identity import canonical_bytes


@dataclass(frozen=True)
class CPUExecutionReceipt:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)

    request_digest: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
    pid: Annotated[int, Field(strict=True, ge=1)]
    main_thread: Annotated[bool, Field(strict=True)]
    native_thread_limit: Annotated[int, Field(strict=True, ge=1)] | None
    native_pools_json: Annotated[bytes, Field(strict=True, min_length=2)]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.request_digest):
            raise ValueError("CPU execution receipt requires its actual request digest")
        if type(self.pid) is not int or self.pid < 1 or type(self.main_thread) is not bool:
            raise TypeError("CPU execution receipt requires actual process/thread facts")
        if self.native_thread_limit is not None and (
            type(self.native_thread_limit) is not int or self.native_thread_limit < 1
        ):
            raise ValueError("CPU execution receipt requires its actual native thread limit")
        if type(self.native_pools_json) is not bytes:
            raise TypeError("CPU native-pool diagnostics require owned immutable JSON bytes")
        pools = json.loads(self.native_pools_json)
        if not isinstance(pools, list) or any(not isinstance(pool, dict) for pool in pools):
            raise ValueError("CPU native-pool diagnostics require an actual report array")
        if canonical_bytes(pools) != self.native_pools_json:
            raise ValueError("CPU native-pool diagnostics must retain canonical actual JSON")

    def record(self) -> dict[str, Any]:
        """JSON-text field matches TypeAdapter's bytes wire schema exactly."""
        return dict(
            request_digest=self.request_digest,
            pid=self.pid,
            main_thread=self.main_thread,
            native_thread_limit=self.native_thread_limit,
            native_pools_json=self.native_pools_json.decode("utf-8"),
        )

    def native_pools(self) -> tuple[dict[str, Any], ...]:
        """Fresh diagnostic views cannot mutate the retained receipt."""
        return tuple(json.loads(self.native_pools_json))
