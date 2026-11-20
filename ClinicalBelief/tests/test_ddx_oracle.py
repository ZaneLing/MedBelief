"""SealedDDxEnvironment oracle behaviour (Ticket T02 tests)."""
from __future__ import annotations

import os
import sys

import numpy as np
from conftest import PROCESSED, SCHEMA_JSON, have_data

from cbh.schemas import Action


def _env(max_asks=6):
    from cbh.envs.ddxplus import SealedDDxEnvironment
    return SealedDDxEnvironment(os.path.join(PROCESSED, "validate.npz"), SCHEMA_JSON, max_asks=max_asks)


def test_reset_reveals_initial_evidence_only():
    if not have_data():
        print("SKIP"); return
    env = _env()
    obs = env.reset(env.case_ids[0])
    assert obs.turn == 0
    # only the initial evidence family atoms are observed at reset
    assert obs.info["atom_mask"].sum() > 0
    assert obs.info["asked_questions"] == []


def test_ask_reveals_whole_family():
    if not have_data():
        print("SKIP"); return
    env = _env()
    obs = env.reset(env.case_ids[0])
    before = obs.info["atom_mask"].sum()
    # pick a multi-member family (E_53 has 7 members)
    q = "E_53" if "ASK:E_53" in obs.legal_actions else [a for a in obs.legal_actions if a.startswith("ASK:")][0].split(":",1)[1]
    obs2 = env.step(Action(kind="ASK", target=q))
    after = obs2.info["atom_mask"].sum()
    assert after > before, "asking a family must reveal new atoms"
    assert obs2.remaining_budget == obs.remaining_budget - 1


def test_duplicate_ask_no_new_evidence():
    if not have_data():
        print("SKIP"); return
    env = _env()
    obs = env.reset(env.case_ids[0])
    q = [a for a in obs.legal_actions if a.startswith("ASK:")][0].split(":", 1)[1]
    o1 = env.step(Action(kind="ASK", target=q))
    m1 = o1.info["atom_mask"].copy(); v1 = o1.info["atom_val"].copy()
    o2 = env.step(Action(kind="ASK", target=q))
    assert o2.info["duplicate"] is True
    assert o2.evidence == []
    assert np.array_equal(o2.info["atom_mask"], m1)
    assert np.array_equal(o2.info["atom_val"], v1)


def test_budget_and_illegal_actions():
    if not have_data():
        print("SKIP"); return
    env = _env(max_asks=2)
    obs = env.reset(env.case_ids[0])
    qs = [a.split(":", 1)[1] for a in obs.legal_actions if a.startswith("ASK:")]
    env.step(Action(kind="ASK", target=qs[0]))
    env.step(Action(kind="ASK", target=qs[1]))
    # budget exhausted -> further ASK must raise
    try:
        env.step(Action(kind="ASK", target=qs[2]))
        raise AssertionError("expected budget-exhausted error")
    except ValueError:
        pass
    # illegal target
    env2 = _env()
    env2.reset(env2.case_ids[0])
    try:
        env2.step(Action(kind="ASK", target="NOT_A_QUESTION"))
        raise AssertionError("expected illegal-target error")
    except ValueError:
        pass


def test_diagnose_terminates():
    if not have_data():
        print("SKIP"); return
    env = _env()
    env.reset(env.case_ids[0])
    obs = env.step(Action(kind="DIAGNOSE", diagnosis="Influenza"))
    assert obs.done is True
    try:
        env.step(Action(kind="ASK", target="E_91"))
        raise AssertionError("episode should be done")
    except RuntimeError:
        pass


def test_unknown_vs_negative_distinct():
    if not have_data():
        print("SKIP"); return
    env = _env()
    obs = env.reset(env.case_ids[3])
    mask = obs.info["atom_mask"]; val = obs.info["atom_val"]
    # an unobserved atom (mask 0) is 'unknown'; a revealed zero (mask 1, val 0) is 'negative'
    assert (mask == 0).any(), "must have unknown atoms"
    # reveal a family and confirm some revealed atoms are negative (val 0, mask 1)
    q = [a.split(":", 1)[1] for a in obs.legal_actions if a.startswith("ASK:")][0]
    o2 = env.step(Action(kind="ASK", target=q))
    m, v = o2.info["atom_mask"], o2.info["atom_val"]
    assert ((m == 1) & (v == 0)).any() or ((m == 1) & (v == 1)).any()


if __name__ == "__main__":
    for fn in [test_reset_reveals_initial_evidence_only, test_ask_reveals_whole_family,
               test_duplicate_ask_no_new_evidence, test_budget_and_illegal_actions,
               test_diagnose_terminates, test_unknown_vs_negative_distinct]:
        fn(); print("ok:", fn.__name__)
