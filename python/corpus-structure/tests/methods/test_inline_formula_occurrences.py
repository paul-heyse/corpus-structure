"""Exact inline syntax and portable replay over the frozen affine-transform spelling."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.contextual_candidates import retained_occurrences
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_contexts import record_source_pin
from methods.inline_formula_support import _FROZEN_TEXT as _FROZEN_TEXT
from methods.m1_source_preparation_support import source
from methods.scoped_relations_support import discover_relations


def discovery(text, **kwargs):
    view = source(text, labels=("text",))
    frame = view
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


def test_affine_query_carriers_use_exact_scoped_occurrences_not_prose_mentions():
    view, frame, output = discovery(_FROZEN_TEXT)
    pin = record_source_pin(frame)
    (node,) = view.items
    pointer = node["self_ref"]
    nodes = {pointer: node}
    selected = tuple(
        occurrence_identity(
            (
                dict(
                    pin=pin,
                    pointer=pointer,
                    space="native",
                    precision="exact",
                    start=start,
                    end=start + 1,
                    source_piece=symbol,
                ),
            )
        )
        for start, symbol in ((237, "X"), (242, "Z"))
    )
    rows, contexts, _ = retained_occurrences(
        output,
        nodes,
        pin,
        "affine-query",
        ("structural.located_participant",),
        required_occurrence_ids=selected,
    )
    assert set(contexts) == set(selected)
    assert [contexts[key][1:] for key in selected] == [(237, 238, "X"), (242, 243, "Z")]
    assert {row["occurrence_id"] for row in rows} == set(selected)
    _, originals = inline_rows(output)
    by_id = {row["contribution_id"]: row for row in originals}
    assert all(
        row["anchors"] == by_id[row["computation_dependencies"][0]]["anchors"] for row in rows
    )

    without_z = {
        "contributions": [
            row for row in output["contributions"] if row.get("occurrence_id") != selected[1]
        ]
    }
    with pytest.raises(ValueError, match="lacks an exact native query carrier"):
        retained_occurrences(
            without_z, nodes, pin, "affine-query", required_occurrence_ids=selected
        )


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

    from corpus_structure.semantic.contributions import bind_contributions
    from corpus_structure.semantic.observations import observation_inputs
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

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
