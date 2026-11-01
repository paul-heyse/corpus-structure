"""Reader dispatch by recorded payload schema (model and projections §3.6; ADR-0022; DP-24).

A stored payload is read under the schema its row records (`payload_schema_id`), never under current
defaults. `PayloadReaders` is built from the registry's rows (`meta.payload_schema`): `read(id,
payload)` finds the row, upcasts the payload along its class's versions to the newest registered one
(each version's `upcaster` names the step from its parent), and validates it with the reader of
that kind. An id the registry does not hold is refused with `UnknownPayloadSchema`; an upcaster or
kind without code, with `UnknownUpcaster` or `UnknownPayloadKind`. All three are `LookupError`s.

`absent` is the upcast of a `nested-additive` version: the new field is optional, so the older
payload reads as it is, the field absent.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any


class UnknownPayloadSchema(LookupError):
    """A payload's recorded schema id is not in the registry."""

    def __init__(self, payload_schema_id: int) -> None:
        self.payload_schema_id = payload_schema_id
        super().__init__(f"payload schema {payload_schema_id} is not registered")


class UnknownUpcaster(LookupError):
    """A registered version names an upcaster that no code implements."""


class UnknownPayloadKind(LookupError):
    """A registered payload kind has no reader."""


@dataclass(frozen=True)
class PayloadSchemaRow:
    """The columns of a `meta.payload_schema` row that dispatch reads."""

    id: int
    class_: str
    kind: str
    version: int
    parent_id: int | None
    upcaster: str | None


def _absent(payload: Any) -> Any:
    return payload


UPCASTERS: Mapping[str, Callable[[Any], Any]] = {"absent": _absent}


def default_readers() -> dict[str, Callable[[Any], Any]]:
    """The core shapes' validators by payload kind (observation kinds and the operations JSON)."""
    from pydantic import JsonValue, TypeAdapter

    from corpus_structure.core import batch, options, payloads

    out: dict[str, Callable[[Any], Any]] = {
        str(kind): model.model_validate for kind, model in payloads.PAYLOADS.items()
    }
    out |= {
        "task_cost": payloads.Cost.model_validate,
        "policy_action": payloads.PolicyAction.model_validate,
        "intervention_target": payloads.InterventionTarget.model_validate,
        "trigger_metrics": payloads.TRIGGER_METRICS.validate_python,
        "citation_frame": TypeAdapter(batch.CitationFrame).validate_python,
        "golden_batch": payloads.GoldenBatchPayload.model_validate,
        "compiled_artifact": TypeAdapter(JsonValue).validate_python,
        "run_options": options.RunOptions.model_validate,
        "intervention_refs": payloads.InterventionRefs.model_validate,
    }
    return out


class PayloadReaders:
    """Dispatch over registered payload schemas (module doc)."""

    def __init__(
        self,
        rows: Iterable[PayloadSchemaRow],
        readers: Mapping[str, Callable[[Any], Any]] | None = None,
        upcasters: Mapping[str, Callable[[Any], Any]] = UPCASTERS,
    ) -> None:
        self.rows = {row.id: row for row in rows}
        self.readers = default_readers() if readers is None else dict(readers)
        self.upcasters = upcasters
        self._child: dict[int, PayloadSchemaRow] = {}
        for row in self.rows.values():
            if row.parent_id is not None:
                self._child[row.parent_id] = row

    def row(self, payload_schema_id: int) -> PayloadSchemaRow:
        try:
            return self.rows[payload_schema_id]
        except KeyError:
            raise UnknownPayloadSchema(payload_schema_id) from None

    def upcast(self, payload_schema_id: int, payload: Any) -> tuple[PayloadSchemaRow, Any]:
        """The payload upcast to its class's newest registered version, with that version."""
        row = self.row(payload_schema_id)
        while row.id in self._child:
            row = self._child[row.id]
            name = row.upcaster or ""
            if name not in self.upcasters:
                raise UnknownUpcaster(
                    f"payload schema {row.id} ({row.class_} v{row.version}) "
                    f"names the upcaster {name!r}, which no code implements"
                )
            payload = self.upcasters[name](payload)
        return row, payload

    def read(self, payload_schema_id: int, payload: Any) -> Any:
        """The payload as its kind's shape, read under its recorded schema."""
        row, current = self.upcast(payload_schema_id, payload)
        if row.kind not in self.readers:
            raise UnknownPayloadKind(f"payload kind {row.kind!r} has no reader")
        return self.readers[row.kind](current)
