"""Released bounded model questions, exact evidence and private linguistic proposals.

The existing native workers supply typed answers. This owner binds their meanings to
the archived question declaration and retained source/candidate population. It does not
turn span reads into a complete logical form or grant provider scores admission authority.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, cast

from corpus_structure.methods.gliner import (
    GlinerInput,
    GlinerPack,
)
from corpus_structure.methods.native_evidence_layers import (
    digest,
)
from corpus_structure.methods.pm2_interpretation_products import (
    render_candidate_options,
)
from corpus_structure.methods.pm2_source import (
    PM2SourceMap,
    SourceMapSegment,
)
from corpus_structure.semantic.characterization import LayerReport
from corpus_structure.semantic.data_product_reference import (
    DataProductMemberReference,
    DataProductReference,
    member_reference,
    read_member_reference,
)
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    CHARACTERIZATION_FAMILIES,
    QuestionFamily,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    record_source_pin,
    source_slice,
)
from corpus_structure.semantic.source_views import PreparedSourceView

D1_SOURCE_FAMILIES = CHARACTERIZATION_FAMILIES[:4]
CANDIDATE_FAMILIES = CHARACTERIZATION_FAMILIES[4:6]
GLINER_CUES, GLINER_FUNCTIONS = CHARACTERIZATION_FAMILIES[6:]


def question_manifest(prepared) -> dict[str, str]:
    """Freeze the actual released wording, stages, choices and native read contracts."""
    from corpus_structure.semantic.interpretation_questions import declared_families

    families = declared_families(prepared.registry_rows)
    if not set(CHARACTERIZATION_FAMILIES) <= families.keys():
        raise ValueError("release lacks the complete baseline characterization question inventory")
    return {name: families[name].digest for name in CHARACTERIZATION_FAMILIES}


@dataclass(frozen=True, slots=True)
class ModelScope:
    view: PreparedSourceView | DeclaredNativeFrameSource
    focal: tuple[int, int]
    examined: tuple[int, int]
    mapping: PM2SourceMap

    @property
    def identity(self) -> str:
        return digest(
            dict(
                source=(
                    self.view.pin.values()
                    if isinstance(self.view, DeclaredNativeFrameSource)
                    else self.view.ref.native_product.values()
                ),
                projection=_projection(self.view),
                focal=self.focal,
                examined=self.examined,
                source_map=self.mapping.input_digest,
            )
        )


def prepare_model_scope(
    view: PreparedSourceView | DeclaredNativeFrameSource,
    focal: tuple[int, int],
    examined: tuple[int, int],
    *,
    max_chars: int = 65536,
) -> ModelScope:
    """Prepare exact source context without tokenization, candidate discovery or inference."""
    a, b = examined
    if not 0 <= a <= focal[0] < focal[1] <= b <= len(view.text):
        raise ValueError("model focal scope must lie inside its declared examined context")
    source = view if isinstance(view, DeclaredNativeFrameSource) else native_source_frame(view, ())
    preparation = PreparedNativeSources((source,))
    context = NativeSourceContext(
        source,
        (),
        (source_slice(source, a, b),),
        "source-language characterization",
        "exact-focal-and-declared-source-context-v1",
        "explicit retained source context",
        max_chars=max_chars,
        version=2,
        preparation=preparation,
    )
    formulas = {
        item["self_ref"] for item in _source_rows(view, "items") if item.get("label") == "formula"
    }
    atoms = tuple(
        (piece["start"] - a, piece["end"] - a)
        for piece in _source_rows(view, "pieces")
        if piece.get("item_ref") in formulas and piece["start"] < b and a < piece["end"]
    )
    if any(start < 0 or end > b - a for start, end in atoms):
        raise ValueError("model context cuts a source-owned protected atom")
    mapping = PM2SourceMap(
        context, context.text, (SourceMapSegment(0, len(context.text), 0),), atoms
    )
    return ModelScope(view, focal, examined, mapping)


def _projection(view):
    return (
        view.projection_digest
        if isinstance(view, DeclaredNativeFrameSource)
        else view.ref.projection_digest
    )


def _source_rows(view, name):
    return (
        view.value.get(name, ())
        if isinstance(view, DeclaredNativeFrameSource)
        else getattr(view, name)
    )


def _related_member(reference, local_id):
    selected = read_member_reference(reference)
    product = (
        selected.product if isinstance(selected, DataProductMemberReference) else selected.layer
    )
    return member_reference(product, local_id).values()


@dataclass(frozen=True)
class DeclaredModelDependency:
    reference: DataProductReference
    payload: dict


type ModelDependencies = (
    Mapping[ProductReference, LayerReport] | Mapping[DataProductReference, DeclaredModelDependency]
)


def declared_model_dependencies(products, source):
    """Project selected current semantic inventories without manufacturing legacy refs."""
    dependencies = {}
    for product in products:
        body = json.loads(product.content)
        if (
            body["source"] != source.value["source"]
            or body["selectors"] != source.value["selectors"]
        ):
            raise ValueError("model dependency belongs to another original source projection")
        reference = DataProductReference(product.semantic_id)
        if reference in dependencies:
            raise ValueError("model dependency repeats a selected semantic product")
        dependencies[reference] = DeclaredModelDependency(
            reference,
            {
                **product.inventory(),
                "source": body["source"],
                "coverage": body["coverage"],
            },
        )
    return dependencies


def _resolve(
    reference: Mapping[str, Any], dependencies: ModelDependencies
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selected = read_member_reference(reference)
    if isinstance(selected, DataProductMemberReference):
        pin, local_id = selected.product, selected.member_id
        layer = cast(Mapping[DataProductReference, DeclaredModelDependency], dependencies).get(pin)
        if layer is None or layer.reference != pin:
            raise ValueError("model candidate is outside its exact selected semantic closure")
    else:
        pin, local_id = selected.layer, selected.local_id
        layer = cast(Mapping[ProductReference, LayerReport], dependencies).get(pin)
        if layer is None or layer.reference(pin.task_id) != pin:
            raise ValueError("model candidate is outside the exact retained dependency closure")
    body = layer.payload
    rows = [
        row
        for name in ("annotations", "terms")
        for row in body.get(name, ())
        if row["local_id"] == local_id
    ]
    if len(rows) != 1:
        raise ValueError("model candidate is not one exact retained annotation or term")
    occurrences = {row["local_id"]: row for row in body["occurrences"]}
    return rows[0], [occurrences[key] for key in rows[0].get("occurrences", ())]


@dataclass(frozen=True, slots=True)
class FrozenCandidates:
    content: bytes

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.content)

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


def freeze_candidates(
    family: QuestionFamily,
    scope: ModelScope,
    dependencies: ModelDependencies,
    *,
    focus: Mapping[str, Any],
    alternatives: Sequence[Mapping[str, Any]],
) -> FrozenCandidates:
    """Freeze actual typed identities and explicit host-set compatibility, never paraphrases."""
    if family.family not in CANDIDATE_FAMILIES:
        raise ValueError("source-first questions cannot consume candidate states")

    def describe(reference, allowed):
        initial, chain, choices = dict(reference), [], []
        while True:
            if canonical_bytes(reference) in {canonical_bytes(item) for item in chain}:
                raise ValueError("cyclic contextual endpoint proxy")
            chain.append(dict(reference))
            node, occurrences = _resolve(reference, dependencies)
            choices.extend(node.get("required_external_choices", ()))
            choices.extend(
                _related_member(reference, choice) for choice in node.get("required_choices", ())
            )
            if node["kind"] not in {"context.symbolic_site", "context.evidence_site"}:
                break
            if len(node.get("external_premises", ())) != 1:
                raise ValueError("contextual endpoint proxy has no unique original endpoint")
            reference = node["external_premises"][0]
        kind = node["kind"]
        if kind not in allowed or not occurrences:
            raise ValueError("candidate type or source support differs from the released question")
        extents = [extent for occurrence in occurrences for extent in occurrence["extents"]]
        if any(
            (
                not isinstance(scope.view, DeclaredNativeFrameSource)
                and extent["source_view_id"] != scope.view.ref.id
            )
            or extent["projection"] != _projection(scope.view)
            or extent.get("synthetic")
            or not scope.examined[0]
            <= extent.get("start", -1)
            < extent.get("end", -1)
            <= scope.examined[1]
            or extent.get("text") != scope.view.text[extent["start"] : extent["end"]]
            for extent in extents
        ):
            raise ValueError("candidate source lies outside the declared examined native context")
        return dict(
            reference=dict(reference),
            origin=initial,
            premises=chain,
            semantic_type=kind,
            located_text=[extent["text"] for extent in extents],
            source_members=extents,
            value=node.get("value", node.get("native_label")),
            required_external_choices=list(
                {canonical_bytes(item): item for item in choices}.values()
            ),
        )

    exact_focus = describe(focus, family.focus_types)
    offered, keys = [], set()
    for alternative in alternatives:
        key = alternative["key"]
        members = alternative["members"]
        compatibility = alternative.get("compatibility", "exclusive")
        if (
            not key
            or key in keys
            or key in {option.key for question in family.questions for option in question.options}
            or not members
            or compatibility not in {"exclusive", "compatible"}
        ):
            raise ValueError("frozen model candidates require distinct explicit alternatives")
        if len(members) > 1 and (
            family.family != "character_host_choice_v1" or compatibility != "compatible"
        ):
            raise ValueError("multiple hosts require one explicitly compatible offered host set")
        described = [describe(member, family.candidate_types) for member in members]
        if len({canonical_bytes(member["reference"]) for member in described}) != len(described):
            raise ValueError("candidate host set repeats an exact member")
        keys.add(key)
        offered.append(
            dict(
                key=key,
                semantic_type="compatible_host_set"
                if len(members) > 1
                else described[0]["semantic_type"],
                compatibility=compatibility,
                members=described,
            )
        )
    if not family.min_candidates <= len(offered) <= family.max_candidates:
        raise ValueError("frozen alternatives exceed the released population bounds")
    return FrozenCandidates(canonical_bytes(dict(focus=exact_focus, alternatives=offered)))


def contextual_candidate_populations(
    family: QuestionFamily, scope: ModelScope, dependencies: ModelDependencies
) -> tuple[tuple[FrozenCandidates, ...], bool]:
    """Expand one retained candidate group on demand; never construct mention pairs globally."""
    upstream = (
        "context.host" if family.family == "character_host_choice_v1" else "context.reference"
    )
    hypothesis_kind = (
        "contextual.host_hypothesis"
        if upstream == "context.host"
        else "contextual.referent_hypothesis"
    )
    complete = False
    populations = []
    for pin, report in dependencies.items():
        body = report.payload
        for row in body["coverage"]:
            if (
                row["family"] == upstream
                and row["outcome"] in {"complete", "empty"}
                and row["availability"] == "available"
                and not row.get("unexamined")
            ):
                complete |= any(
                    selector["projection"] == _projection(scope.view)
                    and selector.get("start", 0) <= scope.examined[0]
                    and selector.get("end", len(scope.view.text)) >= scope.examined[1]
                    for selector in row.get("examined", ())
                )
        nodes = {
            node["local_id"]: node
            for name in ("annotations", "terms")
            for node in body.get(name, ())
        }
        groups = {}
        for role in body["roles"]:
            if (
                role["family"] != upstream
                or role["basis"]["kind"] != "contextual_proposal"
                or not any(
                    nodes.get(key, {}).get("kind") == hypothesis_kind
                    for key in role["basis"].get("premises", ())
                )
            ):
                continue
            owner, target = role["owner"], role["member"]
            members = [
                member["member"]
                for member in sorted(body["memberships"], key=lambda item: item.get("order", 0))
                if member["group"] == target
                and member["role"] in {"native_member", "candidate_member"}
            ]
            if role["role"] == "source_local_coreference_group_candidate":
                candidates = [member for member in members if member != owner]
            else:
                candidates = [target]
            entry = groups.setdefault(owner, dict(candidates={}))
            support = dict(
                premises=[
                    member_reference(pin, role["local_id"]).values(),
                    *(
                        member_reference(pin, key).values()
                        for key in role["basis"].get("premises", ())
                    ),
                ],
                required_external_choices=[
                    *role.get("required_external_choices", ()),
                    *role["basis"].get("required_external_choices", ()),
                    *(
                        member_reference(pin, choice).values()
                        for choice in (
                            *role.get("required_choices", ()),
                            *role["basis"].get("choice_refs", ()),
                        )
                    ),
                ],
            )
            for candidate in candidates:
                supports = entry["candidates"].setdefault(candidate, [])
                if support not in supports:
                    supports.append(support)
        # Unclustered mapped mentions remain an actual unresolved focus with an
        # empty offered list: d1 can distinguish missing antecedent from choosing none.
        for node in nodes.values():
            if (
                node["kind"] == "context.unresolved_reference"
                and family.family == "character_referent_choice_v1"
            ):
                for focus in node.get("premises", ()):
                    groups.setdefault(focus, dict(candidates={}))
        for owner, group in groups.items():
            focus = member_reference(pin, owner).values()
            _node, focus_occurrences = _resolve(focus, dependencies)
            if not all(
                extent["projection"] == _projection(scope.view)
                and scope.focal[0]
                <= extent.get("start", -1)
                < extent.get("end", -1)
                <= scope.focal[1]
                for occurrence in focus_occurrences
                for extent in occurrence["extents"]
            ):
                continue
            alternatives = [
                dict(
                    key="candidate_" + digest([pin.values(), candidate]),
                    members=[member_reference(pin, candidate).values()],
                )
                for candidate in group["candidates"]
            ]
            try:
                frozen = freeze_candidates(
                    family, scope, dependencies, focus=focus, alternatives=alternatives
                )
            except ValueError:
                # A different focal/context scope owns this hypothesis, or its
                # actual candidate population exceeds the released bound. Never trim it.
                complete = False
                continue
            value = frozen.payload
            focus_members = value["focus"]["source_members"]
            if not all(
                scope.focal[0] <= extent["start"] < extent["end"] <= scope.focal[1]
                for extent in focus_members
            ):
                continue
            for alternative, candidate in zip(
                value["alternatives"], group["candidates"], strict=True
            ):
                alternative["hypothesis_supports"] = group["candidates"][candidate]
            populations.append(FrozenCandidates(canonical_bytes(value)))
    return tuple({population.digest: population for population in populations}.values()), complete


@dataclass(frozen=True, slots=True)
class QuestionRequest:
    family: QuestionFamily
    scope: ModelScope
    stage: int
    content: bytes
    candidates: FrozenCandidates | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.content)

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


def compile_question_stage(
    family: QuestionFamily,
    scope: ModelScope,
    stage: int,
    *,
    prior: Mapping[str, Mapping[str, Any]] = {},
    candidates: FrozenCandidates | None = None,
    keys: Sequence[str] = (),
) -> QuestionRequest:
    if family.family not in CHARACTERIZATION_FAMILIES or family.provider != "d1":
        raise ValueError("question family is not a released d1 characterization task")
    if (family.family in CANDIDATE_FAMILIES) != (candidates is not None):
        raise ValueError("source-first and candidate-centered states are independent")
    selected = [
        question
        for question in family.questions
        if question.stage == stage and (not keys or question.key in keys)
    ]
    if not selected:
        raise ValueError("released family has no questions at this stage")
    if any(
        key not in prior or prior[key]["state"] != "proposed"
        for question in selected
        for key in question.depends_on
    ):
        raise ValueError("staged question has unresolved frozen answer prerequisites")
    exact = [] if candidates is None else candidates.payload["alternatives"]
    rendered, aliases = render_candidate_options(family, exact)
    state = dict(
        source=scope.mapping.provider_text,
        focal=dict(
            start=scope.focal[0] - scope.examined[0], end=scope.focal[1] - scope.examined[0]
        ),
        structural_context=[
            dict(pointer=node["self_ref"], label=node.get("label"), text=node.get("text", ""))
            for node in _source_rows(scope.view, "ancestors")
        ],
        prior_answers={
            key: dict(prior[key])
            for key in dict.fromkeys(key for question in selected for key in question.depends_on)
        },
    )
    if candidates is not None:
        state.update(focus=candidates.payload["focus"], candidates=rendered)
    request = dict(
        state=state,
        questions={question.key: question.native(rendered) for question in selected},
        interpretation=dict(
            version="3",
            declaration_digest=family.digest,
            assessed_scope=dict(
                pin=record_source_pin(scope.mapping.context.primary),
                focal_extent=list(scope.focal),
                projection_extent=list(scope.examined),
                scope_digest=scope.mapping.scope_digest,
            ),
            candidates=exact,
            focus=None if candidates is None else candidates.payload["focus"],
            option_aliases=aliases,
            candidate_list_digest=None if candidates is None else candidates.digest,
            frozen_candidates=None if candidates is None else candidates.payload,
        ),
    )
    # Preserve the declaration's question/option order in the actual native request.
    return QuestionRequest(
        family,
        scope,
        stage,
        json.dumps(request, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(),
        candidates,
    )


def gliner_cue_request(
    release_id: str, family: QuestionFamily, scope: ModelScope
) -> tuple[GlinerPack, GlinerInput]:
    if (
        family.family != GLINER_CUES
        or family.provider != "gliner"
        or any(question.kind != "text" for question in family.questions)
    ):
        raise ValueError("located cue extraction requires a released literal-only schema")
    # Choices, attributes and classified fields never become literal source anchors.
    pack = GlinerPack(
        release_id,
        json.dumps(
            dict(entities={question.key: question.instructions for question in family.questions}),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "native-local-v1",
    )
    item = replace(
        GlinerInput.from_context(scope.mapping.context),
        operation="text.model_characterization/2:" + family.digest,
    )
    return pack, item
