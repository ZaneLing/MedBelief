"""Metric numeric assertions on toy examples (Ticket T08)."""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from cbh.eval import belief as M


def test_nll_brier_known_values():
    # 2 classes, perfect prediction on one, wrong on other
    probs = np.array([[0.9, 0.1], [0.2, 0.8]])
    labels = np.array([0, 0])
    nll = M.nll(probs, labels)
    exp = -(np.log(0.9) + np.log(0.2)) / 2
    assert abs(nll - exp) < 1e-9
    brier = M.brier(probs, labels)
    exp_b = ((0.9 - 1) ** 2 + (0.1 - 0) ** 2 + (0.2 - 1) ** 2 + (0.8 - 0) ** 2) / 2
    assert abs(brier - exp_b) < 1e-9


def test_topk_and_mrr():
    probs = np.array([[0.1, 0.6, 0.3], [0.7, 0.2, 0.1]])
    labels = np.array([2, 0])
    assert M.topk_accuracy(probs, labels, 1) == 0.5   # only 2nd correct at top1
    assert M.topk_accuracy(probs, labels, 2) == 1.0   # both in top2
    # ranks: label2 for row0 is rank2 -> 1/2 ; label0 row1 rank1 -> 1
    assert abs(M.mrr(probs, labels) - (0.5 + 1.0) / 2) < 1e-9


def test_js_divergence_bounds():
    p = np.array([0.5, 0.5])
    assert abs(M.js_divergence(p, p)) < 1e-12
    q = np.array([1e-12, 1.0])
    js = M.js_divergence(p, q)
    assert 0 < js <= np.log(2) + 1e-9


def test_ece_perfect_calibration():
    # predictions at 0.8 confidence that are correct 80% of the time -> low ECE
    rng = np.random.default_rng(0)
    n = 5000
    probs = np.zeros((n, 2))
    labels = np.zeros(n, dtype=int)
    for i in range(n):
        probs[i, 0] = 0.8; probs[i, 1] = 0.2
        labels[i] = 0 if rng.random() < 0.8 else 1
    ece = M.expected_calibration_error(probs, labels, n_bins=10)["ece"]
    assert ece < 0.05


def test_bootstrap_ci_contains_point():
    vals = [np.array([1.0, 1.1, 0.9]) for _ in range(50)]
    mean, lo, hi = M.patient_bootstrap_ci(vals, n_boot=500, seed=0)
    assert abs(mean - 1.0) < 1e-9
    assert lo <= mean <= hi


def test_paired_diff_sign():
    a = [np.array([2.0, 2.0]) for _ in range(30)]  # worse (higher NLL)
    b = [np.array([1.0, 1.0]) for _ in range(30)]  # better
    d = M.paired_bootstrap_diff(a, b, n_boot=500, seed=0)
    assert d["diff"] > 0
    assert d["ci_lo"] > 0


def test_recovery_and_reentry_shapes():
    N, T, K = 20, 4, 5
    rng = np.random.default_rng(1)
    seq = rng.dirichlet(np.ones(K), size=(N, T))
    labels = rng.integers(0, K, N)
    r = M.recovery_rate(seq, labels)
    re = M.reentry_rate(seq, labels, k=2)
    assert "recovery_rate" in r and "reentry_rate" in re


if __name__ == "__main__":
    for fn in [test_nll_brier_known_values, test_topk_and_mrr, test_js_divergence_bounds,
               test_ece_perfect_calibration, test_bootstrap_ci_contains_point,
               test_paired_diff_sign, test_recovery_and_reentry_shapes]:
        fn(); print("ok:", fn.__name__)
