"""Released bounded model questions, exact evidence and private linguistic proposals.

The existing native workers supply typed answers. This owner binds their meanings to
the archived question declaration and retained source/candidate population. It does not
turn span reads into a complete logical form or grant provider scores admission authority.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from math import isfinite
from typing import Any

from corpus_structure.methods.gliner import (
    GlinerInput,
    GlinerPack,
    GlinerProfile,
    GlinerReport,
    map_literal,
)
from corpus_structure.methods.native_evidence_layers import (
    NativeEvidenceBuilder,
    digest,
    source_selector,
)
from corpus_structure.methods.pm2_interpretation_products import (
    interpretation_products,
    render_candidate_options,
)
from corpus_structure.methods.pm2_result import d1_evidence
from corpus_structure.methods.pm2_source import (
    D1SourceField,
    MappedSource,
    PM2SourceMap,
    SourceMapReason,
    SourceMapRefused,
    SourceMapSegment,
)
from corpus_structure.semantic.characterization import LayerReport
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    ANSWER_READS,
    CHARACTERIZATION_FAMILIES,
    QuestionFamily,
)
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
    record_source_pin,
    source_slice,
)
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.data_product_reference import (DataProductReference, DataProductMemberReference, member_reference, read_member_reference)

PROFILE = "baseline-model-characterization-v1"
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


def _id(kind: str, *values: Any) -> str:
    return "model:" + kind + ":" + digest(values)


def _score(value: Any, event: str, scheme: str = "d1-native-probability-v1") -> dict[str, Any]:
    if type(value) not in {int, float} or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("native answer probability is not a finite event probability")
    return dict(scheme=scheme, value=source_value(value), meaning=event)


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
                source=(self.view.pin.values() if isinstance(self.view, DeclaredNativeFrameSource) else self.view.ref.native_product.values()),
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
    formulas = {item["self_ref"] for item in _source_rows(view, "items") if item.get("label") == "formula"}
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
    return view.projection_digest if isinstance(view, DeclaredNativeFrameSource) else view.ref.projection_digest


def _source_rows(view, name):
    return view.value.get(name, ()) if isinstance(view, DeclaredNativeFrameSource) else getattr(view, name)


def _related_member(reference, local_id):
    selected = read_member_reference(reference)
    product = selected.product if isinstance(selected, DataProductMemberReference) else selected.layer
    return member_reference(product, local_id).values()


@dataclass(frozen=True)
class DeclaredModelDependency:
    reference: DataProductReference
    payload: dict


def declared_model_dependencies(products, source):
    """Project selected current semantic inventories without manufacturing legacy refs."""
    dependencies = {}
    for product in products:
        body = json.loads(product.content)
        if body["source"] != source.value["source"] or body["selectors"] != source.value["selectors"]:
            raise ValueError("model dependency belongs to another original source projection")
        reference = DataProductReference(product.semantic_id)
        if reference in dependencies:
            raise ValueError("model dependency repeats a selected semantic product")
        dependencies[reference] = DeclaredModelDependency(reference, {
            **product.inventory(), "source": body["source"], "coverage": body["coverage"],
        })
    return dependencies


def _resolve(
    reference: Mapping[str, Any], dependencies: Mapping[ProductReference, LayerReport]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selected = read_member_reference(reference)
    if isinstance(selected, DataProductMemberReference):
        pin, local_id = selected.product, selected.member_id
        layer = dependencies.get(pin)
        if layer is None or layer.reference != pin:
            raise ValueError("model candidate is outside its exact selected semantic closure")
    else:
        pin, local_id = selected.layer, selected.local_id
        layer = dependencies.get(pin)
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
    dependencies: Mapping[ProductReference, LayerReport],
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
                _related_member(reference, choice)
                for choice in node.get("required_choices", ())
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
            (not isinstance(scope.view, DeclaredNativeFrameSource) and extent["source_view_id"] != scope.view.ref.id)
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
    family: QuestionFamily, scope: ModelScope, dependencies: Mapping[ProductReference, LayerReport]
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


class ModelCharacterizationBuilder(NativeEvidenceBuilder):
    """Reuse the shared exact occurrence/layer builder; add question-specific meanings."""

    def __init__(self, base, scope, operation, families=CHARACTERIZATION_FAMILIES):
        super().__init__(base, scope, operation, profile=PROFILE, families=families)
        self.operation["preconditions"] = [
            "released-characterization-question-declarations",
            "exact-source-and-frozen-candidate-closure",
        ]
        self.operation["effects"] = ["private-source-language-proposals; no scientific admission"]
        self.answers: dict[tuple[str, str], dict[str, Any]] = {}
        self.proposals: dict[tuple[str, str], str] = {}

    def payload(self, release_id, *, dependencies=()):
        result = super().payload(release_id, dependencies=dependencies)
        for coverage in result["coverage"]:
            if coverage["outcome"] == "complete" and not any(
                annotation["family"] == coverage["family"] for annotation in self.annotations
            ):
                coverage["outcome"] = "empty"
        return result

    def classification(
        self,
        family: QuestionFamily,
        scope: ModelScope,
        request: Mapping[str, Any],
        product: Any,
        native: Any,
    ):
        value = product.value
        question = next(
            question for question in family.questions if question.key == value["question_key"]
        )
        probabilities = value["native_answer"]["scores"]
        alternatives = [
            dict(
                key=option.key,
                state=value["alternative_states"][option.key],
                **(
                    {
                        "score": _score(
                            probabilities[option.key],
                            "native passage classification confidence",
                            "gliner-native-classification-v1",
                        )
                    }
                    if option.key in probabilities
                    else {}
                ),
            )
            for option in question.options
        ]
        identity = self._question(
            family,
            scope,
            question.key,
            request_id=digest(request),
            answer_kind="gliner_classification",
            state=value["state"],
            native=dict(
                answer=value["native_answer"], request=dict(request), report=asdict(native)
            ),
            alternatives=alternatives,
        )
        answer = self.annotations[-1]["model_answer"]
        answer["observed_keys"], answer["selected_keys"] = (
            list(value["observed_keys"]),
            list(value["selected_keys"]),
        )
        if value["selected_keys"]:
            # This is a category of the exact slice, with explicitly no literal witness.
            self.annotations.append(
                dict(
                    local_id=_id("classification", identity),
                    kind="model.choice_proposal",
                    vocabulary=family.family,
                    native_scheme="gliner-passage-classification-v1",
                    native_label=question.projection_role,
                    occurrences=[self.occurrence(scope.view, *scope.focal)],
                    status="private_proposal",
                    family=family.family,
                    premises=[identity],
                )
            )
        self.record(family.family, [source_selector(scope.view, *scope.examined)])

    def _question(
        self,
        family: QuestionFamily,
        scope: ModelScope,
        key: str,
        *,
        request_id: str,
        answer_kind: str,
        state: str,
        native: Any,
        stage: int = 0,
        candidates: FrozenCandidates | None = None,
        depends_on=(),
        alternatives=(),
        scores=(),
        diagnostic=None,
        external=(),
    ) -> str:
        identity = _id("question", self.operation, family.digest, scope.identity, request_id, key)
        occurrence = self.occurrence(scope.view, *scope.focal)
        model_answer = dict(
            family=family.family,
            question_key=key,
            declaration_digest=family.digest,
            stage=str(stage),
            answer_kind=answer_kind,
            state=state,
            request_digest=request_id,
            native_answer=source_value(native),
            source_field=family.source_field,
            observed_keys=[],
            selected_keys=[],
            depends_on=list(depends_on),
            alternatives=list(alternatives),
        )
        if candidates is not None:
            model_answer["candidate_list_digest"] = candidates.digest
        if diagnostic is not None:
            model_answer["diagnostic"] = diagnostic
        self.annotations.append(
            dict(
                local_id=identity,
                kind="model.question",
                vocabulary=family.family,
                occurrences=[occurrence],
                native_scheme="released-model-question-v1",
                native_label=key,
                status="native_evidence",
                family=family.family,
                model_answer=model_answer,
                scores=list(scores),
                external_premises=list(external),
            )
        )
        return identity

    def unavailable(
        self,
        family: QuestionFamily,
        scope: ModelScope,
        reason: str,
        *,
        stage=0,
        state="failed",
        request_id=None,
        keys=None,
        native=None,
    ):
        request_id = request_id or digest(
            dict(
                family=family.digest, scope=scope.identity, stage=stage, state=state, reason=reason
            )
        )
        for question in family.questions:
            if question.stage == stage and (keys is None or question.key in keys):
                identity = self._question(
                    family,
                    scope,
                    question.key,
                    request_id=request_id,
                    answer_kind=question.kind,
                    state=state,
                    native=dict(outcome=state, reason=reason) if native is None else native,
                    stage=stage,
                    diagnostic=dict(category=state, message=reason),
                    depends_on=[
                        self.answers[(scope.identity + family.family, key)]["annotation_id"]
                        for key in question.depends_on
                        if (scope.identity + family.family, key) in self.answers
                    ],
                )
                self.answers[(scope.identity + family.family, question.key)] = dict(
                    annotation_id=identity, state=state, selected_keys=[]
                )
        self.record(
            family.family,
            [source_selector(scope.view, *scope.examined)],
            "partial" if state == "dependency_unresolved" else "failed",
            reason,
        )

    def _endpoint(
        self, scope: ModelScope, described: Mapping[str, Any], family: str, kind: str
    ) -> str:
        identity = _id("endpoint", kind, described["reference"])
        if not any(annotation["local_id"] == identity for annotation in self.annotations):
            occurrences = [
                self.occurrence(scope.view, extent["start"], extent["end"])
                for extent in described["source_members"]
            ]
            self.annotations.append(
                dict(
                    local_id=identity,
                    kind=kind,
                    vocabulary=described["semantic_type"],
                    native_scheme="retained-characterization-reference-v1",
                    native_label=described["semantic_type"],
                    occurrences=list(dict.fromkeys(occurrences)),
                    status="private_proposal",
                    family=family,
                    external_premises=[described["reference"]],
                    required_external_choices=described["required_external_choices"],
                )
            )
        return identity

    def d1(
        self, request: QuestionRequest, reply: Mapping[str, Any], *, runtime: Mapping[str, Any]
    ) -> dict[str, dict[str, Any]]:
        family, scope = request.family, request.scope
        payload = request.payload
        receipt = reply.get("batch_receipt")
        if self.operation.get("version") != "1":
            if (
                str(runtime.get("device", "")).split(":")[0] != "cuda"
                or runtime.get("dtype") != "torch.bfloat16"
            ):
                raise ValueError("current d1 observation requires CUDA bfloat16 runtime")
            if not isinstance(receipt, dict) or receipt.get("version") != 2:
                raise ValueError(
                    "current d1 observation requires its ordered version2 cohort receipt"
                )
        if receipt is not None:
            from corpus_structure.methods.model_observation import validate_pm2_batch_receipt

            validate_pm2_batch_receipt(receipt, payload, "d1")
        elif self.operation.get("version") == "2":
            raise ValueError("current d1 observation requires its native cohort receipt")
        if reply.get("outcome") not in {"succeeded", "empty"}:
            self.unavailable(
                family,
                scope,
                str(reply.get("reason", reply.get("outcome", "failed"))),
                stage=request.stage,
                request_id=request.digest,
                native=dict(reply),
            )
            return {}
        rendered = reply.get("rendered_state")
        if not isinstance(rendered, str) or canonical_bytes(
            json.loads(rendered)
        ) != canonical_bytes(payload["state"]):
            raise ValueError("d1 rendered state differs from the exact frozen request")
        fields = [row for row in reply.get("state_fields", ()) if row[2] == family.source_field]
        if len(fields) != 1 or any(type(value) is not int for value in fields[0][:2]):
            raise ValueError("d1 has no unique literal source allowlist field")
        field = D1SourceField(rendered, family.source_field, *fields[0][:2])
        located = d1_evidence(
            scope.mapping, reply, field=field, source_path=family.source_field, native=True
        )
        for question in family.questions:
            support = located.get(question.key)
            if (
                question.literal_scope == "focal"
                and isinstance(support, MappedSource)
                and any(
                    not scope.focal[0] <= piece.start < piece.end <= scope.focal[1]
                    for piece in support.pieces
                )
            ):
                located[question.key] = SourceMapRefused(
                    SourceMapReason.INVALID_EXTENT,
                    scope.mapping.scope_digest,
                    "native literal lies outside the released focal output region",
                )
        products = interpretation_products(family, payload, dict(reply), located)
        result = {}
        for product in products:
            key, value = product.value["question_key"], product.value
            question = next(question for question in family.questions if question.key == key)
            native_answer = value["native_answer"]
            depends = [
                self.answers[(scope.identity + family.family, name)]["annotation_id"]
                for name in question.depends_on
            ]
            alternatives = []
            for offered, probability in native_answer.get("probabilities", {}).items():
                durable = payload["interpretation"]["option_aliases"].get(offered, offered)
                alternatives.append(
                    dict(
                        key=durable,
                        state=value["alternative_states"].get(durable, "unobserved"),
                        score=_score(
                            probability, "choice probability for offered alternative " + offered
                        ),
                    )
                )
            scores = (
                [_score(native_answer["found"], "native span extraction presence")]
                if question.kind in ANSWER_READS
                else []
            )
            if question.kind == "noul":
                assert question.positive is not None
                scores = [
                    _score(
                        native_answer["noul"],
                        "native binary positive criterion: " + question.positive,
                    )
                ]
            external = []
            if request.candidates is not None:
                frozen = request.candidates.payload
                external = [
                    *frozen["focus"]["premises"],
                    *(
                        premise
                        for alternative in frozen["alternatives"]
                        for member in alternative["members"]
                        for premise in member["premises"]
                    ),
                    *(
                        premise
                        for alternative in frozen["alternatives"]
                        for support in alternative.get("hypothesis_supports", ())
                        for premise in support["premises"]
                    ),
                ]
                external = list({canonical_bytes(item): item for item in external}.values())
            annotation = self._question(
                family,
                scope,
                key,
                request_id=request.digest,
                answer_kind=question.kind,
                state=value["state"],
                native=dict(
                    answer=native_answer,
                    request=payload,
                    runtime=dict(runtime),
                    rendered_state=rendered,
                    state_fields=reply["state_fields"],
                    usage=reply.get("native", {}).get("usage"),
                    batch_receipt=reply.get("batch_receipt"),
                ),
                stage=request.stage,
                candidates=request.candidates,
                depends_on=depends,
                alternatives=alternatives,
                scores=scores,
                external=external,
            )
            row = self.annotations[-1]["model_answer"]
            row["observed_keys"], row["selected_keys"] = (
                list(value["observed_keys"]),
                list(value["selected_keys"]),
            )
            support = located.get(key)
            proposal = None
            if value["state"] == "proposed":
                occurrences = (
                    [
                        self.occurrence(scope.view, piece.start, piece.end)
                        for piece in support.pieces
                    ]
                    if isinstance(support, MappedSource)
                    else [self.occurrence(scope.view, *scope.focal)]
                )
                proposal = _id("proposal", annotation, value["selected_keys"])
                self.annotations.append(
                    dict(
                        local_id=proposal,
                        kind="model.span_proposal"
                        if isinstance(support, MappedSource)
                        else "model.choice_proposal",
                        vocabulary=family.family,
                        native_scheme="released-model-question-v1",
                        native_label=value["selected_keys"][0]
                        if request.candidates is not None
                        else question.projection_role,
                        occurrences=list(dict.fromkeys(occurrences)),
                        status="private_proposal",
                        premises=[annotation],
                        family=family.family,
                        external_premises=external,
                    )
                )
                self.membership(
                    annotation, proposal, "private_proposal", 0, family.family, occurrences
                )
                for dependency in question.depends_on:
                    previous = self.proposals.get((scope.identity + family.family, dependency))
                    if previous is not None and isinstance(support, MappedSource):
                        role = dict(
                            owner=previous,
                            member=proposal,
                            role=question.projection_role,
                            scheme=family.family,
                            occurrences=occurrences,
                            family=family.family,
                            basis=dict(
                                kind="contextual_proposal",
                                status="private_proposal",
                                premises=[annotation, *depends],
                            ),
                        )
                        self.roles.append(dict(local_id=_id("role", role), **role))
                self.proposals[(scope.identity + family.family, key)] = proposal
                if request.candidates is not None:
                    frozen = request.candidates.payload
                    focus_id = self._endpoint(scope, frozen["focus"], family.family, "model.focus")
                    for selected in value["selected_keys"]:
                        offered = next(
                            alternative
                            for alternative in frozen["alternatives"]
                            if alternative["key"] == selected
                        )
                        for member in offered["members"]:
                            member_id = self._endpoint(
                                scope, member, family.family, "model.candidate"
                            )
                            for hypothesis_support in offered.get(
                                "hypothesis_supports",
                                [dict(premises=[], required_external_choices=[])],
                            ):
                                required = (
                                    frozen["focus"]["required_external_choices"]
                                    + member["required_external_choices"]
                                    + hypothesis_support["required_external_choices"]
                                )
                                role = dict(
                                    owner=focus_id,
                                    member=member_id,
                                    role=question.projection_role,
                                    scheme=family.family,
                                    occurrences=occurrences,
                                    family=family.family,
                                    required_external_choices=list(
                                        {canonical_bytes(item): item for item in required}.values()
                                    ),
                                    basis=dict(
                                        kind="contextual_proposal",
                                        status="private_proposal",
                                        premises=[annotation, proposal],
                                        external_premises=list(
                                            {
                                                canonical_bytes(item): item
                                                for item in [
                                                    *frozen["focus"]["premises"],
                                                    *member["premises"],
                                                    *hypothesis_support["premises"],
                                                ]
                                            }.values()
                                        ),
                                    ),
                                )
                                self.roles.append(dict(local_id=_id("role", role), **role))
            answer = dict(
                annotation_id=annotation,
                state=value["state"],
                selected_keys=list(value["selected_keys"]),
                **(
                    {"text": "".join(piece.quote for piece in support.pieces)}
                    if isinstance(support, MappedSource)
                    else {}
                ),
            )
            self.answers[(scope.identity + family.family, key)] = answer
            result[key] = answer
            if isinstance(support, SourceMapRefused):
                row["diagnostic"] = dict(category=str(support.reason), message=str(support))
                self.record(
                    family.family,
                    [source_selector(scope.view, *scope.examined)],
                    "partial",
                    "Native literal could not be mapped to the allowlisted source field.",
                )
        self.record(family.family, [source_selector(scope.view, *scope.examined)])
        return result


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


def project_gliner_cues(
    builder: ModelCharacterizationBuilder,
    family: QuestionFamily,
    scope: ModelScope,
    pack: GlinerPack,
    item: GlinerInput,
    native: GlinerReport,
    profile: GlinerProfile,
    inference: Mapping[str, Any],
    *,
    threshold: float,
):
    from corpus_structure.methods.pm2_gliner_classification import (
        ClassificationProfile,
        authenticated_gliner_report,
    )

    authenticated = authenticated_gliner_report(
        dict(pack=asdict(pack), item=asdict(item), threshold=threshold, inference=dict(inference)),
        asdict(native),
        ClassificationProfile(
            provider="gliner", device=profile.device, profile=profile, threshold=threshold
        ),
        overlap_policy="nested",
    )
    expected = authenticated.request_digest
    if expected is None:
        raise ValueError("authenticated cue lacks a request commitment")
    raw = native.raw
    if (
        not isinstance(raw, dict)
        or set(raw) != {"entities"}
        or not isinstance(raw["entities"], dict)
        or set(raw["entities"]) != {question.key for question in family.questions}
    ):
        raise ValueError("GLiNER decoded cue population differs from the released schema")
    for question in family.questions:
        spans = raw["entities"][question.key]
        if not isinstance(spans, list):
            raise ValueError("GLiNER cue population is not a located list")
        annotation = builder._question(
            family,
            scope,
            question.key,
            request_id=expected,
            answer_kind="gliner_span",
            state="observed" if spans else "empty",
            native=dict(
                spans=spans,
                report=asdict(native),
                declaration=pack.declaration_json,
                assessed_scope=dict(
                    focal_extent=list(scope.focal),
                    projection_extent=list(scope.examined),
                    source_map_digest=scope.mapping.input_digest,
                ),
            ),
        )
        for index, span in enumerate(spans):
            if not isinstance(span, dict):
                raise ValueError("GLiNER decoded cue must be a located confidence record")
            score = _score(
                span.get("confidence"),
                "native decoded literal confidence",
                "gliner-native-confidence-v1",
            )
            try:
                mapped = map_literal(native, scope.mapping.context, span, allow_multiple=True)
                # Enforce the same protected-atom restriction as d1 and native syntax.
                from corpus_structure.methods.pm2_source import ProviderSpan

                scope.mapping.map_extents(
                    (ProviderSpan(span["start"], span["end"], span["text"]),),
                    scope_digest=scope.mapping.scope_digest,
                )
            except ValueError as error:
                builder.record(
                    family.family,
                    [source_selector(scope.view, *scope.examined)],
                    "partial",
                    str(error),
                )
                continue
            if question.literal_scope == "focal" and any(
                not scope.focal[0] <= piece.start < piece.end <= scope.focal[1] for piece in mapped
            ):
                continue  # Observed context population is retained above; output is focal.
            occurrences = [
                builder.occurrence(scope.view, piece.start, piece.end) for piece in mapped
            ]
            proposal = _id("gliner-span", annotation, index, span)
            builder.annotations.append(
                dict(
                    local_id=proposal,
                    kind="model.span_proposal",
                    vocabulary=family.family,
                    native_scheme="gliner-decoded-literal-v1",
                    native_label=question.projection_role,
                    occurrences=occurrences,
                    status="private_proposal",
                    premises=[annotation],
                    family=family.family,
                    scores=[score],
                )
            )
            builder.membership(
                annotation, proposal, "decoded_proposal", index, family.family, occurrences
            )
    builder.record(family.family, [source_selector(scope.view, *scope.examined)])
