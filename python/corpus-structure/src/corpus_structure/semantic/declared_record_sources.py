"""Declared original-relative record pins and their selected schema projection."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .data_operation_model import BoundRoleMember, SubjectContext, json_context_meaning
from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from .source_products import FrozenNativeSource


@dataclass(frozen=True)
class DeclaredRecordSource:
    """Existing coordinate, complete subject context and semantic member selection.

    This introduces no new identity hash and contains no task/run/view-row alias.
    Selected execution/support references remain in the native input binding.
    """

    document: str
    projection: str
    section_pointer: str
    membership: str
    context: SubjectContext
    product: str
    member: str | None
    kind_contract: str

    @classmethod
    def from_bound(cls, source: FrozenNativeSource, member: BoundRoleMember, *, project: str):
        coordinate = source.value["source"]
        if coordinate["document"] != member.original_source:
            raise ValueError("selected native source differs from its bound original document")
        return cls(
            coordinate["document"],
            coordinate["projection"],
            coordinate["section_pointer"],
            coordinate["membership"],
            SubjectContext(project, member.subject, member.original_source, member.analyzed_scope),
            member.product,
            member.member,
            member.kind_contract,
        )

    def pin(self) -> dict[str, Any]:
        return {
            "format": "declared-native-source-v1",
            "source": canonical_bytes([self.product, self.member]).decode(),
            "subject": self.context.subject,
            "document": self.document,
            "projection_digest": self.projection,
            "section_pointer": self.section_pointer,
            "membership": self.membership,
            "project_id": self.context.project_id,
            "original_source": self.context.original_source,
            "analyzed_scope_meaning": json_context_meaning(self.context.analyzed_scope).decode(),
            "source_product": self.product,
            **({"source_member": self.member} if self.member is not None else {}),
            "kind_contract": self.kind_contract,
        }


def declared_record_inputs(bundle: SourceBundle) -> SourceBundle:
    """Project the existing record model at the selected declared-source boundary.

    Legacy/default and frozen observation artifacts retain their exact pin contract.
    A target release receives a different pin shape and consequently a different
    kind contract. No caller edits a parallel record schema or weakens old fields.
    """
    canonical = (Path(__file__).parents[1] / "model/semantic/observations.yaml").read_bytes()
    supplied = next(
        (item.content for item in bundle.sources if item.name == "observations"), canonical
    )
    from .observations import observation_inputs

    module = yaml.safe_load(supplied)
    prior = module["classes"]["RecordSourcePin"]["attributes"]
    canonical_attributes = yaml.safe_load(canonical)["classes"]["RecordSourcePin"]["attributes"]
    module["classes"]["RecordSourcePin"]["description"] = (
        "Declared semantic source/member and original-relative coordinates with complete context; "
        "task, run and source-view row identities are not source meaning."
    )
    module["classes"]["RecordSourcePin"]["attributes"] = {
        name: {"range": "string", **({"required": True} if name != "source_member" else {})}
        for name in (
            "source",
            "subject",
            "document",
            "projection_digest",
            "section_pointer",
            "membership",
            "project_id",
            "original_source",
            "analyzed_scope_meaning",
            "source_product",
            "source_member",
            "kind_contract",
        )
    }
    module["classes"]["RecordSourcePin"]["attributes"]["format"] = {
        "range": "string",
        "required": True,
        "equals_string": "declared-native-source-v1",
    }
    module["classes"]["RecordSourcePin"]["attributes"]["projection_digest"]["pattern"] = (
        "^[0-9a-f]{64}$"
    )
    if prior not in (canonical_attributes, module["classes"]["RecordSourcePin"]["attributes"]):
        raise ValueError("declared record projection refuses an independently changed source pin")
    content = yaml.safe_dump(module, sort_keys=True).encode()
    names = {item.name for item in bundle.sources}
    if "observations" in names:
        sources = tuple(
            SourceArtifact(item.name, content) if item.name == "observations" else item
            for item in bundle.sources
        )
        return SourceBundle(bundle.root, sources)
    return observation_inputs(bundle, model_content=content)


@dataclass(frozen=True)
class DeclaredSourcePin:
    content: str

    @property
    def source_key(self):
        return self.values()["source"]

    @property
    def original_key(self):
        return self.values()["original_source"]

    @property
    def section_pointer(self):
        return self.values()["section_pointer"]

    @property
    def membership(self):
        return self.values()["membership"]

    def values(self):
        import json

        return json.loads(self.content)


@dataclass(frozen=True)
class DeclaredSourceSlice:
    source: str
    start: int
    end: int
    coordinate_space: str = "native_projection"
    precision: str = "exact"

    def __post_init__(self):
        if (
            not self.source
            or type(self.start) is not int
            or type(self.end) is not int
            or not 0 <= self.start < self.end
            or self.coordinate_space != "native_projection"
            or self.precision != "exact"
        ):
            raise ValueError(
                "declared source slice requires an exact original-relative address and extent"
            )

    @property
    def source_key(self):
        return self.source


def native_language_items(items):
    """Present exact typed pointer columns to the existing native language kernel.

    Reference values retain their original-relative pointers. This reversible wire
    projection introduces no source, task or view identity.
    """
    import json

    result = json.loads(canonical_bytes(items))
    for item in result:
        if isinstance(item.get("parent"), str):
            item["parent"] = {"$ref": item["parent"]}
        for relation in ("children", "captions", "footnotes", "references"):
            if relation in item:
                item[relation] = [{"$ref": pointer} for pointer in item[relation]]
        for cell in item.get("data", {}).get("table_cells", ()):
            if isinstance(cell.get("ref"), str):
                cell["ref"] = {"$ref": cell["ref"]}
    return result


@dataclass(frozen=True)
class DeclaredNativeFrameSource:
    """Native language frame over an admitted semantic member, never a fake view row."""

    source_content: str
    pin_content: str
    version: int = 4
    _text: str = field(init=False, repr=False, compare=False)
    _context: str = field(init=False, repr=False, compare=False)
    _coordinate: tuple[str, str, str] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        value = self.value
        coordinate = value["source"]
        pin = self.pin.values()
        if (
            self.version != 4
            or pin.get("format") != "declared-native-source-v1"
            or any(
                pin.get(field) != coordinate[source_field]
                for field, source_field in (
                    ("document", "document"),
                    ("projection_digest", "projection"),
                    ("section_pointer", "section_pointer"),
                    ("membership", "membership"),
                )
            )
        ):
            raise ValueError("declared frame pin differs from its exact native coordinate")
        object.__setattr__(self, "_text", value["text"])
        object.__setattr__(
            self,
            "_coordinate",
            (coordinate["section_pointer"], coordinate["membership"], coordinate["projection"]),
        )
        object.__setattr__(
            self,
            "_context",
            canonical_bytes(
                {
                    "items": native_language_items(value["items"]),
                    "pieces": value["pieces"],
                    "ancestors": native_language_items(value.get("ancestors", [])),
                    "health": {"formula_outcomes": value.get("recognition", [])},
                }
            ).decode(),
        )

    @property
    def record(self):
        return {
            "source_content": self.source_content,
            "pin_content": self.pin_content,
            "version": self.version,
        }

    @classmethod
    def acquire(cls, prepared, value, member, *, project):
        from .source_products import FrozenNativeSource

        source = FrozenNativeSource.acquire(prepared, value)
        address = DeclaredRecordSource.from_bound(source, member, project=project)
        return cls(source.content.decode(), canonical_bytes(address.pin()).decode())

    @property
    def value(self):
        import json

        return json.loads(self.source_content)

    @property
    def pin(self):
        return DeclaredSourcePin(self.pin_content)

    @property
    def source_key(self):
        return self.pin.source_key

    @property
    def unit_ref(self):
        return self.source_key

    @property
    def original_key(self):
        return self.pin.original_key

    @property
    def text(self):
        return self._text

    @property
    def sentences(self):
        return ()

    @property
    def section_pointer(self):
        return self._coordinate[0]

    @property
    def membership(self):
        return self._coordinate[1]

    @property
    def projection_digest(self):
        return self._coordinate[2]

    @property
    def native_context(self):
        return self._context

    @cached_property
    def _native_columns(self):
        import json

        return json.loads(self._context)

    @property
    def pieces(self):
        """Owned native column tuples; caller edits cannot change source custody."""
        return tuple(deepcopy(self._native_columns["pieces"]))

    @property
    def items(self):
        return tuple(deepcopy(self._native_columns["items"]))

    @property
    def ancestors(self):
        return tuple(deepcopy(self._native_columns["ancestors"]))
