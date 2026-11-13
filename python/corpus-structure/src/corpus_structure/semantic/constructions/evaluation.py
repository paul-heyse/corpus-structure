"""Primary contextual evaluation of retained packed symbols under immutable environments.

Provider calls and hypothesis generation are upstream. This operation only composes
their exact retained products, preserving private proposal standing and unresolved sites.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.characterization import (
    AnnotationReference as LegacyMemberReference,
    LayerReport,
    validate_layer,
    validate_reading_choices,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.product_reference import ProductReference as LegacyProductPin
from corpus_structure.semantic.data_product_reference import (
    DataProductReference, DataProductMemberReference, member_reference, read_member_reference,
)

from .nodes import identity

type MemberReference = LegacyMemberReference | DataProductMemberReference
type ProductPin = LegacyProductPin | DataProductReference


EVALUATION_REVISION = "primary-contextual-evaluation-1"
EVALUATION_FAMILIES = (
    "meaning.predication",
    "meaning.scope",
    "meaning.reference",
    "meaning.attribution",
    "meaning.attachment",
    "meaning.function",
)


def reference(value: Mapping[str, Any]) -> MemberReference:
    return read_member_reference(value)


def _ordered(refs: Sequence[MemberReference]) -> tuple[MemberReference, ...]:
    return tuple(sorted(set(refs), key=lambda r: canonical_bytes(r.values())))


@dataclass(frozen=True, slots=True)
class Binding:
    variable: MemberReference
    binder: MemberReference

    def values(self):
        return dict(variable=self.variable.values(), binder=self.binder.values())


@dataclass(frozen=True, slots=True)
class Environment:
    context_layers: tuple[ProductPin, ...] = ()
    hypotheses: tuple[MemberReference, ...] = ()
    proposals: tuple[MemberReference, ...] = ()
    choices: tuple[MemberReference, ...] = ()
    bindings: tuple[Binding, ...] = ()
    attribution: tuple[MemberReference, ...] = ()

    def values(self):
        return dict(
            context_layers=[p.values() for p in self.context_layers],
            hypotheses=[r.values() for r in self.hypotheses],
            proposals=[r.values() for r in self.proposals],
            choices=[r.values() for r in self.choices],
            bindings=[b.values() for b in self.bindings],
            attribution=[r.values() for r in self.attribution],
        )

    @property
    def digest(self):
        return sha256(canonical_bytes(self.values())).hexdigest()

    def requiring(self, choices):
        return replace(self, choices=_ordered((*self.choices, *choices)))


def environment(*, context_layers=(), hypotheses=(), proposals=(), choices=()) -> Environment:
    """Public selection accepts immutable evidence IDs, never arbitrary bindings."""
    if len(set(context_layers)) != len(context_layers):
        raise ValueError("context environment repeats a selected revision")
    if any(len(set(values)) != len(values) for values in (hypotheses, proposals, choices)):
        raise ValueError("context environment repeats a selected evidence or choice identity")
    return Environment(
        tuple(context_layers), _ordered(hypotheses), _ordered(proposals), _ordered(choices)
    )


class ContextualEvaluator:
    def __init__(
        self,
        layers: Mapping[LegacyProductPin, LayerReport],
        *,
        check_active=lambda: None,
        max_nodes=20000,
        symbolic_layers=None,
    ):
        bases=set()
        for pin,report in layers.items():
            if report.reference(pin.task_id)!=pin:
                raise ValueError("evaluation requires exact retained layer pins")
            bases.add(report.base_document)
        if len(bases)!=1:
            raise ValueError("evaluation requires one immutable source base")
        self._initialize(layers,{pin:report.payload for pin,report in layers.items()},next(iter(bases)),check_active=check_active,max_nodes=max_nodes,symbolic_layers=symbolic_layers)

    @classmethod
    def from_products(cls,source,products,*,check_active=lambda:None,max_nodes=20000,symbolic_products=None):
        coordinate=source.value["source"]
        inputs={}
        payloads={}
        for product in products:
            body=json.loads(product.content)
            if body["source"]!=coordinate:
                raise ValueError("contextual inputs belong to another original source")
            pin=DataProductReference(product.semantic_id)
            if pin in inputs:
                raise ValueError("contextual inputs repeat a governed semantic product")
            inputs[pin]=product
            payloads[pin]={**product.inventory(),"coverage":body["coverage"]}
        if not inputs:
            raise ValueError("contextual evaluation requires explicit retained symbolic products")
        instance=cls.__new__(cls)
        instance._initialize(inputs,payloads,coordinate,check_active=check_active,max_nodes=max_nodes,symbolic_layers=symbolic_products)
        return instance

    def _initialize(self,layers,payloads,base,*,check_active,max_nodes,symbolic_layers):
        self.layers=dict(layers)
        self.payloads=dict(payloads)
        self.base=base
        self.symbolic_layers=frozenset(layers if symbolic_layers is None else symbolic_layers)
        if not self.symbolic_layers<=layers.keys():
            raise ValueError("symbolic selection is outside retained dependency closure")
        self.nodes = {}
        self.occurrences = {}
        self.choices = {}
        self._model_questions = {}
        self._model_proposals = {}
        membership_members = {}
        referent_members = {}
        for pin,payload in self.payloads.items():
            for inventory in ("annotations", "memberships", "roles", "terms"):
                for node in payload[inventory]:
                    self.nodes[member_reference(pin, node["local_id"])] = (inventory, node)
                    if inventory == "memberships":
                        group = member_reference(pin, node["group"])
                        member = member_reference(pin, node["member"])
                        membership_members.setdefault((group, node["role"]), set()).add(member)
                        if node["role"] in {"native_member", "candidate_member"}:
                            referent_members.setdefault(group, set()).add(member)
                    if inventory == "annotations" and "model_answer" in node:
                        self._model_questions.setdefault(
                            (pin, node["model_answer"]["family"]), []
                        ).append(node)
                    elif inventory == "annotations" and node.get("kind") == "model.span_proposal":
                        for premise in node.get("premises", ()):
                            self._model_proposals.setdefault((pin, premise), []).append(node)
            for packet in payload.get("source_facts",()):
                self.nodes[member_reference(pin,packet["member_id"])]=("source_facts",packet["body"])
            for occurrence in payload["occurrences"]:
                self.occurrences[occurrence["local_id"]] = occurrence
            for group in payload["choices"]:
                for member in group["members"]:
                    self.choices[member_reference(pin, member["local_id"])] = (group, member)
        self._membership_members = {
            key: frozenset(values) for key, values in membership_members.items()
        }
        self._referent_members = {
            key: frozenset(values) for key, values in referent_members.items()
        }
        self.check_active, self.max_nodes = check_active, max_nodes
        self.memo: dict[tuple[MemberReference, Environment], str] = {}
        self.terms: dict[str, dict[str, Any]] = {}
        self.groups: dict[str, dict[str, Any]] = {}
        self.roles: dict[str, dict[str, Any]] = {}
        self.output_occurrences = {}
        self.diagnostics: set[str] = set()
        self.family_diagnostics = {family: set() for family in EVALUATION_FAMILIES}
        self.unavailable_families = set()
        self._verified: set[Environment] = set()
        self._active: set[tuple[MemberReference, Environment]] = set()
        self._attached: set[tuple[str, MemberReference]] = set()
        self._available_cache = {}
        self._available_owners = {}
        self._available_addresses = {}
        self._role_proofs = {}

    def available(self, env):
        """Exact context revisions determine the available evidence pool, not a selection."""
        if env.context_layers not in self._available_cache:
            roles = []
            proposals = []
            for pin in env.context_layers:
                body = self.payloads[pin]
                roles.extend(
                    member_reference(pin, row["local_id"])
                    for row in body["roles"]
                    if row["basis"]["kind"] == "contextual_proposal"
                    and row["basis"]["status"] == "private_proposal"
                )
                proposals.extend(
                    member_reference(pin, row["local_id"])
                    for row in body["annotations"]
                    if row.get("kind") in {"model.span_proposal", "model.choice_proposal"}
                    and row["status"] == "private_proposal"
                )
            by_owner = {}
            by_address = {}
            for role_ref in _ordered(roles):
                try:
                    _role, owner, _member, _required = self._authenticate_role(
                        role_ref, env, strict_choices=False
                    )
                    original = self._endpoint(owner)
                    node = self.resolve(original)
                except ValueError as error:
                    self._mark("meaning.reference", str(error))
                    continue
                by_owner.setdefault(original, []).append(role_ref)
                if node.get("kind") == "construction":
                    for member in self._membership_members.get((original, "meaning"), ()):
                        by_owner.setdefault(member, []).append(role_ref)
                elif node.get("kind") in {"native.mention", "model.span_proposal"} and node.get(
                    "occurrences"
                ):
                    by_address.setdefault(self._member_addresses(node), []).append(role_ref)
            self._available_cache[env.context_layers] = (_ordered(roles), _ordered(proposals))
            self._available_owners[env.context_layers] = by_owner
            self._available_addresses[env.context_layers] = by_address
        return self._available_cache[env.context_layers]

    def default_roots(self, env):
        result = []
        for pin, body in self.payloads.items():
            if pin in env.context_layers or pin not in self.symbolic_layers:
                continue
            incoming = {
                e["target"]
                for term in body["terms"]
                for e in term.get("children", ())
                if "target" in e
            }
            incoming.update(
                member["root"] for group in body["choices"] for member in group["members"]
            )
            result.extend(
                member_reference(pin, node["local_id"])
                for node in body["terms"]
                if node["local_id"] not in incoming
                and node["value"] not in {"@sequence", "clause", "start", "predication", "nominal"}
            )
        return _ordered(result)

    def _mark(self, family, reason):
        self.diagnostics.add(reason)
        self.family_diagnostics[family].add(reason)

    def resolve(self, ref: MemberReference, inventory=None):
        found = self.nodes.get(ref)
        if found is None or (inventory is not None and found[0] != inventory):
            raise ValueError(
                "context endpoint does not resolve to its declared retained population"
            )
        return found[1]

    def _requirements(self, ref, node):
        return _ordered(
            (
                *[member_reference(ref.product, key) for key in node.get("required_choices", ())],
                *[reference(value) for value in node.get("required_external_choices", ())],
            )
        )

    def _validate_choices(self, env):
        if len(set(env.choices)) != len(env.choices):
            raise ValueError("environment repeats an analytical choice")
        selected = set(env.choices)
        by_layer = {}
        for choice in selected:
            found = self.choices.get(choice)
            if found is None:
                raise ValueError("environment selection is not a retained analytical choice member")
            by_layer.setdefault(choice.product, []).append(choice.local_id)
            _, member = found
            if not set(self._requirements(choice, member)) <= selected:
                raise ValueError("environment is missing a jointly required upstream choice")
        for pin, ids in by_layer.items():
            validate_reading_choices(self.payloads[pin], ids)

    def _assuming(self, env, choices):
        pending = list(choices)
        selected = set(env.choices)
        while pending:
            choice = pending.pop()
            if choice in selected:
                continue
            found = self.choices.get(choice)
            if found is None:
                raise ValueError("symbolic branch requires an unknown analytical choice")
            selected.add(choice)
            pending.extend(self._requirements(choice, found[1]))
        return replace(env, choices=_ordered(tuple(selected)))

    def _endpoint(self, ref):
        seen = set()
        while ref not in seen:
            seen.add(ref)
            node = self.resolve(ref)
            if node.get("kind") not in {
                "context.symbolic_site",
                "context.evidence_site",
                "model.focus",
                "model.candidate",
            }:
                if node.get("kind") == "native.unmapped_mention":
                    raise ValueError("unmapped native mention is not a contextual endpoint")
                return ref
            refs = node.get("external_premises", ())
            if len(refs) != 1:
                raise ValueError("context proxy requires exactly one original endpoint")
            ref = reference(refs[0])
        raise ValueError("context endpoint proxy cycle")

    def _authenticate_role(self, ref, env, *, strict_choices=True):
        if ref.product not in env.context_layers:
            raise ValueError("selected hypothesis is outside selected context revisions")
        if ref in self._role_proofs:
            proof = self._role_proofs[ref]
            if strict_choices and not proof[3] <= set(env.choices):
                raise ValueError("hypothesis requires unselected upstream analytical choices")
            return proof
        role = self.resolve(ref, "roles")
        basis = role["basis"]
        if basis["kind"] != "contextual_proposal" or basis["status"] != "private_proposal":
            raise ValueError("context selection must preserve private hypothesis standing")

        def local(key):
            return member_reference(ref.product, key)

        owner, member = local(role["owner"]), local(role["member"])
        self._endpoint(owner)
        self._endpoint(member)
        premises = [self.resolve(local(key)) for key in basis.get("premises", ())]
        hypotheses = [
            p
            for p in premises
            if p.get("kind", "").startswith("contextual.") and p.get("status") == "private_proposal"
        ]
        if hypotheses:
            if not any(
                {role["owner"], role["member"]} <= set(h.get("premises", ())) for h in hypotheses
            ):
                raise ValueError("hypothesis role endpoints differ from its retained witness")
            model_requirements = {
                choice
                for hypothesis in hypotheses
                for choice in self._requirements(local(hypothesis["local_id"]), hypothesis)
            }
        else:
            model_requirements = self._authenticate_model_role(ref, role, premises)
        required = set(self._requirements(ref, role)) | set(self._requirements(ref, basis))
        required.update(model_requirements)
        required.update(member_reference(ref.product, key) for key in basis.get("choice_refs", ()))
        for endpoint in (owner, member):
            required.update(self._requirements(endpoint, self.resolve(endpoint)))
            original = self._endpoint(endpoint)
            required.update(self._requirements(original, self.resolve(original)))
        original_owner, original_member = self._endpoint(owner), self._endpoint(member)
        original = self.resolve(original_owner)
        if role["role"] == "declared_binding_site" and not (
            original.get("kind") == "binder"
            and original_owner.product == original_member.product
            and any(
                edge["role"] == "variable" and edge.get("target") == original_member.local_id
                for edge in original.get("children", ())
            )
        ):
            raise ValueError(
                "binding hypothesis differs from the actual declared symbolic variable"
            )
        if role["role"].startswith("attribution_") and not (
            original.get("kind") == "attribution"
            and original_owner.product == original_member.product
            and any(
                edge["role"] == role["role"].removeprefix("attribution_")
                and edge.get("target") == original_member.local_id
                for edge in original.get("children", ())
            )
        ):
            raise ValueError(
                "attribution hypothesis differs from its actual symbolic content/source endpoint"
            )
        if role["role"] == "source_local_coreference_group_candidate" and not (
            original.get("kind") == "native.mention"
            and original.get("native_mention", {}).get("mapping_status") == "mapped"
            and self.resolve(original_member).get("kind") == "native.coreference_cluster"
            and original_owner.product == original_member.product
            and original_owner
            in self._membership_members.get((original_member, "native_member"), ())
        ):
            raise ValueError(
                "referent hypothesis differs from actual native mention/cluster membership"
            )
        if strict_choices and not required <= set(env.choices):
            raise ValueError("hypothesis requires unselected upstream analytical choices")
        proof = (role, owner, member, required)
        self._role_proofs[ref] = proof
        return proof

    def _authenticate_model_role(self, ref, role, premises):
        required = set()
        questions = [p for p in premises if p.get("kind") == "model.question"]
        proposals = [p for p in premises if p.get("kind") == "model.choice_proposal"]
        if not questions:
            raise ValueError("context role has no authenticated hypothesis or model question")
        owner = self.resolve(member_reference(ref.product, role["owner"]))
        member = self.resolve(member_reference(ref.product, role["member"]))
        if owner.get("kind") == "model.focus" and member.get("kind") == "model.candidate":
            if len(questions) != 1 or len(proposals) != 1:
                raise ValueError("model candidate role requires one retained question and proposal")
            question, proposal = questions[0], proposals[0]
            answer = question["model_answer"]
            selected = proposal.get("native_label")
            if (
                answer["state"] != "proposed"
                or selected not in answer.get("selected_keys", ())
                or question["local_id"] not in proposal.get("premises", ())
            ):
                raise ValueError("model role does not name a selected retained candidate")
            native = source_python(answer["native_answer"])
            request = native["request"]
            if (
                sha256(
                    json.dumps(
                        request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    ).encode()
                ).hexdigest()
                != answer["request_digest"]
            ):
                raise ValueError("model role request differs from its immutable determinant")
            frozen = request["interpretation"]
            candidate = next((c for c in frozen["candidates"] if c["key"] == selected), None)
            if (
                candidate is None
                or len(owner.get("external_premises", ())) != 1
                or len(member.get("external_premises", ())) != 1
            ):
                raise ValueError("model role endpoint is outside the offered candidate population")
            if owner["external_premises"][0] != frozen["focus"]["reference"] or member[
                "external_premises"
            ][0] not in [m["reference"] for m in candidate["members"]]:
                raise ValueError("model role endpoints differ from its selected frozen alternative")
            if len(candidate["members"]) > 1 and candidate["compatibility"] != "compatible":
                raise ValueError("multiple model hosts lack explicit compatible-set meaning")
            if frozen.get("candidate_list_digest") != answer["candidate_list_digest"]:
                raise ValueError("model candidate list differs from its retained digest")
            snapshot = frozen.get("frozen_candidates")
            if (
                not isinstance(snapshot, dict)
                or sha256(canonical_bytes(snapshot)).hexdigest() != answer["candidate_list_digest"]
                or snapshot.get("focus") != frozen["focus"]
                or snapshot.get("alternatives") != frozen["candidates"]
            ):
                raise ValueError(
                    "model candidate population differs from its complete frozen snapshot"
                )
            supports = candidate.get("hypothesis_supports", ())
            if supports:
                cited = {
                    canonical_bytes(value) for value in role["basis"].get("external_premises", ())
                }
                selected_supports = [
                    support
                    for support in supports
                    if {canonical_bytes(value) for value in support["premises"]} <= cited
                ]
                if len(selected_supports) != 1:
                    raise ValueError(
                        "model role does not preserve exactly one offered hypothesis support"
                    )
                support = selected_supports[0]
                required.update(
                    reference(value) for value in support.get("required_external_choices", ())
                )
                actual = set(self._requirements(ref, role))
                if not required <= actual:
                    raise ValueError(
                        "model role dropped its offered hypothesis choice requirements"
                    )
                witnesses = []
                for value in support["premises"]:
                    support_ref = reference(value)
                    if self.nodes.get(support_ref, (None, None))[0] == "roles":
                        proof = self._authenticate_role(
                            support_ref,
                            environment(context_layers=tuple(self.layers)),
                            strict_choices=False,
                        )
                        witnesses.append(proof)
                focus_ref = reference(frozen["focus"]["reference"])
                member_ref = self._endpoint(member_reference(ref.product, role["member"]))

                def supported(proof):
                    _row, source, target, _choices = proof
                    source, target = self._endpoint(source), self._endpoint(target)
                    if source != focus_ref:
                        return False
                    return target == member_ref or (
                        target.product == member_ref.product
                        and member_ref in self._referent_members.get(target, ())
                    )

                if not any(supported(proof) for proof in witnesses):
                    raise ValueError(
                        "model selected endpoint differs from its offered hypothesis relationship"
                    )
        elif owner.get("kind") in {"model.span_proposal", "model.choice_proposal"} and member.get(
            "kind"
        ) in {"model.span_proposal", "model.choice_proposal"}:
            for endpoint in (owner, member):
                self._authenticate_proposal(member_reference(ref.product, endpoint["local_id"]))
            if not any(q["model_answer"]["state"] == "proposed" for q in questions):
                raise ValueError("source-first relation has no proposed question answer")
        else:
            raise ValueError("model role has unsupported endpoint meanings")
        return required

    def _authenticate_proposal(self, ref):
        node = self.resolve(ref, "annotations")
        if (
            node.get("kind") not in {"model.span_proposal", "model.choice_proposal"}
            or node["status"] != "private_proposal"
        ):
            raise ValueError("selected model proposal has no private source-language standing")
        questions = [
            self.resolve(member_reference(ref.product, key)) for key in node.get("premises", ())
        ]
        questions = [q for q in questions if q.get("kind") == "model.question"]
        if len(questions) != 1:
            raise ValueError("model proposal requires its unique source-bound question")
        answer = questions[0]["model_answer"]
        supported = answer["state"] == "proposed" or (
            answer["state"] == "observed"
            and answer["answer_kind"] == "gliner_span"
            and node.get("native_scheme") == "gliner-decoded-literal-v1"
            and node["kind"] == "model.span_proposal"
        )
        if not supported or answer.get("source_field") != "/source":
            raise ValueError("model proposal requires its proposed source-bound question")
        if answer.get("candidate_list_digest") and node.get("native_label") not in answer.get(
            "selected_keys", ()
        ):
            raise ValueError("model candidate proposal differs from its selected durable key")
        return node

    def authenticate(self, env: Environment):
        if env in self._verified:
            return
        if any(pin not in self.layers for pin in env.context_layers):
            raise ValueError("environment selects an unavailable context revision")
        self._validate_choices(env)
        for role in env.hypotheses:
            self._authenticate_role(role, env)
        for proposal in env.proposals:
            if proposal.product not in env.context_layers:
                raise ValueError("model proposal is outside selected context revisions")
            self._authenticate_proposal(proposal)
            if not set(self._requirements(proposal, self.resolve(proposal))) <= set(env.choices):
                raise ValueError("model proposal requires unselected choices")
        for binding in env.bindings:
            binder = self.resolve(binding.binder, "terms")
            if (
                binder["kind"] != "binder"
                or binding.variable.product != binding.binder.product
                or not any(
                    e["role"] == "variable" and e.get("target") == binding.variable.local_id
                    for e in binder["children"]
                )
            ):
                raise ValueError("inherited binding differs from its actual symbolic declaration")
        for attribution in env.attribution:
            if self.resolve(attribution, "terms")["kind"] != "attribution":
                raise ValueError("inherited attribution is not a symbolic attribution")
        self._verified.add(env)

    def _support(self, node):
        result = []
        for oid in node.get("occurrences", ()):
            occurrence = self.occurrences[oid]
            self.output_occurrences.setdefault(oid, occurrence)
            result.append(oid)
        return result

    def _member_addresses(self, node):
        return tuple(
            (
                extent["projection"],
                extent["native_pointer"],
                extent.get("start"),
                extent.get("end"),
                extent["synthetic"],
            )
            for oid in node.get("occurrences", ())
            for extent in self.occurrences[oid]["extents"]
        )

    @staticmethod
    def _family(kind):
        return {
            "binder": "meaning.scope",
            "operator": "meaning.scope",
            "attribution": "meaning.attribution",
            "clause_relation": "meaning.attachment",
        }.get(kind, "meaning.predication")

    def _evidence_term(self, ref, env):
        node = self.resolve(ref)
        key = identity("context-evidence", [ref.values(), env.values()])
        self.terms.setdefault(
            key,
            dict(
                local_id=key,
                kind="participant",
                family="meaning.reference",
                vocabulary=EVALUATION_REVISION,
                value=node.get(
                    "value", node.get("native_label", node.get("kind", "context-evidence"))
                ),
                status="private_proposal",
                occurrences=self._support(node),
                external_premises=[ref.values()],
                required_external_choices=[
                    r.values() for r in _ordered((*env.choices, *self._requirements(ref, node)))
                ],
                provenance=["environment:" + env.digest],
            ),
        )
        return key

    def _referent_group_term(self, ref):
        """Reference one retained candidate group without materializing its members."""
        node = self.resolve(ref)
        key = identity("context-referent-group", [ref.values()])
        self.terms.setdefault(
            key,
            dict(
                local_id=key,
                kind="participant",
                family="meaning.reference",
                vocabulary=EVALUATION_REVISION,
                value=node.get("native_label", node["kind"]),
                status="private_proposal",
                occurrences=[],
                external_premises=[ref.values()],
                required_external_choices=[
                    r.values() for r in _ordered(self._requirements(ref, node))
                ],
            ),
        )
        return key

    def _model_fields(self, proposal, question, env, family):
        """Join staged located reads only through their retained question dependencies."""
        direct = set(question["model_answer"].get("depends_on", ()))
        cue_ids = {
            key
            for key in direct
            if self.resolve(member_reference(proposal.product, key))
            .get("model_answer", {})
            .get("question_key", "")
            .endswith("cue")
        }
        anchors = cue_ids or {question["local_id"]}
        roles = {
            "modal_cue": "cue",
            "modal_target": "target",
            "quantifier_cue": "quantifier_cue",
            "negative_cue": "negative_cue",
            "bound_participant": "variable",
            "restrictor": "restrictor",
            "quantifier_body": "body",
            "negative_target": "negative_target",
            "attribution_cue": "cue",
            "reporter": "reporter",
            "attributed_content": "content",
            "embedding_cue": "embedding_cue",
            "function_support": "support",
        }
        fields = {}
        for prior in self._model_questions.get(
            (proposal.product, question["model_answer"]["family"]), ()
        ):
            answer = prior["model_answer"]
            if answer["question_key"] not in roles:
                continue
            if prior["local_id"] not in direct and not set(answer.get("depends_on", ())) & anchors:
                continue
            offered = self._model_proposals.get((proposal.product, prior["local_id"]), ())
            if len(offered) != 1:
                continue
            ref = member_reference(proposal.product, offered[0]["local_id"])
            self._authenticate_proposal(ref)
            applicable = self._assuming(env, self._requirements(ref, offered[0]))
            self.authenticate(applicable)
            term = self._evidence_term(ref, applicable)
            self.terms[term]["family"] = family
            fields[roles[answer["question_key"]]] = (term, ref)
        return fields

    def _model_meaning(self, proposal, node, question, selected, evidence, env, family):
        fields = self._model_fields(proposal, question, env, family)
        answer = question["model_answer"]
        key = identity("model-meaning", [proposal.values(), selected, env.values()])
        name = answer["question_key"]
        kind = "attribution" if name == "stance" and family == "meaning.attribution" else "operator"
        value = (
            "modality:" + selected
            if name == "modal_force"
            else "relative_scope:" + selected
            if name == "relative_scope"
            else "attribution:" + selected
            if kind == "attribution"
            else ("function:" if family == "meaning.function" else "proposed:") + selected
        )
        children = [
            dict(role="proposal", target=evidence, structural=True),
            *[
                dict(role=role, target=term, structural=True)
                for role, (term, _ref) in fields.items()
            ],
        ]
        if (
            name == "relative_scope"
            and selected in {"negative_over_quantifier", "quantifier_over_negative"}
            and {"variable", "restrictor", "body", "quantifier_cue", "negative_cue"}
            <= fields.keys()
        ):
            body_term = fields["body"][0]
            negative = identity("model-negative", [key, selected])
            binder = identity("model-binder", [key, selected])
            binder_children = [
                dict(role=role, target=fields[role][0], structural=True)
                for role in ("variable", "restrictor")
            ]
            binder_children.append(
                dict(role="cue", target=fields["quantifier_cue"][0], structural=True)
            )
            negative_children = [
                dict(role="cue", target=fields["negative_cue"][0], structural=True)
            ]
            if selected == "negative_over_quantifier":
                binder_children.append(dict(role="body", target=body_term, structural=True))
                negative_children.append(dict(role="target", target=binder, structural=True))
                root = negative
            else:
                negative_children.append(dict(role="target", target=body_term, structural=True))
                binder_children.append(dict(role="body", target=negative, structural=True))
                root = binder
            for local_id, term_kind, term_value, edges in (
                (binder, "binder", "source-quantified-proposal", binder_children),
                (negative, "operator", "negation", negative_children),
            ):
                self.terms[local_id] = dict(
                    local_id=local_id,
                    family=family,
                    kind=term_kind,
                    vocabulary=EVALUATION_REVISION,
                    value=term_value,
                    status="private_proposal",
                    children=edges,
                    occurrences=self.terms[evidence]["occurrences"],
                    external_premises=[
                        proposal.values(),
                        *[ref.values() for _term, ref in fields.values()],
                    ],
                    required_external_choices=[r.values() for r in env.choices],
                )
            children.append(dict(role="scoped_proposal", target=root, structural=True))
        self.terms[key] = dict(
            local_id=key,
            family=family,
            kind=kind,
            vocabulary=EVALUATION_REVISION,
            value=value,
            status="private_proposal",
            occurrences=self.terms[evidence]["occurrences"],
            children=children,
            external_premises=[proposal.values()],
            required_external_choices=[r.values() for r in env.choices],
        )
        return key

    def evaluate(self, ref: MemberReference, env: Environment, *, depth=0) -> str:
        self.authenticate(env)
        self.check_active()
        cache = (ref, env)
        if cache in self.memo:
            return self.memo[cache]
        if cache in self._active:
            raise ValueError("context evaluation encountered a structural cycle")
        if len(self.memo) > self.max_nodes or depth > 256:
            raise ValueError("context evaluation exceeds declared node/depth bounds")
        source = self.resolve(ref, "terms")
        required = self._requirements(ref, source)
        if not set(required) <= set(env.choices):
            raise ValueError("symbolic root requires unselected upstream analytical choices")
        self._active.add(cache)
        try:
            key = identity("evaluated", [ref.values(), env.values(), EVALUATION_REVISION])
            children = []
            binding_env = env
            if source["kind"] == "binder":
                variable = next(
                    e.get("target") for e in source["children"] if e["role"] == "variable"
                )
                if variable is None:
                    raise ValueError("binder variable is not an exact symbolic term")
                binding_env = replace(
                    env,
                    bindings=(
                        *env.bindings,
                        Binding(member_reference(ref.product, variable), ref),
                    ),
                )
            attribution_env = (
                replace(env, attribution=(*env.attribution, ref))
                if source["kind"] == "attribution"
                else env
            )
            for edge in source.get("children", ()):
                inherited = (
                    binding_env
                    if source["kind"] == "binder" and edge["role"] == "body"
                    else attribution_env
                    if source["kind"] == "attribution"
                    and edge["role"] in {"content", "body", "target"}
                    else env
                )
                if "target" in edge:
                    target = member_reference(ref.product, edge["target"])
                    child = self.evaluate(target, inherited, depth=depth + 1)
                    children.append(
                        dict(
                            role=edge["role"],
                            target=child,
                            structural=True,
                            **({"order": edge["order"]} if "order" in edge else {}),
                        )
                    )
                else:
                    group = next(
                        g
                        for g in self.payloads[ref.product]["choices"]
                        if g["local_id"] == edge["choice_group"]
                    )
                    selected = [
                        m
                        for m in group["members"]
                        if member_reference(ref.product, m["local_id"]) in env.choices
                    ]
                    if len(selected) > 1:
                        raise ValueError("single-valued symbolic site has several selected roots")
                    if selected:
                        child = self.evaluate(
                            member_reference(ref.product, selected[0]["root"]),
                            inherited,
                            depth=depth + 1,
                        )
                        children.append(dict(role=edge["role"], target=child, structural=True))
                    else:
                        gid = identity(
                            "evaluated-site",
                            [ref.product.values(), group["local_id"], inherited.values()],
                        )
                        members = []
                        for member in group["members"]:
                            upstream = member_reference(ref.product, member["local_id"])
                            branch = self._assuming(
                                inherited, (upstream, *self._requirements(upstream, member))
                            )
                            try:
                                child = self.evaluate(
                                    member_reference(ref.product, member["root"]),
                                    branch,
                                    depth=depth + 1,
                                )
                            except ValueError as error:
                                self._mark(self._family(source["kind"]), str(error))
                                continue
                            members.append(
                                dict(
                                    local_id=identity(
                                        "evaluated-alternative", [gid, upstream.values()]
                                    ),
                                    root=child,
                                    external_premises=[upstream.values()],
                                    required_external_choices=[r.values() for r in branch.choices],
                                )
                            )
                        if not members:
                            raise ValueError(
                                "symbolic choice site has no compatible supported branch"
                            )
                        self.groups[gid] = dict(
                            local_id=gid,
                            family=self._family(source["kind"]),
                            compatibility=group["compatibility"],
                            members=members,
                        )
                        children.append(dict(role=edge["role"], choice_group=gid, structural=True))
                        self._mark(
                            self._family(source["kind"]),
                            "upstream symbolic choice remains unresolved",
                        )
            status = source["status"]
            if env.attribution and source["kind"] in {"predicate", "clause_relation"}:
                status = "private_proposal"
            self.terms[key] = dict(
                local_id=key,
                kind=source["kind"],
                family=self._family(source["kind"]),
                vocabulary=EVALUATION_REVISION,
                value=source["value"],
                status=status,
                children=children,
                occurrences=self._support(source),
                external_premises=[ref.values()],
                required_external_choices=[r.values() for r in env.choices],
                provenance=["environment:" + env.digest],
            )
            self.memo[cache] = key
            self._links(ref, key, env)
            return key
        finally:
            self._active.remove(cache)

    def _relation(
        self,
        owner,
        member,
        role,
        support,
        env,
        *,
        family="meaning.reference",
        support_occurrences=None,
    ):
        key = identity("evaluated-role", [owner, member, role, support.values(), env.values()])
        self.roles.setdefault(
            key,
            dict(
                local_id=key,
                owner=owner,
                member=member,
                role=role,
                scheme=EVALUATION_REVISION,
                family=family,
                occurrences=list(dict.fromkeys(support_occurrences))
                if support_occurrences is not None
                else list(
                    dict.fromkeys(
                        (
                            *self.terms[owner].get("occurrences", ()),
                            *self.terms[member].get("occurrences", ()),
                        )
                    )
                ),
                required_external_choices=[r.values() for r in env.choices],
                basis=dict(
                    kind="contextual_proposal",
                    status="private_proposal",
                    external_premises=[support.values()],
                ),
            ),
        )

    def _links(self, ref, key, env):
        for binding in env.bindings:
            if binding.variable == ref:
                target = self._evidence_term(binding.binder, env)
                self._relation(key, target, "linguistic-bound-variable", binding.binder, env)
        for attribution in env.attribution:
            self._relation(
                key,
                self._evidence_term(attribution, env),
                "reported-content-context",
                attribution,
                env,
                family="meaning.attribution",
            )
        self.available(env)
        candidates = list(self._available_owners[env.context_layers].get(ref, ()))
        source = self.resolve(ref)
        if source["kind"] == "participant" and source.get("occurrences"):
            candidates.extend(
                self._available_addresses[env.context_layers].get(
                    self._member_addresses(source), ()
                )
            )
        for selected in _ordered((*env.hypotheses, *candidates)):
            forced = selected in env.hypotheses
            try:
                role, owner, member, required = self._authenticate_role(
                    selected, env, strict_choices=forced
                )
            except ValueError as error:
                if forced:
                    raise
                self._mark("meaning.reference", str(error))
                continue
            original_owner = self._endpoint(owner)
            owner_node = self.resolve(original_owner)
            matches = original_owner == ref or (
                original_owner.product == ref.product
                and owner_node.get("kind") == "construction"
                and ref in self._membership_members.get((original_owner, "meaning"), ())
            )
            matches = matches or (
                owner_node.get("kind") in {"native.mention", "model.span_proposal"}
                and source.get("kind") == "participant"
                and bool(owner_node.get("occurrences"))
                and self._member_addresses(owner_node) == self._member_addresses(source)
            )
            if not matches:
                continue
            try:
                applicable = self._assuming(env, required)
                self.authenticate(applicable)
            except ValueError:
                # The retained candidate is incompatible with this branch. It remains
                # available in its original layer and in other compatible branches.
                if forced:
                    raise
                continue
            marker = (key, selected)
            if marker in self._attached:
                continue
            self._attached.add(marker)
            original_member = self._endpoint(member)
            if role["role"] == "source_local_coreference_group_candidate":
                members = self._referent_members.get(original_member, ())
                if len(members) <= 1:
                    self._mark(
                        "meaning.reference",
                        "native cluster supplies no distinct source-local referent candidate",
                    )
                    continue
                self._relation(
                    key,
                    self._referent_group_term(original_member),
                    "source-local-referent-group-candidate",
                    selected,
                    applicable,
                    support_occurrences=[*self._support(owner_node), *self._support(role)],
                )
            else:
                self._relation(
                    key,
                    self._evidence_term(original_member, applicable),
                    role["role"],
                    selected,
                    applicable,
                    family="meaning.attachment"
                    if "host" in role["role"]
                    else "meaning.attribution"
                    if "attribution" in role["role"]
                    else "meaning.reference",
                )

    def facts(self, scope, operation, roots, env):
        self.authenticate(env)
        if not roots:
            roots = self.default_roots(env)
        output_roots = []
        for ref in roots:
            try:
                root = self.evaluate(ref, env)
            except ValueError as error:
                source = self.resolve(ref, "terms")
                family = self._family(source["kind"])
                self._mark(family, str(error))
                root = identity("unresolved-evaluation", [ref.values(), env.values(), str(error)])
                self.terms[root] = dict(
                    local_id=root,
                    family=family,
                    kind="unknown",
                    vocabulary=EVALUATION_REVISION,
                    value="unresolved-contextual-evaluation",
                    status="unknown",
                    occurrences=self._support(source),
                    external_premises=[ref.values()],
                )
            output_roots.append(root)
            wrapper = identity("contextual-reading", [ref.values(), env.values()])
            self.terms[wrapper] = dict(
                local_id=wrapper,
                family=self._family(self.resolve(ref)["kind"]),
                kind="unknown",
                vocabulary=EVALUATION_REVISION,
                value="contextual-reading",
                status="unknown" if self.diagnostics else "interpreted",
                children=[dict(role="reading", target=root, structural=True)],
                occurrences=self.terms[root]["occurrences"],
                external_premises=[ref.values()],
                required_external_choices=[r.values() for r in env.choices],
            )
        _, available_proposals = self.available(env)
        for proposal in _ordered((*env.proposals, *available_proposals)):
            forced = proposal in env.proposals
            try:
                node = self._authenticate_proposal(proposal)
                applicable = self._assuming(env, self._requirements(proposal, node))
                self.authenticate(applicable)
            except ValueError as error:
                if forced:
                    raise
                self._mark("meaning.scope", str(error))
                continue
            term = self._evidence_term(proposal, applicable)
            family = node["family"]
            target_family = (
                "meaning.function"
                if "function" in family
                else "meaning.attribution"
                if "attribution" in family
                else "meaning.reference"
                if "referent" in family
                else "meaning.attachment"
                if "host" in family
                else "meaning.scope"
            )
            self.terms[term]["family"] = target_family
            question = next(
                self.resolve(member_reference(proposal.product, key))
                for key in node["premises"]
                if self.resolve(member_reference(proposal.product, key)).get("kind")
                == "model.question"
            )
            answer = question["model_answer"]
            if not answer.get("candidate_list_digest"):
                for selected in answer.get("selected_keys", ()):
                    self._model_meaning(
                        proposal, node, question, selected, term, applicable, target_family
                    )
                if target_family != "meaning.function":
                    self._mark(
                        target_family,
                        "source-first model proposal retains bounded private support; "
                        "unspecified symbolic links remain unresolved",
                    )
        for ref in env.hypotheses:
            if not any(selected == ref for _, selected in self._attached):
                self._mark(
                    "meaning.reference",
                    "selected contextual hypothesis has no exact evaluated symbolic owner",
                )
        for pin in env.context_layers:
            for coverage in self.payloads[pin]["coverage"]:
                if coverage["outcome"] in {"complete", "empty"}:
                    continue
                upstream = coverage["family"]
                family = (
                    "meaning.reference"
                    if any(
                        key in upstream
                        for key in ("reference", "referent", "mention", "cluster", "binding")
                    )
                    else "meaning.attribution"
                    if "attribution" in upstream
                    else "meaning.function"
                    if "function" in upstream
                    else "meaning.scope"
                    if any(key in upstream for key in ("scope", "modal", "cue"))
                    else "meaning.attachment"
                )
                self._mark(
                    family,
                    "selected "
                    + upstream
                    + " is "
                    + coverage["outcome"]
                    + ": "
                    + coverage.get("reason", "context coverage incomplete"),
                )
        symbolic = [
            body
            for pin, body in self.payloads.items()
            if pin in self.symbolic_layers
            and pin not in env.context_layers
            and (isinstance(pin,DataProductReference) or body["operation"]["key"] == "text.constructions")
        ]
        if not symbolic and not roots:
            self._mark(
                "meaning.predication", "required symbolic construction producer is not selected"
            )
            self.unavailable_families.add("meaning.predication")
        for body in symbolic:
            for coverage in body["coverage"]:
                if coverage["outcome"] not in {"complete", "empty"}:
                    family = (
                        "meaning.scope"
                        if "scope" in coverage["family"]
                        else "meaning.attribution"
                        if "attribution" in coverage["family"]
                        else "meaning.function"
                        if "function" in coverage["family"]
                        else "meaning.predication"
                        if any(
                            k in coverage["family"]
                            for k in ("predication", "inflection", "source_readings")
                        )
                        else "meaning.attachment"
                    )
                    self._mark(
                        family,
                        "symbolic "
                        + coverage["family"]
                        + " is "
                        + coverage["outcome"]
                        + ": "
                        + coverage.get("reason", "symbolic coverage incomplete"),
                    )
        rows = []
        for family in EVALUATION_FAMILIES:
            incomplete = bool(self.family_diagnostics[family])
            unavailable = family in self.unavailable_families
            populated = (
                any(t["family"] == family for t in self.terms.values())
                or any(r["family"] == family for r in self.roles.values())
                or any(g["family"] == family for g in self.groups.values())
            )
            rows.append(
                dict(
                    family=family,
                    operation=operation["key"],
                    eligible=scope["selectors"],
                    examined=[] if unavailable else scope["selectors"],
                    unexamined=scope["selectors"] if unavailable else [],
                    availability="unavailable" if unavailable else "available",
                    outcome="unknown"
                    if unavailable
                    else "partial"
                    if incomplete
                    else "complete"
                    if populated
                    else "empty",
                    profile=EVALUATION_REVISION,
                    **(
                        {"reason": "; ".join(sorted(self.family_diagnostics[family]))}
                        if incomplete
                        else {}
                    ),
                )
            )
        return dict(
            outcome="partial" if self.diagnostics else "complete",
            coverage=rows,
            occurrences=list(self.output_occurrences.values()),
            terms=list(self.terms.values()),
            choices=list(self.groups.values()),
            annotations=[],
            memberships=[],
            roles=list(self.roles.values()),
        )

    def payload(self,release_id,scope,operation,roots,env):
        if not isinstance(self.base,LegacyProductPin):
            raise ValueError("source-native evaluator facts require their nominal product projection")
        return dict(
            format="characterization-layer-v1",base_document=self.base.values(),release_id=release_id,
            source_scope=scope,
            operation={**operation,"produced_families":list(EVALUATION_FAMILIES),"required_layers":[pin.values() for pin in self.layers],"outcomes":["complete","partial","failed"],"preconditions":["exact-symbolic-context-and-choice-closure"],"effects":["retain-primary-contextual-meaning; preserve-private-standing"],"result_determinants":["runtime","grammar","configuration","input","context"]},
            dependencies=[pin.values() for pin in self.layers],
            **self.facts(scope,operation,roots,env),
        )

    def finish(self, prepared, scope, operation, roots, env, *, releases=None):
        return validate_layer(
            prepared,
            self.payload(prepared.release_id, scope, operation, roots, env),
            dependencies=self.layers,
            releases=releases,
        )
