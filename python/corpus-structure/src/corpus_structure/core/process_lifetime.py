"""Linux process-group retirement, including adopted zombie descendants."""

import os
from pathlib import Path


def _live_group(group: int) -> bool:
    # Linux reports zombies as group members too. They have no device resources
    # and adopted descendants may remain zombies until their new parent reaps them.
    with os.scandir("/proc") as entries:
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            try:
                stat = Path(entry.path, "stat").read_bytes().rpartition(b")")[2].split()
            except FileNotFoundError, ProcessLookupError, PermissionError:
                continue
            if int(stat[2]) == group and stat[0] not in {b"Z", b"X", b"x"}:
                return True
    return False


def physical_retirement_uncertain(error: BaseException) -> bool:
    """A grouped cleanup failure cannot hide an unretired physical borrower."""
    from .work import PhysicalRetirementUncertain

    return isinstance(error, PhysicalRetirementUncertain) or (
        isinstance(error, BaseExceptionGroup)
        and any(physical_retirement_uncertain(child) for child in error.exceptions)
    )
