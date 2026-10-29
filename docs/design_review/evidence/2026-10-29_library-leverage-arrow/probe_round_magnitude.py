"""Bisect the decimal256 rounding discrepancy seen in probe_round_carry: by total digit count."""

from decimal import ROUND_HALF_EVEN, ROUND_DOWN, Context, Decimal
import pyarrow as pa
import pyarrow.compute as pc

print("pyarrow", pa.__version__)
for scale in (13, 30, 40, 50):
    t = pa.decimal256(76, scale)
    first_bad = None
    for int_digits in range(1, 76 - scale + 1):
        lex = "9" * int_digits + "." + "9" * 12 + "5"
        v = Decimal(lex)
        arr = pa.array([v], t)
        back = arr[0].as_py()
        rt_ok = back == v
        for mode, py in (("half_to_even", ROUND_HALF_EVEN), ("towards_zero", ROUND_DOWN)):
            exp = v.quantize(Decimal("1e-12"), context=Context(prec=200, rounding=py))
            try:
                got = pc.round(arr, ndigits=12, round_mode=mode)[0].as_py()
            except Exception as exc:  # noqa: BLE001
                got = type(exc).__name__
            if (got != exp or not rt_ok) and first_bad is None:
                first_bad = (int_digits, int_digits + scale, mode, rt_ok, str(exp), str(got))
    print(f"decimal256(76,{scale}): first discrepancy (int_digits, total_digits, mode, input_roundtrip_ok, expected, arrow) = {first_bad}")

# decimal128 at the analytic boundary: never more than 38 total digits
t = pa.decimal128(38, 13)
bad = 0
for int_digits in range(1, 26):
    v = Decimal("9" * int_digits + "." + "9" * 12 + "5")
    exp = v.quantize(Decimal("1e-12"), context=Context(prec=200, rounding=ROUND_HALF_EVEN))
    try:
        got = pc.round(pa.array([v], t), ndigits=12)[0].as_py()
    except Exception as exc:  # noqa: BLE001
        got = type(exc).__name__
    bad += got != exp
print("decimal128(38,13) carry cases 1..25 integer digits, discrepancies:", bad)
