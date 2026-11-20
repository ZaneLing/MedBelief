"""FixedEvidenceGenerator + prefix builder (Ticket T04).

Produces deterministic evidence-reveal orders for Mode A (fixed evidence / RQ1)
and offline prefix states used to train the recompute classifier and the neural
belief updater. Every derived order inherits the patient's official split: the
generator only ever reorders *within* a patient, so a patient (and all of its
order/counterfactual variants) stays in the partition it came from.

Three orders (section 6.1):
  * random_valid        -- uniformly random permutation of question families
  * greedy_eig_valid    -- information-first, by a Naive-Bayes discriminativeness
                           proxy for each family (fit-train only)
  * reverse_eig_valid   -- reverse of greedy (least-informative first)

The EIG proxy is a *static* per-family score (prior-weighted across-disease
variance of P(atom=1|d)); it is only used to fix a disclosure order, never to
peek at a test patient's hidden answers.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

import numpy as np


def load_family_atoms(schema: Dict) -> Dict[str, np.ndarray]:
    """qid -> concatenated atom indices of all member evidences."""
    fam: Dict[str, np.ndarray] = {}
    for q, eids in schema["question_to_evidences"].items():
        idx: List[int] = []
        for e in eids:
            enc = schema["encodings"][e]
            idx.extend(range(enc["start"], enc["start"] + enc["count"]))
        fam[q] = np.asarray(idx, dtype=np.int32)
    return fam


class FixedEvidenceGenerator:
    def __init__(self, schema: Dict, family_scores: Optional[Dict[str, float]] = None):
        self.schema = schema
        self.fam_atoms = load_family_atoms(schema)
        self.question_ids: List[str] = sorted(
            self.fam_atoms.keys(), key=lambda q: int(q.split("_")[1])
        )
        self.family_scores = family_scores or {}

    @staticmethod
    def compute_family_scores(fit_atoms: np.ndarray, fit_path: np.ndarray,
                              schema: Dict, K: int) -> Dict[str, float]:
        """Prior-weighted across-disease variance of P(atom=1|d) per family."""
        fam_atoms = load_family_atoms(schema)
        prior = np.bincount(fit_path, minlength=K).astype(np.float64)
        prior /= prior.sum()
        p1 = np.zeros((fit_atoms.shape[1], K))
        for d in range(K):
            m = fit_path == d
            if m.sum() == 0:
                p1[:, d] = fit_atoms.mean(0)
            else:
                p1[:, d] = fit_atoms[m].astype(np.float64).mean(0)
        scores: Dict[str, float] = {}
        for q, idx in fam_atoms.items():
            if len(idx) == 0:
                scores[q] = 0.0
                continue
            sub = p1[idx]                       # [atoms_in_family, K]
            mean_d = (sub * prior[None, :]).sum(1)
            var_d = (prior[None, :] * (sub - mean_d[:, None]) ** 2).sum(1)
            scores[q] = float(np.nan_to_num(var_d).sum())
        return scores

    def order(self, patient_seed: int, mode: str) -> List[str]:
        rng = np.random.default_rng(patient_seed)
        if mode == "random_valid":
            o = list(self.question_ids)
            rng.shuffle(o)
            return o
        if mode in ("greedy_eig_valid", "reverse_eig_valid"):
            o = sorted(self.question_ids, key=lambda q: self.family_scores.get(q, 0.0),
                       reverse=(mode == "greedy_eig_valid"))
            return o
        raise ValueError(f"unknown order mode {mode}")

    # -- prefix construction -------------------------------------------
    def initial_state(self, gt_atoms: np.ndarray, init_ev_idx: int,
                      total_atoms: int) -> Tuple[np.ndarray, np.ndarray]:
        val = np.zeros(total_atoms, dtype=np.int8)
        mask = np.zeros(total_atoms, dtype=np.int8)
        if init_ev_idx >= 0:
            eid = self._evidence_by_index(init_ev_idx)
            if eid is not None:
                enc = self.schema["encodings"][eid]
                s, c = enc["start"], enc["count"]
                val[s:s + c] = gt_atoms[s:s + c]
                mask[s:s + c] = 1
        return val, mask

    def _evidence_by_index(self, idx: int) -> Optional[str]:
        for eid, enc in self.schema["encodings"].items():
            if enc["start"] <= idx < enc["start"] + enc["count"]:
                return eid
        return None

    def reveal(self, val: np.ndarray, mask: np.ndarray, gt_atoms: np.ndarray,
               qid: str) -> Tuple[np.ndarray, np.ndarray]:
        idx = self.fam_atoms[qid]
        val = val.copy()
        mask = mask.copy()
        val[idx] = gt_atoms[idx]
        mask[idx] = 1
        return val, mask

    def prefixes(self, gt_atoms: np.ndarray, init_ev_idx: int, order: List[str],
                 max_reveals: int) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Return the list of (val, mask) public states for t=0..max_reveals."""
        total = self.schema["total_atoms"]
        val, mask = self.initial_state(gt_atoms, init_ev_idx, total)
        out = [(val.copy(), mask.copy())]
        for q in order[:max_reveals]:
            val, mask = self.reveal(val, mask, gt_atoms, q)
            out.append((val.copy(), mask.copy()))
        return out
