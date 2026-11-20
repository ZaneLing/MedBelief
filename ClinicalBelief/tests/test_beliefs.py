"""Belief model invariants (Tickets T05-T07)."""
from __future__ import annotations

import os
import sys

import numpy as np
from conftest import PROCESSED, SCHEMA_JSON, have_data, tiny_nb

from cbh.agents.runner import obs_from_prefix
from cbh.data.ddxplus_convert import load_split
from cbh.schemas import BeliefState


def _val_mask():
    v = np.zeros(972, dtype=np.int8); m = np.zeros(972, dtype=np.int8)
    return v, m


def test_nb_probs_valid():
    if not have_data():
        print("SKIP"); return
    nb, schema = tiny_nb()
    v, m = _val_mask()
    obs = obs_from_prefix("c", 0, v, m, 40, 0)
    st = nb.reset(obs)
    p = np.asarray(st.probs)
    assert abs(p.sum() - 1.0) < 1e-6
    assert (p > 0).all()
    assert len(p) == 49


def test_nb_duplicate_invariance():
    """Re-observing the same evidence must not change the NB belief (no
    double-counting of likelihood)."""
    if not have_data():
        print("SKIP"); return
    nb, schema = tiny_nb()
    val = np.zeros(972, dtype=np.int8); mask = np.zeros(972, dtype=np.int8)
    val[10] = 1; mask[10] = 1; val[200] = 1; mask[200] = 1
    obs = obs_from_prefix("c", 1, val, mask, 55, 1)
    st1 = nb.reset(obs)
    # same observed SET again (simulating a duplicate question) -> identical
    st2 = nb.update(st1, obs)
    assert np.allclose(st1.probs, st2.probs, atol=1e-9)


def test_recompute_ignores_prev_state():
    """The recompute classifier depends only on the current observation, not on
    the previous belief (it is recomputed from scratch each turn)."""
    if not have_data():
        print("SKIP"); return
    path = os.path.join(os.path.dirname(PROCESSED), "..", "models", "mlp.pt")
    path = os.path.abspath(os.path.join(PROCESSED, "..", "..", "models", "mlp.pt"))
    if not os.path.exists(path):
        print("SKIP: mlp not trained"); return
    from cbh.beliefs.recompute import _TorchRecompute
    m = _TorchRecompute.load(path)
    val = np.zeros(972, dtype=np.int8); mask = np.zeros(972, dtype=np.int8)
    val[5] = 1; mask[5] = 1
    obs = obs_from_prefix("c", 1, val, mask, 30, 0)
    prev = BeliefState(diseases=m.diseases, probs=[1.0 / 49] * 49)
    a = np.asarray(m.update(prev, obs).probs)
    prev2 = BeliefState(diseases=m.diseases, probs=[0.9] + [0.1 / 48] * 48)
    b = np.asarray(m.update(prev2, obs).probs)
    assert np.allclose(a, b, atol=1e-9), "recompute must ignore previous belief"


def test_neural_numerical_stability():
    if not have_data():
        print("SKIP"); return
    path = os.path.abspath(os.path.join(PROCESSED, "..", "..", "models", "neural.pt"))
    if not os.path.exists(path):
        print("SKIP: neural not trained"); return
    import json
    from cbh.beliefs.neural_update import BeliefNeuralUpdater
    schema = json.load(open(SCHEMA_JSON))
    nu = BeliefNeuralUpdater(schema["diseases"], schema["total_atoms"])
    nu.load(path)
    val = np.zeros(schema["total_atoms"], dtype=np.int8)
    mask = np.zeros(schema["total_atoms"], dtype=np.int8)
    obs0 = obs_from_prefix("c", 0, val, mask, 20, 0)
    st = nu.reset(obs0)
    assert np.isfinite(st.probs).all()
    assert abs(sum(st.probs) - 1.0) < 1e-6
    # several updates with growing evidence must stay finite and normalized
    for t in range(1, 6):
        val = val.copy(); mask = mask.copy()
        val[t * 3] = 1; mask[t * 3] = 1
        obs = obs_from_prefix("c", t, val, mask, 20, 0)
        st = nu.update(st, obs)
        assert np.isfinite(st.probs).all()
        assert abs(sum(st.probs) - 1.0) < 1e-6


if __name__ == "__main__":
    for fn in [test_nb_probs_valid, test_nb_duplicate_invariance,
               test_recompute_ignores_prev_state, test_neural_numerical_stability]:
        fn(); print("ok:", fn.__name__)
