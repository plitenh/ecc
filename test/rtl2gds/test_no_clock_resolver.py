"""Core no-clock decision and skip-policy boundary tests."""


from chipcompiler.rtl2gds import resolve_no_clock, resolve_skip_steps


def test_explicit_true_wins_over_clock_material():
    decision = resolve_no_clock({"no_clock": True}, materials={"clock_port": "clk"})
    assert decision.enabled is True
    assert decision.source == "explicit"


def test_explicit_false_overrides_empty_clock_inference():
    decision = resolve_no_clock({"no_clock": False}, materials={"clock_port": ""})
    assert decision.enabled is False
    assert decision.source == "off"


def test_empty_clock_infers_no_clock():
    decision = resolve_no_clock({}, materials={"clock_port": ""})
    assert decision.enabled is True
    assert decision.source == "inferred"


def test_non_string_clock_material_is_not_a_clock():
    assert resolve_no_clock({}, materials={"clock_port": 0}).enabled is True
    assert resolve_no_clock({}, materials={"clock_port": True}).enabled is True


def test_clock_name_disables_inference():
    assert resolve_no_clock({}, materials={"clock_port": " clk "}).enabled is False


def test_no_clock_folds_clock_dependent_skips_without_explicit_list():
    skips = resolve_skip_steps({}, materials={"clock_port": ""})
    assert {"preplace", "diff_sizing", "cts", "diff_opt", "timing_optimization"} <= set(skips)


def test_no_clock_folds_clock_dependent_skips_into_explicit_empty_list():
    skips = resolve_skip_steps({"skip_steps": []}, materials={"clock_port": ""})
    assert {"preplace", "diff_sizing", "cts", "diff_opt", "timing_optimization"} <= set(skips)


def test_explicit_cts_skip_is_still_a_plain_chain_skip():
    assert "cts" in resolve_skip_steps({"skip_steps": ["cts"]})
