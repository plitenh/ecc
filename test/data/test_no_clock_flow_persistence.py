"""no-clock flow persistence and validation boundaries."""

from chipcompiler.data.workspace_config import (
    flow_no_clock,
    flow_section_from_flow_config,
    validate_flow_config,
)


def test_validate_flow_config_preserves_no_clock_and_folds_skips():
    section = validate_flow_config({"preset": "rtl2gds", "no_clock": True})
    assert section["no_clock"] is True
    assert "cts" in section["skip_steps"]
    assert "timing_optimization" in section["skip_steps"]


def test_flow_section_persists_inferred_no_clock_from_empty_clock():
    section = flow_section_from_flow_config(
        {"preset": "rtl2gds"},
        materials={"clock_port": ""},
    )
    assert section["no_clock"] is True
    assert "cts" in section["skip_steps"]


def test_flow_section_does_not_persist_no_clock_for_retained_clock():
    section = flow_section_from_flow_config(
        {"preset": "rtl2gds"},
        materials={"clock_port": "clk"},
    )
    assert "no_clock" not in section


def test_flow_no_clock_coerces_common_spellings():
    assert flow_no_clock({"no_clock": True}) is True
    assert flow_no_clock({"no_clock": "yes"}) is True
    assert flow_no_clock({"no_clock": "off"}) is False
