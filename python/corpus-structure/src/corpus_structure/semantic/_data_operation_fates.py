"""Generated from the authoritative DDO protocol; do not edit."""

from typing import Literal

PROTOCOL_SHA256 = "e7a7f838ca5589cc22301ba3890ad4f7fa6eea1a4291b656c3a19a0db7b6badb"

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
