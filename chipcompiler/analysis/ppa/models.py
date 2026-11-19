"""Typed row model and corner mapping for the PPA export layer."""

import re
from dataclasses import dataclass
from enum import StrEnum

CSV_HEADER = ("workspace", "stage", "corner", "metric", "value", "unit", "status")

# Stable process/RC corner labels. MAX/WCL/ML entries are reserved for future
# signoff matrices; the default signoff matrix emits TYP + MIN combinations.
PPA_CORNER_LABELS = frozenset(
    {
        "TYP/TYPICAL",
        "MIN/Cworst",
        "MIN/RCworst",
        "MIN/Cbest",
        "MIN/RCbest",
        "MAX/Cworst",
        "MAX/RCworst",
        "MAX/Cbest",
        "MAX/RCbest",
        "WCL/Cworst",
        "WCL/RCworst",
        "WCL/Cbest",
        "WCL/RCbest",
        "ML/Cworst",
        "ML/RCworst",
        "ML/Cbest",
        "ML/RCbest",
    }
)

_PROCESS_CORNERS = frozenset({"TYP", "MIN", "MAX", "WCL", "ML"})
_RC_CORNER_NAMES = {
    "TYPICAL": "TYPICAL",
    "CWORST": "Cworst",
    "RCWORST": "RCworst",
    "CBEST": "Cbest",
    "RCBEST": "RCbest",
}


def normalize_corner(raw_label: str | None) -> str | None:
    """Flatten a configured STA path label to ``process/rc``.

    ``MIN_m40/Cworst`` and ``MIN/Cworst`` both flatten to ``MIN/Cworst``.
    Unknown labels return ``None``: callers must mark them unavailable rather
    than silently mapping them to a known corner.
    """
    if not raw_label:
        return None
    parts = [part for part in re.split(r"[:/]", raw_label) if part]
    if len(parts) < 2:
        return None
    process = parts[0].split("_", 1)[0].strip("[]:").upper()
    rc = _RC_CORNER_NAMES.get(parts[-1].strip("[]:").upper())
    if process not in _PROCESS_CORNERS or rc is None:
        return None
    candidate = f"{process}/{rc}"
    return candidate if candidate in PPA_CORNER_LABELS else None


class PpaStage(StrEnum):
    STA = "sta"
    POWER = "power"
    AREA = "area"


class PpaStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    NOT_RUN = "not_run"


@dataclass(frozen=True)
class PpaRow:
    workspace: str
    stage: PpaStage
    corner: str
    metric: str
    value: float | int | None
    unit: str
    status: PpaStatus

    def as_tuple(self) -> tuple[str, str, str, str, float | int | None, str, str]:
        return (
            self.workspace,
            self.stage.value,
            self.corner,
            self.metric,
            self.value,
            self.unit,
            self.status.value,
        )
