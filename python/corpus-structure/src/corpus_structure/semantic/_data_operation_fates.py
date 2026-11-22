"""Generated from the authoritative DDO protocol; do not edit."""

from typing import Literal

PROTOCOL_SHA256 = "d2caa75b2be79dd25aa69e660057d273f3e198841921eaff783c43ac7c9835ed"

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
