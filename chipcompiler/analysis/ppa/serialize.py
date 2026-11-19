"""CSV serialization for the PPA long table."""

import csv
import io
from collections.abc import Iterable

from chipcompiler.analysis.ppa.models import CSV_HEADER, PpaRow, PpaStage, PpaStatus


def csv_header() -> tuple[str, ...]:
    """Return the sole column order for the PPA CSV export."""
    return CSV_HEADER


def escape_field(value: object) -> str:
    """Escape control characters so every record remains one CSV line."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _row_values(row: PpaRow | Iterable[object]) -> tuple[object, ...]:
    if isinstance(row, PpaRow):
        return row.as_tuple()
    return tuple(row)


def row_to_csv(row: PpaRow | Iterable[object]) -> str:
    """Serialize one metric row without a trailing newline."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="")
    writer.writerow([escape_field(value) for value in _row_values(row)])
    return buffer.getvalue()


def missing_row(
    workspace: str,
    stage: PpaStage,
    corner: str,
    metric: str,
    unit: str,
    status: PpaStatus = PpaStatus.UNAVAILABLE,
) -> PpaRow:
    """Build an explicit empty-value row with a non-``ok`` status."""
    return PpaRow(
        workspace=workspace,
        stage=stage,
        corner=corner,
        metric=metric,
        value=None,
        unit=unit,
        status=status,
    )


def serialize_csv(rows: Iterable[PpaRow]) -> str:
    """Return header plus one row per metric, with no omitted columns."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(csv_header())
    for row in rows:
        writer.writerow([escape_field(value) for value in _row_values(row)])
    return buffer.getvalue()
