"""CLI/config integration for effective no-clock decisions."""

import pytest

from chipcompiler.cli.core.types import CommandContext, CommandResult, OutputMode
from chipcompiler.cli.project.config import (
    ProjectNoClockDecisionResolver,
    load_project_config,
    validate_project_config,
)
from chipcompiler.cli.project.effective_config import _attach_no_clock, resolve_effective_config
from chipcompiler.cli.project.flow_selection import effective_insert_steps, effective_skip_steps
from chipcompiler.rtl2gds import resolve_skip_steps
from chipcompiler.rtl2gds.builder import NoClockDecision

_DEFAULT_SKIPS = resolve_skip_steps(None)
_NO_CLOCK_SKIPS = ("preplace", "diff_opt", "diff_sizing", "cts", "timing_optimization")
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
    return [
        error
        for error in validate_project_config(cfg)
        if error.startswith(_CLOCK_ERRORS)
    ]


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
