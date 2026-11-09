# PM2 foundation evidence

The [PM2 coordinator](../../../plans/production-milestone-two_2026-11-08.md#foundation-execution)
owns execution disposition. The [combined review](../../reviews/design_review_pm2-foundation_2026-11-08.md)
records the design gate.

## Frozen development baseline

**Tested · 2026-11-08.** The exact acquired target was `corpus_structure_dev`,
OID `25921445`, PostgreSQL system identifier `7701811359771751232`,
Unix socket `/var/run/postgresql:5434`. Maintenance revision
`semantic_dma_audit_current` and archived release
`release:675b5f723ce83aadf7b8b1df7f0784fdc2c455d02b3979f1eae2cec30c352a56`
were read through their installed entry points. The explicit archive check
passed. A request without the archive ID refused because there is no active release.
The project is `nce-grinstead-snell-full-book`.

- Run 404 at source-only cut 514 selects 29 source views. The 518-page parent SHA-256 is
  `763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474460551a5e`.
  The immutable native pin is task 1627, product `integrated`, digest
  `35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`.
- View 383 selects descendants of `#/groups/370`. The view key is
  `source-view:9e6ff4af519fe5d6abf8199254ce01920c2327e479c64c189e6dc9f29771df2a`,
  projection digest `87f5af8a57fea55961e93d25d46ac4283ed24069772bcf41d0919f37a5a1eaa2`,
  recipe digest `9a42d779de26546a6b702b2b7867c85d6785139dbff246e2914ea726f63c4cbc`.
- The source-only sentence spans `[811,907)` and the coherent two-sentence
  scope spans `[811,1018)` in `#/texts/21770`, field `text`. Their exact
  UTF-8 SHA-256 digests are
  `3392e08b410caa7dd21a6d8f12a834fd269a31175219dbb30c4f9a0476a1bb9f` and
  `17bfa7bc5ddd08542b813c95e9afc865cd7698904222c9635702e809f3865f99`.
  The independent A/B/C expectation applies to the sentence only.
  [Source frame](../2026-11-08_dma-audit-repair/raw/reference_frame.json) ·
  [Independent reference record](../2026-11-08_dma-audit-repair/records/dma.audit-development-reference.json)
- Private run 407 at completed cut 517 is the M1 execution comparator under
  the same release, with realization `result:dma-audit-current:grinstead-snell`.
  It settled 29 annotation and 29 candidate tasks. The full-view grading attempt
  against sentence-only set 32, unit 45, refused outside the explicit evaluation
  cut. There is no evaluation result for that pairing.
  [Comparator and grading receipt](../2026-11-08_dma-audit-repair/README.md#private-full-book-replacement) ·
  [Recorded refusal](../2026-11-08_dma-audit-repair/raw/full_book_grade.json)

The two read controls used `ci source inspect 404 --native-view formula` with the
same native pin and an 8 MiB work bound. Both returned one `source_ready` row with
`readable_source_field=orig`.

| Page | Native section and item | Exact characters | Selected SHA-256 |
| --- | --- | ---: | --- |
| 416 | `#/groups/617`, `#/texts/2341` | 515 | `1508f789b24611a648bac9a83d37c3653bedda12ce78311c8c0fb67351e83b16` |
| 418 | `#/groups/618`, `#/texts/2355` | 101 | `ecbafbade8d7d5fd24d4397a927f61799c215dea05735a723a7692ffef3d1d70` |

The existing DMA receipts cover matching Reader, search and proposal packet on cut
514, the 1 MiB refusal, and detached exact-closure replay on view 382 at cut 517.
Those receipts retain their original scope.
[Current development checks](../../../plans/domain-model-alignment_2026-11-08.md#development-adoption-on-2026-11-08) ·
[Detached source replay](../2026-11-08_dma-audit-repair/records/dma.audit-detached-book-source.json)

```sh
uv run ci db status --maintenance --json
uv run ci status 404 --project nce-grinstead-snell-full-book --json
uv run ci status 407 --project nce-grinstead-snell-full-book --json
uv run ci source views 404 --json
uv run ci release check --project nce-grinstead-snell-full-book --release release:675b5f723ce83aadf7b8b1df7f0784fdc2c455d02b3979f1eae2cec30c352a56 --json
uv run ci source inspect 404 --producing-task 1627 --product integrated --native-digest 35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb --pointer '#/texts/2341' --section '#/groups/617' --native-view formula --max-bytes 8388608 --json
uv run ci source inspect 404 --producing-task 1627 --product integrated --native-digest 35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb --pointer '#/texts/2355' --section '#/groups/618' --native-view formula --max-bytes 8388608 --json
```

## Locked native profiles

**Tested · 2026-11-08.** All four exact checkpoints loaded offline and
ran on the RTX 5090 through the same resident supervisor and configured
Nemotron handoff. The host reported CUDA 13.2 with Torch `2.15.0+cu132`.
Torch could run native inference despite the NVML user/kernel version
mismatch. Locked CPU runs also exercised distinct
reference routes for all four providers. The native output remains attributed and private.

| Provider | Runtime and observed work | Native evidence |
| --- | --- | --- |
| HanLP 2.1.7 | CPython 3.14.10, FP32 SDPA. All five selected heads ran and the two scopes yielded one and two grounded dependency roots. The archive's preprocessing adds a space to the synthetic EOS. The adapter restores that sentinel for constituency without changing canonical words. Checkpoint loading accounted for every parameter and buffer. CPU accepted 512 subwords and 128 words, refused 513 subwords and 129 words, and refused a mixed batch of 2,050 padded subwords at the 2,048 limit. | [CUDA scopes](raw/hanlp-cuda.jsonl) · [CPU bounds](raw/hanlp-cpu-bounds.jsonl) |
| Maverick MES 1.0.7 | CPython 3.12.3, FP32 eager. The two frozen textbook scopes were empty. The alternate-vocabulary case returned four located mentions and two clusters. It accepted 512 subtokens and refused 513. The CPU supplied-mention arm accepted 128 and refused 129. All 434 saved tensors matched the FP32 model byte-for-byte, including the resized embeddings. The Transformers regex warning came from an offline config heuristic while DeBERTa kept its native Unigram tokenizer and Metaspace preprocessing. | [CUDA runs](raw/maverick-cuda.jsonl) · [CPU custody and bounds](raw/maverick-cpu-custody.log) |
| Dipo DMRST 0.2.1 | CPython 3.12.3, FP32 SDPA, stride 100. Native segmentation and ordered tree output supplied two and four grounded EDUs on the selected scopes. CPU accepted 2,048 tokens and 128 EDUs and refused 2,049 and 129 respectively. | [CUDA scopes](raw/dipo-cuda.jsonl) · [CPU bounds](raw/dipo-cpu-bounds.jsonl) |
| d1-2B | CPython 3.14.10, CUDA BF16, native set attention with the `d1` implementation. Both scopes recovered the term and its value phrase from the allowed `/source` field. The worker executed 4,096 packed tokens and refused 4,097. A cancelled native request reaped the child and the configured Nemotron service returned awake. | [CUDA scopes, boundary and cancellation](raw/d1-cuda.jsonl) · [CPU FP32 smoke](raw/d1-cpu-smoke.jsonl) |

The [artifact manifest](../../../../python/corpus-structure/src/corpus_structure/methods/pm2_artifacts.json)
pins all staged files, including wrapper-resolved backbones, d1 custom code
and calibration, and the HanLP archive and extracted files. The isolated
project locks were synchronized, and `uv lock --check` and `uv pip check`
passed for each. The HanLP 2.1.7 wheel requires `hanlp-common==0.0.24`,
which was unavailable from PyPI. The HanLP lock selects that version from
the exact upstream source revision.

| Profile | Lock SHA-256 |
| --- | --- |
| [HanLP](../../../../services/pm2-hanlp/uv.lock) | `96efee4f263aaaa75cc52688259ad9c0cae75c6f5a454996fc05cc98bbe5f677` |
| [Maverick](../../../../services/pm2-maverick/uv.lock) | `c6075ef25c2a6aec8d7227343f18dbfb4c9ad64df6b502f89371938c2bce6e89` |
| [Dipo](../../../../services/pm2-dipo/uv.lock) | `7b25ec5e2627c48fa14cf00ee91b383ff21c70fc232f2ba6a0c0502c100cb2b6` |
| [d1 workspace](../../../../uv.lock) | `0d26f2c23d30e478537d0d29cde4cbd2e119223c46cb8178cd479a47710ab750` |

```sh
uv run python services/pm2-models/stage.py
uv sync --locked --project services/pm2-hanlp
uv sync --locked --project services/pm2-maverick
uv sync --locked --project services/pm2-dipo
uv run python docs/design_review/evidence/2026-11-08_pm2-foundation/native_probe.py hanlp
uv run python docs/design_review/evidence/2026-11-08_pm2-foundation/native_probe.py dipo
uv run python docs/design_review/evidence/2026-11-08_pm2-foundation/native_probe.py maverick
uv run python docs/design_review/evidence/2026-11-08_pm2-foundation/native_probe.py d1 --cancel-d1
```

The synthetic HanLP word-boundary controls used 127 and 128 copies of
`word` followed by a period. The subword controls used `A`, 84 copies of
`antidisestablishmentarianism`, four or five copies of `word`, and a period.
The padded refusal used actual row lengths `[410,301,103,23,19]`.
The Maverick alternate-vocabulary probe used “Ada checked the chart. She
corrected it.” The frozen textbook outcomes do not establish accuracy beyond
their admitted scope.

The exact Dipo child returned a startup failure for a missing pinned checkpoint.
The GPU capacity control timed out while the competing process still held the slot.
[Startup refusal](raw/native-load-refusal.json) · [Capacity control](raw/capacity-contention.json)

## Private retained completion

**Tested · 2026-11-08.** Native d1 CUDA output and a 17-question operation
refused at the 16-question limit settled under the existing PostgreSQL claim
owner. The private Reader retained one exact physical occurrence and
both operation outcomes. The same run retained a second source scope through
Dipo CPU. An expired attempt was refused, the new owner ran the exact input,
and both providers remained inspectable at the completed cut. A same-release run selected the original source
and reused the producing task when only the downstream policy changed.
Changing the allowed source field scheduled fresh work.
The focused selection also passed all 34 source, worker, Reader, capacity
and shared claim-owner checks.
[Focused test result](raw/focused-checks.json)
[Native Reader and reuse receipt](records/pm2.private-native-reader.json)

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 3 current, 0 superseded.


**pm2-foundation**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Exact development source and private M1 comparator](records/pm2.development-baseline.json) | PM2-00 | passed | PM2-00 | 2026-11-08 |
| [Native d1 and Dipo settlement, private read and reuse](records/pm2.private-native-reader.json) | PM2-01 | passed | PM2-01, PM2-02 | 2026-11-08 |
| [Locked native profiles and bounded local GPU custody](records/pm2.native-profile-controls.json) | PM2-02 | passed | PM2-01, PM2-02 | 2026-11-08 |
<!-- evidence-index:end -->
