"""Exact inline syntax and portable replay over the frozen affine-transform spelling."""

import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.methods.scoped_relations import ScopedRelationsConfig, discover_relations
from corpus_structure.orchestrate.registry import canonical_numbers
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.serve.inline_formula_replay import verify_inline_formula_report

from .test_m1_source_preparation import source
from .test_scoped_relations import complete_native_fields

_FROZEN_TEXT = (
    "We have seen above that it is possible to simulate a standard normal random variable Z. "
    "If we wish to simulate a normal random variable X with parameters µ and \u03c3, "
    "then we need only "
    "transform the simulated values for Z using the equation X = \u03c3Z + µ."
)


def discovery(text, **kwargs):
    view = complete_native_fields(source(text, labels=("text",)))
    pieces = tuple(dict(piece, source_field="text") for piece in view.pieces)
    projection = dict(
        text=view.text,
        pieces=pieces,
        items=[node["self_ref"] for node in view.items],
        ancestors=[],
        health={},
    )
    view = replace(
        view,
        pieces=pieces,
        ref=replace(
            view.ref,
            projection_digest=sha256(canonical_bytes(projection)).hexdigest(),
        ),
    )
    frame = native_source_frame(view, ())
    result = discover_relations(frame, inline_equations_enabled=True, **kwargs)
    return view, frame, result


def inline_rows(output):
    (operation,) = [
        o for o in output["extra_operations"] if o["question"] == "source_formula_occurrences"
    ]
    return operation, [
        row for row in output["contributions"] if row["operation_key"] == operation["operation_key"]
    ]


@pytest.mark.parametrize("mu", ["µ", "μ"])
def test_frozen_symbol_is_exact_standalone_and_separate_from_geometry(mu):
    _, frame, output = discovery(_FROZEN_TEXT.replace("µ", mu))
    operation, rows = inline_rows(output)
    assert operation["inspected_count"] == 1
    assert operation["outcome"] == "succeeded"
    assert operation["emitted_count"] == len(rows) == 4
    assert {source_python(row["value"])["text"] for row in rows} == {"X", "\u03c3", "Z", mu}
    (z,) = [row for row in rows if source_python(row["value"])["text"] == "Z"]
    (anchor,) = z["anchors"]
    assert (anchor["start"], anchor["end"], anchor["source_piece"]) == (242, 243, "Z")
    assert z["kind"] == "occurrence" and "members" not in z and "endpoints" not in z
    assert source_python(z["value"])["syntax_standing"] == "syntax_only"
    previous = discover_relations(frame)
    assert output["operation"] == previous["operation"]
    assert [row for row in output["contributions"] if row not in rows] == list(
        previous["contributions"]
    )


def test_clipped_equation_produces_no_formula_operation():
    _, _, output = discovery(
        _FROZEN_TEXT,
        passages=(
            SimpleNamespace(
                passage_id="clipped",
                start=237,
                end=247,
                effective_version=None,
            ),
        ),
    )
    assert all(o["question"] != "source_formula_occurrences" for o in output["extra_operations"])


@pytest.mark.parametrize(
    ("text", "max_chars", "outcome"),
    [
        ("using the equation X = χZ + µ.", 200, "unsupported"),
        ("using the equation X = \u03c3Z + µ.", 6, "limited"),
        ("using the equation X = \u03c3Z + µ", 200, "unsupported"),
    ],
)
def test_failed_capture_reports_diagnostic_without_occurrences(text, max_chars, outcome):
    _, _, output = discovery(text, max_formula_chars=max_chars)
    operation, rows = inline_rows(output)
    assert not rows and operation["outcome"] == "unsupported"
    (diagnostic,) = output["formula_diagnostics"]
    assert diagnostic["outcome"] == outcome


def test_unavailable_formula_diagnostics_survive_contribution_binding():
    from pathlib import Path

    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.contributions import bind_contributions
    from corpus_structure.semantic.observations import observation_inputs

    _, frame, output = discovery("using the equation X = χZ + µ.")
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release = prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    operations, _ = bind_contributions(
        release,
        source=frame.unit_ref,
        operations=(output["operation"], *output["extra_operations"]),
        contributions=output["contributions"],
        coordinate_texts=output["coordinates"],
    )
    (operation,) = [o for o in operations if o["question"] == "source_formula_occurrences"]
    assert operation["outcome"] == "unsupported" and operation["emitted_count"] == 0


@pytest.mark.parametrize("tampering", ["wrong_native_symbol", "added_attachment"])
def test_detached_verifier_rejects_wrong_symbol_or_link(tampering):
    view, frame, output = discovery(_FROZEN_TEXT)
    report = json.loads(
        canonical_bytes(
            {
                "configuration": canonical_numbers(ScopedRelationsConfig().model_dump(mode="json")),
                "body": {
                    "contribution_operations": output["extra_operations"],
                    "contributions": output["contributions"],
                    "parse_detail": source_value({"formula_syntax": output["formula_diagnostics"]}),
                },
            }
        )
    )
    original = json.loads(
        canonical_bytes(
            {
                "source_view_id": frame.source_view_id,
                "text": view.text,
                "context": {"items": view.items, "pieces": view.pieces},
                "ref": {
                    "key": frame.unit_ref,
                    "projection_digest": frame.projection_digest,
                    "recipe_digest": frame.recipe_digest,
                    "native_product": frame.native_product.values(),
                },
            }
        )
    )
    verify_inline_formula_report(report, original)

    (row,) = [
        r for r in report["body"]["contributions"] if source_python(r["value"])["text"] == "Z"
    ]
    if tampering == "added_attachment":
        report["body"]["contributions"].append(
            dict(
                kind="relation",
                operation_key=output["operation"]["operation_key"],
                endpoints=[dict(role="attachment", contribution_id=row["contribution_id"])],
            )
        )
        with pytest.raises(ValueError, match="must remain syntax-only evidence"):
            verify_inline_formula_report(report, original)
        return
    value = source_python(row["value"])
    start = _FROZEN_TEXT.rindex("Z", 0, 242)
    value.update(start=start, end=start + 1)
    row["value"] = source_value(value)
    row["anchors"][0].update(start=start, end=start + 1)
    with pytest.raises(ValueError, match="inline formula occurrence differs"):
        verify_inline_formula_report(report, original)
