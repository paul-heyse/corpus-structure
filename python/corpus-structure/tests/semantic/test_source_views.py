"""Source coverage is relative to its explicitly named native universe."""


def test_source_view_health_is_relative_to_its_named_native_universe():
    from corpus_structure.semantic.source_views import source_view_health

    group = {"self_ref": "#/groups/0", "label": "section"}
    formula = {"self_ref": "#/texts/0", "label": "formula", "parent": {"$ref": "#/groups/0"}}
    health = {
        "conversion": "success",
        "display_coverage": "partial",
        "inline_coverage": "complete",
        "cell_coverage": "complete",
        "inline_scope": ["#/groups/0"],
        "cell_scope": ["#/groups/0"],
        "inline_membership": "direct",
        "cell_membership": "direct",
        "formula_outcomes": [
            {"pointer": "#/texts/0", "outcome": "succeeded"},
            {"pointer": "#/texts/1", "outcome": "failed"},
        ],
    }
    local = source_view_health(health, "#/groups/0", "direct", (group, formula), ())
    assert (
        local["display_coverage"] == "complete"
        and local["inline_coverage"] == "complete"
        and local["cell_coverage"] == "complete"
    )
    assert local["formula_outcomes"] == [{"pointer": "#/texts/0", "outcome": "succeeded"}]
    child = {"self_ref": "#/groups/1", "label": "section"}
    outside = source_view_health(health, "#/groups/1", "direct", (child,), ("#/groups/0",))
    assert outside["inline_coverage"] == "unknown" and outside["cell_coverage"] == "unknown"
    strong = source_view_health(
        dict(health, inline_membership="descendants", cell_membership="descendants"),
        "#/groups/1",
        "direct",
        (child,),
        ("#/groups/0",),
    )
    assert strong["inline_coverage"] == "complete" and strong["cell_coverage"] == "complete"
    unqualified = source_view_health(
        dict(health, inline_scope=[], cell_scope=[]), "#/groups/0", "direct", (group, formula), ()
    )
    assert unqualified["inline_coverage"] == "unknown" and unqualified["cell_coverage"] == "unknown"
