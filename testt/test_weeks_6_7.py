"""Weeks 6-7 tests. Run from the project folder:  pytest -q tests
Covers: dataset loading, grounding (every plan item is a real dataset id with its dataset price),
accepted-only totals, the three budget-recovery buttons, and the 37 prompts of the test set."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from cases_weeks_6_7 import CASES, S, ALEX, p
import planner as P

def test_dataset_loads_all_200_rows():
    assert len(P.ITEMS) == 200
    assert {i["city"] for i in P.ITEMS} == {"Cairo", "Alexandria", "Luxor", "Aswan", "Dahab"}

@pytest.mark.parametrize("c", CASES, ids=[c[0] for c in CASES])
def test_prompt(c):
    cid, prompt, persona, typ, pr, exp, setup, step, check = c
    s = S()
    if setup: setup(s)
    r = step(s)
    assert check(r, s), f"{cid}: {r.get('reply')}"

def test_plan_items_are_grounded_in_dataset():
    s = S(); r = s.chat(ALEX)
    for i in p(r)["items"]:
        d = P.BY_ID[i["item_id"]]
        assert i["price_egp"] == d["price_egp"] and i["name"] == d["name"]

def test_totals_count_only_accepted_items():
    s = S(); r = s.chat(ALEX)
    assert p(r)["total_egp"] == 0 and p(r)["proposed_egp"] == 1151
    r = s.act("accept", item_id=p(r)["items"][0]["item_id"])
    assert p(r)["total_egp"] == p(r)["accepted_egp"] == 300
    assert p(r)["left_egp"] == 1800 - 300
    assert p(r)["accepted_egp"] + p(r)["proposed_egp"] == p(r)["all_items_egp"]
