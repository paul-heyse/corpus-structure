"""Bounded direct/NumPy code-generation comparison; no application state or parser changes."""
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import sympy as sp

x = sp.Symbol('x')
expressions = [sp.sqrt(x*x)-x, sp.sin(x)-x, sp.exp(x)-1-x]
report = []
for expr in expressions:
    for count in (12, 1200):
        values = np.linspace(-2, 2, count)
        started = perf_counter()
        direct = np.asarray([complex(expr.xreplace({x: sp.Float(v, 30)}).evalf()) for v in values])
        direct_seconds = perf_counter()-started
        for cse in (False, True):
            started = perf_counter()
            fn = sp.lambdify(x, expr, modules='numpy', cse=cse, docstring_limit=0, use_imps=False)
            build = perf_counter()-started
            started = perf_counter()
            result = np.asarray(fn(values))
            evaluation = perf_counter()-started
            report.append({'expression': str(expr), 'points': count, 'cse': cse,
                'direct_seconds': direct_seconds, 'compile_seconds': build,
                'numpy_seconds': evaluation, 'matches': bool(np.allclose(direct,result,rtol=1e-9,atol=1e-12))})
output = Path(__file__).resolve().parents[1]/'raw'/'numeric-candidates.json'
output.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
