"""Declared original-relative record pins and immutable native source frames."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import JsonValue

from .data_operation_model import BoundRoleMember, SubjectContext, json_context_meaning
from .identity import canonical_bytes
from .source_products import FrozenNativeSource

if TYPE_CHECKING:
    from .proposals import ProposalSentence


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


@dataclass(frozen=True, init=False)
class DeclaredNativeFrameSource:
    """Native language frame over an admitted semantic member, never a fake view row."""

    source_content: str
    pin_content: str
    version: int = 4
    _text: str = field(init=False, repr=False, compare=False)
    _coordinate: tuple[str, str, str] = field(init=False, repr=False, compare=False)
    _acquired_source: ClassVar[FrozenNativeSource]
    _columns: ClassVar[Any]

    def __init__(self, *args, **kwargs):
        raise TypeError("declared native frames require an acquired or verified retained source")

    def __post_init__(self):
        value = self._acquired_source.value
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
        from .native_source_view import freeze_native

        columns = freeze_native(
            {
                "items": native_language_items(value["items"]),
                "pieces": value["pieces"],
                "ancestors": native_language_items(value.get("ancestors", ())),
                "health": {"formula_outcomes": value.get("recognition", ())},
            }
        )
        object.__setattr__(self, "_columns", columns)

    @property
    def record(self) -> dict[str, JsonValue]:
        return {
            "source_content": self.source_content,
            "pin_content": self.pin_content,
            "version": self.version,
        }

    @classmethod
    def acquire(cls, prepared, value, member, *, project):
        source = FrozenNativeSource.acquire(prepared, value)
        address = DeclaredRecordSource.from_bound(source, member, project=project)
        return cls.from_source(source, canonical_bytes(address.pin()).decode())

    @classmethod
    def from_source(cls, source, pin_content):
        """Bind an acquired source payload to this occurrence's exact declared pin."""
        return cls._from_acquired(source, pin_content)

    @classmethod
    def from_retained_record(cls, source_content: str, pin_content: str, version: int = 4):
        """Re-establish projection facts at an authorized retained-read boundary."""
        source = FrozenNativeSource._accept_retained_projection(source_content.encode())
        return cls._from_acquired(source, pin_content, version)

    @classmethod
    def acquire_record(cls, prepared, source_content: str, pin_content: str, version: int = 4):
        """Validate a detached record under its caller's acquired source declaration."""
        from .data_operation_json import wire_json_loads

        source = FrozenNativeSource.acquire(prepared, wire_json_loads(source_content))
        return cls._from_acquired(source, pin_content, version)

    @classmethod
    def _from_worker_record(
        cls, source_content: str, pin_content: str, version: int = 4, *, source=None
    ):
        """Use source bytes from an already authenticated, parent-validated worker packet."""
        content = source_content.encode()
        if source is None:
            source = FrozenNativeSource._accept_parent_validated(content)
        elif source.content != content:
            raise ValueError("worker frame differs from the sealed source carrier")
        return cls._from_acquired(source, pin_content, version)

    @classmethod
    def _from_acquired(cls, source, pin_content, version=4, *, state=()):
        FrozenNativeSource._require_acquired(source)
        result = object.__new__(cls)
        object.__setattr__(result, "source_content", source.content.decode())
        object.__setattr__(result, "pin_content", pin_content)
        object.__setattr__(result, "version", version)
        object.__setattr__(result, "_acquired_source", source)
        for name, value in state:
            object.__setattr__(result, name, value)
        result.__post_init__()
        return result

    @property
    def acquired_source(self) -> FrozenNativeSource:
        """Retain the validated source payload behind this exact occurrence frame."""
        FrozenNativeSource._require_acquired(self._acquired_source)
        return self._acquired_source

    @property
    def value(self):
        return self.view.value

    @cached_property
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

    @cached_property
    def native_context(self):
        return canonical_bytes(self._columns).decode()

    @cached_property
    def view(self):
        from .native_source_view import NativeSourceView

        return NativeSourceView.from_acquired(self._acquired_source, self._columns)

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
