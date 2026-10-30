"""The payload-schema registry content (model and projections §3.6; ADR-0022; TM §9).

`payload_schema_entries(model, log)` is what `meta.payload_schema` gains for the model revision: per
payload class (`ci:payload`), its current version with the JSON Schema `$id`, the Arrow schema
bytes, the `sql_visible` paths, the compatibility class and upcaster from its parent version, and
the reason and authorizing circumstance. S1b's `ensure` writes the rows, resolving
`model_revision_id` and `parent_id`; readers dispatch on the row id (`core/payload_schemas.py`).

**Versions** come from the revision log: a class is at version 1 at the log's root (`initial`), and
each later step whose change record changes the class (`nested-additive` or `mapped`) adds a version
with that change's class, upcaster, reason and authorization. Only the current version's content is
computed; `payload_schema_versions` also loads immutable prior artifacts for fresh databases,
so every version is registered with the bytes and model revision that originally defined it.

A payload class's JSON Schema is the committed core schema of its kind: `payload.<kind>` for an
observation kind, else the kind's own name (`cost` for `task_cost`). A class without one has no
entry until it has one (`without_schema` names them).

Historical installed-model database registration and reconstruction live only in test support.
Current runtime persistence uses immutable semantic releases and protected native operations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from corpus_structure.core import schemas
from corpus_structure.core.vocab import CompatibilityClass, ObservationKind
from corpus_structure.schema.change import ChangeRecord, payload_classes_changed
from corpus_structure.schema.interchange import compile_interchange
from corpus_structure.schema.model import Model, ci_annotations, read_log, revision


class RegistrationError(RuntimeError):
    """A recorded payload artifact cannot be interpreted under its declared identity."""


SCHEMA_NAMES: Mapping[str, str] = {"task_cost": "cost"}
VERSIONED = frozenset({CompatibilityClass.NESTED_ADDITIVE, CompatibilityClass.MAPPED})


@dataclass(frozen=True)
class PayloadSchemaEntry:
    """One `meta.payload_schema` row's content (its ids resolved by the writer)."""

    class_: str
    kind: str
    version: int
    parent_version: int | None
    compatibility_class: CompatibilityClass
    json_schema_id: str
    arrow_schema: bytes
    sql_visible_paths: tuple[str, ...]
    upcaster: str | None
    reason: str
    authorized_by: str

    def row(self) -> dict[str, Any]:
        """The row's columns, `model_revision_id` and `parent_id` left to the writer."""
        return {
            "class": self.class_,
            "kind": self.kind,
            "version": self.version,
            "compatibility_class": self.compatibility_class.value,
            "json_schema_id": self.json_schema_id,
            "arrow_schema": self.arrow_schema,
            "sql_visible_paths": list(self.sql_visible_paths),
            "upcaster": self.upcaster,
            "reason": self.reason,
            "authorized_by": self.authorized_by,
        }


def schema_name(kind: str) -> str:
    """The committed core JSON Schema of a payload kind."""
    if kind in set(ObservationKind):
        return f"payload.{kind}"
    return SCHEMA_NAMES.get(kind, kind)


def payload_schema_entries(
    model: Model, log: Sequence[Mapping[str, Any]] | None = None
) -> list[PayloadSchemaEntry]:
    """Every payload class's versions up to the model revision (module doc)."""
    log = read_log() if log is None else log
    current = revision(model)
    projections = compile_interchange(model)
    committed = set(schemas.SCHEMAS())
    history: dict[str, list[tuple[CompatibilityClass, str | None, str, str]]] = {}
    for entry in log[1:]:
        record = ChangeRecord.model_validate(entry["change_record"])
        touched: dict[str, Any] = {}
        for cls, change in payload_classes_changed(record, model):
            if change.compatibility_class in VERSIONED:
                touched.setdefault(cls, change)
        for cls, change in touched.items():
            history.setdefault(cls, []).append(
                (change.compatibility_class, change.upcaster, change.reason, change.authorized_by)
            )
    out = []
    for name, element in model.system.schema.classes.items():
        kind = ci_annotations(element).get("ci:payload")
        if kind is None or schema_name(str(kind)) not in committed:
            continue
        cls = f"sys:{name}"
        visible = tuple(str(ci_annotations(element).get("ci:sql_visible", "")).split())
        arrow = projections.payloads[cls].serialize().to_pybytes()
        json_id = schemas.schema_id(schema_name(str(kind)), current.content_hash)
        steps = [
            (
                CompatibilityClass.INITIAL,
                None,
                "initial version",
                f"model_revision:{current.label}",
            ),
            *history.get(cls, []),
        ]
        version = len(steps)
        klass, upcaster, reason, authorized_by = steps[-1]
        out.append(
            PayloadSchemaEntry(
                cls,
                str(kind),
                version,
                None if version == 1 else version - 1,
                klass,
                json_id,
                arrow,
                visible,
                upcaster,
                reason,
                authorized_by,
            )
        )
    return out


def _archived_payload(entry: PayloadSchemaEntry, version: int) -> PayloadSchemaEntry:
    import base64
    import json

    path = schemas.DIRECTORY / "history" / f"{entry.kind}.v{version}.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    data = body["entry"]
    if data["class_"] != entry.class_ or data["version"] != version:
        raise RegistrationError(f"{path}: historical payload identity differs")
    if body["json_schema"]["$id"] != data["json_schema_id"]:
        raise RegistrationError(f"{path}: historical JSON Schema identity differs")
    return PayloadSchemaEntry(
        class_=data["class_"],
        kind=data["kind"],
        version=data["version"],
        parent_version=data["parent_version"],
        compatibility_class=CompatibilityClass(data["compatibility_class"]),
        json_schema_id=data["json_schema_id"],
        arrow_schema=base64.b64decode(data["arrow_schema"]),
        sql_visible_paths=tuple(data["sql_visible_paths"]),
        upcaster=data["upcaster"],
        reason=data["reason"],
        authorized_by=data["authorized_by"],
    )


def payload_schema_versions(model: Model) -> list[PayloadSchemaEntry]:
    """All required versions, retaining each version's original bytes and defining revision."""
    out = []
    for entry in payload_schema_entries(model):
        for version in range(1, entry.version):
            out.append(_archived_payload(entry, version))
        archive = schemas.DIRECTORY / "history" / f"{entry.kind}.v{entry.version}.json"
        out.append(_archived_payload(entry, entry.version) if archive.exists() else entry)
    return out


def without_schema(model: Model) -> list[str]:
    """Payload kinds with no committed JSON Schema, which the registry cannot register yet."""
    committed = set(schemas.SCHEMAS())
    kinds = [
        str(ci_annotations(e).get("ci:payload"))
        for e in model.system.schema.classes.values()
        if ci_annotations(e).get("ci:payload")
    ]
    return sorted(k for k in kinds if schema_name(k) not in committed)


# --- Registration --------------------------------------------------------------------------------
