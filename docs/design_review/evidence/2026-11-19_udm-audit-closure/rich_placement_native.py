"""One-off native D1 placement probe over preserved Weibull reference authorship."""

import importlib.util
import json
import os
from contextlib import ExitStack
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import SimpleNamespace

from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    KernelRecipe,
    admit_kernel,
    prepare_kernel,
    split_captured_operations,
)

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_identity import (
    body_identity,
    contextual_product_identity,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_service import (
    DemandOriginalSelection,
    DemandRoot,
    NativeDemandRequest,
    execute_data_demand,
    freeze_native_demand,
)
from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SourceSetEntry,
    source_sets_record,
)
from corpus_structure.semantic.data_operation_support import authored_fact_selection
from corpus_structure.semantic.data_product_reference import DataProductReference
from corpus_structure.semantic.regeneration import acquire_packs
from corpus_structure.semantic.rich_policy_binding import rich_policy_value
from corpus_structure.serve.interpretation_authoring import author_interpretations

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent

pytest_plugins = ("python.corpus-structure.tests.conftest",)


def _initialize_observed(directory, *args):
    from corpus_structure.semantic.cpu_execution import _initialize
    from corpus_structure.semantic.rich_relations import RichRelationKernel

    _initialize(*args)
    original = RichRelationKernel.__init__

    def observe(counts):
        with (Path(directory) / f"rich-views-{os.getpid()}.jsonl").open("a") as output:
            output.write(json.dumps(dict(pid=os.getpid(), **counts)) + "\n")

    def initialize(self, **kwargs):
        original(self, **kwargs, observe_inputs=observe)

    RichRelationKernel.__init__ = initialize


def _probe():
    spec = importlib.util.spec_from_file_location(
        "rich_placement_probe", EVIDENCE / "rich_placement.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preserved_weibull_authorship_runs_native_consolidation(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    from corpus_structure.semantic import cpu_execution
    from corpus_structure.semantic.data_operation_model import ExternalExecutorContract
    from corpus_structure.semantic.declared_math_products import math_operation_declarations
    from corpus_structure.semantic.demand_results import read_demand_result
    from corpus_structure.semantic.external_extraction import (
        external_extraction_operation_sources,
        rich_external_declarations,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources

    probe = _probe()
    bundle, dependencies, profile = acquire_packs((ROOT / "domains/statistics",))
    captured = CapturedKernelInputs(bundle, dependencies, profile)
    base, declarations, sources = split_captured_operations(captured)
    dependencies = data_operation_dependencies(
        base,
        (
            *declarations,
            math_operation_declarations(),
            rich_external_declarations(
                ExternalExecutorContract(
                    "external-executor-v1",
                    "Preserved independent E1-E3 reference annotations.",
                    "preserved-reference-author",
                    None,
                    "declared-inputs-only",
                )
            ),
        ),
        combine_primary_sources(sources, external_extraction_operation_sources()),
    )
    recipe = KernelRecipe(
        "bounded-weibull-rich-authorship",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(bundle, dependencies, profile),
    )
    monkeypatch.setattr(cpu_execution, "_initialize", partial(_initialize_observed, str(tmp_path)))
    from semantic.test_target_installation_native import install_target_root

    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.target_installation import capture_target_installation
    from native_test_support import principal_engine

    preparation = prepare_kernel(recipe, directory=tmp_path / "kernel")
    context, authored, cohort, omitted = probe.authored_propositions(
        preparation.prepared, preparation.model
    )
    kinds = {item.owner: item.key for item in preparation.model.identities if item.domain == "kind"}
    namespace = probe.NS + "rich-knowledge/"
    body = authored.model_dump(mode="python")
    selected_kind = kinds[namespace + "DdoRichAuthoredPropositions"]
    selector = contextual_product_identity(
        kind=selected_kind, context=context, body=body_identity(body).key
    ).key
    policy = rich_policy_value(preparation.prepared, preparation.model).model_dump(mode="python")
    selections = (
        authored_fact_selection(
            "preserved-weibull-reference",
            body,
            kind_contract=selected_kind,
            context=context,
            author="Preserved independently authored E1-E3 reference propositions",
            selection_id="weibull-reference-authorship",
        ),
        authored_fact_selection(
            "current-rich-policy",
            policy,
            kind_contract=kinds[namespace + "DdoRichConsolidationPolicy"],
            context=context,
            author="Current statistics domain policy",
            selection_id="current-rich-policy",
        ),
    )
    sets = (
        FrozenSourceSet.unqualified(
            "rich-authored-propositions",
            (SourceSetEntry.from_semantic_source(DataProductReference(selector), context=context),),
        ),
        *tuple(
            FrozenSourceSet.from_selected(name, ())
            for name in (
                "rich-proposals",
                "rich-proposal-contexts",
                "rich-known-universe",
                "rich-records",
                "rich-readings",
            )
        ),
    )
    pending = NativeDemandRequest(
        project_id=probe.PROJECT,
        release_id=preparation.prepared.release_id,
        runtime_id=preparation.runtime.runtime_id,
        roots=(DemandRoot(subject=context.subject, original_source=None, analyzed_scope={}),),
        targets=("rich.consolidate",),
        original_sources={
            selection.name: DemandOriginalSelection.model_validate(selection.record())
            for selection in selections
        },
        source_sets=source_sets_record(sets),
        inference="bounded-weibull-reference-authorship",
        execution_profile="source-native",
    )
    freeze_native_demand(preparation.prepared, pending)
    epoch = capture_target_installation(get_metadata())
    *_, location = install_target_root(semantic_bare_engine, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    with semantic_bare_engine.begin() as connection:
        kernel = admit_kernel(
            connection, recipe, engine=semantic_bare_engine, preparation=preparation
        )
    with ExitStack() as stack:
        engines = {}
        for purpose in ("write", "admit", "read"):
            engine = principal_engine(native_settings, purpose, semantic_bare_engine.url.database)
            stack.callback(engine.dispose)
            engines[purpose] = engine
        kernel = replace(kernel, clone=SimpleNamespace(purpose=engines.__getitem__))
        from corpus_structure.semantic.data_operation_storage import DataOperationStorage
        from corpus_structure.semantic.identifiers import ProjectId, ReleaseId

        with kernel.purpose("write").begin() as connection:
            DataOperationStorage(connection).initialize_source_project(
                {
                    "project_id": ProjectId(probe.PROJECT),
                    "release_id": ReleaseId(kernel.prepared.release_id),
                }
            )
        retained = author_interpretations(kernel.purpose("write"), kernel.prepared, request=pending)
        assert retained["standing"] == "authored" and len(retained["authored_admissions"]) == 2
        result = execute_data_demand(
            kernel.purpose("write"),
            retained["demand_id"],
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=kernel.purpose("admit"),
            project_id=probe.PROJECT,
            database_capacity=6,
        )
        assert result.receipt_count == 1
        products = []
        continuation = None
        with kernel.purpose("read").begin() as connection:
            while True:
                page = read_demand_result(
                    connection,
                    retained["demand_id"],
                    project_id=probe.PROJECT,
                    continuation=continuation,
                    view="products",
                )
                products.extend(page.members())
                continuation = page.record.get("continuation")
                if continuation is None:
                    break
        headers = [
            row
            for row in products
            if row["kind_contract"] == kinds[namespace + "DdoRichConsolidation"]
        ]
        assert len(headers) == 1
        consolidation = headers[0]["body"]
        selected = consolidation["eligibility"]["selected_fact_ids"]
        assert len(selected) == 26
        for packet in consolidation["members"]:
            member = packet["body"]
            if member["member_type"] == "source-occurrence":
                assert member["original"]["support_references"][0]["kind"] == "authored"
        observations = [
            json.loads(line)
            for path in tmp_path.glob("rich-views-*.jsonl")
            for line in path.read_text().splitlines()
        ]
        assert observations and all(item["pid"] != os.getpid() for item in observations)
        assert all(item["claims"] < 100 and item["entities"] < 100 for item in observations)
        report = dict(
            standing="native-authored-bounded-project-observation",
            project=probe.PROJECT,
            demand_id=retained["demand_id"],
            release_id=kernel.prepared.release_id,
            runtime_id=kernel.runtime,
            receipt_count=result.receipt_count,
            authored_admission_count=len(retained["authored_admissions"]),
            targets=["rich.consolidate"],
            input_member_count=len(authored.members),
            selected_fact_count=len(selected),
            observations=observations,
            omitted_documentary_members=omitted,
            input_hashes={item["unit"]: item["source_hashes"] for item in cohort},
            limitation="Explicit independent reference authorship. Source extraction and full-book project sizing remain unobserved.",
        )
        destination = Path(
            os.environ.get(
                "CORPUS_RICH_PLACEMENT_EVIDENCE", str(tmp_path / "native-rich-placement.json")
            )
        )
        destination.write_bytes(json_bytes(report))
        print("Native rich placement report " + str(destination))
