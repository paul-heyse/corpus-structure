"""Bounded selected structural reports and native authority; private proposals stay private."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.refusals import SemanticRefusal

from .selected_structural import (
    SelectedStructuralRoot,
    StructuralReadRequest,
    bounded_result,
    producer,
    selected_root,
    structural_report,
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


def dossier_member_page(report, *, population, offset, limit):
    """The display policy chooses from immutable membership; reading changes neither."""
    if report.dossier is None:
        raise ValueError("selected output is not a dossier")
    dossier = report.dossier
    representation = dossier.representation
    members = {member.member_id: member for member in dossier.members}
    keys = (
        tuple(member.member_id for member in dossier.members)
        if population == "membership"
        else representation.selected
    )
    if offset < 0 or offset > len(keys):
        raise ValueError("dossier continuation is outside its immutable population")
    chosen = keys[offset : offset + limit]
    selected = set(chosen)
    passages = {passage.passage_id: passage for passage in report.inputs.passages}
    sources = {source.identity: source for source in report.inputs.sources}
    citations = []
    for key in chosen:
        member = members[key]
        if member.contribution_citations:
            cited = tuple(citation.span for citation in member.contribution_citations)
        else:
            cited = (member.citation,)
        for span in cited:
            source = sources[passages[span.passage_id].source_ref]
            citations.append(
                dict(
                    member_id=key,
                    source=source.model_dump(mode="python"),
                    citation=span.model_dump(mode="python"),
                )
            )
        if member.comparison_binding is not None:
            binding = member.comparison_binding
            citations.append(
                dict(
                    member_id=key,
                    context="opposite_comparison_side",
                    source=binding.opposite_source.model_dump(mode="python"),
                    citation=binding.opposite_citation.model_dump(mode="python"),
                )
            )
    end = offset + len(chosen)
    return dict(
        members=[members[key].model_dump(mode="python", exclude_none=True) for key in chosen],
        citations=citations,
        supported_facets=[
            facet.model_dump(mode="python")
            for facet in dossier.supported_facets
            if facet.member_id in selected
        ],
        next_offset=end if end < len(keys) else None,
        full_member_count=len(members),
        display_member_count=len(representation.selected),
        omitted_member_count=len(representation.omitted),
        missing_facet_count=len(representation.missing_facets),
        mandatory_overflow=representation.mandatory_overflow,
        membership_digest=representation.membership_digest,
        facet_digest=representation.facet_digest,
        policy=representation.policy,
        product_id=report.product_id,
    )


def inspect_selected_dossier(conn, request: SelectedDossierRequest):
    from corpus_structure.semantic.demand_queries import _cursor

    from .rich_queries import decode_rich_cursor

    cursor = None if request.cursor is None else decode_rich_cursor(request.cursor)
    if cursor is not None:
        if (
            set(cursor) != {"version", "request", "cut", "binding", "offset"}
            or cursor["version"] != "selected-dossier-page-v1"
            or type(cursor["offset"]) is not int
        ):
            raise ValueError("invalid selected dossier continuation")
        expected = request.model_dump(
            mode="python",
            exclude={"cursor", "limit", "max_bytes", "read_id", "expected_cut", "implementation"},
        )
        if cursor["request"] != expected:
            raise ValueError("dossier continuation differs from requested root or population")
        pinned = cursor["cut"]
        if request.read_id is not None and (
            request.read_id != pinned["read_id"]
            or request.expected_cut != cursor["binding"]["cut_id"]
        ):
            raise ValueError("dossier continuation differs from requested native read")
        if (
            request.implementation is not None
            and request.implementation != cursor["binding"]["implementation"]
        ):
            raise ValueError("dossier continuation differs from requested implementation")
        request = request.model_copy(
            update=dict(
                read_id=pinned["read_id"],
                expected_cut=cursor["binding"]["cut_id"],
                implementation=cursor["binding"]["implementation"],
            )
        )
    with structural_scope(conn, request, roots=(request.root,)) as scope:
        selected = selected_root(scope, request.root)
        if selected is None:
            return bounded_result(
                request,
                dict(
                    format="selected-dossier-page-v1",
                    availability="outside_selection",
                    cut_id=scope.cut.identity,
                    cut=scope.cut.record,
                    implementation=scope.implementation,
                ),
            )
        report = structural_report(scope, selected)
        if report.dossier is None:
            raise ValueError("selected output is not a dossier")
        representation = report.dossier.representation
        binding = dict(
            cut_id=scope.cut.identity,
            implementation=scope.implementation,
            product_id=report.product_id,
            membership_digest=representation.membership_digest,
            facet_digest=representation.facet_digest,
            policy=representation.policy,
        )
        if cursor is not None and cursor["binding"] != binding:
            raise ValueError("dossier continuation differs from exact membership/facets/policy")
        page = dossier_member_page(
            report,
            population=request.population,
            offset=0 if cursor is None else cursor["offset"],
            limit=request.limit,
        )
        offset = page.pop("next_offset")
        next_cursor = (
            None
            if offset is None
            else _cursor(
                dict(
                    version="selected-dossier-page-v1",
                    cut=scope.cut.record,
                    binding=binding,
                    offset=offset,
                    request=request.model_dump(
                        mode="python",
                        exclude={
                            "cursor",
                            "limit",
                            "max_bytes",
                            "read_id",
                            "expected_cut",
                            "implementation",
                        },
                    ),
                )
            )
        )
        result = dict(
            format="selected-dossier-page-v1",
            availability="observed",
            cut_id=scope.cut.identity,
            cut=scope.cut.record,
            implementation=scope.implementation,
            producer=producer(selected),
            population=request.population,
            standing="private_proposal",
            public_admission="not-established",
            **page,
            next_cursor=next_cursor,
        )
        return bounded_result(request, result)


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
