"""Declared original-relative record pins and immutable native source frames."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any

from pydantic import JsonValue

from .data_operation_model import BoundRoleMember, SubjectContext, json_context_meaning
from .identity import canonical_bytes

if TYPE_CHECKING:
    from .proposals import ProposalSentence
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
            SubjectContext(
                project,
                member.subject,
                member.original_source,
                member.analyzed_scope,
                subject_definition=member.subject_definition,
            ),
            member.product,
            member.member,
            member.kind_contract,
        )

    def pin(self) -> dict[str, Any]:
        return {
            "format": "declared-native-source-v1",
            "source": canonical_bytes([self.product, self.member]).decode(),
            "subject": self.context.subject,
            "subject_definition": self.context.subject_definition,
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
        value = self._source_value
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
    def record(self) -> dict[str, JsonValue]:
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

    @cached_property
    def _source_value(self):
        import json

        return json.loads(self.source_content)

    @property
    def value(self) -> dict[str, Any]:
        from .native_source_view import thaw_native

        return thaw_native(self.view.value)

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
    def sentences(self) -> tuple[ProposalSentence, ...]:
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
    def view(self):
        import json

        from .native_source_view import NativeSourceView

        return NativeSourceView(self._source_value, json.loads(self._context))

    @property
    def pieces(self):
        """Owned native column tuples; caller edits cannot change source custody."""
        return self.view.pieces

    @property
    def items(self):
        return self.view.items

    @property
    def ancestors(self):
        return self.view.ancestors

    @cached_property
    def prepared_source(self):
        """Invocation-owned context preparation shared by this frame's block scopes."""
        from .source_contexts import PreparedNativeSource

        return PreparedNativeSource(self)

    @cached_property
    def selected_ranges(self):
        """Exact inspectable original extents from this member's own frozen selectors."""
        from .source_products import selected_source_ranges

        value = self.value
        return selected_source_ranges(value, value["selectors"])

    def contains_span(self, start, end):
        return any(a <= start < end <= b for a, b in self.selected_ranges)

    @property
    def inspectable_pieces(self):
        """Whole selected native pieces; clipped atoms remain unsupported, not empty."""
        return tuple(
            piece for piece in self.pieces if self.contains_span(piece["start"], piece["end"])
        )
