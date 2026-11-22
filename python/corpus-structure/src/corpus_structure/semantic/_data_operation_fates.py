"""Generated from the authoritative DDO protocol; do not edit."""

from typing import Literal

PROTOCOL_SHA256 = "51b75cbbfd0eadf9b8468df426d8f0d354e3156795684771eb5ef471db4acf75"

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
