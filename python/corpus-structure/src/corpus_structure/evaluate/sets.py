"""Release-bound reference set API; legacy physical persistence is retired."""
from .sampling import PoolUnit,Sample,GoldenSetError,allocate,cut_points,sample,stratum
from .semantic import create_reference_set as create_golden_set, golden_units, golden_set_status as golden_status
