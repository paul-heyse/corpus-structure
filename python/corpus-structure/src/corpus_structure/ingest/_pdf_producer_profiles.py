"""Generated from the PDF staging producer declarations."""

from typing import Any, Literal, TypedDict

DEMAND_PREPARATION = "pdf-prepared-native-runtime-v2"
STANDARD_PREPARATION = "pdf-prepared-native-runtime-v3"
DEMAND_LOWERING = "pdf-record-lowering-contract-v2"
STANDARD_LOWERING = "pdf-record-lowering-contract-v3"
STANDARD_SCOPE = "docling-standard-pdf-stream-v1"
STANDARD_CONTRACT_FIELD = "producer_contract"
PREPARATION_FIELDS = {
    "pdf-prepared-native-runtime-v2": (
        "profile",
        "requested_options",
        "effective_options",
        "backend_options",
        "stage_scope",
        "native_variants",
        "initialized_bindings",
        "packages",
        "image_ownership",
    ),
    "pdf-prepared-native-runtime-v3": (
        "producer_contract",
        "profile",
        "requested_options",
        "effective_options",
        "backend_options",
        "stage_scope",
        "native_variants",
        "initialized_bindings",
        "packages",
        "image_ownership",
    ),
}


class DemandPreparationIdentity(TypedDict):
    profile: Literal["pdf-prepared-native-runtime-v2"]
    requested_options: dict[str, Any] | None
    effective_options: dict[str, Any] | None
    backend_options: dict[str, Any] | None
    stage_scope: str
    native_variants: dict[str, Any] | None
    initialized_bindings: dict[str, Any] | None
    packages: dict[str, Any] | None
    image_ownership: dict[str, Any] | None


class StandardPreparationIdentity(TypedDict):
    producer_contract: str
    profile: Literal["pdf-prepared-native-runtime-v3"]
    requested_options: dict[str, Any] | None
    effective_options: dict[str, Any] | None
    backend_options: dict[str, Any] | None
    stage_scope: str
    native_variants: dict[str, Any] | None
    initialized_bindings: dict[str, Any] | None
    packages: dict[str, Any] | None
    image_ownership: dict[str, Any] | None
