"""Fixed Expected-Information-Gain policy (section 5.2).

    a* = argmax_a [ H(b_t) - E_{o | H_t, a} H(b_{t+1}) ]

The predictive outcome distribution comes ONLY from a fit-train Naive-Bayes
observation model (`p1[a,d] = P(atom a = 1 | d)`); the policy never queries a
test patient's hidden answers. Family EIG is approximated by summing a per-atom
binary EIG (atoms treated as conditionally independent given the disease, the
same deliberate simplification as the NB belief), which keeps the computation
tractable over 972 atoms x 209 families.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from ..schemas import Action, BeliefState, PublicObservation


def _entropy(p: np.ndarray) -> float:
    p = np.clip(p, 1e-12, 1)
    return float(-(p * np.log(p)).sum())


class EIGPolicy:
    version = "eig_v1"

    def __init__(self, p1: np.ndarray, family_atoms: Dict[str, np.ndarray],
                 cost_per_ask: float = 0.0, cost_aware: bool = False):
        self.p1 = p1                      # [atoms, K]  P(atom=1 | disease)
        self.p0 = 1.0 - p1
        self.family_atoms = family_atoms
        self.cost_per_ask = cost_per_ask
        self.cost_aware = cost_aware

    def family_eig(self, b: np.ndarray, mask: np.ndarray, qid: str) -> float:
        idx = self.family_atoms[qid]
        # only atoms not yet observed contribute new information
        idx = idx[mask[idx] == 0]
        if len(idx) == 0:
            return 0.0
        p1 = self.p1[idx]                 # [m, K]
        p0 = self.p0[idx]
        h0 = _entropy(b)
        total = 0.0
        for j in range(len(idx)):
            q1 = float(b @ p1[j])         # P(atom=1)
            q1 = min(max(q1, 1e-9), 1 - 1e-9)
            post1 = b * p1[j]
            post1 = post1 / post1.sum()
            post0 = b * p0[j]
            post0 = post0 / post0.sum()
            eh = q1 * _entropy(post1) + (1 - q1) * _entropy(post0)
            total += (h0 - eh)
        return total

    def act(self, obs: PublicObservation, belief: BeliefState) -> Action:
        b = np.asarray(belief.probs, dtype=np.float64)
        mask = obs.info["atom_mask"]
        if obs.remaining_budget <= 0:
            return Action(kind="DIAGNOSE", diagnosis=belief.diseases[int(np.argmax(b))])
        best_q, best_eig = None, -1e9
        asked = set(obs.info.get("asked_questions", []))
        for q in obs.legal_actions:
            if not q.startswith("ASK:"):
                continue
            qid = q.split(":", 1)[1]
            if qid in asked:
                continue
            eig = self.family_eig(b, mask, qid)
            if self.cost_aware:
                eig -= self.cost_per_ask
            if eig > best_eig:
                best_eig, best_q = eig, qid
        # stop when no informative question remains
        if best_q is None or best_eig <= 1e-6:
            return Action(kind="DIAGNOSE", diagnosis=belief.diseases[int(np.argmax(b))])
        return Action(kind="ASK", target=best_q)
