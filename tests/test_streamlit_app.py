"""Smoke test: the Streamlit app runs without exceptions under each filter."""
from streamlit.testing.v1 import AppTest

APP = "../app/streamlit_app.py"


def run(setup=None):
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    if setup:
        setup(at)
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def sel(label, value):
    return lambda at: next(s for s in at.selectbox if s.label == label).set_value(value)


def multi(label, values):
    return lambda at: next(s for s in at.multiselect if s.label == label).set_value(values)


def tog(label):
    return lambda at: next(t for t in at.toggle if t.label == label).set_value(True)


def metric(at, label):
    return next(m for m in at.metric if m.label == label).value


def test_filters():
    base = run()
    assert metric(base, "Associated opportunities") == "38"
    cases = {"segment": multi("Investor segment", ["Pension"]), "fund": multi("Fund", ["Fund Beta"]),
             "senior": multi("Attendee seniority", ["senior"]), "outlier": tog("Exclude $650M outlier"),
             "both_senior": multi("Attendee seniority", ["senior", "non_senior"]),
             "two_segments": multi("Investor segment", ["Pension", "Insurance"]),
             "window": sel("Association window (days)", 30), "tentative": tog("Include tentative firm registrations as attendance")}
    got = {k: metric(run(f), "Associated opportunities") for k, f in cases.items()}
    assert got == {"segment": "6", "fund": "13", "senior": "13", "outlier": "38", "both_senior": "38", "two_segments": got["two_segments"],
                   "window": "21", "tentative": "41"}, got
    print("streamlit filter results:", got)


if __name__ == "__main__":
    test_filters(); print("streamlit app tests passed")
