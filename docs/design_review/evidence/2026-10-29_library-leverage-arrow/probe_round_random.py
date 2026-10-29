"""Seeded differential: pc.round(decimal256(76, s), ndigits=12, half_to_even) vs stdlib.

Characterizes for which input scales s the decimal256 rounding kernel agrees with exact
quantize. 2000 random values per scale, each with total digits <= 75 (no carry overflow).
"""

import random
from decimal import ROUND_HALF_EVEN, Context, Decimal
import pyarrow as pa
import pyarrow.compute as pc

print("pyarrow", pa.__version__)
rng = random.Random(20261029)
for s in (13, 20, 25, 30, 31, 32, 33, 35, 38, 39, 40, 50, 60):
    t = pa.decimal256(76, s)
    values = []
    for _ in range(2000):
        total = rng.randint(s + 1, 75)
        digits = "".join(rng.choice("0123456789") for _ in range(total))
        if rng.random() < 0.3:  # force a tie at digit 13
            digits = digits[: total - s + 12] + "5" + "0" * (s - 13)
        sign = "-" if rng.random() < 0.5 else ""
        values.append(Decimal(sign + digits[: total - s] + "." + digits[total - s:]))
    got = pc.round(pa.array(values, t), ndigits=12, round_mode="half_to_even").to_pylist()
    ctx = Context(prec=200, rounding=ROUND_HALF_EVEN)
    bad = [(v, g) for v, g in zip(values, got) if g != v.quantize(Decimal("1e-12"), context=ctx)]
    example = f" e.g. {bad[0][0]} -> {bad[0][1]}" if bad else ""
    print(f"scale {s:2}: discrepancies {len(bad)}/2000{example}")
