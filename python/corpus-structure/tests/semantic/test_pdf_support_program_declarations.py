"""Direct PDF producers retain their read boundaries and bound private SELECTs."""

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.companion_projection_native import companion_projection_programs
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.pdf_record_context_native import (
    pdf_record_context_page_programs,
    pdf_record_context_programs,
)
from corpus_structure.semantic.pdf_record_pages_native import pdf_record_page_programs
from corpus_structure.semantic.pdf_record_reader_native import (
    pdf_companion_export_programs,
    pdf_materialization_bound_programs,
)
from corpus_structure.semantic.published_document import published_readers_programs


def test_pdf_support_and_bound_readers_are_declared_before_rendering(monkeypatch):
    model = get_metadata()

    def refuse_render(self):
        raise AssertionError("PDF producer eagerly rendered")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    companion = companion_projection_programs(target_metadata=model)
    published = published_readers_programs(target_metadata=model)
    assert len(companion) == 6
    assert len(published) == 18
    assert companion[0].source == "companion-projections:pin"
    assert companion[0].access == INTERNAL_PROGRAM
    assert companion[1].source == "companion-input:private-body:sql-standard"
    assert companion[1].access == INTERNAL_PROGRAM
    assert companion[1].routine.sql_standard is True
    assert companion[1].routine.security_definer is False
    assert companion[1].identity.arguments == (
        "text",
        "text",
        "text",
        "text",
        "text",
        "text",
        "text",
        "text",
        "bigint",
        "text",
        "text",
        "text",
    )
    for private, public in zip(published[::2], published[1::2], strict=True):
        assert private.routine.sql_standard is True
        assert private.access == INTERNAL_PROGRAM
        assert public.identity.name + "_rows" == private.identity.name
        assert public.routine.security_definer is True
        assert public.access.purposes == ("read", "write", "evaluate")
        assert private.source == public.source == "published-document:forward"
    context = pdf_record_context_programs(model)
    page = pdf_record_page_programs(model)[0]
    frozen = pdf_record_page_programs(model, frozen=True)[0]
    assert context[0].access == INTERNAL_PROGRAM
    assert context[1].routine.parameters[-1].default is not None
    assert context[1].identity.arguments == (
        "bigint",
        "text",
        "text",
        "text[]",
        "text",
        "text",
        "bigint",
    )
    assert page.access.purposes == ("read", "write", "evaluate")
    assert frozen.access.purposes == ("write",)
    assert frozen.routine.parameters[-1].default is not None
    supporting = (
        *context,
        *pdf_record_context_page_programs(model),
        page,
        frozen,
        *pdf_materialization_bound_programs(model),
        *pdf_companion_export_programs(target_metadata=model),
    )
    assert len(supporting) == len({item.identity for item in supporting}) == 7
    for declaration in (*companion, *published, *supporting):
        assert declaration.owner == role_name("publisher")
        assert declaration.validity == ()
    for declaration in supporting:
        assert declaration.source == "target-current:PDF publication"
