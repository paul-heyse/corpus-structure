"""Authored private review runs using the ordinary leased source graph and publication."""

from __future__ import annotations

from hashlib import sha256

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.interpretations import (
    AuthorSourceRecordsMethod,
    MeasurementInterpretationMethod,
    TerminologyInterpretationMethod,
)
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import OperationBinding, seal_cut


def author_interpretations(engine, prepared, *, kind: str, configuration: dict, settings):
    """Create a new review run; never activate/select or mutate the referenced source result."""
    methods = {
        "terminology": TerminologyInterpretationMethod,
        "measurement": MeasurementInterpretationMethod,
        "source_records": AuthorSourceRecordsMethod,
    }
    if kind not in methods:
        raise ValueError("unknown authored interpretation kind")
    method = methods[kind]()
    cfg = method.Config.model_validate(configuration)
    source = cfg.source
    # Each input is explicitly pinned and retained in the method config/run dependency
    # manifest. Native completion independently checks the target field and source focus.
    identity = sha256(
        canonical_bytes([prepared.release_id, kind, cfg.model_dump(mode="json")])
    ).hexdigest()
    realization = "interpretation-input:" + identity
    from corpus_structure.semantic._operation_calls import initialize_source_project
    from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId

    with engine.begin() as conn:
        initialize_source_project(
            conn,
            project_id=ProjectId(source.project_id),
            release_id=ReleaseId(prepared.release_id),
            realization_id=RealizationId(realization),
            projection_context=prepared,
        )
    registry = MethodRegistry(
        (method,),
        MethodsFile(configs={method.name: {"authored": cfg.model_dump(mode="json")}}),
        prepared=prepared,
    )
    report = run_source_methods(
        engine,
        project_id=source.project_id,
        prepared=prepared,
        binding=OperationBinding(prepared.release_id, realization, 0, b"{}"),
        registry=registry,
        graph=Graph(((Stage.PROPOSE, (Step(method.name + "/authored"),)),)),
        method_settings=MethodSettings(
            data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache
        ),
        selected_sources=(source,),
        corpus_record=None,
    )
    # Ordinary consolidation seals the completed result and projects the compact
    # record/review read boundary. Private contribution standing remains unchanged.
    with engine.begin() as conn:
        final_cut = seal_cut(conn, report.run_id, "interpretation-final", final=True)
    result = consolidate_cut(
        engine, final_cut, "interpretation-result:" + identity + ":" + str(report.run_id)
    )
    return dict(
        run_id=report.run_id,
        cut_id=final_cut,
        release_id=prepared.release_id,
        realization_id=result.realization_id,
        source_run_id=source.run_id,
        source_cut_id=source.cut_id,
        kind=kind,
        standing="retained_private",
        selected=False,
    )
