"""Verify the scoped formula operation against the exact retained native source."""

from corpus_structure.methods.inline_formula_occurrences import (
    INLINE_FORMULA_OCCURRENCE_FIELDS,
    INLINE_FORMULA_POLICY,
    INLINE_FORMULA_QUESTION,
    INLINE_FORMULA_VERSION,
    inline_equations,
    inline_symbols,
)
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.observations import source_python


def verify_inline_formula_report(report, source):
    from corpus_structure.methods.scoped_relations import ScopedRelationsConfig

    body = report["body"]
    cfg = ScopedRelationsConfig.model_validate(report["configuration"])
    source_id = source["source_view_id"]
    selection = None
    if cfg.inputs is not None:
        (ref,) = [r for r in cfg.inputs.sources if r.source_view_id == source_id]
        selection = tuple(
            (p.passage_id, p.start, p.end, p.effective_version)
            for p in cfg.inputs.passages
            if p.source_ref == ref.identity
        )
    context = source["context"]
    pieces = context["pieces"]
    text = source["text"]
    ref = source["ref"]
    product = ref["native_product"]
    pin = dict(
        source=ref["key"],
        native_product_task_id=product["task_id"],
        product_key=product["product_key"],
        product_digest=product["content_digest"],
        projection_digest=ref["projection_digest"],
        recipe_digest=ref["recipe_digest"],
        source_view_id=source_id,
    )
    op_key = operation_identity(INLINE_FORMULA_QUESTION, INLINE_FORMULA_VERSION, pin, selection)
    operations = [
        op for op in body["contribution_operations"] if op["question"] == INLINE_FORMULA_QUESTION
    ]
    equations = tuple(
        inline_equations(
            text,
            pieces,
            {item["self_ref"]: item for item in context["items"]},
            selection,
            max_chars=cfg.max_formula_chars,
        )
    )
    detail = source_python(body["parse_detail"])
    diagnostics = [
        d for d in detail["formula_syntax"] if d.get("input_policy") == INLINE_FORMULA_POLICY
    ]
    actual = [row for row in body["contributions"] if row["operation_key"] == op_key]
    if not equations and not operations and not diagnostics and not actual:
        return
    if len(operations) != 1 or len(equations) != len(diagnostics) or not equations:
        raise ValueError("inline formula operation differs from retained equation selection")
    (op,) = operations
    dependency = f"native:{product['task_id']}"
    if (
        op["operation_key"] != op_key
        or op["operation_version"] != INLINE_FORMULA_VERSION
        or op["inspected_count"] != len(equations)
        or op["emitted_count"] != len(actual)
        or op["computation_dependencies"] != [dependency]
    ):
        raise ValueError("inline formula operation differs from its exact binding")

    expected = {}
    for equation, diagnostic in zip(equations, diagnostics, strict=True):
        outcome = diagnostic.get("outcome")
        allowed = (
            {"parsed", "unsupported", "ambiguous", "timeout", "unmapped"}
            if equation.status == "captured"
            else {equation.status}
        )
        if outcome not in allowed or diagnostic != equation.diagnostic(outcome):
            raise ValueError("inline formula diagnostic differs from retained equation")
        if outcome != "parsed":
            # Unavailable or timed-out syntax attests no occurrence. Replaying
            # successful syntax alone avoids treating a later fast run as historical evidence.
            continue
        symbols, result = inline_symbols(text, equation, seconds=cfg.formula_seconds)
        if result != "parsed":
            raise ValueError("inline formula syntax could not be replayed")
        for symbol in symbols:
            expected[equation.pointer, symbol.start, symbol.end] = text[symbol.start : symbol.end]

    unavailable = any(d["outcome"] != "parsed" for d in diagnostics)
    outcome = (
        ("limited" if expected else "unsupported")
        if unavailable
        else ("succeeded" if expected else "empty")
    )
    if op["outcome"] != outcome or len(expected) != len(actual):
        raise ValueError("inline formula operation differs from replayed syntax")

    for row in actual:
        value = source_python(row["value"])
        pointer, start, end = value["source_pointer"], value["start"], value["end"]
        literal = expected.pop((pointer, start, end), None)
        matching = [
            piece
            for piece in pieces
            if piece.get("item_ref") == pointer
            and piece.get("kind") == "native_text"
            and piece["start"] <= start < end <= piece["end"]
        ]
        if literal is None or len(matching) != 1 or len(row.get("anchors", ())) != 1:
            raise ValueError("inline formula occurrence differs from exact native symbol")
        (piece,), (anchor,) = matching, row["anchors"]
        if (
            row["pin"] != pin
            or anchor["pin"] != pin
            or row["kind"] != "occurrence"
            or row["semantic_type"] != "structural.located_participant"
            or row.get("members")
            or row.get("endpoints")
            or row["computation_dependencies"] != [dependency]
            or anchor["pointer"] != pointer
            or anchor["space"] != "native"
            or anchor["precision"] != "exact"
            or anchor["source_piece"] != literal
            or anchor["start"] != start - piece["start"]
            or anchor["end"] != end - piece["start"]
            or value
            != dict(
                role="formula_symbol",
                source_pointer=pointer,
                region=pointer,
                text=literal,
                start=start,
                end=end,
                **INLINE_FORMULA_OCCURRENCE_FIELDS,
            )
        ):
            raise ValueError("inline formula occurrence differs from exact native symbol")


def verify_inline_formula_closure(root, manifest):
    from .review_bundle import _detached_relation

    if "reports" not in manifest["relations"]:
        return
    reports = [
        row
        for row in _detached_relation(root, manifest, "reports")
        if row.get("method") == "structure.scoped_relations"
        and (row.get("body") or {}).get("operation_version") == "5"
        and (row.get("body") or {}).get("outcome") in {"produced", "empty"}
    ]
    if not reports:
        return
    ids = {report["origin_unit_id"] for report in reports}
    sources = {
        row["source_view_id"]: row
        for row in _detached_relation(root, manifest, "sources")
        if row["source_view_id"] in ids
    }
    for report in reports:
        source = sources.get(report["origin_unit_id"])
        if source is None:
            raise ValueError("inline formula verification lacks exact retained source")
        verify_inline_formula_report(report, source)
