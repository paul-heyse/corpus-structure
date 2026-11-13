"""Native HanLP heads preserve exact canonical addresses and independent standings."""

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.canonical_sentences import CanonicalProduct
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.hanlp_products import (
    PreparedHanlpProfile,
    detach_hanlp_sentence,
    hanlp_operation_sources,
    hanlp_product_inputs,
    prepare_hanlp_selection,
    resolve_hanlp_port,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_products import (
    FrozenNativeSource,
    native_projection_identity,
    source_subject,
)


@pytest.fixture(scope="module")
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


def inputs(profile):
    text = "The mean is 2."
    words = [("The", 0, 3), ("mean", 4, 8), ("is", 9, 11), ("2", 12, 13), (".", 13, 14)]
    pieces = [
        dict(kind="native_text", start=0, end=len(text), item_ref="#/texts/0", source_field="text")
    ]
    items = [dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)])]
    projection = native_projection_identity(text, pieces, items)
    coordinate = dict(
        document="document:original",
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
    context = dict(
        subject=source_subject(coordinate),
        original_source=coordinate["document"],
        analyzed_scope=dict(source=coordinate, selectors=selectors),
    )
    ids = {(item.owner, item.domain): item.key for item in profile.model.identities}

    def packet(name, body):
        return dict(
            member_id=body["local_id"],
            kind_contract=ids[profile.prepared.index.definitions[name].iri, "kind"],
            context=context,
            body=body,
        )

    token_ids = [f"{index + 1:064x}" for index in range(len(words))]
    sentence = dict(
        record_type="sentence",
        local_id="f" * 64,
        block_id="block:one",
        ordinal=0,
        start=0,
        end=len(text),
        token_ids=token_ids,
    )
    tokens = [
        dict(
            record_type="token",
            local_id=identifier,
            block_id="block:one",
            ordinal=index,
            start=start,
            end=end,
            space=index < 3,
            role="prose",
            piece_indices=[0],
            sentence_ref=sentence["local_id"],
        )
        for index, (identifier, (_, start, end)) in enumerate(zip(token_ids, words, strict=True))
    ]
    value = dict(
        source=coordinate,
        selectors=selectors,
        outcome="complete",
        block_coverage=[
            dict(
                block_id="block:one",
                native_pointer="#/texts/0",
                start=0,
                end=len(text),
                outcome="complete",
            )
        ],
        coverage=[],
        members=[
            *(packet("DdoCanonicalToken", token) for token in tokens),
            packet("DdoCanonicalSentence", sentence),
        ],
    )
    canonical = CanonicalProduct(
        canonical_bytes(value),
        profile.prepared,
        profile.model,
        profile.prepared.index.definitions["DdoCanonicalSentences"].iri,
        _publication_context(source),
    )
    _ = canonical.value
    return (
        source,
        canonical,
        sentence,
        list(zip(token_ids, [word for word, _, _ in words], strict=True)),
    )


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


@pytest.mark.gpu
def test_actual_cuda_hanlp_retains_all_native_heads_and_semantic_addresses(profile):
    source, canonical, _, _ = inputs(profile)
    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue

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
            source.value if role.name == "source" else canonical,
        )
        for role in operation.roles
        if role.direction == "input"
    )
    completion = port.invoke_python(values)
    value = json.loads(completion.outputs[0].content)
    assert value["outcome"] == "complete"
    assert value["canonical"] == canonical.reference.values()
    assert {row["family"] for row in value["coverage"]} == {
        "hanlp.tokens",
        "hanlp.lemma",
        "hanlp.pos",
        "hanlp.dependency",
        "hanlp.constituency",
        "hanlp.srl",
    }
    assert value["alignments"][0]["prepared_words"] == [" The", " mean", " is", " 2", "."]
    assert value["alignments"][0]["token_id_standing"] == "authenticated-vocabulary"
    tokens = [
        packet["body"] for packet in value["members"] if packet["body"]["record_type"] == "token"
    ]
    assert len(tokens) == 5 and all(
        "lemma" in token and "pos" in token and "dependency_head" in token for token in tokens
    )
    assert sum(token["dependency_head"] == 0 for token in tokens) == 1
    assert all(
        packet["body"]["sentence"]["product_id"] == canonical.reference.product_id
        for packet in value["members"]
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
            profile.prepared, profile.model, native_digest="native:meaning-control"
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
    from corpus_structure.semantic.source_products import source_subject
    value = source.value
    return SubjectContext("family-test", source_subject(value["source"]), value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}))
