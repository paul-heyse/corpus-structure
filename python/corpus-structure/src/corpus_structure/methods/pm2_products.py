"""Private parser products before the source contribution boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.contributions import (
    contribution_payload_contracts,
    validate_contribution_semantics,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python

if TYPE_CHECKING:
    from corpus_structure.semantic.types import PreparedRelease

    from .pm2_source import MappedSource, SourceMapRefused


PARSER_QUESTIONS = {
    "hanlp": "pm2.hanlp.frames",
    "maverick": "pm2.maverick.coreference",
    "dipo": "pm2.dipo.discourse",
}

PARSER_PROVIDER = {
    "linguistic.predicate_frame": "hanlp",
    "linguistic.qualifier_cue": "hanlp",
    "linguistic.constituent": "hanlp",
    "maverick.mention": "maverick",
    "maverick.cluster": "maverick",
    "dipo.edu": "dipo",
    "dipo.tree": "dipo",
}


def validate_parser_input(
    prepared: PreparedRelease,
    row: Mapping[str, Any],
    *,
    payload_contracts: Mapping[str, str] | None = None,
) -> None:
    """Require the consuming release's payload contract for a retained parser input."""
    provider = PARSER_PROVIDER.get(row["semantic_type"])
    if provider is not None:
        validate_contribution_semantics(
            prepared,
            row,
            question=PARSER_QUESTIONS[provider],
            payload_contracts=(
                payload_contracts
                if payload_contracts is not None
                else contribution_payload_contracts(prepared.definitions)
            ),
        )


class ProductView(BaseModel):
    """A typed consumer projection of an already validated or archived parser value."""

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")


class ParserView(ProductView):
    location_keys: tuple[str, ...] = ()
    unlocated_members: tuple[str, ...] = ()


class ArgumentView(ProductView):
    role: str
    location: str


class SRLView(ProductView):
    predicate: str | None = None
    arguments: tuple[ArgumentView, ...]


class FrameView(ParserView):
    sentence: int | None = None
    predicate: str
    focus: str | None = None
    dependency_arguments: tuple[ArgumentView, ...]
    srl_frames: tuple[SRLView, ...]


class CueView(ParserView):
    kind: str | None = None
    location: str
    marker: str
    candidates: tuple[str, ...]
    attribution_source: str | None = None


class PhraseView(ParserView):
    sentence: int | None = None
    label: str | None = None
    location: str


class MentionView(ParserView):
    first: int
    last: int


class ClusterView(ParserView):
    member_keys: tuple[str, ...] = ()


class EDUView(ParserView):
    arm: str
    edu: int
    location_key: str | None = None


class SplitView(ProductView):
    left: tuple[int, int]
    right: tuple[int, int]
    nuclearity: str
    relation: str


class TreeView(ParserView):
    arm: str
    root: tuple[int, int]
    splits: tuple[SplitView, ...]


type ParserValue = FrameView | CueView | PhraseView | MentionView | ClusterView | EDUView | TreeView

_VIEWS: Mapping[str, type[ParserValue]] = {
    "linguistic.predicate_frame": FrameView,
    "linguistic.qualifier_cue": CueView,
    "linguistic.constituent": PhraseView,
    "maverick.mention": MentionView,
    "maverick.cluster": ClusterView,
    "dipo.edu": EDUView,
    "dipo.tree": TreeView,
}


def parser_view(row: Mapping[str, Any]) -> ParserValue:
    """Read the consumer fields once rather than decoding keys at each join."""
    view = _VIEWS[row["semantic_type"]]
    return view.model_validate_json(canonical_bytes(source_python(row["value"])))


def parser_member_types(value: ParserValue) -> dict[str, str]:
    """Resolve member roles inside the original typed parser population."""
    keys: tuple[str, ...]
    if isinstance(value, FrameView):
        if value.focus is None or any(frame.predicate is None for frame in value.srl_frames):
            raise ValueError("released parser frame lacks its focal member or SRL predicate")
        keys = (
            value.predicate,
            value.focus,
            *(item.location for item in value.dependency_arguments),
            *(
                key
                for frame in value.srl_frames
                for key in (frame.predicate, *(item.location for item in frame.arguments))
                if key is not None
            ),
        )
    elif isinstance(value, CueView):
        return {
            value.location: "source_occurrence",
            value.marker: "source_occurrence",
            **dict.fromkeys(value.candidates, "linguistic.predicate_frame"),
            **(
                {value.attribution_source: "linguistic.predicate_frame"}
                if value.attribution_source
                else {}
            ),
        }
    elif isinstance(value, PhraseView):
        keys = (value.location,)
    elif isinstance(value, MentionView):
        if value.first > value.last or len(value.location_keys) != 1:
            raise ValueError("released Maverick mention lacks its ordered extent")
        keys = value.location_keys
    elif isinstance(value, ClusterView):
        if len(value.member_keys) != len(set(value.member_keys)):
            raise ValueError("released Maverick cluster repeats a mention")
        return dict.fromkeys(value.member_keys, "maverick.mention")
    elif isinstance(value, EDUView):
        if value.location_key is None:
            raise ValueError("released Dipo EDU lacks its extent")
        keys = (value.location_key,)
    else:
        first, end = value.root
        if first != 0 or end != len(value.location_keys):
            raise ValueError("released Dipo tree differs from its leaf population")
        return {f"{value.arm}:edu:{index}": "dipo.edu" for index in range(end)}
    return dict.fromkeys(keys, "source_occurrence")


def released_parser_members(value: ParserValue) -> dict[str, str]:
    """Bind the role order and distinguish located from explicitly unavailable members."""
    references = parser_member_types(value)
    missing = set(value.unlocated_members)
    if (
        tuple(references) != value.location_keys
        or len(missing) != len(value.unlocated_members)
        or not missing <= references.keys()
    ):
        raise ValueError("released parser roles differ from their ordered source members")
    return {key: kind for key, kind in references.items() if key not in missing}


def validate_parser_members(row: Mapping[str, Any], population: Mapping[str, Any]) -> None:
    """Refuse changed, reordered or foreign members in an exact retained closure."""
    members = row.get("members", ())
    expected = released_parser_members(parser_view(row))
    if len(members) != len(expected) or len(set(members)) != len(members):
        raise ValueError("released parser member closure differs from its located roles")
    for (key, semantic_type), identity in zip(expected.items(), members, strict=True):
        member = population.get(identity)
        if (
            member is None
            or member["item_key"] != key
            or member["semantic_type"] != semantic_type
            or member["pin"] != row["pin"]
            or member["operation_key"] != row["operation_key"]
        ):
            raise ValueError("released parser member differs from its original source role")


def parser_value_for_contract(semantic_type: str, value: dict[str, Any]) -> dict[str, Any]:
    """Lower the native adapter's optional values into the versioned release shape."""
    if semantic_type == "linguistic.predicate_frame":

        def arguments(rows):
            return [{key: item for key, item in row.items() if item is not None} for row in rows]

        return {
            **value,
            "dependency_arguments": arguments(value["dependency_arguments"]),
            "srl_frames": [
                {**frame, "arguments": arguments(frame["arguments"])}
                for frame in value["srl_frames"]
            ],
        }
    if semantic_type == "linguistic.qualifier_cue":
        return {key: item for key, item in value.items() if item is not None}
    if semantic_type == "dipo.tree":
        return {
            **value,
            "provider_gaps": [
                {"start": start, "end": end} for start, end in value["provider_gaps"]
            ],
        }
    return value


@dataclass(frozen=True)
class ParserProduct:
    key: str
    semantic_type: str
    value: dict[str, Any]
    members: tuple[str, ...]


@dataclass(frozen=True)
class ParserProducts:
    locations: dict[str, MappedSource | SourceMapRefused]
    products: tuple[ParserProduct, ...]
