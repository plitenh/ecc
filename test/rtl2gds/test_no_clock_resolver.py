"""Core no-clock decision and skip-policy boundary tests."""

import pytest

from chipcompiler.rtl2gds import resolve_no_clock, resolve_skip_steps
from chipcompiler.rtl2gds.builder import NoClockDecision

_NO_CLOCK_SKIPS = ("preplace", "diff_opt", "diff_sizing", "cts", "timing_optimization")


def test_explicit_true_wins_over_clock_material():
    decision = resolve_no_clock({"no_clock": True}, materials={"clock_port": "clk"})

    assert decision == NoClockDecision(enabled=True, source="explicit")


def test_explicit_false_overrides_empty_clock_inference():
    decision = resolve_no_clock({"no_clock": False}, materials={"clock_port": ""})

    assert decision == NoClockDecision(enabled=False, source="off")


@pytest.mark.parametrize("clock_port", ["", "   "])
def test_empty_clock_infers_no_clock(clock_port):
    decision = resolve_no_clock({}, materials={"clock_port": clock_port})

    assert decision == NoClockDecision(enabled=True, source="inferred")


@pytest.mark.parametrize("clock_port", [None, 0, True, ["clk"]])
def test_non_string_clock_material_is_not_a_clock(clock_port):
    decision = resolve_no_clock({}, materials={"clock_port": clock_port})

    assert decision == NoClockDecision(enabled=True, source="inferred")


@pytest.mark.parametrize("materials", [{"clock_port": " clk "}, {"clock": "clk"}])
def test_clock_name_disables_inference(materials):
    assert resolve_no_clock({}, materials=materials) == NoClockDecision(
        enabled=False, source="off"
    )


def test_missing_materials_do_not_trigger_inference():
    assert resolve_no_clock({}) == NoClockDecision(enabled=False, source="off")


@pytest.mark.parametrize("flow_config", [{}, {"skip_steps": []}])
def test_inferred_no_clock_folds_clock_dependent_skips(flow_config):
    skips = resolve_skip_steps(flow_config, materials={"clock_port": ""})

    assert skips == _NO_CLOCK_SKIPS


def test_explicit_no_clock_folds_skips_and_preserves_requested_steps():
    skips = resolve_skip_steps(
        {"no_clock": True, "skip_steps": ["routing"]},
        materials={"clock_port": "clk"},
    )

    assert skips == (*_NO_CLOCK_SKIPS, "routing")


def test_explicit_false_disables_no_clock_skip_folding():
    skips = resolve_skip_steps(
        {"no_clock": False, "skip_steps": []},
        materials={"clock_port": ""},
    )

    assert skips == ()
