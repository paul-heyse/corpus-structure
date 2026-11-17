"""Current contextual native consumer setup with a controlled local model.

The model is a real small untrained BERT/mean-pooling implementation. It exercises
captured assets, tokenizer and owned CPU execution; it is not provider evidence.
"""

from hashlib import sha256

from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations


def controlled_encoder(directory):
    import torch
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.sentence_transformer.modules import Pooling, Transformer
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from tokenizers.processors import TemplateProcessing
    from transformers import BertConfig, BertModel, PreTrainedTokenizerFast

    from corpus_structure.methods.contextual_embeddings import EncoderProfile
    from corpus_structure.semantic.contextual_encoder import ContextualEncoderSelection
    from corpus_structure.semantic.identity import canonical_bytes

    base = directory / "base"
    base.mkdir(parents=True)
    words = (
        "[PAD]",
        "[UNK]",
        "[CLS]",
        "[SEP]",
        "[MASK]",
        "Ada",
        "acts",
        "alpha",
        "Meaning",
        "Mention",
        "Context",
        "Type",
        "unknown",
        "query",
        "passage",
        ":",
        ".",
    )
    vocabulary = dict(zip(words, range(len(words)), strict=True))
    tokenizer = Tokenizer(WordLevel(vocabulary, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 2), ("[SEP]", 3)]
    )
    tokenizer_fast = PreTrainedTokenizerFast(
        tokenizer_object=tokenizer,
        unk_token="[UNK]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        sep_token="[SEP]",
        mask_token="[MASK]",
        model_max_length=128,
    )
    tokenizer_fast.save_pretrained(base)
    config = BertConfig(
        vocab_size=len(words),
        hidden_size=8,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=16,
        hidden_dropout_prob=0.0,
        attention_probs_dropout_prob=0.0,
        max_position_embeddings=128,
        pad_token_id=0,
    )
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(73)
        BertModel(config).save_pretrained(base)
    model = SentenceTransformer(
        modules=[
            Transformer(str(base), model_kwargs={"local_files_only": True}),
            Pooling(8, pooling_mode="mean"),
        ],
        device="cpu",
    )
    root = directory / "model"
    model.save(str(root), create_model_card=False)
    files = tuple(
        (path.relative_to(root).as_posix(), sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )
    # This is the actual local asset revision, not a provider/repository assertion.
    revision = sha256(canonical_bytes(files)).hexdigest()[:40]
    profile = EncoderProfile(
        "controlled-local-bert",
        revision,
        8,
        "query: ",
        "passage: ",
        "mean",
        max_tokens=128,
        batch_size=2,
        max_items=32,
        timeout_seconds=120,
    )
    return ContextualEncoderSelection.acquire(profile, root)


def contextual_recipe(directory, selection):
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
        read_data_operation_inputs,
    )
    from corpus_structure.semantic.contextual_encoder import (
        contextual_encoder_declarations,
        contextual_encoder_operation_sources,
    )
    from corpus_structure.semantic.contextual_operations import (
        contextual_inputs,
        contextual_operation_declarations,
    )
    from corpus_structure.semantic.declared_structural_calls import structural_inputs
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.types import ResolvedDependencies
    from semantic.current_pdf_source_support import current_pdf_recipe
    from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe
    from semantic.structural_native_fixture import operation_sources

    base = current_pdf_recipe(directory)
    captured = base.captured_inputs
    assert captured is not None
    acquired = read_data_operation_inputs(captured.dependencies)
    assert acquired is not None and acquired[1] is not None
    declarations, sources = acquired
    assert sources is not None
    sources = combine_primary_sources(
        sources, operation_sources(), contextual_encoder_operation_sources(selection)
    )
    dependencies = data_operation_dependencies(
        ResolvedDependencies(
            tuple(
                item
                for item in captured.dependencies.artifacts
                if not item.name.startswith("data-operations/")
            ),
            captured.dependencies.vocabularies,
            captured.dependencies.ontology_sources,
        ),
        (
            *declarations,
            contextual_encoder_declarations(),
            contextual_operation_declarations(),
            structural_operation_declarations(),
        ),
        sources,
    )
    return KernelRecipe(
        "current-contextual-controlled-model",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            contextual_inputs(structural_inputs(captured.bundle)), dependencies, captured.profile
        ),
    )


def contextual_workflow_recipe(directory, selection):
    """Compose the actual definition consumer and the separate finite source matcher."""
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
        read_data_operation_inputs,
    )
    from corpus_structure.semantic.contextual_encoder import (
        contextual_encoder_declarations,
        contextual_encoder_operation_sources,
    )
    from corpus_structure.semantic.contextual_operations import contextual_operation_declarations
    from corpus_structure.semantic.definition_applicability_products import (
        applicability_inputs,
        applicability_operation_sources,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.types import ResolvedDependencies
    from semantic.contextual_native_fixture import operation_sources
    from semantic.current_pdf_source_support import current_pdf_recipe
    from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe

    base = current_pdf_recipe(directory)
    captured = base.captured_inputs
    assert captured is not None
    acquired = read_data_operation_inputs(captured.dependencies)
    assert acquired is not None and acquired[1] is not None
    declarations, sources = acquired
    assert sources is not None
    dependencies = data_operation_dependencies(
        ResolvedDependencies(
            tuple(
                row
                for row in captured.dependencies.artifacts
                if not row.name.startswith("data-operations/")
            ),
            captured.dependencies.vocabularies,
            captured.dependencies.ontology_sources,
        ),
        (
            *declarations,
            contextual_encoder_declarations(),
            contextual_operation_declarations(),
            structural_operation_declarations(),
        ),
        combine_primary_sources(
            sources,
            contextual_encoder_operation_sources(selection),
            operation_sources(),
            applicability_operation_sources(),
        ),
    )
    return KernelRecipe(
        "current-contextual-definition-workflow",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            applicability_inputs(captured.bundle), dependencies, captured.profile
        ),
    )


def run_intent(kernel, intent):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner
    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.current_pdf_source_support import PROJECT, ROOT

    with kernel.purpose("write").begin() as connection:
        demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            intent, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
    result = execute_data_demand(
        kernel.purpose("write"),
        demand,
        source_root=ROOT,
        project_id=PROJECT,
        admission_engine=kernel.purpose("admit"),
        database_capacity=6,
    )
    return demand, result


def query_intent(kernel, source, occurrence, *, replicate, context_selection=None, primary=()):
    """Acquire exactly the requested retained carrier, never all same-context contributions."""
    from corpus_structure.semantic.contextual_selection import (
        ContextualSelectedProduct,
        acquire_contextual_query_selection,
        freeze_contextual_query_demand,
    )
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from semantic.current_pdf_source_support import PROJECT

    def chosen(value):
        pin = value.read
        return ContextualSelectedProduct(
            pin.demand_id,
            value.row["product_id"],
            read_id=pin.read_id,
            expected_cut=pin.cut_id,
            member_id=value.row["member_id"],
        )

    with kernel.purpose("read").begin() as connection:
        selection = acquire_contextual_query_selection(
            connection, project_id=PROJECT, source=chosen(source), occurrence=chosen(occurrence)
        )
    return freeze_contextual_query_demand(
        kernel.model,
        selection,
        replicate=replicate,
        inference="exact-retained-source-occurrence",
        execution_profile=kernel.recipe.execution_profile,
        context_selection=context_selection,
        source_sets=(
            FrozenSourceSet.from_selected(
                "query-context-primary", tuple(value.entry() for value in primary)
            ),
        )
        if context_selection is not None
        else (),
    )


def registry_targets(names):
    from corpus_structure.semantic.contextual_registry import RegistryTarget

    # Equal real text makes all three channels tied; IDs preserve distinct targets.
    return tuple(
        RegistryTarget(
            target_id=name, label="Ada", description="Ada acts", type_name="concept", scope="global"
        )
        for name in names
    )


def target_intent(kernel, names, *, replicate, discovery_only=False, targets=None):
    from corpus_structure.semantic.contextual_selection import freeze_contextual_target_demand
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_support import authored_fact_selection
    from corpus_structure.semantic.observations import source_value
    from semantic.current_pdf_source_support import PROJECT

    context = SubjectContext(
        PROJECT, "curated-registry", None, b"{}", subject_definition="contextual-registry"
    )
    kind = kernel.identities[
        "https://corpus-structure.dev/semantic/data-operation-contextual/DdoCuratedContextualTargets",
        "kind",
    ]
    authored = authored_fact_selection(
        "curated-targets",
        dict(
            targets=source_value(
                [
                    value.model_dump(mode="python")
                    for value in (registry_targets(names) if targets is None else targets)
                ]
            )
        ),
        kind_contract=kind,
        context=context,
        author="controlled test curator",
        selection_id="explicit-contextual-target-descriptions",
    )
    values = dict(
        roots=(RootSubject(context.subject, None, b"{}"),),
        original_sources=(authored,),
        inference="explicit-curated-target-observations",
        execution_profile=kernel.recipe.execution_profile,
    )
    if discovery_only:
        return freeze_demand(
            kernel.model, targets=("retrieve.contextual_targets/curated",), **values
        )
    return freeze_contextual_target_demand(
        kernel.model, producer="retrieve.contextual_targets/curated", replicate=replicate, **values
    )


def retained_products(kernel, demand, kind):
    from semantic.structural_admission_native_support import selected

    return selected(
        kernel,
        demand,
        kind="https://corpus-structure.dev/semantic/data-operation-contextual/" + kind,
    )


def inventory_intent(kernel, query, names, *, targets=None, effective_version=None):
    from dataclasses import asdict

    from corpus_structure.semantic.contextual_registry import registry_input
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from corpus_structure.semantic.data_operation_support import authored_fact_selection
    from corpus_structure.semantic.observations import source_value

    registry, representations = registry_input(
        registry_targets(names) if targets is None else targets
    )
    selected = authored_fact_selection(
        "contextual-inventory",
        dict(
            source_selection=registry,
            scope="global",
            targets=source_value([asdict(value) for value in representations]),
            semantic_targets=source_value({}),
            **({"effective_version": effective_version} if effective_version is not None else {}),
        ),
        kind_contract=kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetSelection",
            "kind",
        ],
        context=query.context,
        author="controlled test curator",
        selection_id="exact-complete-target-inventory",
    )
    return freeze_demand(
        kernel.model,
        roots=(
            RootSubject(
                query.context.subject, query.context.original_source, query.context.analyzed_scope
            ),
        ),
        targets=("retrieve.contextual_inventory/declared",),
        original_sources=(selected,),
        inference="explicit-inventory-membership",
        execution_profile=kernel.recipe.execution_profile,
    )


def final_selection(
    kernel, query_demand, query, query_vector, target_demand, targets, inventory_demand, inventory
):
    from corpus_structure.semantic.contextual_selection import (
        ContextualSelectedProduct,
        acquire_contextual_vector_selection,
    )
    from semantic.current_pdf_source_support import PROJECT

    def selected(demand, value):
        return ContextualSelectedProduct(demand, value.row["product_id"])

    with kernel.purpose("read").begin() as connection:
        return acquire_contextual_vector_selection(
            connection,
            project_id=PROJECT,
            inventory=selected(inventory_demand, inventory),
            query=selected(query_demand, query),
            query_vector=selected(query_demand, query_vector),
            targets=tuple(selected(target_demand, value) for value in targets),
        )


def retrieval_intent(kernel, selection, *, budget):
    from corpus_structure.semantic.contextual_selection import freeze_contextual_retrieval_demand
    from corpus_structure.semantic.data_operation_support import authored_fact_selection
    from corpus_structure.semantic.observations import source_value

    body = dict(
        budget=budget,
        channel_budget=32,
        constraints=source_value(
            [
                dict(
                    constraint_id="meaning",
                    relation_kinds=["denotes"],
                    occurrence_role="mention",
                    target_role="concept",
                    multiplicity="one",
                )
            ]
        ),
        exclusions=source_value([]),
    )
    policy = authored_fact_selection(
        "contextual-policy",
        body,
        kind_contract=kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalPolicy",
            "kind",
        ],
        context=selection.query_context,
        author="controlled test operator",
        selection_id="explicit-candidate-capacity",
    )
    return freeze_contextual_retrieval_demand(
        kernel.model,
        selection,
        inference="exact-bounded-contextual-candidates",
        execution_profile=kernel.recipe.execution_profile,
        original_sources=(policy,),
    )


def witnessed_retrieval_intent(
    kernel,
    selection,
    query_demand,
    query,
    *,
    hypotheses,
    budget,
    relations=("denotes",),
    cues=None,
    constraints=None,
):
    """Actual admitted author assertions and exact selected source cues, never inference claims."""
    from corpus_structure.semantic.contextual_selection import (
        ContextualSelectedProduct,
        acquire_contextual_witness_selection,
        freeze_contextual_witnessed_retrieval_demand,
    )
    from corpus_structure.semantic.data_operation_support import authored_fact_selection
    from corpus_structure.semantic.observations import source_value
    from semantic.current_pdf_source_support import PROJECT

    carrier = query.body["carrier"]
    with kernel.purpose("read").begin() as connection:
        selected = acquire_contextual_witness_selection(
            connection,
            selection,
            project_id=PROJECT,
            query=ContextualSelectedProduct(query_demand, query.row["product_id"]),
            cues=(carrier,) if cues is None else cues,
        )
    author = "controlled contextual test author"
    assertions = authored_fact_selection(
        "contextual-authored-hypotheses",
        dict(author_assertion=author, hypotheses=hypotheses),
        kind_contract=kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualWitnessHypotheses",
            "kind",
        ],
        context=selection.query_context,
        author=author,
        selection_id="explicit-private-source-relationship-hypotheses",
    )
    policy = authored_fact_selection(
        "contextual-policy",
        dict(
            budget=budget,
            channel_budget=32,
            constraints=source_value(
                [
                    dict(
                        constraint_id="source-relationship",
                        relation_kinds=list(relations),
                        occurrence_role="mention",
                        target_role="concept",
                        multiplicity="one",
                    )
                ]
                if constraints is None
                else constraints
            ),
            exclusions=source_value([]),
        ),
        kind_contract=kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalPolicy",
            "kind",
        ],
        context=selection.query_context,
        author=author,
        selection_id="explicit-source-relationship-constraints",
    )
    return freeze_contextual_witnessed_retrieval_demand(
        kernel.model,
        selected,
        inference="explicit-private-authored-source-cue-binding",
        execution_profile=kernel.recipe.execution_profile,
        original_sources=(assertions, policy),
    )
