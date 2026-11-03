"""Forward deployment of bounded derivations and native consumer custody."""

from pathlib import Path


def native_task_completion_sql(context=None) -> str:
    """One rendered completion source for normal products and native authoring."""
    from .native_shapes import record_shape_guards
    from .pdf_contracts import trusted_pdf_context

    context = trusted_pdf_context() if context is None else context
    return (
        Path(__file__)
        .with_name("sql")
        .joinpath("native_task_completion.sql")
        .read_text()
        .replace(
            "-- {native_input_shape_guard}",
            record_shape_guards(context.boundary, "PdfNativeObservationInput", "native_input"),
        )
        .replace(
            "-- {source_record_guard}",
            Path(__file__).with_name("sql").joinpath("source_record_completion.sql").read_text(),
        )
    )
