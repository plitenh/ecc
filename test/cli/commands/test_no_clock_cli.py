"""CLI/config integration for effective no-clock decisions."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import chipcompiler.data as data_api
from chipcompiler.cli import main as cli_main
from chipcompiler.cli.command_handlers.project import (
    _preflight_environment,
    _preflight_flow_range,
)
from chipcompiler.cli.core.types import CommandContext, CommandResult, OutputMode
from chipcompiler.cli.project.config import (
    ProjectNoClockDecisionResolver,
    load_project_config,
    to_parameters,
    validate_project_config,
)
from chipcompiler.cli.project.effective_config import _attach_no_clock, resolve_effective_config
from chipcompiler.cli.project.flow_selection import effective_insert_steps, effective_skip_steps
from chipcompiler.data.workspace.sdc_inputs import SdcInputs
from chipcompiler.rtl2gds import resolve_skip_steps
from chipcompiler.rtl2gds.builder import NoClockDecision

_DEFAULT_SKIPS = resolve_skip_steps(None)
_NO_CLOCK_SKIPS = ("preplace", "diff_opt", "diff_sizing", "cts", "timing_optimization")
_NO_CLOCK_ADDED_SKIPS = frozenset(_NO_CLOCK_SKIPS).difference(_DEFAULT_SKIPS)
_CLOCK_ERRORS = ("design.clock_port", "design.frequency_mhz")


@pytest.fixture(autouse=True)
def _pdk_contents_are_valid(monkeypatch):
    monkeypatch.setattr(
        "chipcompiler.cli.project.config._validate_pdk_contents",
        lambda name, root, overrides=None: None,
    )


def _load_config(
    project_dir,
    *,
    no_clock=None,
    clock="",
    frequency=0,
    skip_steps=None,
    insert_steps=None,
):
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "pdk").mkdir(exist_ok=True)
    flow = ['preset = "rtl2gds"']
    if no_clock is not None:
        flow.append(f"no_clock = {no_clock}")
    if skip_steps is not None:
        flow.append(f"skip_steps = {skip_steps}")
    if insert_steps is not None:
        flow.append(f"insert_steps = {insert_steps}")
    (project_dir / "ecc.toml").write_text(
        "[design]\n"
        'name = "gcd"\n'
        'top = "gcd"\n'
        'rtl = ["rtl/gcd.v"]\n'
        f'clock_port = "{clock}"\n'
        f"frequency_mhz = {frequency}\n"
        "\n[pdk]\n"
        'name = "ics55"\n'
        f'root = "{project_dir / "pdk"}"\n'
        "\n[flow]\n" + "\n".join(flow) + "\n"
    )
    return load_project_config(str(project_dir / "ecc.toml"))


def _timing_errors(cfg):
    return [error for error in validate_project_config(cfg) if error.startswith(_CLOCK_ERRORS)]


def _capture_preflight_steps(monkeypatch):
    captured = []

    def capture(steps):
        captured.append(tuple(getattr(step, "value", str(step)) for step, _tool, _state in steps))
        return ()

    monkeypatch.setattr("chipcompiler.cli.inspection.env_probe.probe_components_for_steps", capture)
    return captured


@pytest.mark.parametrize(
    ("literal", "clock", "flag", "source", "skips"),
    [
        ("true", "", True, "explicit", _NO_CLOCK_SKIPS),
        ('"yes"', "clk", True, "explicit", _NO_CLOCK_SKIPS),
        ("false", "", False, "off", _DEFAULT_SKIPS),
    ],
)
def test_explicit_no_clock_precedence(tmp_path, literal, clock, flag, source, skips):
    cfg = _load_config(tmp_path, no_clock=literal, clock=clock)

    decision = ProjectNoClockDecisionResolver(cfg).resolve()

    assert cfg.flow_no_clock is flag
    assert "flow.no_clock" in cfg._explicit_keys
    assert decision == NoClockDecision(enabled=flag, source=source)
    assert effective_skip_steps(cfg, None) == skips


def test_empty_clock_infers_no_clock_through_project_resolver(tmp_path):
    cfg = _load_config(tmp_path)

    assert ProjectNoClockDecisionResolver(cfg).resolve() == NoClockDecision(
        enabled=True, source="inferred"
    )
    assert effective_skip_steps(cfg, None) == _NO_CLOCK_SKIPS
    assert _timing_errors(cfg) == []


def test_missing_project_config_does_not_infer_no_clock():
    assert ProjectNoClockDecisionResolver(None).resolve() == NoClockDecision(
        enabled=False, source="off"
    )


@pytest.mark.parametrize(
    ("clock", "no_clock", "expect_clock_steps"),
    [
        ("", None, False),
        ("   ", None, False),
        ("clk", None, True),
        ("", False, True),
    ],
)
def test_preflight_paths_apply_inferred_and_explicit_no_clock(
    tmp_path, monkeypatch, clock, no_clock, expect_clock_steps
):
    literal = None if no_clock is None else str(no_clock).lower()
    cfg = _load_config(tmp_path, no_clock=literal, clock=clock)
    captured = _capture_preflight_steps(monkeypatch)
    flow_config = {"start_step": "synthesis", "end_step": "harden"}
    if no_clock is not None:
        flow_config["no_clock"] = no_clock

    assert _preflight_flow_range(flow_config, None, cfg) is None
    assert _preflight_environment("rtl2gds", None, flow_config, cfg) is None
    expected = _NO_CLOCK_ADDED_SKIPS if expect_clock_steps else frozenset()
    assert [set(steps) & _NO_CLOCK_ADDED_SKIPS for steps in captured] == [
        expected,
        expected,
    ]


def test_preflight_paths_without_config_keep_no_material_behavior(monkeypatch):
    captured = _capture_preflight_steps(monkeypatch)
    flow_config = {"start_step": "synthesis", "end_step": "harden"}

    assert _preflight_flow_range(flow_config, None) is None
    assert _preflight_environment("rtl2gds", None, flow_config) is None
    assert [set(steps) & _NO_CLOCK_ADDED_SKIPS for steps in captured] == [
        _NO_CLOCK_ADDED_SKIPS,
        _NO_CLOCK_ADDED_SKIPS,
    ]


@pytest.mark.parametrize(
    ("start_step", "end_step"),
    [
        ("preplace", "harden"),
        ("synthesis", "cts"),
        ("diff_sizing", "cts"),
    ],
    ids=["skipped-start", "skipped-end", "clock-steps-only"],
)
def test_no_clock_flow_range_with_skipped_boundaries_degrades_to_no_preflight(
    tmp_path, monkeypatch, start_step, end_step
):
    cfg = _load_config(tmp_path)
    captured = _capture_preflight_steps(monkeypatch)
    flow_config = {"start_step": start_step, "end_step": end_step}

    assert _preflight_flow_range(flow_config, None, cfg) is None
    assert captured == []


@pytest.mark.parametrize(
    ("no_clock", "clock", "frequency", "expected"),
    [
        ("true", "", 0, []),
        (
            "false",
            "",
            0,
            [
                "design.clock_port is required",
                "design.frequency_mhz must be greater than 0",
            ],
        ),
        ("true", "clk", 0, ["design.frequency_mhz must be greater than 0"]),
        (None, "clk", 100, []),
        (None, "   ", 0, []),
    ],
)
def test_no_clock_timing_validation(tmp_path, no_clock, clock, frequency, expected):
    cfg = _load_config(
        tmp_path,
        no_clock=no_clock,
        clock=clock,
        frequency=frequency,
    )

    assert _timing_errors(cfg) == expected


def test_to_parameters_trims_nonempty_clock_and_requires_frequency(tmp_path):
    cfg = _load_config(tmp_path, clock=" clk ")

    assert to_parameters(cfg) == {
        "pdk": "ics55",
        "design": "gcd",
        "top_module": "gcd",
        "clock": "clk",
        "frequency_max": 0,
    }
    assert _timing_errors(cfg) == ["design.frequency_mhz must be greater than 0"]


def test_whitespace_clock_is_normalized_for_sdc_consumers(tmp_path):
    cfg = _load_config(tmp_path, clock="   ")

    assert validate_project_config(cfg) == []
    parameters = to_parameters(cfg)
    assert parameters["clock"] == ""
    assert SdcInputs.from_parameters(parameters).clocks(parameters, "TYP") == ()


def test_attach_no_clock_leaves_inference_and_insert_steps_unchanged(tmp_path):
    flow_config = {"insert_steps": ["lec@routing"]}

    assert (
        _attach_no_clock(
            flow_config,
            no_clock_decision=NoClockDecision(enabled=True, source="inferred"),
        )
        is flow_config
    )
    attached = _attach_no_clock(
        flow_config,
        no_clock_decision=NoClockDecision(enabled=True, source="explicit"),
    )
    cfg = _load_config(
        tmp_path,
        no_clock="true",
        clock="clk",
        frequency=100,
        insert_steps='["lec@routing"]',
    )

    assert attached == {"insert_steps": ["lec@routing"], "no_clock": True}
    assert flow_config == {"insert_steps": ["lec@routing"]}
    assert effective_insert_steps(cfg, attached) == ("lec@routing",)


def test_virgin_project_passes_explicit_no_clock_to_workspace_creation(
    create_cli_project, flow_mocks
):
    project_dir = create_cli_project()
    with Path(project_dir, "ecc.toml").open("a") as config_file:
        config_file.write("no_clock = true\n")

    rc = cli_main.run(["run", "--project", project_dir])

    assert rc == 0
    flow_config = flow_mocks.capture["create_kwargs"]["flow_config"]
    assert flow_config["no_clock"] is True


@pytest.mark.parametrize("clock", ["", "   "])
def test_virgin_project_infers_no_clock_through_fresh_run(
    monkeypatch, create_cli_project, flow_mocks, clock
):
    from chipcompiler.rtl2gds import build_rtl2gds_flow

    monkeypatch.setattr("chipcompiler.rtl2gds.builder.build_rtl2gds_flow", build_rtl2gds_flow)
    create_workspace = data_api.create_workspace

    def create_with_parameters(**kwargs):
        workspace = cast(Any, create_workspace(**kwargs))
        workspace.parameters = SimpleNamespace(data={})
        return workspace

    monkeypatch.setattr(data_api, "create_workspace", create_with_parameters)
    monkeypatch.setattr("chipcompiler.data.parameter.save_parameter", lambda _parameters: True)
    project_dir = create_cli_project(freq=0)
    config_path = Path(project_dir, "ecc.toml")
    config_path.write_text(
        config_path.read_text().replace('clock_port = "clk"', f'clock_port = "{clock}"')
    )

    rc = cli_main.run(["run", "--project", project_dir])

    assert rc == 0
    (flow,) = flow_mocks.flow.instances
    step_names = [str(step) for step, _tool, _state in flow.added_steps]
    assert set(step_names).isdisjoint(_NO_CLOCK_SKIPS)
    assert flow.workspace.parameters.data["_flow"] == {
        "preset": "rtl2gds",
        "no_clock": True,
        "skip_steps": list(_NO_CLOCK_SKIPS),
    }


def test_effective_config_carries_no_clock_without_losing_inserts(tmp_path, manifest_stubs):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    manifest_stubs.write(project_dir, [manifest_stubs.entry(project_dir, "ws_0001")])
    cfg = _load_config(
        project_dir,
        no_clock="true",
        clock="clk",
        frequency=100,
        skip_steps="[]",
        insert_steps='["lec@routing"]',
    )
    ctx = CommandContext(
        project_dir=str(project_dir),
        project=str(project_dir),
        run_dir=str(project_dir / "ws_0001"),
        run_id="ws_0001",
        output_mode=OutputMode.PLAIN,
        config=cfg,
        project_state="manifest",
    )

    resolved = resolve_effective_config(ctx, "ws_0001", cfg)

    assert not isinstance(resolved, CommandResult)
    effective, flow_config, _warnings = resolved
    assert effective is cfg
    assert flow_config == {
        "skip_steps": [],
        "no_clock": True,
        "insert_steps": ["lec@routing"],
    }
