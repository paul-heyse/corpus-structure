"""P6 (2026-10-28): quote location by token-sequence alignment, on the regex probe's seeded quotes.

    cd docs/design_review/evidence/2026-10-28_design-spikes
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python ../2026-10-28_library-text-math/p6_quote_tokens.py

Same quotes, perturbations and seed as code/regex_probe.py part A (499 quotes, 527 perturbed). Compares
the spike cascade (s0_locate.locate_quote: exact -> spacing -> macros -> rapidfuzz + BESTMATCH refine)
with a token variant of the fuzzy step: quote and cited sentence split into TeX/word tokens
(control word, control symbol, word, other non-space character); each distinct token mapped to one
private-use character so rapidfuzz.fuzz.partial_ratio_alignment aligns token sequences (optimal up to
64 tokens rather than 64 characters); the span runs from the first to the last aligned token.
Whitespace never enters the comparison. Scored against the unperturbed quote's span.
"""
import json, math, random, sys, time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-10-28_design-spikes" / "code"))
import regex  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402
from rapidfuzz.distance import Levenshtein  # noqa: E402
import regex_probe as RP  # noqa: E402
from s0_check import context  # noqa: E402
from s0_locate import locate_quote  # noqa: E402

TOK = regex.compile(r"\\[A-Za-z]+|\\.|\w+|[^\w\s]")


def toks(s, base=0):
    return [(m.group(), base + m.start(), base + m.end()) for m in TOK.finditer(s)]


def token_align(quote, text, lo, hi, cutoff):
    qt, st = toks(quote.rstrip(".,;:") or quote), toks(text[lo:hi], lo)
    vocab = {}
    enc = lambda ts: "".join(chr(0xE000 + vocab.setdefault(t[0], len(vocab))) for t in ts)  # noqa: E731
    qs, ss = enc(qt), enc(st)
    r = fuzz.partial_ratio_alignment(qs, ss, score_cutoff=cutoff)
    if r is None or r.dest_end <= r.dest_start:
        return None
    # trim unmatched tokens at the window edges (partial_ratio returns a window of the quote's length)
    a, b = r.dest_start, r.dest_end
    qset = set(qs)
    while a < b and ss[a] not in qset:
        a += 1
    while b > a and ss[b - 1] not in qset:
        b -= 1
    return st[a][1], st[b - 1][2], round(r.score, 1), len(qt)


def token_refine(quote, text, lo, hi, cutoff, pad=3):
    """Token window from partial_ratio_alignment, widened by pad tokens, then a global Levenshtein
    alignment (opcodes) of the quote's tokens against the window: the span runs from the window token
    aligned to the quote's first token to the one aligned to its last (insertions inside are kept)."""
    qt, st = toks(quote.rstrip(".,;:") or quote), toks(text[lo:hi], lo)
    vocab = {}
    enc = lambda ts: "".join(chr(0xE000 + vocab.setdefault(t[0], len(vocab))) for t in ts)  # noqa: E731
    qs, ss = enc(qt), enc(st)
    r = fuzz.partial_ratio_alignment(qs, ss, score_cutoff=cutoff)
    if r is None:
        return None
    w0, w1 = max(0, r.dest_start - pad), min(len(ss), r.dest_end + pad)
    ops = [o for o in Levenshtein.opcodes(qs, ss[w0:w1]) if o.tag != "insert" or o.src_start not in (0, len(qs))]
    used = [o for o in ops if o.tag in ("equal", "replace")]
    if not used:
        return None
    a, b = w0 + used[0].dest_start, w0 + used[-1].dest_end
    return st[a][1], st[b - 1][2], round(r.score, 1), len(qt)


def best_of(quote, text, lo, hi, cutoff=80):
    """Token window as above; candidates: the token-opcode span, and regex BESTMATCH inside the token
    window (padded), snapped outward to word boundaries; keep the candidate whose text is nearest the
    quote by character Levenshtein distance (ties: the token span)."""
    tr = token_refine(quote, text, lo, hi, cutoff)
    if tr is None:
        return None
    qq = quote.rstrip(".,;:") or quote
    pad = math.ceil(0.3 * len(qq))
    wlo, whi = max(lo, tr[0] - pad), min(hi, tr[1] + pad)
    k = max(1, math.ceil(0.15 * len(qq)))
    cands = [(tr[0], tr[1])]
    try:
        m = regex.search(r"(?b)(?:" + regex.escape(qq) + "){e<=" + str(k) + "}", text, pos=wlo, endpos=whi, timeout=0.2)
    except TimeoutError:
        m = None
    if m is not None and m.end() > m.start():
        cands.append(RP.snap(text, m.start(), m.end(), lo, hi))
    return min(cands, key=lambda c: Levenshtein.distance(qq, text[c[0]:c[1]].rstrip(".,;:")))


rng = random.Random(20261028)
kinds = ["respace", "typo", "drop_word", "trim_end", "add_period", "macro"]
agg = defaultdict(Counter)
ms = defaultdict(list)
long_tok = 0
for unit, sid, q in RP.quotes():
    ctx = context(unit)
    RP.UNIT[0] = unit
    gt = locate_quote(q, sid, ctx)
    if gt.tier not in (1, 2) or sid not in ctx.sentences:
        continue
    lo, hi = ctx.sentences[sid]
    for kind in kinds:
        pq = RP.perturb(q, kind, rng)
        if pq is None or pq == q:
            continue
        t = time.perf_counter(); cur = locate_quote(pq, sid, ctx); ms["cascade"].append(time.perf_counter() - t)
        t = time.perf_counter(); ta = token_align(pq, ctx.text, lo, hi, 80); ms["token"].append(time.perf_counter() - t)
        t = time.perf_counter(); tr = token_refine(pq, ctx.text, lo, hi, 80); ms["token_refine"].append(time.perf_counter() - t)
        # cascade with the token step replacing the fuzzy step (exact/spacing/macros unchanged)
        hyb = (cur.start, cur.end) if cur.tier in (1, 2, 3, 4) else ((tr[0], tr[1]) if tr else None)
        t = time.perf_counter(); bo = best_of(pq, ctx.text, lo, hi); ms["best_of"].append(time.perf_counter() - t)
        hyb2 = (cur.start, cur.end) if cur.tier in (1, 2, 3, 4) else bo
        for name, span in (("cascade", (cur.start, cur.end) if cur.tier else None), ("token_only", ta[:2] if ta else None), ("token_refine_only", tr[:2] if tr else None),
                           ("cascade_token_fuzzy", hyb), ("cascade_best_of", hyb2)):
            agg[(kind, name)]["n"] += 1
            if span:
                agg[(kind, name)]["found"] += 1
                agg[(kind, name)]["exact"] += span == (gt.start, gt.end)
                inter = max(0, min(span[1], gt.end) - max(span[0], gt.start)); union = max(span[1], gt.end) - min(span[0], gt.start)
                agg[(kind, name)]["iou>=0.9"] += inter / union >= 0.9
        if ta and ta[3] > 64:
            long_tok += 1
table = {f"{k}|{m}": dict(v) for (k, m), v in sorted(agg.items())}
tot = defaultdict(Counter)
for (k, m), v in agg.items():
    tot[m].update(v)
print(json.dumps({"by_kind": table, "totals": {m: dict(v) for m, v in tot.items()},
                  "median_ms": {m: round(sorted(v)[len(v) // 2] * 1000, 3) for m, v in ms.items()},
                  "max_ms": {m: round(max(v) * 1000, 2) for m, v in ms.items()}, "quotes_over_64_tokens": long_tok}, indent=1))
