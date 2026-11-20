"""Belief metrics + patient-level statistics (Ticket T08).

All proper scoring rules operate per turn. Confidence intervals use a
*patient-level* stratified bootstrap (section 7.4): the resampling unit is the
patient, never the (patient, turn) pair, because multiple reveal orders/turns
for one patient are repeated measures.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


def nll(probs: np.ndarray, labels: np.ndarray) -> float:
    """probs [N,K], labels [N] -> mean negative log-likelihood."""
    p = np.clip(probs[np.arange(len(labels)), labels], 1e-12, 1.0)
    return float(-np.log(p).mean())


def brier(probs: np.ndarray, labels: np.ndarray) -> float:
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(labels)), labels] = 1.0
    return float(((probs - onehot) ** 2).sum(1).mean())


def topk_accuracy(probs: np.ndarray, labels: np.ndarray, k: int) -> float:
    idx = np.argsort(-probs, axis=1)[:, :k]
    hit = (idx == labels[:, None]).any(1)
    return float(hit.mean())


def mrr(probs: np.ndarray, labels: np.ndarray) -> float:
    order = np.argsort(-probs, axis=1)
    ranks = (order == labels[:, None]).argmax(1) + 1
    return float((1.0 / ranks).mean())


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> Dict[str, float]:
    conf = probs.max(1)
    pred = probs.argmax(1)
    acc = (pred == labels).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        m = (conf > edges[i]) & (conf <= edges[i + 1]) if i > 0 else (conf >= edges[0]) & (conf <= edges[1])
        if m.sum() == 0:
            continue
        ece += m.mean() * abs(acc[m].mean() - conf[m].mean())
    return {"ece": float(ece), "mean_conf": float(conf.mean()), "acc": float(acc.mean())}


def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p = np.clip(p, 1e-12, 1)
    q = np.clip(q, 1e-12, 1)
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    def kl(a, b):
        return float((a * np.log(a / b)).sum())
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def js_divergence_batch(P: np.ndarray, Q: np.ndarray) -> np.ndarray:
    P = np.clip(P, 1e-12, 1); P /= P.sum(1, keepdims=True)
    Q = np.clip(Q, 1e-12, 1); Q /= Q.sum(1, keepdims=True)
    M = 0.5 * (P + Q)
    kl = lambda a, b: (a * np.log(a / b)).sum(1)
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def recovery_rate(probs_seq: np.ndarray, labels: np.ndarray, conf_thresh: float = 0.5,
                  k: int = 1) -> Dict[str, float]:
    """probs_seq [N, T, K]. Among patients whose top-1 was WRONG at t=0 but
    reached >= conf_thresh at some point, fraction correct at final turn.
    Also reports the adverse correct->wrong direction."""
    N, T, K = probs_seq.shape
    top1_0 = probs_seq[:, 0].argmax(1)
    top1_T = probs_seq[:, -1].argmax(1)
    wrong0 = top1_0 != labels
    confT = probs_seq[:, -1].max(1)
    denom = wrong0 & (confT >= conf_thresh)
    recovered = denom & (top1_T == labels)
    right0 = top1_0 == labels
    lost = right0 & (top1_T != labels)
    return {
        "n_wrong0_highconf": int(denom.sum()),
        "recovery_rate": float(recovered.sum() / denom.sum()) if denom.sum() else float("nan"),
        "correct_to_wrong_rate": float(lost.sum() / right0.sum()) if right0.sum() else float("nan"),
    }


def reentry_rate(probs_seq: np.ndarray, labels: np.ndarray, k: int = 5) -> Dict[str, float]:
    """If the true disease is NOT in top-k at t=0, does it re-enter top-k later?"""
    N, T, K = probs_seq.shape
    topk0 = np.argsort(-probs_seq[:, 0], axis=1)[:, :k]
    missing0 = ~(topk0 == labels[:, None]).any(1)
    reentered = np.zeros(N, dtype=bool)
    for t in range(1, T):
        topkt = np.argsort(-probs_seq[:, t], axis=1)[:, :k]
        reentered |= (topkt == labels[:, None]).any(1)
    denom = missing0
    return {
        "n_missing0_topk": int(denom.sum()),
        "reentry_rate": float((reentered & denom).sum() / denom.sum()) if denom.sum() else float("nan"),
    }


def patient_bootstrap_ci(values_per_patient: Sequence[np.ndarray], n_boot: int = 2000,
                         seed: int = 0, strata: Optional[np.ndarray] = None,
                         alpha: float = 0.05) -> Tuple[float, float, float]:
    """values_per_patient: one array of per-turn values for each patient.
    Returns (mean, lo, hi) resampling whole patients (stratified if strata given).
    """
    arrs = [np.asarray(v, dtype=float).ravel() for v in values_per_patient]
    if not arrs:
        return float("nan"), float("nan"), float("nan")
    point = float(np.concatenate(arrs).mean())
    rng = np.random.default_rng(seed)
    n = len(arrs)
    if strata is None:
        strata = np.zeros(n, dtype=int)
    strata = np.asarray(strata)
    groups: Dict[int, np.ndarray] = {}
    for s in np.unique(strata):
        groups[int(s)] = np.where(strata == s)[0]
    boots = np.empty(n_boot)
    for b in range(n_boot):
        picks: List[np.ndarray] = []
        for s, idxs in groups.items():
            sel = rng.choice(idxs, size=len(idxs), replace=True)
            picks.extend([arrs[i] for i in sel])
        boots[b] = np.concatenate(picks).mean() if picks else point
    lo = float(np.quantile(boots, alpha / 2))
    hi = float(np.quantile(boots, 1 - alpha / 2))
    return point, lo, hi


def paired_bootstrap_diff(a_per_patient: Sequence[np.ndarray], b_per_patient: Sequence[np.ndarray],
                          n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> Dict[str, float]:
    """Paired (same patients) bootstrap of mean(a)-mean(b); lower is better for
    NLL/Brier. Returns diff, CI, and one-sided p that a<b."""
    a = [np.asarray(x, float).ravel() for x in a_per_patient]
    b = [np.asarray(x, float).ravel() for x in b_per_patient]
    assert len(a) == len(b)
    diff_point = float(np.concatenate(a).mean() - np.concatenate(b).mean())
    rng = np.random.default_rng(seed)
    n = len(a)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        ai = np.concatenate([a[j] for j in idx])
        bi = np.concatenate([b[j] for j in idx])
        diffs[i] = ai.mean() - bi.mean()
    lo = float(np.quantile(diffs, alpha / 2))
    hi = float(np.quantile(diffs, 1 - alpha / 2))
    p = float((diffs >= 0).mean())  # one-sided: prob a worse-or-equal than b
    return {"diff": diff_point, "ci_lo": lo, "ci_hi": hi, "p_a_ge_b": p}


def summarize(probs_seq: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    """probs_seq [N,T,K] -> per-turn-averaged headline metrics."""
    N, T, K = probs_seq.shape
    flat = probs_seq.reshape(N * T, K)
    flaty = np.repeat(labels, T)
    out = {
        "nll": nll(flat, flaty),
        "brier": brier(flat, flaty),
        "top1": topk_accuracy(flat, flaty, 1),
        "top3": topk_accuracy(flat, flaty, 3),
        "top5": topk_accuracy(flat, flaty, 5),
        "mrr": mrr(flat, flaty),
        "final_nll": nll(probs_seq[:, -1], labels),
        "final_top1": topk_accuracy(probs_seq[:, -1], labels, 1),
        "final_top3": topk_accuracy(probs_seq[:, -1], labels, 3),
        "mean_entropy": float(-(probs_seq * np.log(np.clip(probs_seq, 1e-12, 1))).sum(-1).mean()),
    }
    out.update({f"ece_{k}": v for k, v in expected_calibration_error(flat, flaty).items()})
    return out
