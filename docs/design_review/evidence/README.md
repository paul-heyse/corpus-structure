# Evidence

Probes, spikes and investigations that informed a decision, kept so they are not recreated and so
a later reader can see what a decision rested on. Evidence, never authority: the architectural
collection and the ADRs decide (binding §4).

**Layout.** One folder per investigation, `YYYY-MM-DD_<topic>/`, with:
- `README.md`: the question, how it was run (commands, versions, machine), the result, and which
  review, ADR or plan item consumes it;
- the probe's sources (small text, tracked normally);
- `raw/` for raw tool output (Git LFS, with PDFs, archives, Arrow and Parquet; `.gitattributes`).

Never commit virtualenvs, `target/` directories, stores or caches (`.gitignore` here); record how
to rebuild them instead. Keep a probe runnable where that is cheap; otherwise keep its source and
its recorded output.

## Index

A folder stays while a current decision, open finding, test or build consumes it; otherwise it is
removed and recovered from Git (ADR-0001, [historical recovery](../../README.md#historical-recovery)).

| Folder | Question | Current consumer |
|---|---|---|
