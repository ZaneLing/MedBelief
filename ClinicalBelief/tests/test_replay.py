"""Replay determinism (Gate 0): same case/seed/action-sequence -> same trajectory."""
from __future__ import annotations

import os
import sys

import numpy as np
from conftest import PROCESSED, SCHEMA_JSON, have_data

from cbh.envs.ddxplus import SealedDDxEnvironment
from cbh.schemas import Action


def _traj(env, cid, actions):
    obs = env.reset(cid)
    trace = [(obs.turn, tuple(obs.info["atom_val"].tolist()[:5]), obs.remaining_budget)]
    for a in actions:
        obs = env.step(a)
        trace.append((obs.turn, tuple(obs.info["atom_val"].tolist()[:5]),
                      obs.remaining_budget, tuple(int(x) for x in obs.info["atom_mask"][:5]),
                      obs.info["duplicate"]))
    return trace


def test_replay_deterministic():
    if not have_data():
        print("SKIP"); return
    cid = SealedDDxEnvironment(os.path.join(PROCESSED, "validate.npz"), SCHEMA_JSON).case_ids[5]
    acts = [Action(kind="ASK", target="E_53"), Action(kind="ASK", target="E_91"),
            Action(kind="ASK", target="E_53"), Action(kind="DIAGNOSE", diagnosis="X")]
    e1 = SealedDDxEnvironment(os.path.join(PROCESSED, "validate.npz"), SCHEMA_JSON)
    e2 = SealedDDxEnvironment(os.path.join(PROCESSED, "validate.npz"), SCHEMA_JSON)
    t1 = _traj(e1, cid, acts)
    t2 = _traj(e2, cid, acts)
    assert t1 == t2, "trajectory must be reproducible"


def test_fixed_evidence_order_deterministic():
    if not have_data():
        print("SKIP"); return
    import json
    from cbh.beliefs.build import load_schema, make_generator
    from cbh.data.ddxplus_convert import load_split
    schema = load_schema(SCHEMA_JSON)
    fit = load_split(os.path.join(PROCESSED, "fit.npz"))
    gen = make_generator(schema, {k: v[:2000] for k, v in fit.items()}, len(schema["diseases"]))
    o1 = gen.order(123, "random_valid")
    o2 = gen.order(123, "random_valid")
    assert o1 == o2
    # greedy order is stable and sorted by score descending
    g1 = gen.order(1, "greedy_eig_valid")
    g2 = gen.order(1, "greedy_eig_valid")
    assert g1 == g2
    scores = [gen.family_scores.get(q, 0) for q in g1]
    assert all(scores[i] >= scores[i + 1] - 1e-12 for i in range(len(scores) - 1))


if __name__ == "__main__":
    for fn in [test_replay_deterministic, test_fixed_evidence_order_deterministic]:
        fn(); print("ok:", fn.__name__)
