"""Generated from the authoritative DDO protocol; do not edit."""

from typing import Literal

PROTOCOL_SHA256 = "c2cf6b37107ae423ab537199f5735d252fe4286a834dac75b4d048cec75b0ffd"

type DataTaskState = Literal["pending", "running", "done", "empty", "failed", "cancelled"]

type RecordableFate = Literal[
    "known-absent",
    "unknown",
    "unavailable",
    "invalid",
    "closed",
    "awaiting-discovery",
    "awaiting-inputs",
    "awaiting-population",
    "not-applicable",
    "failed",
    "cancelled",
    "partial",
]

type HistoricalFate = Literal[
    "known-absent",
    "unknown",
    "unavailable",
    "invalid",
    "closed",
    "awaiting-discovery",
    "awaiting-inputs",
    "awaiting-population",
    "not-applicable",
    "failed",
    "cancelled",
    "partial",
    "attached",
    "fulfilled",
]

type VisibleFate = Literal[
    "known-absent",
    "unknown",
    "unavailable",
    "invalid",
    "closed",
    "awaiting-discovery",
    "awaiting-inputs",
    "awaiting-external",
    "awaiting-population",
    "not-applicable",
    "failed",
    "cancelled",
    "partial",
    "attached",
    "fulfilled",
    "waiting",
]

type RevocationSelectorKind = Literal[
    "derivation", "recipe", "runtime", "product", "original-source", "original-admission"
]
