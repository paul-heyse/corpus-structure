"""Typed independent guards and publication search retain their source authority."""

from dataclasses import replace

import pytest

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM, NativeProgramAccess
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.pdf_completion_native import pdf_completion_native_programs
from corpus_structure.semantic.pdf_domain import pdf_call_bindings
from corpus_structure.semantic.pdf_search_native import search_native_programs
from corpus_structure.semantic.pdf_source_search import (
    PUBLICATION_FILL_BYTES,
    search_configuration,
    search_pin_native_programs,
    search_projection_programs,
    search_projection_sources,
)
from corpus_structure.semantic.record_policy_native import record_policy_native_programs
from corpus_structure.semantic.structural_admission_native import (
    structural_admission_native_programs,
)


def test_independent_guard_producers_do_not_render_and_preserve_restricted_principal(monkeypatch):
    model = get_metadata()

    def refuse_render(self):
        raise AssertionError("independent guard producer eagerly rendered")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    groups = (
        (structural_admission_native_programs(model), 14, "data-operations:forward"),
        (record_policy_native_programs(target_metadata=model), 6, "data-operations:forward"),
        (pdf_completion_native_programs(model), 2, "target-current:PDF publication"),
    )
    for programs, count, source in groups:
        assert len(programs) == len({item.identity for item in programs}) == count
        for declaration in programs:
            assert declaration.source == source
            assert declaration.owner == role_name("publisher")
            assert declaration.validity == ()
            assert declaration.routine.security_definer or declaration.access == INTERNAL_PROGRAM
            assert declaration.access == (
                NativeProgramAccess(purposes=("fit",))
                if declaration.identity.name == "ddo_require_feature_fit_principal"
                else INTERNAL_PROGRAM
            )
    structural = {item.identity.name: item for item in groups[0][0]}
    assert structural["ddo_structural_pick"].identity.arguments == ("jsonb", "text[]", "boolean")
    assert structural["ddo_structural_pick"].routine.parameters[-1].default is not None
    completion = {item.identity.name: item for item in groups[-1][0]}
    assert completion["ddo_require_pdf_completion"].identity.arguments == (
        "jsonb",
        "bigint",
        "bigint",
        "text",
        "text",
        "text",
    )


def test_search_producers_keep_typed_table_results_without_rendering_or_reparsing(monkeypatch):
    model = get_metadata()
    bindings = pdf_call_bindings()

    def refuse_render(self):
        raise AssertionError("search producer eagerly rendered")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    programs = (
        *search_pin_native_programs(
            model,
            renderer="a" * 64,
            default_policy_digest="b" * 64,
            configuration=search_configuration(model),
        ),
        *search_native_programs(
            model,
            bindings,
            max_fill_bytes=PUBLICATION_FILL_BYTES,
            configuration=search_configuration(model),
        ),
    )
    assert tuple(item.identity.name for item in programs) == (
        "ddo_pdf_search_pin",
        "ensure_pdf_search_projection",
        "ddo_pdf_search_keys",
        "rank_pdf_search_projection",
    )
    for declaration in programs:
        assert declaration.source == "data-operations:forward"
        assert declaration.owner == role_name("publisher")
        assert declaration.access == INTERNAL_PROGRAM
        assert declaration.validity == ()
    keys = programs[2].routine
    assert keys.returns.setof is True
    assert tuple(name for name, _ in keys.table_columns) == (
        "source_index",
        "population_id",
        "section_pointer",
        "membership",
        "key",
    )


@pytest.mark.parametrize("name", ["native/pdf-search-pin.sql", "native/pdf-source-search.sql"])
def test_search_capture_rejects_independently_changed_pin_or_program(name):
    model = get_metadata()
    sources = search_projection_sources(target_metadata=model)
    assert len(search_projection_programs(sources, target_metadata=model)) == 4
    changed = tuple(
        replace(item, content=item.content + b"\nchanged") if item.name == name else item
        for item in sources
    )
    with pytest.raises(ValueError, match="differ from captured"):
        search_projection_programs(changed, target_metadata=model)
