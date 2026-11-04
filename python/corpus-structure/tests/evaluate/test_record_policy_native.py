"""Native full-reading label controls; these do not establish fitted model quality."""

from copy import deepcopy

from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.test_private_records import candidate
from semantic.test_private_records import private_source as private_source
from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes


def test_native_whole_reading_labels_keep_meaning_and_source_occurrence(
    private_source, semantic_db_engine
):
    record = candidate(private_source)
    different = deepcopy(record)
    different["fields"][0]["value"]["lexical"] = "13"
    different["fields"][0]["original"] = "13"
    different_occurrence = candidate(private_source, cell=1)
    explanatory = deepcopy(record)
    explanatory["fields"][0]["reason"] = "independently inspected"
    evidence = deepcopy(record)
    evidence["fields"][0]["evidence_sets"] = ["another-set"]
    with semantic_db_engine.connect() as conn:

        def correct(prediction):
            return conn.execute(
                text(
                    "SELECT eval.record_policy_full_correct("
                    ":release,CAST(:candidate AS jsonb),CAST(:refs AS jsonb))"
                ),
                dict(
                    release=private_source.prepared.release_id,
                    candidate=canonical_bytes(prediction).decode(),
                    refs=canonical_bytes([record]).decode(),
                ),
            ).scalar_one()

        assert correct(record) is True
        assert correct(explanatory) is True
        assert correct(different) is False
        assert correct(different_occurrence) is False
        assert correct(evidence) is False
