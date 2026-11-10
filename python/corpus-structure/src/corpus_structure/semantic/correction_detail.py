"""Bounded views of actual validator evidence, without a second validation pass."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import islice
from typing import Any

from .identity import canonical_bytes


class InputPath(str):
    """A display pointer carrying segments established by the owning traversal."""

    segments: tuple
    locator: str | None

    def __new__(cls, segments=(), *, display=None, locator=None):
        result = super().__new__(
            cls,
            display
            if display is not None
            else "#"
            + "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in segments),
        )
        result.segments = tuple(segments)
        result.locator = locator
        return result


def child_path(path, segment):
    return InputPath(
        (*getattr(path, "segments", ()), segment),
        display=str(path) + "/" + str(segment).replace("~", "~0").replace("/", "~1"),
        locator=getattr(path, "locator", None),
    )


@dataclass(frozen=True)
class BoundaryDiagnostic:
    code: str
    category: str
    message: str
    input_path: tuple | None = None
    schema_path: str | None = None
    locator: str | None = None

    @property
    def pointer(self):
        return str(InputPath(self.input_path)) if self.input_path is not None else None


@dataclass(frozen=True)
class JsonErrorCapture:
    errors: tuple
    inventory_complete: bool
    examined_count: int


def capture_json_errors(validator, value, *, detail=False, max_errors=100):
    if type(max_errors) is not int or not 1 <= max_errors <= 1000:
        raise ValueError("max_errors must be from 1 through 1000")
    limit = max_errors if detail else 1
    observed = tuple(islice(validator.iter_errors(value), limit + 1))
    return JsonErrorCapture(observed[:limit], len(observed) <= limit, len(observed))


def path_segments(path):
    return [
        dict(kind="index", index=p) if type(p) is int else dict(kind="field", field=str(p))
        for p in path
    ]


def _safe_value(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float:
        import math

        return value if math.isfinite(value) else {"unavailable": "nonfinite"}
    if isinstance(value, dict):
        return {str(k): _safe_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(v) for v in value]
    return {"unavailable": "non-JSON value", "type": type(value).__name__}


def _detail_limits(max_errors, max_depth, max_bytes):
    if type(max_errors) is not int or not 1 <= max_errors <= 1000:
        raise ValueError("max_errors must be from 1 through 1000")
    if (
        type(max_depth) is not int
        or not 1 <= max_depth <= 16
        or type(max_bytes) is not int
        or not 1024 <= max_bytes <= 1048576
    ):
        raise ValueError("correction limits exceed supported depth/byte range")


def _bounded_detail(detail, evidence, max_bytes):
    """One byte budget covers the detail and its inline evidence together."""
    if (
        len(canonical_bytes(dict(correction_detail=detail, evidence=evidence))) > max_bytes
        and evidence.get("content") is not None
    ):
        evidence = dict(
            evidence,
            kind="marker",
            content=None,
            reason="Original evidence exceeds the combined correction-detail byte limit.",
        )
    while (
        len(canonical_bytes(dict(correction_detail=detail, evidence=evidence))) > max_bytes
        and detail["nodes"]
    ):
        detail["nodes"].pop()
        detail["render_complete"] = False
    return detail, evidence


def error_detail(
    error, *, raw_evidence=False, max_errors=100, max_depth=8, max_bytes=262144, defer_bytes=False
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retain branching and multiplicity; messages containing input values are opt-in."""
    _detail_limits(max_errors, max_depth, max_bytes)
    from jsonschema.exceptions import SchemaError
    from jsonschema.exceptions import ValidationError as JsonError
    from pydantic import ValidationError

    if isinstance(getattr(error, "original", None), (JsonError, SchemaError, ValidationError)):
        error = error.original
    fact = getattr(error, "boundary_diagnostic", None)
    if fact is not None and getattr(error, "validation_capture", None) is None:
        return dict(
            engine="boundary",
            nodes=[
                dict(
                    ordinal=0,
                    parent=None,
                    engine="boundary",
                    keyword=fact.code,
                    message=fact.message,
                    input_path=path_segments(fact.input_path or ()),
                    schema_path=[],
                )
            ],
            examined_count=1,
            inventory_complete=True,
            render_complete=True,
            coverage_note="Owner-assigned wrapper diagnostic; original cause remains in-call.",
        ), dict(
            kind="marker",
            engine="boundary",
            media_type="application/json",
            sensitivity="safe",
            reason="Original wrapper cause remains in-call.",
        )
    capture = getattr(error, "validation_capture", None)
    if capture is not None:
        roots, complete, engine = capture.errors, capture.inventory_complete, "jsonschema"
    elif isinstance(error, (JsonError, SchemaError)):
        roots, complete, engine = (error,), False, "jsonschema"
    elif isinstance(error, ValidationError):
        roots, complete, engine = (
            error.errors(include_url=False, include_input=False, include_context=False),
            True,
            "pydantic",
        )
    else:
        roots, complete, engine = (), False, "boundary"
    nodes, raw, rendered = [], [], True

    def append(item, parent, depth):
        nonlocal rendered
        if len(nodes) >= max_errors or depth > max_depth:
            rendered = False
            return
        if isinstance(item, dict):
            keyword, input_path, schema_path = item["type"], item["loc"], ()
            children = ()
            message = item["msg"]
        else:
            keyword, input_path, schema_path = (
                str(item.validator),
                item.absolute_path,
                item.absolute_schema_path,
            )
            children, message = item.context, item.message
        node = dict(
            ordinal=len(nodes),
            parent=parent,
            engine=engine,
            keyword=keyword,
            input_path=path_segments(input_path),
            schema_path=path_segments(schema_path),
            message=message if raw_evidence else "Validation constraint failed: " + keyword,
        )
        if not defer_bytes and len(canonical_bytes(dict(nodes=[*nodes, node]))) > max_bytes:
            rendered = False
            return
        ordinal = len(nodes)
        nodes.append(node)
        if raw_evidence:
            raw.append(dict(ordinal=ordinal, message=message))
        for child in children:
            append(child, ordinal, depth + 1)

    for item in roots:
        append(item, None, 0)
    detail = dict(
        engine=engine,
        nodes=nodes,
        examined_count=capture.examined_count if capture else len(roots),
        inventory_complete=complete,
        render_complete=rendered,
        coverage_note=(
            "Yield limits do not preempt individual validator work or eager union evaluation."
        ),
    )
    content = canonical_bytes(raw) if raw_evidence else None
    evidence = dict(
        kind="inline" if content is not None else "marker",
        engine=engine,
        media_type="application/json",
        digest=sha256(content).hexdigest() if content else None,
        content=content.decode() if content else None,
        sensitivity="raw" if raw_evidence else "safe",
        reason=None
        if raw_evidence
        else "Input-bearing engine messages withheld; original errors remain in-call.",
    )
    return (detail, evidence) if defer_bytes else _bounded_detail(detail, evidence, max_bytes)


def rdf_term(node, *, values=False):
    from rdflib import BNode, Literal, URIRef

    if isinstance(node, URIRef):
        return dict(kind="iri", value=str(node) if values else None, withheld=not values)
    if isinstance(node, BNode):
        return dict(kind="blank", value=str(node))
    if isinstance(node, Literal):
        return dict(
            kind="literal",
            value=str(node) if values else None,
            datatype=str(node.datatype) if node.datatype else None,
            language=node.language,
            withheld=not values,
        )
    return dict(kind="unavailable")


def shacl_path(graph, node, *, max_depth=8, max_nodes=1000):
    """Admit bounded SHACL structure before invoking RDFLib's recursive parser."""
    from rdflib import RDF, BNode, URIRef
    from rdflib.extras.shacl import parse_shacl_path
    from rdflib.namespace import SH
    from rdflib.paths import AlternativePath, InvPath, MulPath, SequencePath

    count = 0
    active = set()
    forms = (
        SH.inversePath,
        SH.alternativePath,
        SH.zeroOrMorePath,
        SH.oneOrMorePath,
        SH.zeroOrOnePath,
    )

    def admit(value, depth):
        nonlocal count
        count += 1
        if count > max_nodes or depth > max_depth or value in active:
            raise ValueError("cyclic or oversized SHACL path")
        if isinstance(value, URIRef):
            return
        if not isinstance(value, BNode):
            raise ValueError("unsupported SHACL path term")
        active.add(value)
        try:
            found = [
                (p, tuple(graph.objects(value, p))) for p in forms if (value, p, None) in graph
            ]
            is_list = (value, RDF.first, None) in graph
            if len(found) + is_list != 1:
                raise ValueError("ambiguous or unsupported SHACL path")
            if is_list or found[0][0] == SH.alternativePath:
                cursor = value if is_list else found[0][1][0]
                if not is_list and len(found[0][1]) != 1:
                    raise ValueError("multiple alternative path lists")
                seen = set()
                size = 0
                while cursor != RDF.nil:
                    count += 1
                    if cursor in seen or count > max_nodes:
                        raise ValueError("cyclic or oversized RDF list")
                    seen.add(cursor)
                    first, rest = (
                        tuple(graph.objects(cursor, RDF.first)),
                        tuple(graph.objects(cursor, RDF.rest)),
                    )
                    if len(first) != 1 or len(rest) != 1:
                        raise ValueError("malformed RDF list")
                    admit(first[0], depth + 1)
                    cursor = rest[0]
                    size += 1
                if size < 2:
                    raise ValueError("SHACL path list requires two members")
            else:
                if len(found[0][1]) != 1:
                    raise ValueError("multiple SHACL path operands")
                admit(found[0][1][0], depth + 1)
        finally:
            active.remove(value)

    def encode(path):
        if isinstance(path, URIRef):
            return dict(kind="predicate", iri=str(path))
        if isinstance(path, (SequencePath, AlternativePath)):
            return dict(
                kind="sequence" if isinstance(path, SequencePath) else "alternative",
                members=[encode(p) for p in path.args],
            )
        if isinstance(path, InvPath):
            return dict(kind="inverse", member=encode(path.arg))
        if isinstance(path, MulPath) and path.mod in ("*", "+", "?"):
            return dict(kind="repeat", modifier=path.mod, member=encode(path.path))
        raise ValueError("unsupported RDFLib path class")

    try:
        admit(node, 0)
        return dict(status="available", path=encode(parse_shacl_path(graph, node)))
    except (ValueError, TypeError, RecursionError) as exc:
        return dict(status="unsupported", reason=str(exc), original=rdf_term(node))


def graph_detail(
    validation,
    *,
    raw_evidence=False,
    max_errors=100,
    max_depth=8,
    max_bytes=262144,
    defer_bytes=False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _detail_limits(max_errors, max_depth, max_bytes)
    from rdflib import RDF, Graph
    from rdflib.namespace import SH

    nodes, rendered = [], True
    if len(validation.report) <= 8 * 1024 * 1024:
        from rdflib.exceptions import ParserError

        try:
            graph = Graph().parse(data=validation.report, format="nt")
        except ParserError:
            graph = Graph()
            rendered = False
        active = set()

        def append(result, parent, depth):
            nonlocal rendered
            if result in active or depth > max_depth or len(nodes) >= max_errors:
                rendered = False
                return
            active.add(result)
            ordinal = len(nodes)
            details = dict(
                focus=rdf_term(graph.value(result, SH.focusNode), values=raw_evidence),
                value=rdf_term(graph.value(result, SH.value), values=raw_evidence),
                source_constraint=rdf_term(graph.value(result, SH.sourceConstraint), values=True),
            )
            path = graph.value(result, SH.resultPath)
            node = dict(
                ordinal=ordinal,
                parent=parent,
                engine="pyshacl",
                keyword=str(graph.value(result, SH.sourceConstraintComponent) or "SHACL"),
                input_path=[],
                schema_path=[],
                message="Graph constraint failed.",
                rdf_json=canonical_bytes(details).decode(),
                path_json=canonical_bytes(shacl_path(graph, path, max_depth=max_depth)).decode()
                if path is not None
                else None,
            )
            if not defer_bytes and len(canonical_bytes(dict(nodes=[*nodes, node]))) > max_bytes:
                rendered = False
                active.remove(result)
                return
            nodes.append(node)
            for child in sorted(graph.objects(result, SH.detail), key=str):
                append(child, ordinal, depth + 1)
            active.remove(result)

        children = set(graph.objects(None, SH.detail))
        for result in sorted(
            set(graph.subjects(RDF.type, SH.ValidationResult)) - children, key=str
        ):
            append(result, None, 0)
        if not nodes and not validation.conforms:
            rendered = False
    else:
        rendered = False
    content = validation.report if raw_evidence and len(validation.report) <= max_bytes else None
    detail = dict(
        engine="pyshacl",
        nodes=nodes,
        examined_count=len(nodes),
        inventory_complete=rendered,
        render_complete=rendered,
        coverage_note="Detail bounds do not change the original graph conformance result.",
    )
    evidence = dict(
        kind="inline" if content is not None else "marker",
        engine="pyshacl",
        media_type="application/n-triples",
        digest=sha256(validation.report).hexdigest(),
        content=content.decode() if content is not None else None,
        sensitivity="raw" if raw_evidence else "safe",
        reason=None
        if content is not None
        else "Original graph bytes withheld or exceed requested byte limit.",
    )

    return (detail, evidence) if defer_bytes else _bounded_detail(detail, evidence, max_bytes)


def preparation_diagnostic(item, *, raw_evidence=False):
    """Present compiler/wire diagnostics without trusting library exception wording."""
    from dataclasses import asdict

    facts = asdict(item)
    if not raw_evidence:
        facts.update(message="Model constraint failed: " + item.code, expected=None, actual=None)
    return facts
