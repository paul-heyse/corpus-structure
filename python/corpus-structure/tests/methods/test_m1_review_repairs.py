"""Independent review regressions: native hierarchy and exact retained document selection."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine

from corpus_structure.methods.m1_source import M1Config, _structural_groups
from corpus_structure.orchestrate.m1 import RetainedIntegratedConfig, RetainedIntegratedPdf
from corpus_structure.semantic.product_reference import ProductReference

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("axis", ["column", "row"])
@pytest.mark.parametrize(
    "geometry,expected",
    [
        ("nested", "present"),
        ("crossing", "unresolved"),
        ("overlapping_levels", "unresolved"),
    ],
)
def test_only_nested_nonoverlapping_native_header_paths_are_readings(
    monkeypatch, axis, geometry, expected
):
    from corpus_structure.methods import record_assembly

    rectangles = [(0, 1, 0, 2), (1, 2, 1, 2), (2, 3, 1, 2)]
    if geometry == "crossing":
        rectangles[1] = (1, 2, 1, 3)
    if geometry == "overlapping_levels":
        rectangles[0] = (0, 2, 0, 2)
    cells = []
    for index, (ra, rb, ca, cb) in enumerate(rectangles):
        if axis == "row":
            ra, rb, ca, cb = ca, cb, ra, rb
        cells.append(
            dict(
                text=("parent", "child", "value")[index],
                start_row_offset_idx=ra,
                end_row_offset_idx=rb,
                start_col_offset_idx=ca,
                end_col_offset_idx=cb,
                **(
                    {"column_header" if axis == "column" else "row_header": True}
                    if index < 2
                    else {}
                ),
            )
        )
    captured = {}

    def capture(context, **kwargs):
        captured.update(kwargs)
        return ()

    monkeypatch.setattr(record_assembly, "native_table_groups", capture)
    _structural_groups(
        SimpleNamespace(items=(dict(self_ref="#/tables/1", data=dict(table_cells=cells)),)),
        SimpleNamespace(region="#/tables/1", families=("table",)),
        object(),
    )
    key = "header_paths" if axis == "column" else "row_paths"
    assert captured[key].get(2, ()) == ((0, 1) if expected == "present" else ())


def test_retained_nondefault_original_cannot_silently_select_nothing(monkeypatch):
    from corpus_structure.ingest.pdf_recognition_methods import PdfIntegratedIngestConfig

    method = RetainedIntegratedPdf()
    cfg = PdfIntegratedIngestConfig(integrated_product=ProductReference(23, "integrated", "a" * 64))

    # Review repro: the inherited selector would filter against its Siegrist default.
    def documents(originals):
        raise AssertionError("unbound retained input reached document selection")

    run = SimpleNamespace(
        run_id=17,
        options={"corpus": {"documents": ["other-book"]}},
        reader=SimpleNamespace(documents=documents),
    )
    with pytest.raises(ValueError, match="document binding"):
        method.select(run, cfg)


@pytest.fixture
def retained_input(monkeypatch):
    from corpus_structure.semantic import pdf_record_reader, pdf_storage

    pin = ProductReference(23, "integrated", "a" * 64)
    revision = dict(
        task_id=23,
        product_key="integrated",
        logical_digest="a" * 64,
        build_id="published-build",
        release_id="producer-release",
        source_digest="b" * 64,
        kind="integrated",
    )
    reader = MagicMock(reference=pin, revision=revision)
    reader.iter_companions.return_value = [
        dict(source_scope="whole_document", conversion="success")
    ]
    reader.sections.return_value = [dict(pointer="#/groups/1")]
    monkeypatch.setattr(pdf_record_reader, "published_record_reader", lambda *a, **kw: reader)
    identity = dict(kind="integrated")
    monkeypatch.setattr(pdf_storage, "_record_product_identity", lambda *a, **kw: identity)
    row = dict(
        unit_type="document",
        id=2,
        key="other-book",
        content_hash="b" * 64,
        source_uri="other_book/Full.pdf",
        mime="application/pdf",
        document_project="project",
        producer_project="project",
    )
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.one_or_none.side_effect = lambda: row
    documents = [dict(id=2, key="other-book", content_hash="b" * 64)]
    return SimpleNamespace(
        pin=pin, reader=reader, identity=identity, row=row, conn=conn, documents=documents
    )


@pytest.mark.parametrize(
    "failure,match",
    [
        ("wrong_corpus", "outside the selected corpus"),
        ("wrong_project", "another project"),
        ("wrong_original", "original differs"),
        ("wrong_pin", "placement differs"),
        ("wrong_kind", "not an integrated"),
        ("unsupported_schema", "unsupported schema"),
        ("partial_source", "successful whole PDF"),
        ("missing_publication", "absent or unpublished"),
        ("missing_document", "producing document binding"),
        ("wrong_document_unit", "producing document binding"),
    ],
)
def test_exact_product_preflight_refuses_mismatched_custody(
    retained_input, monkeypatch, failure, match
):
    from corpus_structure.orchestrate.m1 import retained_document

    f = retained_input
    if failure == "wrong_corpus":
        f.documents = []
    elif failure == "wrong_project":
        f.row["producer_project"] = "another-project"
    elif failure == "wrong_original":
        f.row["content_hash"] = "c" * 64
    elif failure == "wrong_pin":
        f.reader.revision["logical_digest"] = "c" * 64
    elif failure == "wrong_kind":
        f.identity["kind"] = "native"
    elif failure == "unsupported_schema":
        f.reader._native_schema_mapping.side_effect = ValueError("unsupported schema")
    elif failure == "partial_source":
        f.reader.iter_companions.return_value = [
            dict(source_scope="page_range", conversion="success")
        ]
    elif failure == "missing_publication":
        from corpus_structure.semantic import pdf_record_reader

        monkeypatch.setattr(pdf_record_reader, "published_record_reader", lambda *a, **kw: None)
    elif failure == "missing_document":
        f.conn.execute.return_value.mappings.return_value.one_or_none.side_effect = lambda: None
    elif failure == "wrong_document_unit":
        f.row["unit_type"] = "source_view"
    with pytest.raises(ValueError, match=match):
        retained_document(
            f.conn, f.pin, prepared=object(), project_id="project", documents=f.documents
        )


def test_nondefault_original_is_bound_and_selected_exactly(retained_input):
    from corpus_structure.orchestrate.m1 import bind_retained_document, registry, retained_document
    from corpus_structure.orchestrate.phase0 import bind_pdf_source

    f = retained_input
    document = retained_document(
        f.conn, f.pin, prepared=object(), project_id="project", documents=f.documents
    )
    bound = bind_retained_document(
        bind_pdf_source(registry(ROOT / "domains/statistics"), f.pin, input_role="integrated"),
        document,
    )
    cfg = bound.overlay("ingest.pdf_integrated", "default")
    assert isinstance(cfg, RetainedIntegratedConfig)
    assert cfg.originals == ("other_book/Full.pdf",)
    assert cfg.retained_document_id == 2 and cfg.retained_document_key == "other-book"
    assert cfg.retained_original_digest == "b" * 64
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType

    requests = []
    rows = [SimpleNamespace(id=2, key="other-book")]

    def documents(originals):
        assert originals == ("other_book/Full.pdf",)
        requests.append(originals)
        return tuple(UnitRef(TaskUnitType.DOCUMENT, row.id, row.key) for row in rows)

    run = SimpleNamespace(
        run_id=17,
        options={"corpus": {"documents": ["other-book"]}},
        reader=SimpleNamespace(documents=documents),
    )
    method = bound.method("ingest.pdf_integrated")
    assert isinstance(method, RetainedIntegratedPdf)
    assert json.loads(method.original_recipe(cfg))["document"] == dict(
        id=2, key="other-book", original_digest="b" * 64, source_uri="other_book/Full.pdf"
    )
    assert [ref.unit_id for ref in method.select(run, cfg)] == [2]
    assert requests == [("other_book/Full.pdf",)]
    rows.clear()
    with pytest.raises(ValueError, match="exact corpus member"):
        method.select(run, cfg)


@pytest.mark.parametrize("refuse", [False, True])
@pytest.mark.parametrize("configuration", ["default", "described"])
def test_command_preflight_precedes_run_creation_and_narrows_corpus(
    monkeypatch, tmp_path, refuse, configuration
):
    from corpus_structure.orchestrate import commands, m1, semantic
    from corpus_structure.semantic import releases

    pack = tmp_path / "statistics"
    pack.mkdir()
    for name in ("m1-methods.yaml", "m1-guideline.md"):
        (pack / name).write_bytes((ROOT / "domains/statistics" / name).read_bytes())
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.one.return_value = dict(
        release_id="release", data_revision=1
    )
    docs = [
        dict(id=i, key=key, content_hash=digest * 64, mime="application/pdf", meta={})
        for i, key, digest in ((1, "siegrist", "c"), (2, "other-book", "b"))
    ]
    conn.execute.return_value.mappings.return_value.__iter__.side_effect = lambda: iter(docs)
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(releases, "load_release", lambda *a: SimpleNamespace(release_id="release"))
    preflight = []

    def selected(*args, **kwargs):
        preflight.append(kwargs)
        if refuse:
            raise ValueError("mismatched exact product")
        return m1.RetainedDocument(2, "other-book", "b" * 64, "other_book/Full.pdf")

    monkeypatch.setattr(m1, "retained_document", selected)
    started = MagicMock(return_value="candidate-source-result")
    monkeypatch.setattr(semantic, "run_source_methods", started)
    kwargs = dict(
        release_id="release",
        realization_id="input",
        project_id="project",
        domain="statistics",
        domains=tmp_path,
        method_settings=None,
        extraction_policy="m1-candidate",
        integrated_product=ProductReference(23, "integrated", "a" * 64),
        m1_configuration=configuration,
    )
    if refuse:
        with pytest.raises(ValueError, match="mismatched exact product"):
            commands.start_bound_run(engine, **kwargs)
        started.assert_not_called()
    else:
        assert commands.start_bound_run(engine, **kwargs) == "candidate-source-result"
        result = started.call_args.kwargs
        assert result["corpus_record"]["documents"] == ["other-book"]
        assert result["graph"].stages[1][1][1].config == f"extract.m1_candidates/{configuration}"
        assert result["configurations"] == (
            {"extract.m1_candidates": "described"} if configuration == "described" else None
        )
        assert result["registry"].overlay("ingest.pdf_integrated", "default").originals == (
            "other_book/Full.pdf",
        )
    assert len(preflight) == 1


def test_configured_descriptions_change_pack_conditioning_without_changing_released_roles():
    from corpus_structure.methods.m1_source import configured_packs
    from corpus_structure.orchestrate.m1 import registry
    from methods.test_m1_producer import release

    cfg = registry(ROOT / "domains/statistics").overlay("extract.m1_candidates", "described")
    assert isinstance(cfg, M1Config)
    described = configured_packs(release(), cfg)
    plain = configured_packs(release(), cfg.model_copy(update={"pack_descriptions": {}}))
    assert set(described) == {"definition", "assertion", "measurement", "table", "formula_context"}
    for family, pack in described.items():
        actual = json.loads(pack.declaration_json)["structures"][family]
        old = json.loads(plain[family].declaration_json)["structures"][family]
        assert pack.fingerprint != plain[family].fingerprint
        for field in actual["fields"]:
            assert field["description"] == cfg.pack_descriptions[family][field["name"]]
            del field["description"]
        assert actual == old


def test_default_policy_is_baseline_and_described_is_explicit_experimental_selection():
    from corpus_structure.orchestrate.commands import CommandError, start_bound_run
    from corpus_structure.orchestrate.m1 import M1, registry, source_graph

    methods = registry(ROOT / "domains/statistics")
    baseline = methods.overlay("extract.m1_candidates", "default")
    experimental = methods.overlay("extract.m1_candidates", "described")
    assert isinstance(baseline, M1Config) and isinstance(experimental, M1Config)
    assert baseline.pack_descriptions == {}
    assert experimental.pack_descriptions
    assert baseline.model_dump(exclude={"pack_descriptions"}) == experimental.model_dump(
        exclude={"pack_descriptions"}
    )
    assert (
        methods.resolve("extract.m1_candidates", "default").config_hash
        != methods.resolve("extract.m1_candidates", "described").config_hash
    )
    assert source_graph() is M1
    assert source_graph("described").stages[1][1][1].config == "extract.m1_candidates/described"
    # Preserve the invalid runtime engine: parameter preflight must never touch it.
    with pytest.raises(CommandError, match="nondefault M1 configuration"):
        start_bound_run(
            cast(Engine, object()),
            release_id="release",
            realization_id="input",
            project_id="project",
            domain="statistics",
            method_settings=None,
            m1_configuration="described",
        )


@pytest.mark.parametrize(
    "descriptions,match",
    [
        ({"invented_family": {"term": "instruction"}}, "unsupported M1 family"),
        ({"definition": {"term": " "}}, "must be nonempty"),
        ({"definition": {"invented_role": "instruction"}}, "unreleased family role"),
    ],
)
def test_description_policy_rejects_unknown_families_empty_instructions_and_unreleased_roles(
    descriptions, match
):
    from corpus_structure.methods.m1_source import configured_packs
    from corpus_structure.orchestrate.m1 import registry
    from methods.test_m1_producer import release

    cfg = registry(ROOT / "domains/statistics").overlay("extract.m1_candidates", "described")
    with pytest.raises(ValueError, match=match):
        changed = type(cfg).model_validate(
            dict(cfg.model_dump(mode="python"), pack_descriptions=descriptions)
        )
        configured_packs(release(), changed)
