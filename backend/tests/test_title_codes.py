from app.sales.title_codes import coded_label, guess


def test_codes_and_labels():
    """Issues are listed the way BMI names them (Craig, feedback #25)."""
    assert guess("obh", "OnBoard Hospitality (OBH)") == "OBH"
    assert guess("tbtm", "The Business Travel Magazine (TBTM)") == "TBTM"
    assert guess("new-thing", "Brand New Weekly") == "BNW"
    assert coded_label("OBH", "108") == "OBH108"
    assert coded_label("OBH Web", "Jan 2027") == "OBH Web Jan 2027"
    assert coded_label(None, "108") == "Issue 108"
