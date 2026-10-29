"""Targeted carry sweep: round-up ties/above-ties that carry through runs of 9s.

decimal256(76, s), ndigits=12, half_to_even, for integer parts "9"*k and "1"+"9"*k, k=1..,
fractional parts "9"*12 + tail; tails "5" (tie), "6", "51". Exact stdlib quantize is the oracle.
"""

from decimal import ROUND_HALF_EVEN, Context, Decimal
import pyarrow as pa
import pyarrow.compute as pc

print("pyarrow", pa.__version__)
ctx = Context(prec=200, rounding=ROUND_HALF_EVEN)
for ctor, prec in ((pa.decimal128, 38), (pa.decimal256, 76)):
    for s in (13, 18, 20, 25, 28, 30, 32, 35, 38, 39, 40, 45, 50, 60):
        if s > prec:
            continue
        t = ctor(prec, s)
        cases = bad = refused = 0
        first = None
        for lead in ("9", "19", "49"):
            for k in range(1, prec):
                for tail in ("5", "6", "51"):
                    if 12 + len(tail) > s:
                        continue
                    ip = (lead[:-1] + "9" * k)
                    if len(ip) + s + 1 > prec:  # leave room for the carry digit
                        continue
                    v = Decimal(ip + "." + "9" * 12 + tail)
                    cases += 1
                    exp = v.quantize(Decimal("1e-12"), context=ctx)
                    try:
                        got = pc.round(pa.array([v], t), ndigits=12)[0].as_py()
                    except Exception:  # noqa: BLE001
                        refused += 1
                        continue
                    if got != exp:
                        bad += 1
                        first = first or (str(v), str(exp), str(got))
        print(f"{t}: cases {cases} wrong {bad} refused {refused} first={first}")
