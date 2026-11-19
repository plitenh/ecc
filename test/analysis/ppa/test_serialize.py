from chipcompiler.analysis.ppa import (
    PpaStage,
    PpaStatus,
    csv_header,
    escape_field,
    missing_row,
    normalize_corner,
    row_to_csv,
    serialize_csv,
)


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


def test_serialize_csv_keeps_empty_columns(tmp_path):
    rows = [
        missing_row("gcd", PpaStage.POWER, "TYP/TYPICAL", "total_power", "mW"),
    ]
    assert serialize_csv(rows) == (
        "workspace,stage,corner,metric,value,unit,status\n"
        "gcd,power,TYP/TYPICAL,total_power,,mW,unavailable\n"
    )
