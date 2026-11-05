"""Evidence-wrapper controls; no database/provider or producer-truth oracle."""

import argparse
import importlib.util
import json
from pathlib import Path

import pytest

from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.semantic.identity import canonical_bytes


@pytest.fixture(scope="module")
def driver():
    path = Path(__file__).with_name("pce07_paired_assessment.py")
    spec = importlib.util.spec_from_file_location("pce07_output_test_driver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(driver):
    old = driver.foundation_driver()
    pin = dict(source="source:50", source_view_id=50, native_product_task_id=1,
        product_key="integrated", product_digest="a" * 64,
        projection_digest="b" * 64, recipe_digest="c" * 64)
    text = "The normal distribution is defined by its density."
    items = {"#/texts/1": dict(self_ref="#/texts/1", text=text)}
    piece = dict(pointer="#/texts/1", precision="exact", start=4, end=23,
        text="normal distribution")
    anchor = old.make_anchor(pin, "#/texts/1", "normal distribution", 4, 23, items)
    frame = assessment.OperationEvaluationFrame(unit=pin["source"], release_id="release-1",
        guideline_version="pce07-fresh-output-source-1", rubric_version="pce07-output-local-1",
        context_policy="exact-native-source-output-question-1",
        operation_question="retain_native_spans_attributes_relations",
        operation_version="native-local-contributions-2", domain="scientific-source",
        direction="output_first", pin=pin, anchor_ids=(anchor["anchor_id"],),
        contribution_ids=("frozen-role",))
    mention = dict(contribution_id="private-mention", kind="occurrence",
        semantic_type="entity.distribution", anchors=[anchor])
    # Deliberately wrong hidden output label; independent author answers must
    # remain defined_term and never acquire this value or its confidence.
    output = dict(contribution_id="frozen-role", kind="proposal", semantic_type="attribute.role",
        operation_key="local-op",
        anchors=[], endpoints=[dict(role="mention", contribution_id="private-mention")],
        value=dict(kind="text", text="mentioned_term"), score=0.999)
    interest = driver.source_interest(output, {"private-mention": mention},
        interest_id="interest-1", frame_key="operation1:unit2",
        question=frame.operation_question, version=frame.operation_version)
    entry = dict(interest_id="interest-1", selected_facet="conditional_role",
        source_state="stated", judgment="supported", inspected_scope=["#/texts/1"],
        primary=[piece], alternatives=[dict(fields=dict(value="defined_term"),
            anchor_endpoint_role="mention", endpoints=[dict(role="mention", anchors=[piece],
                fields=dict(semantic_type="entity.distribution"))])],
        explanation="The independently inspected source explicitly says is defined.", limitations=[])
    sources = {50: dict(pin=pin, items=items)}
    return dict(old=old, pin=pin, items=items, piece=piece, anchor=anchor, frame=frame,
        mention=mention, output=output, interest=interest, entry=entry, sources=sources)


def test_conditional_wrapper_uses_author_label_and_exact_source_only(driver, source):
    case, anchors = driver.serialize_output_case(source["entry"], source["interest"],
        dict(contribution=source["output"]), frame=source["frame"], sources=source["sources"],
        provenance=dict(actor="independent"), old=source["old"])
    assert case.contribution_kind == "proposal" and case.anchor_endpoint_role == "mention"
    assert case.alternatives[0]["value"] == dict(kind="text", text="defined_term")
    assert case.anchor_ids == (source["anchor"]["anchor_id"],)
    assert list(anchors) == [source["anchor"]["anchor_id"]]
    result = assessment.score_cases(source["frame"], (case,), (source["output"],),
        endpoint_closure=(source["mention"],))
    assert result["cases"][0]["judgment"] == "unsupported"
    assert result["cases"][0]["error_category"] == "wrong_structure"


@pytest.mark.parametrize("changed", [dict(text="Gaussian distribution"), dict(start=5),
    dict(precision="item"), dict(anchor_id="copied-generated-id")])
def test_independent_piece_refuses_wrong_native_text_offsets_or_generated_ids(driver, source, changed):
    with pytest.raises(ValueError):
        driver.output_author_anchor(dict(source["piece"], **changed),
            frame=source["frame"], sources=source["sources"], old=source["old"])


def test_author_expected_fields_cannot_select_model_score_or_generated_identity(driver, source):
    for field in ("score", "confidence", "contribution_id", "endpoint_semantics"):
        with pytest.raises(ValueError, match="never output IDs or scores"):
            driver.output_expected_fields({field: "copied"}, [source["anchor"]])


def test_directional_source_case_requires_explicit_primary_port_and_endpoints(driver, source):
    entry = dict(source["entry"], selected_facet="directional_source_association",
        alternatives=[dict(fields=dict(semantic_type="relation.alias_of"))])
    interest = dict(source["interest"], available_facets=["directional_source_association"])
    captured = dict(contribution=dict(source["output"], kind="relation"))
    with pytest.raises(ValueError, match="primary role and ordered endpoint"):
        driver.serialize_output_case(entry, interest, captured, frame=source["frame"],
            sources=source["sources"], provenance=dict(actor="independent"), old=source["old"])


def test_unassessed_source_answer_never_invents_expected_value(driver, source):
    entry = dict(source["entry"], judgment="unassessed", source_state="uninspected",
        primary=[], alternatives=[], explanation="Independent role question is not determined.")
    case, _ = driver.serialize_output_case(entry, source["interest"],
        dict(contribution=source["output"]), frame=source["frame"], sources=source["sources"],
        provenance=dict(actor="independent"), old=source["old"])
    assert case.alternatives == () and case.judgment == "unassessed"
    assert case.contribution_id == "frozen-role"


def make_artifacts(driver, source, tmp_path):
    def write(name, value):
        path = tmp_path / name
        path.write_bytes(canonical_bytes(value))
        return path

    key = "operation1:unit2"
    packet = dict(source_scopes=[dict(frame_key=key, pin=source["pin"],
        native_items=list(source["items"].values()), native_ancestors=[])],
        assessment_interests=[source["interest"]])
    packet_path = write("source-packet.json", packet)
    private_path = write("private-products.json", dict(selected_outputs=[dict(
        interest_id="interest-1", frame_key=key, contribution=source["output"])],
        endpoint_member_closure=[source["mention"], source["output"]]))
    selection = dict(protocol="pce07-frozen-output-frame-1",
        source_run_id=100, source_cut_id=200, release_id="release-1", runtime_id="runtime-1",
        frames={key: assessment.encode_frame(source["frame"])},
        author_source_packet=str(packet_path), private_product_capture=str(private_path),
        output_selection=dict(selected=1, contribution_ids=["frozen-role"]),
        operation_inventory=[dict(operation_key="local-op", question=source["frame"].operation_question,
            operation_version=source["frame"].operation_version)])
    selection_path = write("selection.json", selection)
    paths = {}
    for kind in "AB":
        paths[kind] = write(f"author-{kind}.json", dict(protocol=driver.OUTPUT_ANSWER_PROTOCOL,
            actor="independent-" + kind, model="controlled-source-author",
            source_packet_sha256=driver.digest(packet_path), cases=[source["entry"]]))
    paths["C"] = write("author-C.json", dict(protocol=driver.OUTPUT_ANSWER_PROTOCOL,
        actor="independent-C", model="controlled-source-author",
        source_packet_sha256=driver.digest(packet_path), cases=[source["entry"]],
        author_inputs=[dict(path=str(paths[kind]), sha256=driver.digest(paths[kind])) for kind in "AB"],
        adjudication_reasons=["Both source answers agree; independently verified exact span and cue."]))
    args = argparse.Namespace(selection=str(selection_path), author_a=str(paths["A"]),
        author_b=str(paths["B"]), author_c=str(paths["C"]))
    return args, paths, selection, packet_path


def test_full_fresh_wrapper_roundtrip_keeps_frozen_population_and_all_author_hashes(driver, source, tmp_path):
    args, paths, selection, _ = make_artifacts(driver, source, tmp_path)
    wrappers = driver.output_serialize(args, None, source["old"])
    frame = assessment.decode_frame(wrappers["frames"]["operation1:unit2"])
    assert frame.contribution_ids == source["frame"].contribution_ids
    assert frame.operation_question == source["frame"].operation_question
    assert frame.operation_version == source["frame"].operation_version
    assert frame.rubric_version == source["frame"].rubric_version
    for kind in "ABC":
        assert wrappers["source_author_artifacts"][kind]["sha256"] == driver.digest(paths[kind])
        authored = wrappers["payloads"]["operation1:unit2"][kind]["authored"]
        decoded = assessment.decode_authored(canonical_bytes(authored), frame)
        assert decoded["cases"][0].alternatives[0]["value"]["text"] == "defined_term"
    assert wrappers["output_selection"] == selection["output_selection"]
    assert wrappers["database_mutations"] is False


@pytest.mark.parametrize("fault", ("missing_interest", "source_hash", "C_inputs", "same_actor"))
def test_serialization_refuses_incomplete_or_rebound_independent_answers(driver, source, tmp_path, fault):
    args, paths, _, _ = make_artifacts(driver, source, tmp_path)
    kind = "C" if fault == "C_inputs" else "B"
    value = json.loads(paths[kind].read_bytes())
    if fault == "missing_interest":
        value["cases"] = []
    elif fault == "source_hash":
        value["source_packet_sha256"] = "wrong-packet"
    elif fault == "C_inputs":
        value["author_inputs"][0]["sha256"] = "wrong-input"
    else:
        value["actor"] = "independent-A"
    paths[kind].write_bytes(canonical_bytes(value))
    with pytest.raises(ValueError):
        driver.output_serialize(args, None, source["old"])


def test_capability_priority_covers_new_questions_amid_many_legacy_proposal_strata(driver):
    pool = {f"legacy-{index}": dict(kind="proposal", semantic_type=f"a-legacy-field-{index}",
        operation_question="recover", operation_version="1", value="withheld", score=0.99)
        for index in range(80)}
    for index, semantic_type in enumerate(driver.OUTPUT_PRIORITY_TYPES):
        kind = "relation" if semantic_type.startswith(("table.", "relation.")) else "proposal"
        for copy in range(3):
            pool[f"priority-{index}-{copy}"] = dict(kind=kind, semantic_type=semantic_type,
                operation_question="new-local" if kind == "proposal" else "attachments",
                operation_version="2", value="withheld", score=0.1)
    for marker in ("native", "returned"):
        pool[marker] = dict(kind="composite", semantic_type=f"table.{marker}_group",
            operation_question="recover", operation_version="1")
    pool["literal"] = dict(kind="occurrence", semantic_type="source_occurrence",
        operation_question="recover", operation_version="1")
    pool["diagnostic"] = dict(kind="diagnostic", semantic_type="parse_diagnostic",
        operation_question="parse", operation_version="2")
    chosen = driver.choose_outputs(pool)
    assert len(chosen) == len(set(chosen)) == 24
    assert set(driver.OUTPUT_PRIORITY_TYPES) <= {pool[identity]["semantic_type"] for identity in chosen}
    assert sum(pool[identity]["semantic_type"] == "attribute.role" for identity in chosen) >= 2
    assert {"native", "returned", "literal", "diagnostic"} <= set(chosen)
    assert chosen == driver.choose_outputs(dict(reversed(list(pool.items()))))
    changed = {identity: dict(row, value="different hidden value", score=0.99999)
        for identity, row in pool.items()}
    assert chosen == driver.choose_outputs(changed)


def test_contextual_support_is_preserved_without_becoming_product_owned_literal(driver, source):
    text = source['items']['#/texts/1']['text']
    supporting = dict(pointer='#/texts/1', precision='exact', start=0, end=len(text), text=text)
    alternative = dict(source['entry']['alternatives'][0], supporting_source_pieces=[supporting])
    entry = dict(source['entry'], alternatives=[alternative])
    case, anchors = driver.serialize_output_case(entry, source['interest'],
        dict(contribution=source['output']), frame=source['frame'], sources=source['sources'],
        provenance=dict(actor='independent'), old=source['old'])
    assert case.alternatives[0]['value'] == dict(kind='text', text='defined_term')
    assert 'source_pieces' not in case.alternatives[0]
    evidence = case.assessor_provenance['supporting_source_evidence'][0]
    assert evidence[0]['source_piece'] == text
    assert evidence[0]['anchor_id'] in anchors
    with pytest.raises(ValueError, match='independently authored exact anchors'):
        driver.output_expected_fields(dict(source_pieces=[text]), [source['anchor']])


def test_independent_exact_primary_can_supply_literal_without_hidden_product_value(driver, source):
    entry = dict(source['entry'], selected_facet='literal_extent_fidelity', alternatives=[])
    interest = dict(source['interest'], available_facets=['literal_extent_fidelity'])
    case, _ = driver.serialize_output_case(entry, interest,
        dict(contribution=dict(source['output'], value={'wrong': 'hidden'})),
        frame=source['frame'], sources=source['sources'], provenance=dict(actor='independent'),
        old=source['old'])
    assert case.alternatives[0]['source_pieces'] == ['normal distribution']
    assert 'value' not in case.alternatives[0]


def test_unresolved_ambiguity_does_not_require_invented_permissible_label(driver, source):
    entry = dict(source['entry'], judgment='ambiguous', source_state='unresolved', alternatives=[])
    case, _ = driver.serialize_output_case(entry, source['interest'],
        dict(contribution=source['output']), frame=source['frame'], sources=source['sources'],
        provenance=dict(actor='independent'), old=source['old'])
    assert case.judgment == 'ambiguous' and case.alternatives == ()


@pytest.mark.parametrize('kind', ['proposal', 'occurrence'])
def test_literal_facet_compares_source_pieces_not_metadata_or_absent_value(driver, source, kind):
    raw = dict(source['output'], kind=kind, anchors=[source['anchor']], endpoints=[],
        source_pieces=['normal distribution'])
    if kind == 'proposal':
        raw['value'] = {'kind': 'text', 'text': 'matcher metadata'}
    else:
        raw.pop('value')
    entry = dict(source['entry'], selected_facet='literal_extent_fidelity',
        alternatives=[dict(fields=dict(value='normal distribution'))])
    interest = dict(source['interest'], available_facets=['literal_extent_fidelity'])
    case, _ = driver.serialize_output_case(entry, interest, dict(contribution=raw),
        frame=source['frame'], sources=source['sources'], provenance=dict(actor='independent'),
        old=source['old'])
    assert 'value' not in case.alternatives[0]
    result = assessment.score_cases(source['frame'], (case,), (raw,))
    assert result['cases'][0]['judgment'] == 'supported'
    entry['alternatives'][0]['fields']['value'] = 'different literal'
    with pytest.raises(ValueError, match='ordered exact pieces'):
        driver.serialize_output_case(entry, interest, dict(contribution=raw),
            frame=source['frame'], sources=source['sources'], provenance=dict(actor='independent'),
            old=source['old'])


def test_item_only_empty_source_fact_remains_distinct_from_exact_literal_applicability(driver, source):
    entry = dict(source['entry'], selected_facet='literal_extent_fidelity', source_state='unstated',
        primary=[dict(pointer='#/texts/1', precision='item')],
        alternatives=[dict(fields=dict(value=''))])
    interest = dict(source['interest'], available_facets=['literal_extent_fidelity'])
    case, _ = driver.serialize_output_case(entry, interest,
        dict(contribution=dict(source['output'], kind='occurrence')), frame=source['frame'],
        sources=source['sources'], provenance=dict(actor='independent'), old=source['old'])
    assert case.judgment == 'unassessed' and case.alternatives == ()
    assert case.assessor_provenance['source_expectation_judgment'] == 'supported'
    assert case.assessor_provenance['fresh_source_answer']['source_state'] == 'unstated'
    assert 'item-only' in case.assessor_provenance['assessment_applicability']


def test_literal_normalization_never_concatenates_discontinuous_pieces(driver, source):
    pieces = [dict(pointer='#/texts/1', precision='exact', start=4, end=10, text='normal'),
        dict(pointer='#/texts/1', precision='exact', start=11, end=23, text='distribution')]
    entry = dict(source['entry'], selected_facet='literal_extent_fidelity', primary=pieces,
        alternatives=[dict(fields=dict(value='normaldistribution'))])
    interest = dict(source['interest'], available_facets=['literal_extent_fidelity'])
    with pytest.raises(ValueError, match='ordered exact pieces'):
        driver.serialize_output_case(entry, interest, dict(contribution=source['output']),
            frame=source['frame'], sources=source['sources'], provenance=dict(actor='independent'),
            old=source['old'])
    entry['alternatives'][0]['fields']['value'] = ['normal', 'distribution']
    case, _ = driver.serialize_output_case(entry, interest, dict(contribution=source['output']),
        frame=source['frame'], sources=source['sources'], provenance=dict(actor='independent'),
        old=source['old'])
    assert case.alternatives[0]['source_pieces'] == ['normal', 'distribution']
