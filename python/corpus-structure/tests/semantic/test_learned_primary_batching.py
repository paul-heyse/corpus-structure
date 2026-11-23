"""Controlled coroutine/scatter contracts; no actual provider qualification."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import ReadyGroup
from corpus_structure.methods.characterization_resources import ProviderReply, _execution_receipt
from corpus_structure.methods.gliner import CUDA_WHITESPACE_PROFILE
from corpus_structure.methods.gliner_worker import GlinerAdmission
from corpus_structure.methods.native_profiles import gliner_selection, pm2_selection
from corpus_structure.methods.pm2_products import ParserProducts
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.learned_primary import PreparedLearnedPrimary
from corpus_structure.semantic.observations import source_python
from semantic.model_characterization_support import d1_reply, gliner_profile, gliner_report, scope


def harness(monkeypatch, tmp_path, family, provider):
    from corpus_structure.methods import pm2_result
    from corpus_structure.semantic import (
        characterization_manifests,
        declared_candidate_products,
        declared_record_sources,
        interpretation_questions,
        sentence_products,
    )

    frame = scope("First. Second. Third.").mapping.context.primary
    blocks = tuple(
        SimpleNamespace(block_id=f"block:{index}", start=start, end=end)
        for index, (start, end) in enumerate(((0, 6), (7, 14), (15, 21)))
    )
    monkeypatch.setattr(
        declared_record_sources.DeclaredNativeFrameSource,
        "acquire",
        classmethod(lambda cls, *args, **kwargs: frame),
    )
    monkeypatch.setattr(sentence_products, "_blocks", lambda source: (blocks, ()))
    monkeypatch.setattr(
        sentence_products,
        "source_annotation_blocks",
        lambda _inventory: tuple(
            {"annotation": {"source": frame.pin.values(), "block_id": block.block_id}}
            for block in blocks
        ),
    )
    monkeypatch.setattr(interpretation_questions, "declared_families", lambda rows: {})
    monkeypatch.setattr(pm2_result, "_parser_products", lambda *args: ParserProducts({}, ()))
    monkeypatch.setattr(characterization_manifests, "manifest_contract", lambda *args: None)
    monkeypatch.setattr(characterization_manifests, "compact_manifest", lambda *args: {})
    monkeypatch.setattr(
        declared_candidate_products, "candidate_inspection_report", lambda *args, **kwargs: kwargs
    )
    selected = (
        gliner_selection(
            replace(gliner_profile().profile, snapshot=tmp_path, version=CUDA_WHITESPACE_PROFILE),
            {"controlled": "runtime"},
        )
        if provider == "gliner"
        else pm2_selection(provider, tmp_path, {"controlled": "runtime"}, {})
    )
    prepared = SimpleNamespace(
        registry_rows=(),
        release_id="controlled",
        index=SimpleNamespace(definitions={}),
        validate_json=lambda name, body: SimpleNamespace(
            model_dump=lambda **kwargs: json.loads(body)
        ),
    )
    questions = []
    providers = SimpleNamespace(
        policy=SimpleNamespace(max_provider_jobs=2),
        declare_native=lambda selections: None,
        work=lambda request, **kwargs: questions.append(request) or request,
    )
    owner = SimpleNamespace(
        providers=providers,
        reservation=object(),
        claim=SimpleNamespace(request_id="controlled", generation=1, task_id=2, attempt=1),
    )
    binding = SimpleNamespace(
        subject_context=SimpleNamespace(project_id="p"),
        roles=(SimpleNamespace(role="source", members=(object(),)),),
    )
    profile = PreparedLearnedPrimary(prepared, object(), family, provider, selected, 0.5, 65536)
    observation_kind = "Ddo" + profile.nominal_name + "Observations"
    prepared.index.definitions[observation_kind] = SimpleNamespace(
        iri="urn:controlled:" + observation_kind, abstract=False, ancestors=()
    )
    return (
        profile,
        SimpleNamespace(value=json.loads(frame.source_content)),
        binding,
        owner,
        blocks,
        questions,
    )


def finish(plan, value):
    with pytest.raises(StopIteration) as stopped:
        plan.send(value)
    return stopped.value.value


@pytest.mark.parametrize("family", ["dipo", "maverick"])
def test_independent_blocks_reduce_source_order_after_reverse_completion(
    monkeypatch, tmp_path, family
):
    from corpus_structure.semantic import learned_primary

    profile, source, binding, owner, blocks, questions = harness(
        monkeypatch, tmp_path, family, family
    )
    monkeypatch.setattr(
        learned_primary,
        "maverick_input",
        lambda annotation, frame, block, mapping: (
            mapping,
            {"text": mapping.provider_text},
        ),
    )
    plan = profile.run(
        source,
        binding=binding,
        annotations=object() if family == "maverick" else None,
        execution_owner=owner,
        check_active=lambda: None,
    )
    group = next(plan)
    assert isinstance(group, ReadyGroup) and group.max_active == 2
    assert len(group.plans) == 3
    requests = [next(child)[0] for child in group.plans]
    assert [request.logical_members[0].member for request in requests] == [
        block.block_id for block in blocks
    ]
    results = [None] * 3
    for index in (2, 1, 0):
        request = requests[index]
        native = {"outcome": "empty", "block": index}
        reply = ProviderReply(
            request.correlation,
            payload_content=canonical_bytes(native),
            execution_receipt=_execution_receipt(request, ()),
        )
        results[index] = finish(group.plans[index], (reply,))
    products = finish(plan, tuple(results))
    observations = json.loads(products.observation)["observations"]
    assert [source_python(value)["native"]["block"] for value in observations] == [0, 1, 2]
    assert len(products.provider_receipts) == 3 and len(questions) == 3


@pytest.mark.parametrize("producer", ["gliner_cues", "gliner_function"])
def test_gliner_multi_input_refusal_preserves_admitted_blocks_and_original_member_custody(
    monkeypatch, tmp_path, producer
):
    from corpus_structure.methods import model_observation
    from corpus_structure.semantic import interpretation_questions, model_characterization

    profile, source, binding, owner, blocks, questions = harness(
        monkeypatch, tmp_path, producer, "gliner"
    )
    cue = producer == "gliner_cues"
    question = SimpleNamespace(
        key="cue" if cue else "role",
        kind="text" if cue else "choice",
        instructions="exact cue",
        projection_role="cue",
        multiple=True,
        candidate_options=False,
        minimum_probability=None,
        options=(SimpleNamespace(key="function", criterion="a function"),),
    )
    family = SimpleNamespace(
        family=model_characterization.GLINER_CUES
        if cue
        else model_characterization.GLINER_FUNCTIONS,
        provider="gliner",
        digest="f" * 64,
        questions=(question,),
        focus_types=(),
        candidate_types=(),
        select_questions=lambda keys: (question,),
    )
    monkeypatch.setattr(
        interpretation_questions, "declared_families", lambda rows: {family.family: family}
    )
    monkeypatch.setattr(
        model_observation,
        "declared_policy",
        lambda prepared: model_observation.installed_policy()[0],
    )
    plan = profile.run(source, binding=binding, execution_owner=owner, check_active=lambda: None)
    first = next(plan)
    assert isinstance(first, tuple)
    (request,) = first
    assert len(questions) == 1 and len(request.inputs) == 3
    assert [member.member for member in request.logical_members] == [
        block.block_id for block in blocks
    ]
    assert [(member.start, member.count) for member in request.logical_members] == [
        (0, 1),
        (1, 1),
        (2, 1),
    ]
    raw = (
        {"entities": {"cue": []}} if cue else {"role": [{"label": "function", "confidence": 0.75}]}
    )
    reports = tuple(
        gliner_report(
            request.pack,
            item,
            request.profile,
            raw,
            overlap=request.overlap_policy,
            threshold=request.threshold,
        )
        for item in (request.inputs[0], request.inputs[2])
    )
    reply = ProviderReply(
        request.correlation,
        reports=reports,
        admissions=tuple(
            GlinerAdmission(
                index,
                item.context_id,
                item.context_digest,
                index != 1,
                "controlled member refusal" if index == 1 else None,
            )
            for index, item in enumerate(request.inputs)
        ),
        execution_receipt=_execution_receipt(request, ()),
    )
    group = plan.send((reply,))
    assert isinstance(group, ReadyGroup)
    results = []
    for child in group.plans:
        with pytest.raises(StopIteration) as stopped:
            next(child)
        results.append(stopped.value.value)
    products = finish(plan, tuple(results))
    value = json.loads(products.observation)
    assert value["coverage"][0]["examined"] == [
        {"projection": source.value["source"]["projection"], "start": block.start, "end": block.end}
        for block in (blocks[0], blocks[2])
    ]
    assert value["coverage"][0]["unexamined"][0]["start"] == blocks[1].start
    assert value["outcome"] == "partial" and len(products.provider_receipts) == 1
    report = json.loads(products.candidates)
    assert [row["outcome"] for row in report["coverage"]] == ["complete", "unsupported", "complete"]


@pytest.mark.parametrize("producer", ["d1_source", "d1_candidates"])
def test_d1_children_keep_stage_priors_local_when_blocks_advance_out_of_order(
    monkeypatch, tmp_path, producer
):
    from corpus_structure.methods import model_observation, pm2_interpretation_products
    from corpus_structure.methods.pm2_products import ParserProduct
    from corpus_structure.semantic import (
        interpretation_questions,
        learned_primary,
        model_characterization,
    )

    profile, source, binding, owner, blocks, _ = harness(monkeypatch, tmp_path, producer, "d1")
    family = SimpleNamespace(
        family="controlled.d1",
        source_field="/source",
        questions=(
            SimpleNamespace(key="first", stage=0, depends_on=()),
            SimpleNamespace(key="second", stage=1, depends_on=("first",)),
        ),
    )
    monkeypatch.setattr(
        interpretation_questions, "declared_families", lambda rows: {family.family: family}
    )
    monkeypatch.setattr(model_characterization, "D1_SOURCE_FAMILIES", (family.family,))
    monkeypatch.setattr(model_characterization, "CANDIDATE_FAMILIES", (family.family,))
    monkeypatch.setattr(model_characterization, "declared_model_dependencies", lambda *args: ())
    monkeypatch.setattr(
        model_characterization, "contextual_candidate_populations", lambda *args: (((),), True)
    )
    compiled = []

    def compile_stage(family, scope, stage, *, prior, candidates, keys):
        text = scope.mapping.provider_text
        assert set(prior) == (set() if stage == 0 else {"first"})
        if stage == 1:
            assert prior["first"]["origin"] == text
        compiled.append((text, stage))
        return SimpleNamespace(
            family=family, payload={"state": {"source": text}, "questions": keys}
        )

    monkeypatch.setattr(model_characterization, "compile_question_stage", compile_stage)
    monkeypatch.setattr(learned_primary, "learned_d1_evidence", lambda *args: {})
    monkeypatch.setattr(
        pm2_interpretation_products,
        "interpretation_products",
        lambda family, request, native, located: tuple(
            ParserProduct(
                key,
                "controlled.answer",
                {
                    "question_key": key,
                    "state": "proposed",
                    "origin": request["state"]["source"],
                },
                (),
            )
            for key in request["questions"]
        ),
    )
    plan = profile.run(source, binding=binding, execution_owner=owner, check_active=lambda: None)
    group = next(plan)
    assert isinstance(group, ReadyGroup) and group.max_active == 2
    requests = [next(child)[0] for child in group.plans]

    def answer(request):
        payloads = json.loads(request.payload)["batch"]
        header = {"provider": "d1", "profile": "a" * 64, "runtime": "b" * 64}
        members = [model_observation.pm2_member_digest(payload) for payload in payloads]
        native = []
        for index, payload in enumerate(payloads):
            value: dict[str, object] = dict(d1_reply(SimpleNamespace(payload=payload), {}))
            value["batch_receipt"] = dict(
                version=2,
                header=header,
                members=members,
                member_ordinal=index,
                digest=model_observation.pm2_cohort_digest(header, members),
            )
            native.append(value)
        return ProviderReply(
            request.correlation,
            payload_content=canonical_bytes({"batch": native}),
            execution_receipt=_execution_receipt(request, ()),
        )

    results = [None] * len(blocks)
    # Advance the final block through both stages while its siblings still await stage zero.
    for index in (2, 0, 1):
        (second,) = group.plans[index].send((answer(requests[index]),))
        assert json.loads(second.payload)["batch"][0]["questions"] == ["second"]
        results[index] = finish(group.plans[index], (answer(second),))
    products = finish(plan, tuple(results))
    assert compiled == [
        ("First.", 0),
        ("Second.", 0),
        ("Third.", 0),
        ("Third.", 1),
        ("First.", 1),
        ("Second.", 1),
    ]
    observations = [
        source_python(value) for value in json.loads(products.observation)["observations"]
    ]
    assert [row["request"]["state"]["source"] for row in observations] == [
        "First.",
        "First.",
        "Second.",
        "Second.",
        "Third.",
        "Third.",
    ]
    assert len(products.provider_receipts) == 6
