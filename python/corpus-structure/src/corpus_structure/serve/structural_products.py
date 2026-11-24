"""Bounded selected structural reports and native authority; private proposals stay private."""

from contextlib import nullcontext
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.page_envelope import PageEnvelope
from corpus_structure.semantic.refusal_types import SemanticRefusal
from corpus_structure.semantic.selected_pages import byte_bounded_page
from corpus_structure.semantic.selected_structural_projection import (
    STRUCTURAL_QUERY_ROOTS,
    dossier_row_inputs,
    producer,
    selected_root,
    structural_report,
)
from corpus_structure.semantic.serving_code import capture_page_refusal

from .selected_structural import (
    SelectedStructuralRoot,
    StructuralReadRequest,
    bounded_result,
    structural_scope,
)


class SelectedStructuralAdmissionBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    report: SelectedStructuralRoot
    admission: SelectedStructuralRoot


class SelectedStructuralRequest(StructuralReadRequest):
    roots: tuple[SelectedStructuralRoot, ...] = Field(min_length=1, max_length=100)
    admissions: tuple[SelectedStructuralAdmissionBinding, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def exact_admission_reports(self):
        if any(binding.report not in self.roots for binding in self.admissions) or len(
            set(self.admissions)
        ) != len(self.admissions):
            raise ValueError(
                "structural admissions require distinct bindings to explicit report roots"
            )
        return self

    @property
    def selection_roots(self):
        return tuple(
            dict.fromkeys((*self.roots, *(binding.admission for binding in self.admissions)))
        )


def inspect_selected_structures(conn, request: SelectedStructuralRequest):
    """Inspect explicit reports and only their explicitly selected native conclusions."""
    from .selected_structural_admission import (
        selected_structural_admission,
        selected_structural_support_root,
    )

    with structural_scope(conn, request, roots=request.selection_roots) as scope:
        reports: list[dict[str, Any]] = []
        for root in request.roots:
            selected = selected_root(scope, root)
            selection_basis = "selected_output"
            if selected is None:
                candidates = [
                    value
                    for binding in request.admissions
                    if binding.report == root
                    for value in (selected_structural_support_root(scope, root, binding.admission),)
                    if value is not None
                ]
                if candidates:
                    selected = candidates[0]
                    selection_basis = "native_structural_report_support"
                    if any(value != selected for value in candidates):
                        raise ValueError(
                            "structural admission bindings disagree on exact ordinary report support"
                        )
            if selected is None:
                reports.append(
                    dict(root=root.model_dump(mode="python"), availability="outside_selection")
                )
                continue
            report = structural_report(scope, selected)
            public_assertions = []
            for binding in request.admissions:
                if binding.report != root:
                    continue
                admitted = selected_structural_admission(scope, binding.admission, selected, report)
                if admitted is not None:
                    value, leaf = admitted
                    public_assertions.append(
                        dict(
                            admission_root=binding.admission.model_dump(mode="python"),
                            admission=value.model_dump(mode="python"),
                            authority=leaf.model_dump(mode="python"),
                        )
                    )
            reports.append(
                dict(
                    root=root.model_dump(mode="python"),
                    availability="observed",
                    selection_basis=selection_basis,
                    producer=producer(selected),
                    report=report.model_dump(mode="python", exclude_none=True),
                    public_assertions=public_assertions,
                )
            )
        return bounded_result(
            request,
            dict(
                format="selected-structural-reports-v1",
                cut_id=scope.cut.identity,
                cut=scope.cut.record,
                implementation=scope.implementation,
                reports=reports,
                standing="private_proposal",
                source_coverage="declared_report_inputs_only",
                public_admission="selected_native_statements"
                if any(report.get("public_assertions") for report in reports)
                else "not-established",
            ),
        )


class SelectedDossierRequest(StructuralReadRequest):
    root: SelectedStructuralRoot
    population: Literal["membership", "display"] = "display"
    limit: int = Field(default=20, strict=True, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=32768)


def inspect_selected_dossier(reader, request: SelectedDossierRequest):

    from corpus_structure.semantic.serving_identity import installed_read_implementation

    with installed_read_implementation(
        type(request),
        entry="corpus_structure.semantic.selected_structural_projection",
        profile="selected-structural-read-v1",
        callables=STRUCTURAL_QUERY_ROOTS,
    ) as implementation:
        if request.implementation is not None and request.implementation != implementation:
            raise ValueError("dossier resource differs from its installed implementation")
        return _inspect_selected_dossier(reader, request, implementation)


def _inspect_selected_dossier(reader, request: SelectedDossierRequest, implementation):
    from corpus_structure.semantic import dossier_row_projection
    from corpus_structure.semantic.continuation_codec import (
        bind_cursor_request,
        decode_pinned_cursor,
        pinned_cursor_basis,
        require_cursor_cut,
        selection_digest,
    )
    from corpus_structure.semantic.refusal_types import InvalidContinuation
    from corpus_structure.semantic.selected_query_cache import (
        ENTRY_ROWS,
        SELECTED_QUERY_CACHE,
        bounded_rows,
        served_key,
        uncached_rows_from,
    )
    from corpus_structure.semantic.serving_identity import installed_read_implementation

    from .selected_structural import StructuralScope

    selection = selection_digest(
        request.model_dump(
            mode="python",
            exclude={"cursor", "limit", "max_bytes", "read_id", "expected_cut", "implementation"},
        )
    )
    version = "selected-dossier-cursor-v3"
    cursor = None
    if request.cursor is not None:
        cursor = decode_pinned_cursor(
            request.cursor, version=version, selection=selection, extra_fields=("binding",)
        )
        request = bind_cursor_request(request, cursor)
    offset = 0 if cursor is None else cursor["position"]

    detached = isinstance(reader, StructuralScope)
    with installed_read_implementation(
        type(request),
        entry=dossier_row_projection.__name__,
        profile="selected-dossier-rows-v1",
        callables=(dossier_row_projection.__name__ + ".dossier_rows",),
    ) as row_implementation:
        with nullcontext(reader) if detached else reader() as conn:
            with structural_scope(conn, request, roots=(request.root,)) as scope:
                current_cut = scope.cut
                if cursor is not None:
                    require_cursor_cut(cursor, current_cut)
                selected = selected_root(scope, request.root)
                if selected is None:
                    return bounded_result(
                        request,
                        dict(
                            format="selected-dossier-page-v2",
                            availability="outside_selection",
                            cut_id=current_cut.identity,
                            cut=current_cut.record,
                            implementation=implementation,
                        ),
                    )
                # Resolve and authorize the actual producing references on every read, including hits.
                report = structural_report(scope, selected)
                if report.dossier is None:
                    raise ValueError("selected output is not a dossier")
                provenance = producer(selected)
                release = current_cut.record.get("release_id")
                numeric_policy = scope.decimal_fixed_point_digits
                member_count = len(
                    report.dossier.members
                    if request.population == "membership"
                    else report.dossier.representation.selected
                )
                if offset > member_count:
                    raise InvalidContinuation(
                        "cursor is outside its immutable derived row population",
                        reason="invalid_continuation",
                    )

            # The selected whole product address commits its body, nominal contract and
            # context. Both releases and the installed report interpreter bind how that
            # body becomes normalized rows. The independent row proof governs reuse.
            key = (
                served_key(
                    conn,
                    "dossier",
                    implementation=row_implementation,
                    basis=(
                        request.root.product_id,
                        release,
                        selected.release_id,
                        numeric_policy,
                        provenance,
                        str(implementation),
                    ),
                    selection=(request.project_id, request.population),
                )
                if not detached
                and member_count <= ENTRY_ROWS
                and row_implementation.reuse_identity is not None
                else None
            )
        del scope, selected
        reuse_refusal = capture_page_refusal()
        with SELECTED_QUERY_CACHE.loading(key) if key is not None else nullcontext() as entry:
            remaining = None
            metadata = None
            if entry is None:
                # Detached or large populations prepare just the requested page plus
                # a lookahead. They never encode a prefix merely to warm the cache.
                inputs, metadata, _ = dossier_row_inputs(
                    report,
                    population=request.population,
                    offset=offset if key is None else 0,
                    limit=request.limit + 1 if key is None else None,
                )
                metadata["producer"] = provenance
                items = dossier_row_projection.dossier_rows(*inputs)
                if key is None:
                    remaining = items
                else:
                    entry, remaining = bounded_rows(items, metadata)
                    if entry is not None:
                        SELECTED_QUERY_CACHE.put(key, entry)
        del report
        metadata = entry.record() if entry is not None else metadata
        assert metadata is not None
        binding = {
            name: metadata[name]
            for name in ("product_id", "membership_digest", "facet_digest", "policy")
        }
        if cursor is not None and cursor["binding"] != binding:
            raise ValueError("dossier continuation differs from exact membership/facets/policy")
        if entry is not None:
            rows = entry.rows(offset)
        elif key is None:
            rows = remaining
        else:
            rows = uncached_rows_from(remaining, offset)

        presentation = PageEnvelope(
            reuse_refusal=reuse_refusal,
            header=dict(
                format="selected-dossier-page-v2",
                availability="observed",
                cut_id=current_cut.identity,
                cut=current_cut.record,
                implementation=implementation,
                population=request.population,
                standing="private_proposal",
                public_admission="not-established",
                **metadata,
            ),
            cursor_basis=pinned_cursor_basis(
                version, selection, current_cut, implementation, binding=binding
            ),
            cursor_field="next_cursor",
            position_field="position",
            arrays=(
                ("members", "members", None, None),
                ("citations", "citations", None, None),
                ("supported_facets", "supported_facets", "value", "ordinal"),
            ),
        )

        try:
            return byte_bounded_page(
                rows,
                offset=offset,
                limit=request.limit,
                max_bytes=request.max_bytes,
                presentation=presentation,
            )
        finally:
            if remaining is not None:
                remaining.close()


class DossierContinuation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    membership_digest: str
    facet_digest: str
    policy: str
    offset: int = Field(strict=True, ge=0)


def dossier_representation_page(report, *, limit=20, continuation=None):
    """Page selected members without changing immutable membership or selection.

    The enclosing completed-cut reader authenticates the report. The continuation
    binds both its source-derived membership and independently supported facets.
    Mandatory overflow is a normal pageable result, never a dropped exception.
    """
    if report.dossier is None or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("representation page requires a dossier and limit 1..100")
    value = report.dossier
    representation = value.representation
    binding = dict(
        product_id=report.product_id,
        membership_digest=representation.membership_digest,
        facet_digest=representation.facet_digest,
        policy=representation.policy,
    )
    offset = 0
    if continuation is not None:
        cursor = DossierContinuation.model_validate(continuation)
        if any(getattr(cursor, key) != expected for key, expected in binding.items()):
            raise SemanticRefusal(
                "dossier continuation differs from exact membership/facets/policy"
            )
        offset = cursor.offset
    if offset > len(representation.selected):
        raise SemanticRefusal("dossier continuation is outside representation")
    selected = representation.selected[offset : offset + limit]
    members = {m.member_id: m for m in value.members}
    end = offset + len(selected)
    return dict(
        members=tuple(members[key] for key in selected),
        continuation=DossierContinuation(**binding, offset=end).model_dump(mode="json")
        if end < len(representation.selected)
        else None,
        mandatory_overflow=representation.mandatory_overflow,
        omitted=representation.omitted,
        missing_facets=representation.missing_facets,
    )
