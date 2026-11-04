# Boundaries and composition

**Implemented source inspected, 2026-11-03.** [Baseline](README.md#baseline).
Paths omit `python/corpus-structure/src/corpus_structure/`.

<a id="da-018"></a>

## DA-018 — Historical extension-version correction retained

The earlier phase0 extension-pin correction retains its October29 evidence date. No fresh
provider/version campaign was run. This refresh supplies no reason to reinstate that diagnosis.

<a id="da-019"></a>

## DA-019 — Historical test-sweep lease correction not refreshed

The former phase0 test-lease finding remains historical. The independent test account owns its
current coverage; this production audit does not renew that baseline.

<a id="da-020"></a>

## DA-020 — Analytics-setting propagation diagnosis corrected

consolidate_cut receives actual AnalyticsSettings and forwards thread/memory/scratch to AnalysisScope
(`semantic/domain_operations.py:2058–2088`). Finalization forwards settings
(`orchestrate/commands.py:387`), and both CLI routes pass settings.analytics
(`cli/regenerate.py:262`; cli/orchestrate.py:287). This is source correction, not performance qualification.

<a id="da-045"></a>

## DA-045 — Exposed method-reader connection premise corrected

**Source-inspected 2026-11-04, M1-20261104-r4.** The method-facing `Reader` now exposes owned
operations rather than a raw connection (`core/method.py`). `ScopedSourceReader` borrows a read
snapshot for each operation; `BoundReader` supplies the database adapter. Registration retains
its transaction ownership without handing that capability through the method protocol. The
previous exposed-connection diagnosis no longer describes this supported interface. This is
an ownership correction, not Python sandboxing or a claim about arbitrary reflective code.

<a id="da-047"></a>

## DA-047 — Advertised operational surfaces overstate their current behavior

**FP-06, DP-15/22/24; implemented, narrowed.** Orphan status is always empty
(`orchestrate/commands.py:399,441`); CLI advertises by_unit (`cli/orchestrate.py:141`) while
semantic execution refuses it (`orchestrate/semantic.py:91–95`). These surfaces can imply
functionality they do not establish. Omitted proposal schema hash being replaced by the server
value (`intervene/semantic_server.py:575`) is an interface-policy fact, not automatically a defect.
PreparedRelease.queries remains descriptor state, not proof of a missing execution consumer.
The old empty-fusion claim is removed: fusion consumes admitted-cut candidates
(`domain_operations.py:2080–2091`). Native SQL/generators now have authoring consumers;
no blanket dead-code diagnosis remains.

<a id="da-052"></a>

## DA-052 — Knowledge-claim agent production is bound to a literal method identity

**FP-02/03/04, DP-06/08/16; implemented.** Scheduling builds agent.opus explicitly
(`orchestrate/semantic.py:885–899`), routing requires that name (`:1024–1031`), and snapshots select
only its configurations (`:151–173`). MCP and automation do the same
(`intervene/semantic_server.py:142–159`; automated.py:88–97,307–314`). Another agent identity needs
coordinated policy, queue and provider edits rather than one producer binding.
M1 source-record candidates now pass through source completion records
(`semantic/observations.py:260–272`), which corrects the old claim that other producers cannot
contribute anything. That route does not establish a general knowledge-claim proposal contract.
Actual attribution limits have one home at [DA-051](served-claims.md#da-051).
