import os

from hypothesis import settings

settings.register_profile("ci", derandomize=True, print_blob=True, max_examples=20)
settings.register_profile("dev", database=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
