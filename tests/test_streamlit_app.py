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


def test_filters_survive_a_visit_to_the_planner():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    next(s for s in at.multiselect if s.label == "Investor segment").set_value(["Pension"]); at.run()
    at.radio(key="nav").set_value("Next Event Planner"); at.run()
    at.radio(key="nav").set_value("Executive summary"); at.run()
    assert not at.exception and metric(at, "Associated opportunities") == "6"


def test_firm_explorer_has_only_its_own_filters():
    at = run(lambda a: a.radio(key="nav").set_value("Firm explorer"))
    labels = [m.label for m in at.multiselect]
    assert labels == ["Event", "Tier", "Investor segment", "Region", "Stage"], labels  # Stage is the in-chart filter


def test_filters():
    base = run()
    assert metric(base, "Associated opportunities") == "37"
    cases = {"segment": multi("Investor segment", ["Pension"]), "fund": multi("Fund", ["Fund Beta"]),
             "senior": multi("Attendee seniority", ["senior"]), "outlier": tog("Exclude $650M outlier"),
             "both_senior": multi("Attendee seniority", ["senior", "non_senior"]),
             "two_segments": multi("Investor segment", ["Pension", "Insurance"]),
             "london": multi("Event", ["E002"]),
             "window": sel("Association window (days)", 30), "tentative": tog("Include tentative firm registrations as attendance")}
    got = {k: metric(run(f), "Associated opportunities") for k, f in cases.items()}
    assert got == {"segment": "6", "fund": "12", "senior": "12", "outlier": "37", "both_senior": "37", "two_segments": "12", "london": "13",
                   "window": "20", "tentative": "40"}, got
    print("streamlit filter results:", got)


def test_planner_reproduces_london():
    """Default dinner scenario (London's budget and tier mix) should land on London's actual 2026 result."""
    at = run(lambda a: a.radio(key="nav").set_value("Next Event Planner"))
    assert not at.multiselect, "page filters should be hidden on the planner tab"
    assert metric(at, "Associated opportunities (90d)") == "13"
    assert metric(at, "Cost per associated opp") == "$14K"


if __name__ == "__main__":
    test_planner_reproduces_london()
    test_firm_explorer_has_only_its_own_filters()
    test_filters_survive_a_visit_to_the_planner()
    test_filters(); print("streamlit app tests passed")
