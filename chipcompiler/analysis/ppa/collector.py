"""Collect current-workspace PPA metrics into stable long-table rows."""

from pathlib import Path

from chipcompiler.analysis.ppa.models import (
    PpaRow,
    PpaStage,
    PpaStatus,
    normalize_corner,
)
from chipcompiler.data import StateEnum, StepEnum
from chipcompiler.data.step import STEP_DIRECTORIES
from chipcompiler.tools.ecc.power_artifacts import (
    power_step_path,
    workspace_power_report_source_path,
    workspace_power_summary_path,
)
from chipcompiler.tools.ecc.qor_metrics import QorMetrics
from chipcompiler.tools.ecc.sta_qor import (
    STA_TIMING_PATHS_FILENAME,
    configured_sta_artifact_directories,
    read_power_step_summary_json,
    read_sta_power_summary,
    read_sta_power_summary_json,
    read_sta_qor_summary,
    read_sta_timing_paths,
)
from chipcompiler.utility.json import json_read

_STA_METRICS = (
    ("wns", "ps"),
    ("tns", "ps"),
    ("failing_endpoints", "count"),
    ("violating_paths", "count"),
)
_POWER_METRICS = (
    ("total_power", "mW"),
    ("dynamic_power", "mW"),
    ("leakage_power", "mW"),
)
_AREA_METRICS = (
    ("cell_area", "um2"),
    ("macro_area", "um2"),
    ("utilization", "%"),
)

_CELL_AREA_PAIRS = (
    (StepEnum.HARDEN.value, "std_cell_area"),
    (StepEnum.ROUTING.value, "std_cell_area"),
    (StepEnum.LEGALIZATION.value, "std_cell_area"),
    (StepEnum.PLACEMENT.value, "std_cell_area"),
    (StepEnum.POST_FLOORPLAN.value, "std_cell_area"),
    (StepEnum.SYNTHESIS.value, "synthesis_cell_area"),
)
_MACRO_AREA_PAIRS = (
    (StepEnum.HARDEN.value, "macro_area"),
    (StepEnum.ROUTING.value, "macro_area"),
    (StepEnum.PLACEMENT.value, "macro_area"),
    (StepEnum.POST_FLOORPLAN.value, "macro_area"),
)
_UTILIZATION_PAIRS = (
    (StepEnum.HARDEN.value, "core_utilization"),
    (StepEnum.ROUTING.value, "core_utilization"),
    (StepEnum.LEGALIZATION.value, "core_utilization"),
    (StepEnum.PLACEMENT.value, "core_utilization"),
    (StepEnum.POST_FLOORPLAN.value, "core_utilization"),
)


def _workspace_name(workspace) -> str:
    name = getattr(workspace, "name", "")
    if name:
        return name
    return Path(workspace.directory).name


def _flow_states(workspace, workspace_root: Path) -> dict[str, str]:
    flow = getattr(workspace, "flow", None)
    data = getattr(flow, "data", None)
    if not isinstance(data, dict):
        data = json_read(workspace_root / "home" / "flow.json")
    if not isinstance(data, dict):
        return {}
    steps = data.get("steps")
    if not isinstance(steps, list):
        return {}
    states: dict[str, str] = {}
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("name"), str):
            continue
        state = step.get("state")
        if isinstance(state, str):
            states[step["name"]] = state
    return states


def _is_success(states: dict[str, str], step_name: str) -> bool:
    return states.get(step_name) == StateEnum.Success.value


def _sta_candidates(workspace, workspace_root: Path) -> list[tuple[str, Path]]:
    feature_root = workspace_root / STEP_DIRECTORIES[StepEnum.STA.value] / "feature"
    configured = configured_sta_artifact_directories(workspace, feature_root)
    if configured:
        return configured

    if not feature_root.is_dir():
        return []
    candidates = []
    seen = set()
    for path in sorted(feature_root.glob("*/*/qor_summary.json")):
        if not path.is_file():
            continue
        label = path.parent.relative_to(feature_root).as_posix()
        if label in seen:
            continue
        seen.add(label)
        candidates.append((label, path.parent))
    return candidates


def _violating_path_count(raw_label: str, path: Path) -> int | None:
    timing_paths = read_sta_timing_paths(raw_label, path)
    if timing_paths is None:
        return None
    return sum(
        1
        for item in timing_paths.paths
        if item.get("analysis_type") == "setup" and float(item.get("slack_ns")) < 0
    )


def _sta_rows(workspace, workspace_root: Path, states: dict[str, str]) -> list[PpaRow]:
    workspace_name = _workspace_name(workspace)
    candidates = _sta_candidates(workspace, workspace_root)
    step_success = _is_success(states, StepEnum.STA.value)

    if not candidates:
        status = PpaStatus.UNAVAILABLE if step_success else PpaStatus.NOT_RUN
        return [
            PpaRow(
                workspace=workspace_name,
                stage=PpaStage.STA,
                corner="",
                metric=metric,
                value=None,
                unit=unit,
                status=status,
            )
            for metric, unit in _STA_METRICS
        ]

    rows: list[PpaRow] = []
    for raw_label, feature_dir in candidates:
        canonical_corner = normalize_corner(raw_label)
        corner = canonical_corner or raw_label
        summary_path = feature_dir / "qor_summary.json"
        timing_path = feature_dir / STA_TIMING_PATHS_FILENAME
        if not step_success:
            rows.extend(
                PpaRow(
                    workspace=workspace_name,
                    stage=PpaStage.STA,
                    corner=corner,
                    metric=metric,
                    value=None,
                    unit=unit,
                    status=PpaStatus.NOT_RUN,
                )
                for metric, unit in _STA_METRICS
            )
            continue
        if canonical_corner is None:
            rows.extend(
                PpaRow(
                    workspace=workspace_name,
                    stage=PpaStage.STA,
                    corner=corner,
                    metric=metric,
                    value=None,
                    unit=unit,
                    status=PpaStatus.UNAVAILABLE,
                )
                for metric, unit in _STA_METRICS
            )
            continue

        summary = read_sta_qor_summary(raw_label, summary_path, require_hold=False)
        violating_paths = _violating_path_count(raw_label, timing_path)
        for metric, unit in _STA_METRICS:
            if summary is None or (metric == "violating_paths" and violating_paths is None):
                rows.append(
                    PpaRow(
                        workspace=workspace_name,
                        stage=PpaStage.STA,
                        corner=corner,
                        metric=metric,
                        value=None,
                        unit=unit,
                        status=PpaStatus.UNAVAILABLE,
                    )
                )
                continue
            if metric == "wns":
                value = summary.setup_wns * 1000
            elif metric == "tns":
                value = summary.setup_tns * 1000
            elif metric == "failing_endpoints":
                value = summary.setup_nvp
            else:
                value = violating_paths
            rows.append(
                PpaRow(
                    workspace=workspace_name,
                    stage=PpaStage.STA,
                    corner=corner,
                    metric=metric,
                    value=value,
                    unit=unit,
                    status=PpaStatus.OK,
                )
            )
    return rows


def _power_values(workspace_root: Path) -> tuple[float | None, float | None, float | None]:
    """Return (total, dynamic, leakage) in mW from the powerAnalysis step."""
    report_path = workspace_power_report_source_path(workspace_root)
    summary = read_sta_power_summary(report_path)
    if summary is None:
        feature_dir = workspace_root / STEP_DIRECTORIES[StepEnum.POWER_ANALYSIS.value] / "feature"
        summary = read_power_step_summary_json(power_step_path(feature_dir))
    if summary is None:
        summary = read_sta_power_summary_json(workspace_power_summary_path(workspace_root))

    if summary is None:
        return None, None, None
    dynamic_mw = summary.dynamic_uw / 1000
    leakage_mw = summary.leakage_uw / 1000
    return dynamic_mw + leakage_mw, dynamic_mw, leakage_mw


def _power_rows(workspace, workspace_root: Path, states: dict[str, str]) -> list[PpaRow]:
    workspace_name = _workspace_name(workspace)
    step_success = _is_success(states, StepEnum.POWER_ANALYSIS.value)
    values = _power_values(workspace_root) if step_success else (None, None, None)
    rows: list[PpaRow] = []
    for index, (metric, unit) in enumerate(_POWER_METRICS):
        rows.append(
            PpaRow(
                workspace=workspace_name,
                stage=PpaStage.POWER,
                corner="TYP/TYPICAL",
                metric=metric,
                value=values[index],
                unit=unit,
                status=PpaStatus.OK
                if values[index] is not None
                else (PpaStatus.NOT_RUN if not step_success else PpaStatus.UNAVAILABLE),
            )
        )
    return rows


def _qor_area_value(
    workspace_root: Path, states: dict[str, str], pairs: tuple[tuple[str, str], ...]
) -> float | None:
    for step_name, metric_id in pairs:
        if not _is_success(states, step_name):
            continue
        step_dir = workspace_root / STEP_DIRECTORIES[step_name]
        metrics = QorMetrics(step_dir / "analysis" / "qor_metrics.json")
        value, _error = metrics.number(metric_id)
        if value is not None:
            return value
    return None


def _utilization_pct(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 100 if 0 < value <= 1 else value


def _area_rows(workspace, workspace_root: Path, states: dict[str, str]) -> list[PpaRow]:
    workspace_name = _workspace_name(workspace)
    rows: list[PpaRow] = []
    for metric, unit in _AREA_METRICS:
        if metric == "cell_area":
            pairs = _CELL_AREA_PAIRS
        elif metric == "macro_area":
            pairs = _MACRO_AREA_PAIRS
        else:
            pairs = _UTILIZATION_PAIRS
        has_run = any(_is_success(states, step_name) for step_name, _metric_id in pairs)
        value = _qor_area_value(workspace_root, states, pairs) if has_run else None
        if metric == "utilization":
            value = _utilization_pct(value)
        rows.append(
            PpaRow(
                workspace=workspace_name,
                stage=PpaStage.AREA,
                corner="",
                metric=metric,
                value=value,
                unit=unit,
                status=(
                    PpaStatus.NOT_RUN
                    if not has_run
                    else PpaStatus.OK
                    if value is not None
                    else PpaStatus.UNAVAILABLE
                ),
            )
        )
    return rows


def collect_ppa_rows(workspace) -> list[PpaRow]:
    """Collect all PPA rows for one workspace in deterministic stage order."""
    workspace_root = Path(workspace.directory)
    states = _flow_states(workspace, workspace_root)
    return [
        *_sta_rows(workspace, workspace_root, states),
        *_power_rows(workspace, workspace_root, states),
        *_area_rows(workspace, workspace_root, states),
    ]
