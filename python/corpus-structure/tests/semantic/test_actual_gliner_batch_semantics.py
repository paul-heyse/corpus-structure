"""PE-S30 production CUDA packs on book inputs, without DDO/linguistic-quality claims.

Batch membership and source anchoring are required. Output/label/confidence changes
are recorded separately; this does not require numerical or classification invariance.
"""

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import pytest
import yaml

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.methods.characterization_resources import (
    GLiNERWork,
    LogicalProviderMember,
    ProviderExecution,
)
from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, map_literal
from corpus_structure.methods.m1_source import M1Config, configured_pack_variants
from corpus_structure.methods.model_observation import declared_policy
from corpus_structure.methods.native_host import payload_digest
from corpus_structure.methods.native_profiles import gliner_selection, preflight_native_runtime
from corpus_structure.methods.pm2_gliner_classification import (
    ClassificationProfile,
    authenticated_gliner_report,
    classification_request,
)
from corpus_structure.semantic.cpu_execution import OwnedByteBudget
from corpus_structure.semantic.declared_structural_calls import _passage
from corpus_structure.semantic.definition_model_products import definition_request
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.model_characterization import gliner_cue_request
from semantic.provider_book_panel_support import ROOT, book_panel, panel_release

pytestmark = [
    pytest.mark.provider_evidence,
    pytest.mark.gpu,
    pytest.mark.prerequisite("provider_book_panel"),
    pytest.mark.prerequisite("gliner_panel_snapshot"),
    pytest.mark.xdist_group("pe-s30-gliner-book-panel"),
]


@dataclass(frozen=True)
class PackCase:
    name: str
    pack: GlinerPack
    inputs: tuple[GlinerInput, ...]
    threshold: float
    overlap: str


@dataclass(frozen=True)
class GlinerObservation:
    pack: str
    grouping: str
    members: int
    physical_cohorts: int
    literal_spans: int
    changed_outputs: int
    changed_label_or_span_structure: int
    max_shared_confidence_deviation: float | None
    cohort_digests: tuple[str, ...]


def _packs(prepared, panel, profile, cfg):
    families = declared_families(prepared.registry_rows)
    inference = declared_policy(prepared)["inference"]
    classification = ClassificationProfile(
        provider="gliner", device="cuda", profile=profile, threshold=0.5
    )
    cues, choices, definitions = [], [], []
    for source in panel:
        cues.append(
            gliner_cue_request(
                prepared.release_id, families["character_gliner_cues_v1"], source.scope
            )
        )
        family = families["character_gliner_function_v1"]
        choices.append(
            classification_request(
                prepared.release_id,
                family,
                family.questions[0].key,
                source.scope.mapping,
                classification,
                inference,
                characterization_family=family.family,
            )
        )
        _, passage = _passage(
            source.frame,
            passage_id=source.selector,
            start=0,
            end=len(source.frame.text),
            scope="explicit book excerpt",
        )
        definitions.append(
            definition_request(prepared, source.frame, passage, profile, threshold=0.5)
        )
    cue_pack = cues[0][0]
    assert all(pack == cue_pack for pack, _ in cues)
    result = [PackCase("cues", cue_pack, tuple(item for _, item in cues), 0.5, "nested")]
    for name, requests in (("classification", choices), ("definition", definitions)):
        pack = GlinerPack(**requests[0]["pack"])
        assert all(GlinerPack(**value["pack"]) == pack for value in requests)
        assert len({value["threshold"] for value in requests}) == 1
        result.append(
            PackCase(
                name,
                pack,
                tuple(GlinerInput(**value["item"]) for value in requests),
                requests[0]["threshold"],
                "flat",
            )
        )
    for family, variants in configured_pack_variants(prepared, cfg).items():
        for variant, _anchor, pack in variants:
            result.append(
                PackCase(
                    "m1:" + family + ":" + variant,
                    pack,
                    tuple(
                        GlinerInput.from_context(source.scope.mapping.context) for source in panel
                    ),
                    cfg.threshold,
                    "flat",
                )
            )
    return {case.name: case for case in result}


@pytest.fixture(scope="module")
def gliner_panel():
    prepared = panel_release()
    panel = book_panel(prepared)
    selected = json.loads((ROOT / "domains/statistics/profiles/gliner.json").read_bytes())
    values = dict(selected["profile"]["parameters"]["gliner_profile"])
    values["artifact_hashes"] = tuple(tuple(pair) for pair in values["artifact_hashes"])
    profile = GlinerProfile(Path(selected["assets"]), **values)
    manifest = yaml.safe_load((ROOT / "domains/statistics/operations.yaml").read_bytes())
    cfg = M1Config.model_validate(
        yaml.safe_load((ROOT / manifest["primary_profile"]["m1"]["configuration"]).read_bytes())
    )
    assert cfg.profile() == profile, (
        "the production M1 and learned GLiNER profiles must share the selected model basis"
    )
    policy = CharacterizationExecutionPolicy(provider_threads=profile.threads)
    execution = ProviderExecution(OwnedByteBudget(policy.max_owned_bytes), policy)
    try:
        actual = preflight_native_runtime("gliner", profile.snapshot)
        execution.declare_native((gliner_selection(profile, actual["runtime_identity"]),))
        # Startup has its own bounded native-host contract. Per-exchange deadlines
        # below measure calls on that resident, rather than timing cold model load.
        execution.native_group.ensure(lambda: None)
        yield prepared, panel, profile, execution, _packs(prepared, panel, profile, cfg)
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def _exchange(execution, profile, case, groups, phase):
    handles = []
    try:
        for index, items in enumerate(groups):
            correlation = f"unadmitted:provider-panel:{case.name}:{phase}:{index}"
            logical = LogicalProviderMember(
                correlation,
                1,
                1,
                1,
                correlation,
                0,
                len(items),
                payload_digest([asdict(item) for item in items]),
            )
            work = GLiNERWork(
                profile,
                case.pack,
                tuple(items),
                case.threshold,
                case.overlap,
                correlation,
                (lambda: None,),
                logical_members=(logical,),
            )
            handle = execution.try_submit(work)
            assert handle is not None, "bounded panel unexpectedly exhausted provider admission"
            handles.append(handle)
        for handle in handles:
            handle.flush()
        result = []
        for handle in handles:
            handle.future.result(timeout=profile.timeout_seconds + 30)
            reply = handle.collect()
            assert reply is not None
            assert reply.error_type is None, (reply.error_type, reply.error_message)
            receipt = reply.execution_receipt
            assert receipt is not None and receipt.physical and receipt.logical_members
            assert len(reply.reports) == len(handle.request.inputs)
            assert receipt.native_member_digests == tuple(
                payload_digest(asdict(item)) for item in handle.request.inputs
            )
            result.append((handle.request.inputs, reply))
        return result
    finally:
        for handle in handles:
            if not handle.future.done():
                handle.cancel()
        for handle in handles:
            if handle.future.done():
                handle.retire()


def _literal_spans(value, structures, path=()):
    if len(path) >= 2 and path[0] in structures:
        field = next(
            (field for field in structures[path[0]]["fields"] if field["name"] == path[1]), None
        )
        if field is not None and field.get("choices"):
            return
    if isinstance(value, dict):
        if {"text", "start", "end"} <= value.keys():
            yield value
            return
        for key, child in value.items():
            yield from _literal_spans(child, structures, (*path, key))
    elif isinstance(value, list):
        for child in value:
            yield from _literal_spans(child, structures, path)


def _shape_and_scores(value, path=()):
    if type(value) is float:
        assert math.isfinite(value), "native confidence observation is not finite"
        return "native-float-observation", {path: value}
    if isinstance(value, dict):
        shape, scores = {}, {}
        for key, child in value.items():
            if key in {"score", "confidence", "probability"} and type(child) in {float, int}:
                scores[(*path, key)] = float(child)
            else:
                shape[key], part = _shape_and_scores(child, (*path, key))
                scores.update(part)
        return shape, scores
    if isinstance(value, list):
        shape, scores = [], {}
        for index, child in enumerate(value):
            member, part = _shape_and_scores(child, (*path, index))
            shape.append(member)
            scores.update(part)
        return shape, scores
    return value, {}


@pytest.mark.parametrize(
    "pack_name",
    [
        "cues",
        "classification",
        "definition",
        "m1:definition:default",
        "m1:assertion:default",
        "m1:measurement:default",
        "m1:table:default",
        "m1:formula_context:default",
    ],
)
def test_actual_gliner_production_packs_keep_member_attribution_across_cohorts(
    gliner_panel, pack_name, request
):
    prepared, panel, profile, execution, packs = gliner_panel
    case = packs[pack_name]
    classification = ClassificationProfile(
        provider="gliner", device="cuda", profile=profile, threshold=case.threshold
    )
    inference = declared_policy(prepared)["inference"]
    structures = json.loads(case.pack.declaration_json).get("structures", {})
    by_context = {item.context_id: source for item, source in zip(case.inputs, panel, strict=True)}
    baseline = {}
    observations = []

    def inspect(groups, phase):
        replies = _exchange(execution, profile, case, groups, phase)
        members, spans, changed, changed_shape = 0, 0, 0, 0
        deviations = []
        digests = set()
        for items, reply in replies:
            digests.add(reply.execution_receipt.cohort_digest)
            for item, report in zip(items, reply.reports, strict=True):
                checked = authenticated_gliner_report(
                    dict(
                        pack=asdict(case.pack),
                        item=asdict(item),
                        threshold=case.threshold,
                        inference=inference,
                    ),
                    asdict(report),
                    classification,
                    overlap_policy=case.overlap,
                )
                source = by_context[item.context_id]
                for span in _literal_spans(checked.raw, structures):
                    if case.name == "definition":
                        # Definition extraction owns an explicit passage identity,
                        # not the whole source-context digest used by cues/M1.
                        _, window = _passage(
                            source.frame,
                            passage_id=source.selector,
                            start=0,
                            end=len(source.frame.text),
                            scope="explicit book excerpt",
                        )
                        assert checked.context_digest == item.context_digest == window.identity
                        assert item.text == window.text == source.frame.text
                        start, end, literal = span["start"], span["end"], span["text"]
                        assert type(start) is int and type(end) is int
                        assert 0 <= start < end <= len(item.text)
                        assert item.text[start:end] == literal
                        anchors = source.scope.mapping.context.map_span(start, end, literal=literal)
                    else:
                        anchors = map_literal(checked, source.scope.mapping.context, span)
                    assert anchors
                    for anchor in anchors:
                        assert source.frame.text[anchor.start : anchor.end] == anchor.quote
                    spans += 1
                shape, scores = _shape_and_scores(checked.raw)
                if phase == "singleton":
                    baseline[item.context_id] = checked.raw_json, shape, scores
                else:
                    original_json, original_shape, original_scores = baseline[item.context_id]
                    changed += checked.raw_json != original_json
                    changed_shape += shape != original_shape
                    deviations.extend(
                        abs(scores[key] - original_scores[key])
                        for key in scores.keys() & original_scores.keys()
                    )
                members += 1
        population = {item.context_id for items, _ in replies for item in items}
        assert members == len(population), "native reports duplicated a panel member"
        observations.append(
            GlinerObservation(
                case.name,
                phase,
                members,
                len(digests),
                spans,
                changed,
                changed_shape,
                max(deviations) if deviations else None,
                tuple(sorted(digests)),
            )
        )
        if phase == "cross-request-scatter":
            assert len(digests) == 1, (
                "compatible ready requests did not share the intended physical cohort"
            )
        return population

    request.node.user_properties.append(
        (
            "provider_panel_scope",
            "actual CUDA pack and receipt mechanism; no DDO admission, table geometry or linguistic-quality qualification",
        )
    )
    try:
        for item in case.inputs:
            inspect(((item,),), "singleton")
        expected = set(baseline)
        assert inspect((case.inputs,), "mixed") == expected
        assert inspect((tuple(reversed(case.inputs)),), "reversed") == expected
        regrouped = inspect((case.inputs[:2],), "regrouped-first-pair")
        regrouped |= inspect((case.inputs[2:],), "regrouped-second-pair")
        assert regrouped == expected
        assert inspect(tuple((item,) for item in case.inputs), "cross-request-scatter") == expected
    finally:
        request.node.user_properties.append(
            (
                "gliner_cohort_observations",
                json.dumps(
                    dict(
                        version="pe-s30-book-panel-v1",
                        profile=profile.fingerprint,
                        pack=case.pack.fingerprint,
                        sources=[
                            dict(
                                path=entry.path,
                                original_sha256=entry.original_digest,
                                selector=entry.selector,
                            )
                            for entry in panel
                        ],
                        observations=[asdict(value) for value in observations],
                    ),
                    sort_keys=True,
                ),
            )
        )
