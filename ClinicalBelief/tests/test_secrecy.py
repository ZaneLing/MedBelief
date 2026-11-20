"""Secrecy / no-leakage tests (Gate 0).

Asserts the sealed environment never exposes the pathology label, the full
ground-truth atom vector, or un-revealed evidence through any public channel.
"""
from __future__ import annotations

import numpy as np
from conftest import PROCESSED, SCHEMA_JSON, have_data

import os
import sys


def _env(max_asks=6):
    from cbh.envs.ddxplus import SealedDDxEnvironment
    return SealedDDxEnvironment(os.path.join(PROCESSED, "validate.npz"), SCHEMA_JSON, max_asks=max_asks)


def test_observation_has_no_hidden_fields():
    if not have_data():
        print("SKIP: no data")
        return
    env = _env()
    cid = env.case_ids[0]
    obs = env.reset(cid)
    blob = repr(obs.info) + repr(obs.evidence) + repr(obs.legal_actions)
    gt = env.ground_truth(cid)
    assert "pathology" not in blob.lower() or gt["pathology"].lower() not in blob.lower()
    # the true label string must not appear anywhere in the public observation
    assert gt["pathology"] not in blob
    # atom_val must be zero wherever mask is zero (no future evidence leak)
    val = obs.info["atom_val"]; mask = obs.info["atom_mask"]
    assert np.all(val[mask == 0] == 0), "unobserved atoms must be 0"


def test_no_full_truth_leak_after_asks():
    if not have_data():
        print("SKIP: no data")
        return
    env = _env(max_asks=3)
    cid = env.case_ids[1]
    obs = env.reset(cid)
    gt = env.ground_truth(cid)
    for _ in range(3):
        asks = [a for a in obs.legal_actions if a.startswith("ASK:")]
        obs = env.step(type("A", (), {"kind": "ASK", "target": asks[0].split(":", 1)[1], "diagnosis": None})())
        val = obs.info["atom_val"]; mask = obs.info["atom_mask"]
        # revealed values must equal ground truth; unrevealed must be 0
        assert np.all(val[mask == 1] == gt["atoms"][mask == 1])
        assert np.all(val[mask == 0] == 0)
        # the public state must never equal the full hidden vector unless fully revealed
        assert not np.array_equal(val.astype(np.int8), gt["atoms"]) or mask.all()


def test_ground_truth_only_via_evaluator():
    if not have_data():
        print("SKIP: no data")
        return
    env = _env()
    # PublicObservation has no attribute carrying the label index
    obs = env.reset(env.case_ids[2])
    for attr in ("pathology", "label", "pathology_idx", "gt", "truth"):
        assert not hasattr(obs, attr)
    assert "pathology_idx" not in obs.info and "atoms" not in obs.info


if __name__ == "__main__":
    for fn in [test_observation_has_no_hidden_fields, test_no_full_truth_leak_after_asks,
               test_ground_truth_only_via_evaluator]:
        fn(); print("ok:", fn.__name__)
