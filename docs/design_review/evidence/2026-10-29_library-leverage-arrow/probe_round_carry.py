"""Follow-up to P2: pc.round HALF_EVEN on decimals when the tie rounds up through a carry.

Compares pyarrow decimal rounding with stdlib Decimal.quantize(ROUND_HALF_EVEN) over
decimal128/decimal256 and several input scales, for every round_mode Arrow exposes.
"""

from decimal import (ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_HALF_DOWN, ROUND_UP, ROUND_DOWN,
                     ROUND_CEILING, ROUND_FLOOR, Context, Decimal)
import pyarrow as pa
import pyarrow.compute as pc

print("pyarrow", pa.__version__)
MODES = {
    "half_to_even": ROUND_HALF_EVEN, "half_towards_infinity": ROUND_HALF_UP,
    "half_towards_zero": ROUND_HALF_DOWN, "towards_infinity": ROUND_UP,
    "towards_zero": ROUND_DOWN, "up": ROUND_CEILING, "down": ROUND_FLOOR,
}
cases = ["0.9999999999995", "9.9999999999995", "0.0000000000015", "0.0000000000025",
         "1.0000000000035", "0.9999999999985", "-0.9999999999995", "0.9999999999996",
         "99999999999999999999999999.9999999999995", "0.9999999999994", "0.1999999999995"]
differ = 0
total = 0
for ctor, prec in ((pa.decimal128, 38), (pa.decimal256, 76)):
    for in_scale in (13, 20, 30, 38, 39, 40, 50, 63):
        t = ctor(prec, in_scale)
        for mode, py_mode in MODES.items():
            for lex in cases:
                v = Decimal(lex)
                if v.adjusted() + 1 + in_scale > prec:
                    continue
                total += 1
                exp = v.quantize(Decimal("1e-12"), context=Context(prec=200, rounding=py_mode))
                try:
                    got = pc.round(pa.array([v], t), ndigits=12, round_mode=mode)[0].as_py()
                except Exception as exc:  # noqa: BLE001
                    got = f"{type(exc).__name__}: {exc}"
                if not isinstance(got, Decimal) or got != exp:
                    differ += 1
                    print(f"DIFFER {t} {mode:22} {lex:>42} expected={exp} arrow={got}")
print(f"cases={total} differ={differ}")
