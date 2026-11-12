"""Physical characterization capacity, independent of semantic demand and identity."""

from dataclasses import asdict, dataclass
from typing import Annotated, ClassVar

from pydantic import ConfigDict, Field

_PositiveInt = Annotated[int, Field(strict=True, ge=1)]


@dataclass(frozen=True)
class CharacterizationExecutionPolicy:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    workers: _PositiveInt = 2
    max_submissions: _PositiveInt = 2
    max_regions: _PositiveInt = 2
    max_active_stage_runs: _PositiveInt = 2
    max_claims: _PositiveInt = 4
    provider_threads: _PositiveInt = 4
    provider_interop_threads: _PositiveInt = 1
    cpu_native_threads: _PositiveInt = 1
    max_provider_jobs: _PositiveInt = 2
    max_owned_bytes: _PositiveInt = 2 * 1024**3
    max_packet_bytes: _PositiveInt = 256 * 1024**2
    max_reply_bytes: _PositiveInt = 64 * 1024**2
    max_native_request_bytes: _PositiveInt = 8 * 1024**2
    max_native_reply_bytes: _PositiveInt = 8 * 1024**2

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in asdict(self).values()):
            raise ValueError("execution policy requires positive finite integer bounds")
        if self.max_packet_bytes + self.max_reply_bytes > self.max_owned_bytes:
            raise ValueError("CPU transfer bounds exceed combined owned-state capacity")
        if self.max_native_request_bytes + self.max_native_reply_bytes > self.max_owned_bytes:
            raise ValueError("native transfer bounds exceed combined owned-state capacity")
