"""PPA long-table export layer.

Collect the current workspace's STA/power/area metrics into stable rows and
serialize them as CSV. The collector does not rerun EDA; it only normalizes
already-published per-step artifacts.
"""

from chipcompiler.analysis.ppa.collector import collect_ppa_rows
from chipcompiler.analysis.ppa.models import (
    CSV_HEADER,
    PPA_CORNER_LABELS,
    PpaRow,
    PpaStage,
    PpaStatus,
    normalize_corner,
)
from chipcompiler.analysis.ppa.serialize import (
    csv_header,
    escape_field,
    missing_row,
    row_to_csv,
    serialize_csv,
)

__all__ = [
    "CSV_HEADER",
    "PPA_CORNER_LABELS",
    "PpaRow",
    "PpaStage",
    "PpaStatus",
    "collect_ppa_rows",
    "csv_header",
    "escape_field",
    "generate_ppa_csv",
    "missing_row",
    "normalize_corner",
    "row_to_csv",
    "serialize_csv",
]


def collect(workspace) -> list[PpaRow]:
    """Alias for :func:`collect_ppa_rows` matching the export-stage API."""
    return collect_ppa_rows(workspace)


def generate_ppa_csv(workspace) -> str:
    """Collect and serialize the workspace PPA rows."""
    return serialize_csv(collect_ppa_rows(workspace))
