"""Signoff CSV export and CI gate projection helpers.

``.github/scripts/export_signoff_csv*`` are thin entrypoints. Run-vs-run
dashboard diffs are intentionally not part of this package.
"""

from chipcompiler.engine.signoff.csv.bundle import (
    CsvExportBundle,
    CsvTable,
    build_csv_bundle,
    render_csv,
    write_csv_bundle,
)
from chipcompiler.engine.signoff.csv.compare import (
    METRIC_OPS,
    compare_values,
    evaluate_checklist_gate,
    evaluate_metric_gate,
)
from chipcompiler.engine.signoff.csv.manifest import (
    MANIFEST_SCHEMA_VERSION,
    RunManifest,
    build_run_manifest,
    write_run_manifest,
)
from chipcompiler.engine.signoff.csv.projection import projection_lines
from chipcompiler.engine.signoff.csv.spec import (
    ChecklistItemSpec,
    CsvExportSpec,
    CsvSpecError,
    MetricSpec,
    load_csv_spec,
)

__all__ = [
    "METRIC_OPS",
    "MANIFEST_SCHEMA_VERSION",
    "ChecklistItemSpec",
    "CsvExportBundle",
    "CsvExportSpec",
    "CsvSpecError",
    "CsvTable",
    "MetricSpec",
    "RunManifest",
    "build_csv_bundle",
    "build_run_manifest",
    "compare_values",
    "evaluate_checklist_gate",
    "evaluate_metric_gate",
    "load_csv_spec",
    "projection_lines",
    "render_csv",
    "write_csv_bundle",
    "write_run_manifest",
]
