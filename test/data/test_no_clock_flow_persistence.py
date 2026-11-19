"""No-clock flow persistence and validation boundaries."""

import pytest

from chipcompiler.data import create_workspace, load_workspace
from chipcompiler.data.types import SkippableStepEnum
from chipcompiler.data.workspace import build_dynamic_flow_data
from chipcompiler.data.workspace_config import (
    flow_no_clock,
    flow_section_from_flow_config,
    validate_flow_config,
)

_NO_CLOCK_SKIPS = [
    SkippableStepEnum.PREPLACE.value,
    SkippableStepEnum.DIFF_OPT.value,
    SkippableStepEnum.DIFF_SIZING.value,
    SkippableStepEnum.CTS.value,
    SkippableStepEnum.TIMING_OPT.value,
]


def test_build_dynamic_flow_data_infers_no_clock_from_materials():
    flow_data = build_dynamic_flow_data(
        {"preset": "rtl2gds"}, materials={"clock_port": ""}
    )

    step_names = [step["name"] for step in flow_data["steps"]]
    assert "synthesis" in step_names
    assert set(step_names).isdisjoint(_NO_CLOCK_SKIPS)


def test_create_workspace_persists_inferred_no_clock(
    tmp_path, minimal_ics55_pdk_factory, default_ics55_parameters
):
    pdk_root = minimal_ics55_pdk_factory(tmp_path / "ics55")
    rtl_path = tmp_path / "gcd.v"
    rtl_path.write_text("module gcd(output y); assign y = 1'b0; endmodule\n")
    workspace_dir = tmp_path / "workspace"

    workspace = create_workspace(
        directory=workspace_dir,
        origin_def="",
        origin_verilog=rtl_path,
        pdk="ics55",
        parameters={**default_ics55_parameters, "clock": ""},
        pdk_root=pdk_root,
        flow_config={"preset": "rtl2gds"},
    )

    assert workspace is not None
    persisted = load_workspace(str(workspace_dir))
    step_names = [step["name"] for step in persisted.flow.steps()]
    assert set(step_names).isdisjoint(_NO_CLOCK_SKIPS)
    assert persisted.parameters.data["_flow"] == {
        "preset": "rtl2gds",
        "no_clock": True,
        "skip_steps": _NO_CLOCK_SKIPS,
    }


def test_validate_flow_config_preserves_no_clock_and_folds_skips():
    section = validate_flow_config({"preset": "rtl2gds", "no_clock": True})

    assert section == {
        "preset": "rtl2gds",
        "no_clock": True,
        "skip_steps": _NO_CLOCK_SKIPS,
    }


def test_flow_section_persists_inferred_no_clock_from_empty_clock():
    flow_config = {"preset": "rtl2gds"}

    section = flow_section_from_flow_config(flow_config, materials={"clock_port": ""})

    assert section == {
        "preset": "rtl2gds",
        "no_clock": True,
        "skip_steps": _NO_CLOCK_SKIPS,
    }
    assert flow_config == {"preset": "rtl2gds"}


def test_flow_section_does_not_persist_no_clock_for_retained_clock():
    section = flow_section_from_flow_config(
        {"preset": "rtl2gds"},
        materials={"clock_port": "clk"},
    )

    assert section == {"preset": "rtl2gds"}


def test_flow_section_does_not_infer_no_clock_without_materials():
    assert flow_section_from_flow_config({"preset": "rtl2gds"}) == {"preset": "rtl2gds"}


def test_explicit_no_clock_false_does_not_persist_or_infer():
    section = flow_section_from_flow_config(
        {"preset": "rtl2gds", "no_clock": False},
        materials={"clock_port": ""},
    )

    assert section == {"preset": "rtl2gds"}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        (1.0, True),
        (0.0, False),
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        (" YES ", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
        ("other", False),
    ],
)
def test_flow_no_clock_coerces_common_spellings(value, expected):
    assert flow_no_clock({"no_clock": value}) is expected
