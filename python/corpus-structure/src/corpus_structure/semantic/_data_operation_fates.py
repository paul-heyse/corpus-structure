"""Generated from the authoritative DDO protocol; do not edit."""

from typing import Literal

PROTOCOL_SHA256 = "7bca48dbf67540e4d503009459058f8f6ba9dea50b84a6a612c1fafec011b140"

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
