import json
from types import SimpleNamespace

from chipcompiler.analysis.ppa import (
    PpaStage,
    PpaStatus,
    collect,
    csv_header,
    escape_field,
    generate_ppa_csv,
    missing_row,
    normalize_corner,
    row_to_csv,
    serialize_csv,
)


def _qor_summary(wns, tns, nvp, corner):
    return {
        "corner": corner,
        "path_groups": [],
        "summary": {
            "setup": {"wns": wns, "tns": tns, "nvp": nvp, "frequency_mhz": 100.0},
            "hold": {"wns": 0.01, "tns": 0.0, "nvp": 0},
        },
    }


def _timing_path(path_id, slack_ns):
    return {
        "corner": "ignored",
        "path_id": path_id,
        "path_group": "clk",
        "start_point": "a",
        "end_point": "b",
        "launch_clock": "clk",
        "capture_clock": "clk",
        "check_type": "setup",
        "analysis_type": "setup",
        "slack_ns": slack_ns,
        "arrival_ns": 1.0,
        "required_ns": 2.0,
        "cppr_ns": 0.0,
        "launch_clock_network_delay_ns": 0.0,
        "capture_clock_network_delay_ns": 0.0,
        "stages": [
            {
                "kind": "net",
                "pin": "p",
                "instance": "u",
                "cell": "c",
                "transition": "rise",
                "incremental_delay_ns": 0.1,
                "arrival_ns": 0.2,
            }
        ],
    }


def _timing_paths(corner, paths):
    return {
        "schema_version": 1,
        "corner": corner,
        "path_limit": 10,
        "paths": paths,
    }


def _qor_metrics(metrics):
    return {
        "schema_version": 3,
        "metrics": [
            {"id": metric_id, "value": value, "unit": unit} for metric_id, value, unit in metrics
        ],
    }


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = payload if isinstance(payload, str) else json.dumps(payload)
    path.write_text(content, encoding="utf-8")


def _workspace(root, states=None, config=None):
    return SimpleNamespace(
        directory=root,
        name="gcd",
        design=SimpleNamespace(name="gcd"),
        config=config or {},
        flow=SimpleNamespace(data={"steps": states or []}),
    )


def _flow_steps(states):
    return [{"name": name, "tool": "ecc", "state": state} for name, state in states.items()]


def test_normalize_corner_maps_default_and_reserved_labels():
    assert normalize_corner("TYP_25/TYPICAL") == "TYP/TYPICAL"
    assert normalize_corner("MIN_m40/Cworst") == "MIN/Cworst"
    assert normalize_corner("MIN/RCworst") == "MIN/RCworst"
    assert normalize_corner("MAX_125/Cbest") == "MAX/Cbest"
    assert normalize_corner("WCL_85/RCbest") == "WCL/RCbest"
    assert normalize_corner("TYP:[TYPICAL]") == "TYP/TYPICAL"
    assert normalize_corner("ML_0/RCworst") == "ML/RCworst"
    assert normalize_corner("FOO/BAR") is None
    assert normalize_corner("TYP/Cworst") is None


def test_csv_header_and_row_serialization():
    assert csv_header() == ("workspace", "stage", "corner", "metric", "value", "unit", "status")
    row = missing_row(
        "gcd",
        PpaStage.POWER,
        "TYP/TYPICAL",
        "total_power",
        "mW",
        PpaStatus.UNAVAILABLE,
    )
    assert row_to_csv(row) == "gcd,power,TYP/TYPICAL,total_power,,mW,unavailable"
    assert "\\n" in escape_field("a\nb")
    assert "\\t" in escape_field("a\tb")
    assert "\\r" in escape_field("a\rb")
    assert escape_field(None) == ""


def test_collect_success_rows_for_sta_power_area(tmp_path):
    states = _flow_steps(
        {
            "sta": "Success",
            "powerAnalysis": "Success",
            "Harden": "Success",
        }
    )
    workspace = _workspace(tmp_path, states)
    for label, corner in (
        ("TYP_25/TYPICAL", "TYP_25/TYPICAL"),
        ("MIN_m40/Cworst", "MIN_m40/Cworst"),
    ):
        feature_dir = tmp_path / "sta_ecc" / "feature" / label
        _write(feature_dir / "qor_summary.json", _qor_summary(0.012, -0.4, 2, corner))
        _write(
            feature_dir / "timing_paths.json",
            _timing_paths(
                corner,
                [_timing_path("p1", -0.1), _timing_path("p2", 0.2)],
            ),
        )
    power_report = tmp_path / "powerAnalysis_ecc" / "report" / "powerAnalysis.rpt"
    _write(
        power_report,
        (
            "Cell Internal Power = 1.000 mW\n"
            "Net Switching Power = 2.000 mW\n"
            "Total Dynamic Power = 3.000 mW\n"
            "Cell Leakage Power = 0.500 mW\n"
        ),
    )
    _write(
        tmp_path / "Harden_ecc" / "analysis" / "qor_metrics.json",
        _qor_metrics(
            [
                ("std_cell_area", 1200.0, "um^2"),
                ("macro_area", 300.0, "um^2"),
                ("core_utilization", 0.62, "ratio"),
            ]
        ),
    )

    rows = collect(workspace)

    assert len(rows) == 14
    by_key = {(row.stage.value, row.corner, row.metric): row for row in rows}
    assert by_key[("sta", "TYP/TYPICAL", "wns")].value == 12.0
    assert by_key[("sta", "TYP/TYPICAL", "tns")].value == -400.0
    assert by_key[("sta", "TYP/TYPICAL", "failing_endpoints")].value == 2
    assert by_key[("sta", "TYP/TYPICAL", "violating_paths")].value == 1
    assert by_key[("power", "TYP/TYPICAL", "total_power")].value == 3.5
    assert by_key[("power", "TYP/TYPICAL", "dynamic_power")].value == 3.0
    assert by_key[("power", "TYP/TYPICAL", "leakage_power")].value == 0.5
    assert by_key[("area", "", "cell_area")].value == 1200.0
    assert by_key[("area", "", "macro_area")].value == 300.0
    assert by_key[("area", "", "utilization")].value == 62.0

    csv_text = generate_ppa_csv(workspace)
    lines = csv_text.splitlines()
    assert lines[0] == "workspace,stage,corner,metric,value,unit,status"
    assert "gcd,sta,TYP/TYPICAL,wns,12.0,ps,ok" in lines
    assert "gcd,power,TYP/TYPICAL,total_power,3.5,mW,ok" in lines


def test_collect_not_run_for_skipped_and_unstarted_steps(tmp_path):
    states = _flow_steps({"sta": "Skipped", "powerAnalysis": "Unstart"})
    workspace = _workspace(tmp_path, states)

    rows = collect(workspace)

    assert {row.status for row in rows} == {PpaStatus.NOT_RUN}
    assert {row.stage for row in rows} == {PpaStage.STA, PpaStage.POWER, PpaStage.AREA}
    assert len(rows) == 10
    assert all(row.value is None for row in rows)


def test_collect_unavailable_when_success_but_artifacts_missing(tmp_path):
    states = _flow_steps({"sta": "Success", "powerAnalysis": "Success", "Harden": "Success"})
    workspace = _workspace(tmp_path, states)

    rows = collect(workspace)

    assert {row.status for row in rows} == {PpaStatus.UNAVAILABLE}
    assert all(row.value is None for row in rows)
    assert {row.stage for row in rows} == {PpaStage.STA, PpaStage.POWER, PpaStage.AREA}


def test_unmapped_corner_is_unavailable_not_silently_flattened(tmp_path):
    states = _flow_steps({"sta": "Success"})
    workspace = _workspace(tmp_path, states)
    feature_dir = tmp_path / "sta_ecc" / "feature" / "FOO_25" / "BAR"
    _write(feature_dir / "qor_summary.json", _qor_summary(0.012, 0.0, 0, "FOO_25/BAR"))

    rows = [row for row in collect(workspace) if row.stage == PpaStage.STA]

    assert len(rows) == 4
    assert {row.corner for row in rows} == {"FOO_25/BAR"}
    assert {row.status for row in rows} == {PpaStatus.UNAVAILABLE}
    assert all(row.value is None for row in rows)


def test_serialize_csv_keeps_empty_columns(tmp_path):
    rows = [
        missing_row("gcd", PpaStage.POWER, "TYP/TYPICAL", "total_power", "mW"),
    ]
    assert serialize_csv(rows) == (
        "workspace,stage,corner,metric,value,unit,status\n"
        "gcd,power,TYP/TYPICAL,total_power,,mW,unavailable\n"
    )


def test_workspace_field_prefers_workspace_name_over_design_name(tmp_path):
    workspace = _workspace(
        tmp_path,
        _flow_steps({"sta": "Skipped", "powerAnalysis": "Skipped"}),
    )
    workspace.name = "workspace_name"
    workspace.design.name = "design_name"

    rows = collect(workspace)

    assert rows
    assert all(row.workspace == "workspace_name" for row in rows)


def test_workspace_field_falls_back_to_directory_basename(tmp_path):
    workspace = _workspace(tmp_path, _flow_steps({"sta": "Skipped"}))
    del workspace.name

    rows = collect(workspace)

    assert rows
    assert all(row.workspace == tmp_path.name for row in rows)
