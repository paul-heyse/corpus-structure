"""Shared controlled inputs and builders for evaluation record references support."""

from copy import deepcopy
from dataclasses import replace
from functools import cache

from evaluation_record_alignment_support import frame, reading

from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.record_contracts import (
    interpretation_identity,
    record_family_contract,
    record_identity,
)


@cache
def bundle():
    from evaluation_record_alignment_support import bundle as current_bundle

    return current_bundle()


@cache
def prepared():
    return prepare_release(bundle())


@cache
def model():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations

    return compile_data_operations(bundle())


def fixture(family="measurement"):
    row, contexts = reading(family)
    row = deepcopy(row)
    row["record_id"] = record_identity(record_family_contract(model(), row["contract"]), row)
    row["interpretation_id"] = interpretation_identity(row)
    return row, contexts, replace(frame(row), release_id=prepared().release_id)
