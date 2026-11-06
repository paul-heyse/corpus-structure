"""Own physical occurrence selection does not imply endpoint association closure."""

from dataclasses import replace

from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.contributions import contribution_identity
from semantic.native_record_fixtures import complete_contributions as complete
from semantic.native_record_fixtures import contribution_drafts as drafts
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import private_source as private_source


def test_occurrence_selector_excludes_anchorless_conditional_endpoint_product(private_source):
    case = private_source
    result = drafts(case)
    assert result.contributions is not None
    source, proposal = result.contributions
    proposal = dict(proposal)
    proposal["anchors"] = ()
    proposal.pop("occurrence_id")
    proposal["semantic_type"] = "conditional.role"
    proposal["endpoints"] = (dict(role="condition", contribution_id=source["contribution_id"]),)
    proposal["contribution_id"] = contribution_identity(proposal)
    with case.writer.begin() as conn:
        complete(case, conn, replace(result, contributions=(source, proposal)))
    with case.writer.connect() as conn:
        physical = read_source_contributions(
            conn, prepared=case.prepared, run_id=case.run, occurrence_id=source["occurrence_id"]
        )
        assert [row["contribution_id"] for row in physical.contributions] == [
            source["contribution_id"]
        ]
        conditional = read_source_contributions(
            conn,
            prepared=case.prepared,
            run_id=case.run,
            contribution_id=proposal["contribution_id"],
            include_interpretation=True,
        )
        assert conditional.contributions[0]["occurrence_id"] is None
        assert (
            conditional.interpretations[0]["endpoints"][0]["contribution_id"]
            == source["contribution_id"]
        )
        assert len(physical.operations) == 2  # Includes the independent zero-output operation.
