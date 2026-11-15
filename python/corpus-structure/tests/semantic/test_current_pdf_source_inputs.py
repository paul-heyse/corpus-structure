"""Current source journey preparation; native custody remains a separate obligation."""

from semantic.current_pdf_source_support import current_pdf_recipe
from semantic.data_operation_kernel_support import prepare_kernel


def test_current_pdf_fixture_prepares_real_native_owners_without_legacy_seed(tmp_path):
    recipe = current_pdf_recipe(tmp_path)
    assert recipe.project_id is None and recipe.source_stage is None
    prepared = prepare_kernel(recipe)
    operations = {operation.semantic_id for operation in prepared.model.operations}
    assert {"data.initialize_source_project", "source.pdf/capture", "source.pdf_views/discovery"} <= operations
    incomplete = [(item.root, item.unknowns) for item in prepared.model.implementation_slices if not item.complete]
    assert not incomplete
