"""Explicit on-demand parsing against pinned archived source and text products.

Each request owns a new task/run and immutable outputs. A source-ready cut establishes only
this request's products; it is never a graded or fully evaluated run-completion claim.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, select

from corpus_structure.core.evidence import MacroDef, RenditionContent
from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.macros import MacroFragment, MacroSource, read_macros
from corpus_structure.ingest.text_product import text_product_artifacts, text_product_payload
from corpus_structure.methods.math.grammar import PARSE_SECONDS

from .identity import canonical_bytes
from .metadata import table
from .operations import (
    OperationConflict,
    OperationDescriptor,
    binding_of,
    claim_tasks,
    complete_unit_result,
    create_run,
    create_task,
    end_source_run,
    record_method,
    seal_cut,
)
from .parsing_products import (
    ParsingProductUnavailable,
    PreparedLayeredParsingProduct,
    PreparedParsingProductSet,
    ProductReference,
    parsing_context_for_task,
    prepare_layered_product,
    read_layered_product,
)

Demand = Literal["lexical", "structure", "syntax", "interpretation", "symbolic", "assessment"]


class ParsingRequestUnavailable(ValueError):
    """A pinned input cannot be consumed by this finite implementation."""

    def __init__(self, reason: str, detail: str, *, rebuild_required: bool = False):
        self.reason, self.detail, self.rebuild_required = reason, detail, rebuild_required
        super().__init__(detail)


class ParsingRequestConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    root: dict[str, Any]
    text_product: dict[str, Any]
    demand: Demand
    seconds: float = Field(default=PARSE_SECONDS, gt=0, allow_inf_nan=False, strict=True)
    math_index: int | None = None
    start: int | None = None
    end: int | None = None
    question: str | None = None
    predicate: str | None = None


@dataclass(frozen=True, slots=True)
class ParsingRequestResult:
    run_id: int
    task_id: int
    cut_id: int | None
    status: Literal["source_ready", "failed", "cancelled"]
    products: tuple[ProductReference, ...]
    diagnostic: str | None = None
    inputs: tuple[ProductReference, ...] = ()


def _math_section(dependencies: bytes) -> Mapping[str, Any]:
    """Only the originating invocation's archived admitted math section supplies defaults."""
    sections = [
        operation.get("parameters", {}).get("math")
        for operation in json.loads(dependencies).get("operations", {}).values()
        if operation.get("parameters", {}).get("math") is not None
    ]
    if sections and any(section != sections[0] for section in sections[1:]):
        raise ParsingRequestUnavailable(
            "context_ambiguous", "source run has competing archived math configurations"
        )
    return sections[0] if sections else {}


def _page_sources(payload: Mapping[str, Any]) -> tuple[MacroSource, ...]:
    """Reconstruct page artifacts using the retained recipe, preserving original source maps."""
    projected = {
        e["representation_id"]
        for m in payload["mappings"]
        if m["operation"] == "project"
        for e in payload["mapping_endpoints"]
        if e["mapping_id"] == m["mapping_id"] and e["side"] == "target"
    }
    event_reps = {
        n["representation_id"] for n in payload["nodes"] if n["kind"] == "macro_event"
    } - projected
    out = []
    for rep in payload["representations"]:
        key = rep["representation_id"]
        if key not in event_reps:
            continue
        value = rep["text_content"]
        read = read_macros(value, source_ref=key)
        retained = [
            n
            for n in payload["nodes"]
            if n["kind"] == "macro_event" and n["representation_id"] == key
        ]
        if len(retained) != len(read.events):
            raise ParsingRequestUnavailable(
                "rebuild_required",
                "archived macro recipe cannot be reconstructed",
                rebuild_required=True,
            )
        events = []
        for event, original in zip(read.events, retained, strict=True):
            details = original.get("macro_event")
            if not isinstance(details, Mapping):
                raise ParsingRequestUnavailable(
                    "rebuild_required",
                    "archived macro events lack typed metadata",
                    rebuild_required=True,
                )
            if (event.start, event.end, event.name) != (
                original["start_offset"],
                original["end_offset"],
                original["name"],
            ):
                raise ParsingRequestUnavailable(
                    "rebuild_required",
                    "archived macro event coordinates differ",
                    rebuild_required=True,
                )
            events.append(replace(event, status=details["status"]))
        fragments = []
        for mapping in payload["mappings"]:
            targets = [
                e
                for e in payload["mapping_endpoints"]
                if e["mapping_id"] == mapping["mapping_id"]
                and e["side"] == "target"
                and e["representation_id"] == key
            ]
            sources = tuple(
                (e["start_offset"], e["end_offset"])
                for e in payload["mapping_endpoints"]
                if e["mapping_id"] == mapping["mapping_id"]
                and e["side"] == "source"
                and e["representation_id"] == "decoded"
            )
            fragments.extend(
                MacroFragment(e["start_offset"], e["end_offset"], sources, mapping["reason"])
                for e in targets
            )
        out.append(MacroSource(key, value, replace(read, events=tuple(events)), tuple(fragments)))
    return tuple(out)


def _selected_views(
    payload: Mapping[str, Any], config: ParsingRequestConfig
) -> list[dict[str, Any]]:
    views = sorted(
        (n for n in payload["nodes"] if n["kind"] == "parse_view"),
        key=lambda n: (n["start_offset"], n["end_offset"]),
    )
    if config.math_index is not None:
        if config.math_index < 0 or config.math_index >= len(views):
            raise ParsingRequestUnavailable(
                "selector_invalid", "math index is outside the pinned text product"
            )
        return [views[config.math_index]]
    if config.start is not None:
        found = [
            n for n in views if (n["start_offset"], n["end_offset"]) == (config.start, config.end)
        ]
        if len(found) != 1:
            raise ParsingRequestUnavailable(
                "selector_invalid",
                "range must identify exactly one archived mathematical parse view",
            )
        return found
    if config.demand in {"lexical", "structure"}:
        return views
    raise ParsingRequestUnavailable(
        "selector_required", "select one mathematical index or exact archived parse-view range"
    )


def _products(
    config: ParsingRequestConfig,
    *,
    task_id: int,
    root: ProductReference,
    text_reference: ProductReference,
    text_payload: Mapping[str, Any],
    content: RenditionContent,
    context,
    prepared,
    section: Mapping[str, Any],
    source_run_id: int,
    source_dependency_digest: str,
):
    from corpus_structure.core.tex import effective_macros

    canonical = next(
        r["text_content"]
        for r in text_payload["representations"]
        if r["representation_id"] == "canonical"
    )
    views = _selected_views(text_payload, config)
    pages = _page_sources(text_payload)
    page_table = {
        event.name: event.definition
        for source in pages
        for event in source.read.events
        if event.status == "accepted" and event.definition is not None
    }
    fallback = {name: MacroDef(body=body) for name, body in section.get("macros", {}).items()}
    if config.demand in {"lexical", "structure"}:
        # Views are already exact inner source ranges. Capture includes the complete canonical
        # representation; re-demanding structure never changes the original product.
        text = text_product_payload(
            canonical,
            root=root.values(),
            math_ranges=[
                (n["start_offset"], n["end_offset"], None, None)
                for n in views
                if n["end_offset"] > n["start_offset"]
            ],
            macro_sources=pages,
            fallback_macros=fallback,
            fallback_source_ref=f"run:{source_run_id}:dependencies:{source_dependency_digest}:math",
            structure=config.demand == "structure",
            expand_macros=config.demand != "lexical",
            product_key="text:" + config.demand,
        )
        artifacts = text_product_artifacts(text)
        text["dependencies"].append(
            dict(
                name="input-text",
                kind="product",
                target_task_id=text_reference.task_id,
                target_product_key=text_reference.product_key,
                target_content_digest=text_reference.content_digest,
            )
        )
        prepared_text = prepare_layered_product(text, context=context)
        return PreparedParsingProductSet(
            (prepared_text,), required=("text:" + config.demand,), artifacts=artifacts
        )
    products = []
    artifacts = ()
    from corpus_structure.methods.math.prepared import PreparedMathInput
    from corpus_structure.methods.math.products import (
        assessment_product_payload,
        interpretation_product_payload,
    )

    from .analysis_contracts import prepare_interpretation_context

    view = views[0]
    a, b = view["start_offset"], view["end_offset"]
    source_id = f"text:{text_reference.task_id}:{text_reference.product_key}:{text_reference.content_digest}"
    macros = effective_macros(page_table, fallback)
    if config.demand == "syntax":
        mathematical_context = prepare_interpretation_context(
            prepared,
            macros=macros,
            constants=section.get("constants", ()),
            source_id=source_id,
            scope=dict(root=root.values(), node=view["node_id"]),
            demand="syntax",
        )
        operand = PreparedMathInput(
            mathematical_context,
            canonical[a:b],
            seconds=config.seconds,
            source_text=canonical[a:b],
            source_start=a,
            parse_start=a,
        )
    else:
        from corpus_structure.methods.math.source_context import prepare_source_math

        if content.canonical_text != canonical:
            raise ParsingRequestUnavailable(
                "source_mismatch", "selected source and text products disagree on canonical content"
            )
        source_math = prepare_source_math(
            content,
            prepared=prepared,
            macros=macros,
            constants=section.get("constants", ()),
            source_id=source_id,
            seconds=config.seconds,
            through_offset=b,
            demand="scientific" if config.demand == "assessment" else config.demand,
            source_views={
                (node["start_offset"], node["end_offset"]): node["node_id"]
                for node in text_payload["nodes"] if node["kind"] == "parse_view"
            },
        )
        matches = [op for op in source_math.operands
                   if op.parse_start == a and op.parse_start + len(op.latex) == b]
        if len(matches) != 1:
            raise ParsingRequestUnavailable(
                "selector_invalid", "selected parse view does not identify one archived source expression"
            )
        operand = matches[0]
    selected_text = text_reference
    stage = "symbolic" if config.demand == "assessment" else config.demand
    math_payload = interpretation_product_payload(
        operand,
        root=root,
        text_product=selected_text,
        source_node_id=view["node_id"],
        product_key="math",
        stage=stage,
    )
    prepared_math = prepare_layered_product(math_payload, context=context)
    products.append(prepared_math)
    if math_payload["lifecycle"] != "available":
        return PreparedParsingProductSet(tuple(products), artifacts=artifacts)
    if config.demand == "assessment":
        assert config.question is not None
        assessment = operand.assess(config.question, predicate=config.predicate)
        value = assessment_product_payload(
            operand,
            assessment,
            root=root,
            interpretation_product=ProductReference(task_id, "math", prepared_math.digest),
        )
        products.append(prepare_layered_product(value, context=context))
    required = tuple(p.product_key for p in products if p.values()["lifecycle"] == "available")
    return PreparedParsingProductSet(tuple(products), required=required, artifacts=artifacts)


def request_parsing(
    engine: Engine,
    *,
    root: ProductReference,
    text_product: ProductReference,
    demand: Demand,
    code_commit: str,
    seconds: float = PARSE_SECONDS,
    math_index: int | None = None,
    start: int | None = None,
    end: int | None = None,
    question: str | None = None,
    predicate: str | None = None,
    holder: str = "parsing-request",
) -> ParsingRequestResult:
    """Run a finite demand against pinned inputs before the publication transaction."""
    if root.product_key != "source":
        raise ParsingRequestUnavailable(
            "wrong_product", "root must identify the pinned original source product"
        )
    config = ParsingRequestConfig(
        root=root.values(),
        text_product=text_product.values(),
        demand=demand,
        math_index=math_index,
        start=start,
        end=end,
        question=question,
        predicate=predicate,
        seconds=seconds,
    )
    if (start is None) != (end is None) or (math_index is not None and start is not None):
        raise ValueError("choose a math index or one paired range")
    if (demand == "assessment") != (question is not None) or (
        predicate is not None and demand != "assessment"
    ):
        raise ValueError(
            "named assessments require a question; other demands do not accept "
            "assessment parameters"
        )
    if not code_commit or not holder:
        raise ValueError("request requires code identity and claim holder")
    from .parsing_products import select_parsing_request_source
    from .releases import open_release

    task, run, build = (table(n) for n in ("ops.task", "ops.run", "ops.rendition_build"))
    with engine.begin() as conn:
        origin = (
            conn.execute(
                select(run, build.c.rendition_id)
                .join(task, task.c.run_id == run.c.id)
                .join(build, build.c.task_id == task.c.id)
                .where(task.c.id == root.task_id)
            )
            .mappings()
            .one_or_none()
        )
        if origin is None:
            raise ParsingRequestUnavailable(
                "missing_source", "pinned source build is unavailable", rebuild_required=True
            )
        prepared = open_release(conn, origin["release_id"])
        from .contracts import EXECUTION_COMPILER_VERSION, execution_payload

        archived_execution = execution_payload(prepared)
        if (
            archived_execution is None
            or json.loads(archived_execution)["inputs"]["compiler_version"]
            != EXECUTION_COMPILER_VERSION
        ):
            raise ParsingRequestUnavailable(
                "rebuild_required",
                "archived execution ABI has no admitted on-demand parsing producer",
                rebuild_required=True,
            )
        try:
            context = parsing_context_for_task(conn, root.task_id)
            source = read_layered_product(conn, root, context=context)
            text = read_layered_product(conn, text_product, context=context)
        except ParsingProductUnavailable as error:
            raise ParsingRequestUnavailable(
                "rebuild_required", str(error), rebuild_required=True
            ) from error
        if source is None or not isinstance(text, PreparedLayeredParsingProduct):
            raise ParsingRequestUnavailable(
                "missing_product",
                "pinned source/text product is unavailable",
                rebuild_required=True,
            )
        text_payload = text.values()
        if (
            text_payload["kind"] != "text"
            or text_payload["root"] != root.values()
            or text_payload["lifecycle"] != "available"
        ):
            raise ParsingRequestUnavailable(
                "wrong_product", "text product does not name this available pinned source root"
            )
        _selected_views(text_payload, config)
        renditions = table("kb.rendition")
        content = RenditionContent.model_validate(
            conn.scalar(select(renditions.c.content).where(renditions.c.id == origin["rendition_id"]))
        )
        source_binding = binding_of(conn, origin["id"])
        section = _math_section(source_binding.dependencies)
        params = config.model_dump(mode="json")
        digest = sha256(canonical_bytes(params)).hexdigest()
        method = OperationDescriptor(
            "parsing.request",
            "2",
            MethodFamily.NORMALIZE,
            MethodTier.DETERMINISTIC,
            TaskUnitType.RENDITION,
            ParsingRequestConfig,
        )
        run_id = create_run(
            conn,
            project_id=origin["project_id"],
            binding=source_binding,
            kind="slice",
            options={"parsing_request": params},
            code_commit=code_commit,
        )
        rendition_id = select_parsing_request_source(conn, run_id=run_id, root=root)
        config_id = record_method(conn, method, "request", params, digest, prepared=prepared)
        task_id = create_task(
            conn,
            run_id=run_id,
            config_id=config_id,
            stage="parsing",
            unit_type="rendition",
            unit_id=rendition_id,
            unit_key="parsing:" + digest,
            input_hash=digest,
            fresh=False,
        )
        reused = conn.scalar(select(task.c.reused_task_id).where(task.c.id == task_id))
        if reused is not None:
            from .parsing_products import select_layered_products

            selected = select_layered_products(
                conn,
                run_id=run_id,
                rendition_id=rendition_id,
                producing_task_id=reused,
                root_task_id=root.task_id,
            )
            expected = (
                ("text:" + demand,)
                if demand in {"lexical", "structure"}
                else (("math", "assessment") if demand == "assessment" else ("math",))
            )
            if {p.reference.product_key for p in selected} != set(expected) or any(
                p.lifecycle != "available" for p in selected
            ):
                raise ParsingRequestUnavailable(
                    "reused_result_unavailable",
                    "completed request does not retain its required available products",
                )
            cut = seal_cut(conn, run_id, "parsing-request-source", final=True)
            references = {p.reference.product_key: p.reference for p in selected}
            return ParsingRequestResult(
                run_id,
                task_id,
                cut,
                "source_ready",
                tuple(references[key] for key in expected),
                inputs=(root, text_product),
            )
        claim = claim_tasks(conn, run_id=run_id, config_id=config_id, holder=holder)[0]
    try:
        products = _products(
            config,
            task_id=task_id,
            root=root,
            text_reference=text_product,
            text_payload=text_payload,
            content=content,
            context=context,
            prepared=prepared,
            section=section,
            source_run_id=origin["id"],
            source_dependency_digest=source_binding.dependency_digest,
        )
        failed = any(p.values()["lifecycle"] != "available" for p in products.products)
        result = UnitResult(
            ref=UnitRef(TaskUnitType.RENDITION, rendition_id, "parsing:" + digest),
            outcome=ObservationOutcome.FAILED if failed else ObservationOutcome.EMPTY,
            error="requested parsing stage unavailable" if failed else None,
            parsing_products=products,
        )
        with engine.begin() as conn:
            complete_unit_result(
                conn,
                task_id=task_id,
                attempt=claim.attempt,
                holder=holder,
                prepared=prepared,
                result=result,
                method=method,
                configuration_hash=digest,
                source="parsing-request",
            )
            if failed:
                end_source_run(conn, run_id, failure={"message": result.error})
                cut_id = None
            else:
                cut_id = seal_cut(conn, run_id, "parsing-request-source", final=True)
        refs = tuple(ProductReference(task_id, p.product_key, p.digest) for p in products.products)
        return ParsingRequestResult(
            run_id,
            task_id,
            cut_id,
            "failed" if failed else "source_ready",
            refs,
            result.error,
            (root, text_product),
        )
    except Exception as error:
        diagnostic = f"{type(error).__name__}: {error}"
        with engine.begin() as conn:
            current = conn.execute(select(task.c.status).where(task.c.id == task_id)).scalar_one()
            if current == "running":
                failure = UnitResult(
                    ref=UnitRef(TaskUnitType.RENDITION, rendition_id, "parsing:" + digest),
                    outcome=ObservationOutcome.FAILED,
                    error=diagnostic,
                )
                try:
                    with conn.begin_nested():
                        complete_unit_result(
                            conn,
                            task_id=task_id,
                            attempt=claim.attempt,
                            holder=holder,
                            prepared=prepared,
                            result=failure,
                            method=method,
                            configuration_hash=digest,
                            source="parsing-request",
                        )
                except OperationConflict:
                    # An expired attempt cannot record a terminal result; draining the owned
                    # run below still prevents a stale worker from publishing afterwards.
                    pass
            end_source_run(conn, run_id, failure={"message": diagnostic})
            status = conn.execute(select(run.c.status).where(run.c.id == run_id)).scalar_one()
        return ParsingRequestResult(
            run_id,
            task_id,
            None,
            "cancelled" if status == "cancelled" else "failed",
            (),
            diagnostic,
            (root, text_product),
        )
    except BaseException:
        # Drain our owned attempt before propagating operator cancellation.
        with engine.begin() as conn:
            end_source_run(conn, run_id)
        raise
