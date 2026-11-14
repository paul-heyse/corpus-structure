"""Resolve ordinary source choices into the same admitted native demand service."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from corpus_structure.semantic.data_operation_service import (
    DemandDiscoverySelection,
    DemandOperationSelection,
    DemandOriginalSelection,
    DemandRoot,
    NativeDemandRequest,
    create_native_demand,
    execute_data_demand,
)

from .source_request import (
    NamedScope,
    NamedSlice,
    PackDefault,
    SourceRequestError,
    SourceRunRequest,
)

CommandError = SourceRequestError


def prepare_source_demand(
    connection, request: SourceRunRequest, *, domains: Path | None = None, prepared=None
):
    """Acquire exact immutable originals; frozen declarations own executable closure.

    Pack files provide only source-selection conveniences. Provider configuration,
    prepared factories and semantic operation declarations come from the retained
    admitted release/runtime, never from a registry rebuilt from current code.
    """
    import yaml

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_kind_refinements import input_kind_refinements
    from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.original_documents import acquire_original_document_selection
    from corpus_structure.semantic.primary_operations import primary_operation_targets
    from corpus_structure.semantic.releases import load_release
    from corpus_structure.semantic.source_admission import acquire_original_source_selection

    from .commands import resolve_source_domain
    from .slices import records

    prepared = load_release(connection, request.release_id) if prepared is None else prepared
    if prepared.release_id != request.release_id:
        raise SourceRequestError("prepared source request belongs to another release")
    model = bound_data_operation_model(prepared)
    domain = resolve_source_domain(
        connection, request.project_id, request.release_id, request.domain, domains=domains
    )
    document = table("kb.document")
    query = select(document).where(document.c.project_id == request.project_id)
    if request.documents:
        if len(set(request.documents)) != len(request.documents):
            raise SourceRequestError("source documents must be distinct exact keys")
        query = query.where(document.c.key.in_(request.documents))
    documents = list(connection.execute(query.order_by(document.c.key)).mappings())
    if request.documents and {value["key"] for value in documents} != set(request.documents):
        raise SourceRequestError("a selected document is outside the project")
    if request.retained_sources:
        if isinstance(request.selection, (NamedSlice, NamedScope)):
            raise SourceRequestError("retained source selectors cannot combine with named scopes")
        acquired_views = tuple(
            acquire_original_source_selection(
                connection, prepared, value.source, value.selectors, name="view:" + str(index)
            )
            for index, value in enumerate(request.retained_sources)
        )
        if any(value.reference.project_id != request.project_id for value in acquired_views):
            raise SourceRequestError("retained source belongs to a different project")
        keys = {value.root.original_source for value in acquired_views}
        if not keys <= {value["key"] for value in documents}:
            raise SourceRequestError("retained source is outside the selected originals")
        documents = [value for value in documents if value["key"] in keys]
        sections = []
    else:
        acquired_views = ()
        pack = (domains or DOMAINS) / domain
        scopes = (
            yaml.safe_load((pack / "slices.yaml").read_text())
            if (pack / "slices.yaml").exists()
            else {}
        )
        scope = (
            request.selection.name
            if isinstance(request.selection, NamedScope)
            else scopes.get("default_scope")
            if isinstance(request.selection, PackDefault)
            else None
        )
        _, selected = records(
            documents,
            scopes.get("slices", scopes),
            slice=request.selection.name if isinstance(request.selection, NamedSlice) else None,
            scope=scope,
            corpus=None,
        )
        sections = selected["sections"] if selected is not None else []
    originals = tuple(
        acquire_original_document_selection(
            connection,
            project_id=request.project_id,
            document_key=value["key"],
            name="original:" + str(index),
        )
        for index, value in enumerate(documents)
    )
    if not originals:
        raise SourceRequestError("source demand requires at least one registered PDF original")
    if any(value.reference.mime != "application/pdf" for value in originals):
        raise SourceRequestError("source acquisition requires immutable PDF originals")
    captured = not request.retained_sources
    targets = request.targets or primary_operation_targets(request.workflow, captured=captured)
    supplied = {value.operation: value for value in request.selections}
    if len(supplied) != len(request.selections):
        raise SourceRequestError("duplicate source operation selection")
    # Full means the optional families explicitly declared by this admitted
    # composition, not a manually maintained method dependency list.
    for target in targets:
        selected = model.operation(target)
        if selected.potential_dependencies and target not in supplied:
            supplied[target] = DemandOperationSelection(
                operation=target, selected_dependencies=selected.potential_dependencies
            )
    producer = "source.pdf_views/discovery" if captured else "source.selected_views/discovery"
    selection = DemandOperationSelection(
        operation=producer,
        parameters={"sections": sections, "membership": request.membership}
        if captured
        else {"complete": True},
    )
    if producer in supplied and supplied[producer] != selection:
        raise SourceRequestError(
            "source discovery parameters differ from the selected source scope"
        )
    supplied[producer] = selection
    graph = model.projection_graph(
        "selected-dependencies",
        selected_dependencies=tuple(
            (name, value.selected_dependencies) for name, value in supplied.items()
        ),
    )
    closure = set(targets) | {producer}
    for target in tuple(closure):
        closure.update(graph.closure((target,)))
    output = next(
        role
        for role in model.operation(producer).roles
        if role.direction == "output" and role.name == "result"
    )
    member_kinds = set(derive_member_kinds(model, output.kind))
    discoveries = []
    for operation_id in sorted(closure):
        operation = model.operation(operation_id)
        if operation.subject != "original-source-view":
            continue
        roles = [
            role
            for role in operation.roles
            if role.direction == "input"
            and role.support is not None
            and "computation" in role.support.origins
            and set(input_kind_refinements(model, (role.kind,))[role.kind]).intersection(
                member_kinds
            )
        ]
        if len(roles) > 1:
            raise SourceRequestError(
                "source target has ambiguous discovered-source roles: " + operation_id
            )
        discoveries.append(
            DemandDiscoverySelection(
                producer=producer,
                output_role="result",
                target=operation_id,
                population="selected-source-views",
                target_role=roles[0].name if roles else None,
            )
        )
    root_targets = tuple(
        target for target in targets if model.operation(target).subject != "original-source-view"
    )
    native = NativeDemandRequest(
        project_id=request.project_id,
        release_id=request.release_id,
        runtime_id=request.runtime_id,
        roots=tuple(
            DemandRoot(
                subject=value.root.subject,
                original_source=value.root.original_source,
                analyzed_scope={
                    "document": value.reference.document_key,
                    "scope": "whole-document",
                },
            )
            for value in originals
        ),
        targets=tuple(dict.fromkeys((*root_targets, producer))),
        selections=tuple(supplied.values()),
        discovery=tuple(discoveries),
        original_sources={
            value.name: DemandOriginalSelection(
                reference=value.selection().record()["reference"],
                selectors=tuple(value.selection().record()["selectors"]),
            )
            for value in (*originals, *acquired_views)
        },
        inference=request.inference,
        execution_profile=request.execution_profile,
    )
    return native


def run_source_operation(
    engine,
    request: SourceRunRequest,
    method_settings,
    *,
    source_root: Path,
    admission_engine=None,
    domains: Path | None = None,
    on_registered=None,
):
    from corpus_structure.semantic.releases import load_release

    with engine.begin() as connection:
        prepared = load_release(connection, request.release_id)
        native_request = prepare_source_demand(
            connection, request, domains=domains, prepared=prepared
        )
        snapshot = create_native_demand(connection, native_request, prepared=prepared)
    if on_registered is not None:
        on_registered(snapshot)
    return execute_data_demand(
        engine,
        snapshot["demand_id"],
        source_root=source_root,
        project_id=request.project_id,
        policy=method_settings.execution_policy,
        admission_engine=admission_engine,
        nemotron_endpoint=method_settings.nemotron_endpoint,
    )
