"""Failure audit (protocol section 10).

Codes interpretable failure modes from belief trajectories so the Go/No-Go
decision rests on a stratified error profile rather than a single aggregate.
Operates on the fixed-evidence probability tensors [N, modes, T, K] (Mode A) and
on online per-case results (Mode C).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np


def audit_fixed(probs: np.ndarray, labels: np.ndarray, k: int = 5,
                conf_thresh: float = 0.5) -> Dict[str, float]:
    """probs [N, T, K] for a single disclosure order."""
    N, T, K = probs.shape
    top1_0 = probs[:, 0].argmax(1)
    top1_T = probs[:, -1].argmax(1)
    conf_T = probs[:, -1].max(1)
    topk0 = np.argsort(-probs[:, 0], axis=1)[:, :k]
    in_pool0 = (topk0 == labels[:, None]).any(1)

    wrong_pool = ~in_pool0                                   # (1) true not in top-k at t=0
    overconf_wrong = (top1_T != labels) & (conf_T >= conf_thresh)  # (3) high-conf wrong
    correct0 = top1_0 == labels
    lost = correct0 & (top1_T != labels)                       # correct -> wrong drift
    wrong0 = top1_0 != labels
    recovered = wrong0 & (top1_T == labels)

    # (6) support re-entry: missing top-k at t=0 but back in top-k at some later turn
    reentered = np.zeros(N, dtype=bool)
    for t in range(1, T):
        tk = np.argsort(-probs[:, t], axis=1)[:, :k]
        reentered |= (tk == labels[:, None]).any(1)
    reentry = wrong_pool & reentered

    denom_pool = max(wrong_pool.sum(), 1)
    return {
        "wrong_initial_pool_rate": float(wrong_pool.mean()),
        "reentry_given_wrong_pool": float(reentry.sum() / denom_pool),
        "overconfident_wrong_rate": float(overconf_wrong.mean()),
        "correct_to_wrong_rate": float(lost.sum() / max(correct0.sum(), 1)),
        "recovery_rate_wrong0": float(recovered.sum() / max(wrong0.sum(), 1)),
        "mean_final_conf_when_wrong": float(conf_T[top1_T != labels].mean()) if (top1_T != labels).any() else float("nan"),
    }


def audit_online(results: List[dict], disease_index: Dict[str, int], k: int = 3) -> Dict[str, float]:
    """results: list of run_episode dicts (Mode C)."""
    n = len(results)
    if n == 0:
        return {}
    wrong = [r for r in results if not r["correct"]]
    premature = [r for r in wrong if r["asks"] < r.get("budget", r["asks"])]
    topk_hit = 0
    for r in results:
        p = np.asarray(r["final_probs"])
        topk_hit += int(r["true_idx"] in np.argsort(-p)[:k])
    return {
        "n": n,
        "error_rate": float(len(wrong) / n),
        f"top{k}_miss_rate": float(1 - topk_hit / n),
        "mean_asks_when_wrong": float(np.mean([r["asks"] for r in wrong])) if wrong else float("nan"),
        "invalid_action_rate": float(sum(r["invalid"] for r in results) / n),
    }
