"""No-clock flow persistence and validation boundaries."""

import pytest

from chipcompiler.data.types import SkippableStepEnum
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
