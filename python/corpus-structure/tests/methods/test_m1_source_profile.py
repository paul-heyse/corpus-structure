"""Independent source/profile/geometry expectations; no model or database execution."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from corpus_structure.methods import gliner, m1_source
from corpus_structure.methods import source_preparation as prep
from corpus_structure.methods.record_packs import formula_pack_variants
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    ContextRelationship,
    ContextRetrieval,
    PreparedNativeSources,
    RelatedNativeSource,
    RetrievalOutcome,
    SourceSlice,
    SyntheticText,
)
from methods.test_m1_producer import detail_object, detail_objects
from methods.test_m1_source_preparation import source
from methods.test_record_assembly import context, fields, release, report, span


def config(tmp_path, **changes):
    return m1_source.M1Config(
        snapshot=tmp_path,
        checkpoint="fixture",
        revision="immutable",
        artifact_hashes=tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
        **changes,
    )


def test_explicit_profile_budgets_and_unchanged_whitespace_identity(tmp_path):
    old = config(tmp_path)
    expected = gliner.GlinerProfile(tmp_path, "fixture", "immutable", old.artifact_hashes)
    assert old.profile() == expected and old.profile().fingerprint == expected.fingerprint
    new = config(
        tmp_path, execution_profile=gliner.CODEPOINT_PROFILE, max_words=4096, max_subwords=4608
    )
    assert new.profile().version == gliner.CODEPOINT_PROFILE
    assert (new.profile().max_words, new.profile().max_subwords) == (4096, 4608)
    assert new.profile().fingerprint != old.profile().fingerprint
    for bad in (
        {"max_words": 0},
        {"max_subwords": -1},
        {"execution_profile": "char"},
        {"formula_prose": True},
    ):
        with pytest.raises(ValidationError):
            config(tmp_path, **bad)
    assert config(tmp_path, policy=prep.POLICY_V5, formula_prose=True).formula_prose


def test_codepoints_preserve_exact_welded_unicode_source_boundaries():
    from gliner2.processing.targets import (
        char_span_to_word_boundaries,
        word_boundaries_to_char_span,
    )
    from gliner2.processing.word_splitter import WhitespaceTokenSplitter

    text = "IfXis İe\u0301\u200d😀\tZ"
    tokens = list(gliner.UnicodeCodepointSplitter()(text))
    assert tokens == [
        ("i", 0, 1),
        ("f", 1, 2),
        ("x", 2, 3),
        ("i", 3, 4),
        ("s", 4, 5),
        ("i\u0307", 6, 7),
        ("e", 7, 8),
        ("\u0301", 8, 9),
        ("\u200d", 9, 10),
        ("😀", 10, 11),
        ("z", 12, 13),
    ]
    assert list(gliner.UnicodeCodepointSplitter()(text, lower=False))[5] == ("İ", 6, 7)
    starts, ends = [x[1] for x in tokens], [x[2] for x in tokens]
    assert word_boundaries_to_char_span(
        *char_span_to_word_boundaries(2, 3, starts, ends), starts, ends
    ) == (2, 3)
    old = list(WhitespaceTokenSplitter()(text))
    assert word_boundaries_to_char_span(
        *char_span_to_word_boundaries(2, 3, [x[1] for x in old], [x[2] for x in old]),
        [x[1] for x in old],
        [x[2] for x in old],
    ) == (0, 5)


@pytest.mark.parametrize(
    "version,splitter_name",
    [
        (gliner.WHITESPACE_PROFILE, "WhitespaceTokenSplitter"),
        (gliner.CODEPOINT_PROFILE, "UnicodeCodepointSplitter"),
    ],
)
def test_loader_requests_and_proves_actual_splitter_without_model_execution(
    tmp_path, monkeypatch, version, splitter_name
):
    from dataclasses import dataclass

    import torch
    from gliner2 import AutoExtractor
    from gliner2.processing.word_splitter import WhitespaceTokenSplitter

    @dataclass
    class Settings:
        adaptive_threshold: bool = False

    received = []
    model = SimpleNamespace(
        eval=lambda: None,
        to=lambda device: model,
        parameters=lambda: iter(()),
        architecture="boundary",
        boundary_settings=Settings(),
        config=SimpleNamespace(to_dict=lambda: {}),
    )

    def load(path, **kwargs):
        received.append(kwargs)
        actual = kwargs["word_splitter"]
        model.processor = SimpleNamespace(
            word_splitter=(WhitespaceTokenSplitter() if actual == "whitespace" else actual)
        )
        return model

    monkeypatch.setattr(AutoExtractor, "from_pretrained", load)
    monkeypatch.setattr(gliner.GlinerProfile, "verify_artifacts", lambda _: None)
    monkeypatch.setattr(torch, "set_num_threads", lambda _: None)
    monkeypatch.setattr(torch, "set_num_interop_threads", lambda _: None)
    profile = config(tmp_path, execution_profile=version).profile()
    _, effective = gliner.load_model(profile)
    assert received[0]["map_location"] == "cpu" and received[0]["attention_backend"] == "standard"
    assert json.loads(effective)["splitter"] == splitter_name
    assert json.loads(effective)["profile"] == profile.fingerprint
    requested = received[0]["word_splitter"]
    assert (
        (requested == "whitespace")
        if version == gliner.WHITESPACE_PROFILE
        else isinstance(requested, gliner.UnicodeCodepointSplitter)
    )

    def wrong(path, **kwargs):
        model.processor.word_splitter = (
            WhitespaceTokenSplitter()
            if version == gliner.CODEPOINT_PROFILE
            else gliner.UnicodeCodepointSplitter()
        )
        return model

    monkeypatch.setattr(AutoExtractor, "from_pretrained", wrong)
    with pytest.raises(gliner.GlinerRefused, match="splitter differs"):
        gliner.load_model(profile)


def windows(text="L1\nL2\nF\nR1\nR2", *, max_chars=7, max_pieces=5, related=False):
    chunks = text.split("\n")
    middle = chunks.index("F")
    view = source(text, labels=tuple("formula" if c == "F" else "text" for c in chunks))
    frame = native_source_frame(view, ())
    piece = next(p for p in view.pieces if p.get("item_ref") == f"#/texts/{middle}")
    retrieval = ContextRetrieval(
        ContextRelationship.DECLARATION,
        "missing declaration",
        "native scope",
        "b" * 64,
        (),
        (),
        (),
        RetrievalOutcome.MISSING_SCOPE,
        "not supplied",
    )
    selection = prep.ContextSelection(
        f"#/texts/{middle}",
        piece["start"],
        piece["end"],
        ("formula_context",),
        "native formula",
        pieces=(SourceSlice(7, piece["start"], piece["end"]),),
        retrievals=(retrieval,),
        local_dispositions=(("#/missing", "missing_scope", "retained failure"),),
    )
    annotations = tuple(
        SimpleNamespace(
            kind="paragraph", block_id=p["item_ref"], block_start=p["start"], block_end=p["end"]
        )
        for p in view.pieces
        if p["kind"] == "native_text"
    )
    sources = (frame,)
    neighbors = ()
    if related:
        other = source("EX", labels=("text",))
        other = replace(other, ref=replace(other.ref, id=8, key="source:8"))
        other_frame = native_source_frame(other, ())
        neighbors = (RelatedNativeSource(other_frame, ContextRelationship.DECLARATION, "owned"),)
        sources += (other_frame,)
        selection = replace(
            selection,
            pieces=(*selection.pieces, SyntheticText("\n", "owned"), SourceSlice(8, 0, 2)),
            relationships=((8, ContextRelationship.DECLARATION, "owned"),),
        )
    preparation = PreparedNativeSources(sources)
    regions = [
        prep.RegionDisposition(
            selection.region,
            "formula",
            (middle,),
            selection.families,
            "selected",
            "native formula",
            (0,),
        )
    ]
    result, regions = prep._formula_windows(
        view,
        frame,
        [selection],
        regions,
        annotations,
        neighbors,
        preparation,
        max_chars=max_chars,
        max_pieces=max_pieces,
        check_active=lambda: None,
    )
    contexts = [
        s.context(
            frame,
            max_chars=max_chars,
            max_pieces=max_pieces,
            related=neighbors,
            preparation=preparation,
            policy=prep.POLICY_V5,
        )
        for s in result
    ]
    return result, regions, contexts


def test_balanced_and_one_sided_windows_preserve_complete_blocks_and_failures():
    selections, regions, contexts = windows()
    assert [c.text for c in contexts] == ["F", "L2\nF\nR1", "L1\nL2\nF", "F\nR1\nR2"]
    assert regions[0].selections == (0, 1, 2, 3)
    assert all(s.retrievals == selections[0].retrievals for s in selections)
    assert all(
        ("#/missing", "missing_scope", "retained failure") in s.local_dispositions
        for s in selections
    )
    assert any(row[1] == "resource_limit" for row in selections[0].local_dispositions)
    assert all(len(c.text) <= 7 and len(c.intervals) <= 5 for c in contexts)


def test_no_cropping_or_skipping_oversized_nearest_paragraph_and_dedup():
    _, _, contexts = windows("x\nTooLong\nF\nR", max_chars=4, max_pieces=5)
    assert [c.text for c in contexts] == ["F", "F\nR"]
    _, _, contexts = windows(max_chars=1, max_pieces=1)
    assert [c.text for c in contexts] == ["F"]


def test_selected_related_source_custody_survives_every_alternative():
    _, _, contexts = windows(max_chars=10, max_pieces=7, related=True)
    assert len(contexts) > 1
    for ctx in contexts:
        assert ctx.text.endswith("EX") and ctx.related[0].source.source_view_id == 8
        assert (
            ctx.map_span(len(ctx.text) - 2, len(ctx.text), literal="EX")[0].source.source_view_id
            == 8
        )


def test_prose_formula_route_is_explicit_and_never_creates_native_occurrence():
    view = source("q = 1-p", labels=("text",))
    old = prep.prepare_source(view, persisted_annotations=())
    new = prep.prepare_source(
        view, persisted_annotations=(), policy=prep.POLICY_V5, formula_prose=True
    )
    assert old.selections[0].families == prep.PROSE_FAMILIES
    assert new.selections[0].families == (*prep.PROSE_FAMILIES, "formula_context")
    selection = new.selections[0]
    ctx = selection.context(new.source, max_chars=4096, max_pieces=64, preparation=new.preparation)
    assert ctx.policy == prep.POLICY_V5
    assert m1_source._structural_groups(view, selection, ctx) == ()
    supplement = m1_source._prose_formula_scope(view, ctx, {"formula": span(0, 7, "q = 1-p")})
    assert supplement is not None and [f.role for f in supplement.fields] == ["scope"]
    assert supplement.fields[0].native_pointer == view.ref.section_pointer
    assert m1_source._prose_formula_scope(view, ctx, {"formula": span(0, 7, "changed")}) is None


def test_natural_formula_variants_keep_roles_and_distinct_grouping_without_false_absence():
    from corpus_structure.methods.record_assembly import (
        OCCURRENCE_POLICY,
        NativeRecordGroup,
        RoleInput,
        assemble_records,
    )

    variants = formula_pack_variants(release(), source_inspection=True)
    assert [(name, anchor) for name, anchor, _ in variants] == [
        ("symbol_binding", "symbol"),
        ("formula_reading", "formula"),
    ]
    declarations = [
        json.loads(p.declaration_json)["structures"]["formula_context"] for _, _, p in variants
    ]
    assert declarations[0]["fields"] == declarations[1]["fields"]
    assert variants[0][2].fingerprint != variants[1][2].fingerprint
    text = "x+y x means left y means right z=0"
    ctx = context(text)
    binding_pack = variants[0][2]
    groups = []
    for spelling, word in (("x", "left"), ("y", "right")):
        a, b = text.index(spelling + " means"), text.index(word)
        groups.append(
            dict(
                formula=span(0, 3, "x+y"),
                formula__state="present",
                symbol=span(a, a + 1, spelling),
                symbol__state="present",
                meaning=span(b, b + len(word), word),
                meaning__state="present",
                domain__state="unstated",
                assumption__state="unstated",
            )
        )
    scope = NativeRecordGroup((RoleInput("scope", native_pointer="#/groups/1"),), "owned scope")
    result = assemble_records(
        release(),
        ctx,
        binding_pack,
        report(ctx, binding_pack, "formula_context", groups),
        contract="FormulaRecordFields",
        anchor_role="symbol",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
        supplements={0: scope, 1: scope},
    )
    assert len(result.records) == 2
    assert [fields(r)["symbol"]["original"] for r in result.records] == ["x", "y"]
    assert len({r.model_dump()["record_id"] for r in result.records}) == 2
    bare_pack = variants[1][2]
    start = text.index("z=0")
    bare = dict(
        formula=span(start, start + 3, "z=0"),
        formula__state="present",
        symbol__state="unstated",
        meaning__state="unstated",
        domain__state="unstated",
        assumption__state="unstated",
    )

    def assemble(group):
        return assemble_records(
            release(),
            ctx,
            bare_pack,
            report(ctx, bare_pack, "formula_context", [group]),
            contract="FormulaRecordFields",
            anchor_role="formula",
            policy_version="test",
            occurrence_policy=OCCURRENCE_POLICY,
            supplements={0: scope},
        )

    assert fields(assemble(bare).records[0])["symbol"]["state"] == "unstated"
    assert not assemble(dict(formula=bare["formula"], formula__state="present")).records
    assert fields(assemble(groups[0]).records[0])["symbol"]["original"] == "x"


@pytest.mark.parametrize("binding_refused", [False, True])
def test_variant_attempts_have_matched_execution_report_and_coverage_rows(
    tmp_path, monkeypatch, binding_refused
):
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods import m1_annotations

    view = source("x=1", labels=("formula",))
    product = prep.prepare_source(view, persisted_annotations=())
    cfg = config(tmp_path, policy=prep.POLICY_V5, source_inspection=True)
    native_context = product.selections[0].context(
        product.source,
        max_chars=2048,
        max_pieces=64,
        preparation=product.preparation,
        policy=prep.POLICY_V5,
    )
    monkeypatch.setattr(m1_source, "prepare_source", lambda *_args, **_kwargs: product)
    monkeypatch.setattr(m1_source, "_structural_groups", lambda *_: ())
    monkeypatch.setattr(
        m1_annotations,
        "consume_annotations",
        lambda *_: (
            (),
            (),
            dict(method="extract.m1_annotations", input_hash="input", configuration_hash="config"),
        ),
    )

    class Worker:
        def extract(self, pack, inputs, **kwargs):
            if (
                binding_refused
                and json.loads(pack.declaration_json)["structures"]["formula_context"]["anchor"]
                == "symbol"
            ):
                raise gliner.GlinerRefused("controlled capacity refusal")
            return (report(native_context, pack, "formula_context", []),)

    producer = m1_source.M1Candidates()
    monkeypatch.setattr(producer, "_resident", lambda _, **_kwargs: Worker())
    ctx = SimpleNamespace(
        reader=SimpleNamespace(prepared=release(), source_view=lambda _: view),
        check_active=lambda: None,
    )
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, 7, "source:7"))
    result = producer._source(unit, cfg, ctx)
    assert result.parse_detail is not None
    details = result.parse_detail
    executions = detail_objects(details["execution"])
    reports = [r for r in detail_objects(details["reports"]) if r["family"] == "formula_context"]
    coverage = [r for r in result.coverage if r.family == "formula_context"]
    assert len(executions) == len(reports) == len(coverage) == 2
    assert (
        {r["variant"] for r in executions}
        == {r["variant"] for r in reports}
        == {"symbol_binding", "formula_reading"}
    )
    assert len({r.scope for r in coverage}) == 2
    assert executions[0]["outcome"] == ("limited" if binding_refused else "complete")
    assert executions[1]["outcome"] == "complete"
    if not binding_refused:
        fingerprints = []
        for row in reports:
            fingerprint = detail_object(row["report"])["pack"]
            assert isinstance(fingerprint, str)
            fingerprints.append(fingerprint)
        assert len(set(fingerprints)) == 2
