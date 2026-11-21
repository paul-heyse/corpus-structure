"""Native HanLP heads preserve exact canonical addresses and independent standings."""

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic.canonical_sentences import CanonicalProduct
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.hanlp_products import (
    PreparedHanlpProfile,
    admitted_hanlp_rows,
    canonical_hanlp_rows,
    detach_hanlp_sentence,
    hanlp_admission_batches,
    hanlp_operation_sources,
    hanlp_product_inputs,
    hanlp_sentence_batches,
    prepare_hanlp_selection,
    resolve_hanlp_port,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.original_documents import original_document_subject
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.source_products import (
    FrozenNativeSource,
    native_projection_identity,
    source_subject,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from test_preparation import preparation_fixture


@preparation_fixture("hanlp_profile", scope="module")
def profile():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = hanlp_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(bundle)
    selection = prepare_hanlp_selection(Path("/home/paul/corpus-structure/build/models/pm2"))
    model = compile_data_operations(
        schema=bundle,
        python_sources=hanlp_operation_sources(selection),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return PreparedHanlpProfile(prepared, model, selection)


def inputs(profile, *, text="The mean is 2.", words=None, pieces=None, items=None):
    words = (
        [("The", 0, 3), ("mean", 4, 8), ("is", 9, 11), ("2", 12, 13), (".", 13, 14)]
        if words is None
        else words
    )
    pieces = (
        [
            dict(
                kind="native_text",
                start=0,
                end=len(text),
                item_ref="#/texts/0",
                source_field="text",
            )
        ]
        if pieces is None
        else pieces
    )
    items = (
        [dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)])]
        if items is None
        else items
    )
    projection = native_projection_identity(text, pieces, items)
    coordinate = dict(
        document="document:original",
        document_subject=original_document_subject("document:original"),
        section_pointer="#/texts/0",
        membership="direct",
        projection=projection,
    )
    selectors = [dict(projection=projection, native_pointer="#/texts/0")]
    source = FrozenNativeSource.acquire(
        profile.prepared,
        dict(
            source=coordinate,
            text=text,
            pieces=pieces,
            items=items,
            recognition=[],
            selectors=selectors,
        ),
    )
    from corpus_structure.semantic.characterization_manifests import (
        append_manifest,
        manifest_contract,
    )
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.sentence_partitions import SentenceBlock

    key = "#/texts/0"
    extent = len(text)
    rows: list[dict[str, Any]] = [
        dict(
            record_type="sentence",
            ordinal=0,
            start=0,
            end=extent,
            extent=extent,
            annotation=SemanticReference.item("inventory", "rows", key, ("sentence", 0)).values(),
        )
    ]
    for index, (_, start, end) in enumerate(words):
        rows.append(
            dict(
                record_type="token",
                ordinal=index,
                start=start,
                end=end,
                extent=extent,
                sentence=0,
                space=index < 3,
                role="prose",
                piece_indices=[0],
                annotation=SemanticReference.item(
                    "inventory", "rows", key, ("token", index)
                ).values(),
            )
        )
    value = append_manifest(
        dict(
            source=coordinate,
            selectors=selectors,
            outcome="complete",
            block_coverage=[
                dict(block_id=key, native_pointer=key, start=0, end=extent, outcome="complete")
            ],
            coverage=[],
        ),
        manifest_contract(profile.prepared, profile.model, "DdoCanonicalManifest"),
    )
    canonical = CanonicalProduct.from_projection(
        {"header": value, "partitions": [SentenceBlock(key, 0, 0, extent, tuple(rows)).packet()]},
        profile.prepared,
        profile.model,
        profile.prepared.index.definitions["DdoCanonicalSentences"].iri,
        subject_context=_publication_context(source),
    )
    ((sentence, tokens),) = canonical_hanlp_rows(source, canonical)
    return source, canonical, sentence, tokens


def test_detached_head_failures_preserve_valid_siblings_and_native_tree_groups(profile):
    _, canonical, sentence, tokens = inputs(profile)
    words = [word for _, word in tokens]
    preparation = dict(
        prepared_words=words,
        word_subwords=[[i] for i in range(1, 6)],
        input_ids=[100, 1, 2, 3, 4, 5, 101],
    )
    heads = dict(
        lemma=["the", "mean", "be", "2", "."],
        pos=["DT", "NN", "VBZ", "CD", "."],
        dependency=[[2, "det"], [3, "nsubj"], [0, "root"], [3, "attr"], [3, "punct"]],
        constituency=["S", [["NP", ["The", "mean"]], ["VP", ["is", "2"]], "."]],
        srl=[[["is", "PRED", 2, 3], ["The mean", "ARG0", 0, 2], ["2", "ARG1", 3, 4]]],
    )
    units, alignment, coverage = detach_hanlp_sentence(
        sentence, tokens, canonical, heads, preparation, "vocabulary:exact"
    )
    assert all(row["outcome"] == "complete" for row in coverage)
    assert alignment["input_ids"] == preparation["input_ids"]
    assert alignment["vocabulary_namespace"] == "vocabulary:exact"
    assert [unit["dependency_head"] for unit in units if unit["record_type"] == "token"] == [
        2,
        3,
        0,
        3,
        3,
    ]
    assert any(
        unit["record_type"] == "srl_group" and unit["roles"][0]["label"] == "PRED" for unit in units
    )
    assert any(
        unit["record_type"] == "constituent" and unit["path"] == [] and len(unit["tokens"]) == 5
        for unit in units
    )
    broken = {**heads, "dependency": [[0, "root"]] * 5}
    retained, _, standings = detach_hanlp_sentence(sentence, tokens, canonical, broken, preparation)
    assert (
        next(row for row in standings if row["family"] == "hanlp.dependency")["outcome"] == "failed"
    )
    assert all(
        unit.get("lemma") == heads["lemma"][unit["ordinal"]]
        for unit in retained
        if unit["record_type"] == "token"
    )
    assert (
        "input_ids" not in detach_hanlp_sentence(sentence, tokens, canonical, heads, preparation)[1]
    )


def test_actual_subword_lengths_bound_outer_batches_without_cutting_sentences():
    rows = [
        (dict(local_id=name), [(name + ":token", "unchanged")]) for name in ("one", "two", "three")
    ]
    ready, refused = admitted_hanlp_rows(
        rows,
        dict(
            outcome="prepared_batch",
            members=[
                dict(ordinal=ordinal, outcome="prepared", row_tokens=400) for ordinal in range(3)
            ],
        ),
    )
    assert not refused
    batches = hanlp_sentence_batches(
        ready, dict(max_sentences=8, max_padded_subwords=750, max_batch_chars=32768)
    )
    assert [[row[0]["local_id"] for row in batch] for batch in batches] == [
        ["one"],
        ["two"],
        ["three"],
    ]
    assert all(batch[0] is rows[index] for index, batch in enumerate(batches))
    ready, refused = admitted_hanlp_rows(
        rows[:1],
        dict(
            outcome="prepared_batch",
            members=[dict(ordinal=0, outcome="limited", reason="sentence_subwords", limit=512)],
        ),
    )
    assert not ready and refused[0][0] is rows[0]
    assert refused[0][1]["reason"] == "sentence_subwords"


@pytest.mark.parametrize(
    "members",
    [
        [],
        [dict(ordinal=1, outcome="prepared", row_tokens=400)],
        [dict(ordinal=0, outcome="prepared", row_tokens=0)],
        [dict(ordinal=0, outcome="prepared", row_tokens=True)],
    ],
)
def test_native_sentence_admission_refuses_changed_population_order_or_lengths(members):
    with pytest.raises(ValueError, match=r"population|order|subword length"):
        admitted_hanlp_rows(
            [(dict(local_id="one"), [("token", "unchanged")])],
            dict(outcome="prepared_batch", members=members),
        )


def test_current_hanlp_preserves_borrowed_host_cancellation_and_provider_failure(profile):
    source, canonical, _, _ = inputs(profile)

    class Cancelled(Exception):
        pass

    class Host:
        policy = CharacterizationExecutionPolicy()

        def __init__(self):
            self.declared = []
            self.requests = []

        def declare(self, selections):
            self.declared.extend(selections)

        def startup(self, selection, check_active):
            assert selection is profile.selection
            check_active()
            return dict(max_sentences=8)

        def infer_result(self, selection, payload, check_active):
            from corpus_structure.methods.pm2_worker import Pm2WorkerError

            assert selection is profile.selection
            self.requests.append(payload)
            raise Pm2WorkerError("controlled actual-provider failure boundary")

        def close(self):
            pytest.fail("producer closed invocation-owned host")

    host = Host()

    def cancel():
        raise Cancelled("native task lease lost")

    with pytest.raises(Cancelled, match="lease lost"):
        profile.run(source, canonical, host=host, check_active=cancel)
    assert host.declared == [profile.selection] and not host.requests
    from corpus_structure.methods.pm2_worker import Pm2WorkerError

    with pytest.raises(Pm2WorkerError, match="controlled actual-provider failure"):
        profile.run(source, canonical, host=host)
    assert host.requests == [dict(sentences=[["The", "mean", "is", "2", "."]], prepare_bulk=True)]


@pytest.mark.gpu
def test_actual_cuda_hanlp_retains_all_native_heads_and_semantic_addresses(profile):
    source, canonical, _, _ = inputs(profile)
    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
    from corpus_structure.semantic.data_operation_partitions import PartitionedInput
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.sentence_partitions import blocks_from_packets

    header = json.loads(canonical.content)
    partitioned = PartitionedInput(canonical.content, canonical.partitions)
    sources = hanlp_operation_sources(profile.selection)
    operation = profile.model.operation("text.hanlp_native/source-native")
    assert operation.implementation_root is not None
    ids = {(item.owner, item.domain): item.key for item in profile.model.identities}
    boundaries = (
        *operation.assets,
        *(
            boundary
            for implementation in profile.model.implementation_slices
            if implementation.root == operation.implementation_root
            for boundary in implementation.boundaries
        ),
    )
    identity = PreparedCapabilityIdentity(
        sha256(profile.model.content).hexdigest(),
        operation.semantic_id,
        ids[operation.semantic_id, "definition"],
        ids[operation.semantic_id, "recipe"],
        ids[operation.implementation_root, "implementation-slice"],
        operation.callable_surfaces[0].declaration,
        sha256(
            canonical_bytes(
                tuple(
                    (source.module, sha256(source.content).hexdigest())
                    for source in sources.sources
                )
            )
        ).hexdigest(),
        canonical_bytes(asdict(operation.capabilities)),
        ids[operation.semantic_id, "eligibility"],
        "runtime:actual-native-host",
        canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )
    port = resolve_hanlp_port(
        profile.prepared,
        profile.model,
        operation.semantic_id,
        identity=identity,
        authorize=lambda _: None,
        custody=sources.boundary_contracts,
        sources=sources,
        selection=profile.selection,
    )
    values = tuple(
        PythonRoleValue(
            role.name,
            ids[role.kind, "kind"],
            source.value if role.name == "source" else header,
            partitioned=partitioned if role.name == "canonical" else None,
        )
        for role in operation.roles
        if role.direction == "input"
    )
    completion = port.invoke_python(values)
    value = json.loads(completion.outputs[0].content)
    assert value["outcome"] == "complete"
    assert value["canonical_input"] == SemanticReference.whole("canonical").values()
    assert {row["family"] for row in value["coverage"]} == {
        "hanlp.tokens",
        "hanlp.lemma",
        "hanlp.pos",
        "hanlp.dependency",
        "hanlp.constituency",
        "hanlp.srl",
    }
    (block,) = blocks_from_packets(
        tuple(json.loads(packet) for packet in completion.outputs[0].partitions)
    )
    (alignment,) = (row for row in block.rows if row["record_type"] == "alignment")
    assert alignment["prepared_words"] == [" The", " mean", " is", " 2", "."]
    assert alignment["token_id_standing"] == "authenticated-vocabulary"
    tokens = [row for row in block.rows if row["record_type"] == "token"]
    assert len(tokens) == 5 and all(
        "lemma" in token and "pos" in token and "dependency_head" in token for token in tokens
    )
    assert sum(token["dependency_head"] == 0 for token in tokens) == 1
    assert all(
        row["sentence"]
        == SemanticReference.item("canonical", "rows", "#/texts/0", ("sentence", 0)).values()
        for row in block.rows
    )
    assert completion.execution_evidence
    assert all(
        receipt["provider"] == "hanlp" for receipt in json.loads(completion.execution_evidence)
    )
    assert len(completion.outputs[0].members) == len(value["members"])
    from corpus_structure.semantic.data_operation_storage import (
        data_operation_definition_projection,
    )
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema

    projection = json.loads(
        data_operation_definition_projection(
            profile.prepared,
            profile.model,
            native_digest="native:meaning-control",
            captured_contracts=sources.boundary_contracts,
        )
    )
    contracts = {kind["kind_contract"]: kind for kind in projection["kinds"]}
    assert completion.outputs[0].meaning is not None
    validate_wire_schema(
        contracts[completion.outputs[0].kind_contract]["meaning_schema"],
        json.loads(completion.outputs[0].meaning),
    )
    for packet in completion.outputs[0].members:
        member = json.loads(packet)
        validate_wire_schema(contracts[member["kind_contract"]]["meaning_schema"], member["body"])


def _publication_context(source):
    from corpus_structure.semantic.data_operation_model import SubjectContext

    value = source.value
    return SubjectContext(
        "family-test",
        source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}),
        subject_definition="original-source-view",
    )


@pytest.mark.parametrize("predicate_count", [0, 1, 2])
def test_raw_srl_preserves_unicode_whitespace_roles_and_honest_predicate_standing(
    profile, predicate_count
):
    text = "X X é x+y [3]."
    population = [
        ("X", 0, 1),
        ("X", 2, 3),
        ("é", 4, 5),
        ("x+y", 6, 9),
        ("[3]", 10, 13),
        (".", 13, 14),
    ]
    _, canonical, sentence, tokens = inputs(profile, text=text, words=population)
    words = [word for _, word in tokens]
    prepared = [word if index == 0 else " " + word for index, word in enumerate(words)]
    preparation = dict(
        prepared_words=prepared,
        word_subwords=[[i + 1] for i in range(len(words))],
        input_ids=[100, *range(1, len(words) + 1), 101],
    )
    roles = [("X", "ARG1", 0, 1), (" X", "R-ARG1", 1, 2), (" x+y", "C-ARG1", 3, 4)]
    roles.extend((" é", "PRED", 2, 3) for _ in range(predicate_count))
    heads = dict(
        lemma=[" " + word for word in words],
        pos=["NN"] * len(words),
        dependency=[[len(words), "dep"] for _ in words[:-1]] + [[0, "root"]],
        constituency=[
            "TOP",
            [
                [
                    "FRAG",
                    [
                        ["WHADVP", [["NN", [prepared[0]]]]],
                        *[["NN", [word]] for word in prepared[1:]],
                    ],
                ]
            ],
        ],
        srl=[roles],
    )
    units, alignment, coverage = detach_hanlp_sentence(
        sentence, tokens, canonical, heads, preparation
    )
    by_family = {row["family"]: row["outcome"] for row in coverage}
    assert by_family["hanlp.srl"] == ("complete" if predicate_count == 1 else "partial")
    assert all(
        outcome == "complete" for family, outcome in by_family.items() if family != "hanlp.srl"
    )
    (group,) = [row for row in units if row["record_type"] == "srl_group"]
    assert [
        (row["native_text"], row["label"], row["start"], row["end"]) for row in group["roles"]
    ] == roles
    assert [row["tokens"][0] for row in group["roles"][:3]] == [tokens[i][0] for i in (0, 1, 3)]
    native_tokens = [row for row in units if row["record_type"] == "token"]
    assert native_tokens[1]["lemma"] == " X" and native_tokens[-1]["dependency_head"] == 0
    constituents = [row for row in units if row["record_type"] == "constituent"]
    assert {row["label"] for row in constituents} == {"TOP", "FRAG", "WHADVP", "NN"}
    assert len(constituents) == len(words) + 3
    assert alignment["prepared_words"] == prepared


def test_hanlp_admission_chunks_by_actual_frames_not_sentence_cap():
    from types import SimpleNamespace

    from corpus_structure.methods.native_host import host_request_frame_size

    selection = SimpleNamespace(provider="hanlp", native=SimpleNamespace(fingerprint="a" * 64))
    rows = [
        (index, [(0, word)])
        for index, word in enumerate(
            ['é"', "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
        )
    ]
    payload = dict(sentences=[[row[1][0][1]] for row in rows], prepare_bulk=True)
    bound = host_request_frame_size(selection, payload, 10000)
    assert list(hanlp_admission_batches(rows, selection, bound)) == [rows]
    bound = host_request_frame_size(
        selection, dict(sentences=[[row[1][0][1]] for row in rows[:3]], prepare_bulk=True), 10000
    )
    batches = list(hanlp_admission_batches(rows, selection, bound))
    assert [row for batch in batches for row in batch] == rows
    assert batches[0] == rows[:3]
    for index, batch in enumerate(batches):
        words = [[word for _, word in row[1]] for row in batch]
        assert (
            host_request_frame_size(selection, dict(sentences=words, prepare_bulk=True), 10000)
            <= bound
        )
        if index + 1 < len(batches):
            extra = [word for _, word in batches[index + 1][0][1]]
            assert (
                host_request_frame_size(
                    selection, dict(sentences=[*words, extra], prepare_bulk=True), 10000
                )
                > bound
            )


def test_hanlp_admission_refuses_indivisible_oversized_sentence():
    from types import SimpleNamespace

    from corpus_structure.methods.native_host import host_request_frame_size
    from corpus_structure.methods.pm2_worker import Pm2WorkerRefused

    selection = SimpleNamespace(provider="hanlp", native=SimpleNamespace(fingerprint="a" * 64))
    bound = host_request_frame_size(
        selection, dict(sentences=[["short"]], prepare_bulk=True), 10000
    )
    with pytest.raises(Pm2WorkerRefused, match="one HanLP admission sentence"):
        list(hanlp_admission_batches([(0, [(0, "x" * 100)])], selection, bound))
