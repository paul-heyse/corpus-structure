"""Read-only diagnosis of the actual combined export's local-facet refusal."""
import json
from collections import Counter
from corpus_structure.settings import Settings
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import ContributionRequest, _contributions

out = []
with open_runtime_engine(Settings(), 'pce-combined-budget-diagnosis', purpose='read') as engine:
    for run in (31, 43, 45):
        for facets in (False, True):
            try:
                with engine.connect() as conn, conn.begin():
                    conn.exec_driver_sql('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                    page = _contributions(conn, ContributionRequest(
                        run_id=run, source_view_id=46, include_details=True,
                        include_interpretation=True, include_assessment=facets,
                        include_publication=facets, include_support=facets,
                        max_bytes=32_000_000), paginate=False)
                    counts = Counter(row['population'] for row in page.items)
                    sizes = Counter()
                    for row in page.items:
                        sizes[row['population']] += len(canonical_bytes(row['row']))
                    out.append(dict(run_id=run, facets=facets, outcome='passed',
                                    populations=dict(counts), bytes_by_population=dict(sizes)))
            except Exception as error:
                out.append(dict(run_id=run, facets=facets, outcome='failed',
                                error_type=type(error).__name__, error=str(error).split("\n", 1)[0]))
print(json.dumps(out, sort_keys=True))
