"""Baseline B0: Naive Bayes belief (Ticket T05).

Deliberately simplified probabilistic baseline: atoms are treated as
conditionally independent Bernoulli given the disease, plus categorical
likelihoods for sex and age-decade. Because the score is computed over the
*observed set* (the mask), re-asking a question family cannot double-count
likelihood -- this is asserted in the unit tests.

Priors/likelihoods are estimated only from the `fit` partition with Laplace
smoothing; the smoothing coefficient is a hyperparameter chosen on validate.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np

from ..schemas import BeliefState, PublicObservation
from .base import BeliefModel


class BeliefNB(BeliefModel):
    version = "nb_v1"

    def __init__(self, diseases: List[str], total_atoms: int, alpha: float = 1.0):
        super().__init__(diseases)
        self.total_atoms = total_atoms
        self.alpha = alpha
        self.log_prior: Optional[np.ndarray] = None       # [K]
        self.log_p1: Optional[np.ndarray] = None          # [atoms, K]
        self.log_p0: Optional[np.ndarray] = None          # [atoms, K]
        self.log_sex: Optional[np.ndarray] = None         # [3, K]
        self.log_age: Optional[np.ndarray] = None         # [nbuckets, K]

    @staticmethod
    def age_bucket(age: int) -> int:
        return min(max(int(age) // 10, 0), 9)

    def fit(self, atoms: np.ndarray, age: np.ndarray, sex: np.ndarray,
            pathology_idx: np.ndarray) -> "BeliefNB":
        K = self.K
        A = self.total_atoms
        counts = np.zeros((A, K), dtype=np.float64)
        dcounts = np.zeros(K, dtype=np.float64) + self.alpha
        sex_counts = np.zeros((3, K), dtype=np.float64) + self.alpha
        age_counts = np.zeros((10, K), dtype=np.float64) + self.alpha

        X = atoms.astype(np.float64)  # [N, A]
        for d in range(K):
            m = pathology_idx == d
            nd = m.sum()
            dcounts[d] += nd
            if nd == 0:
                continue
            counts[:, d] = X[m].sum(0)
            for s in range(3):
                sex_counts[s, d] += (sex[m] == s).sum()
            ab = np.array([self.age_bucket(a) for a in age[m]])
            for b in range(10):
                age_counts[b, d] += (ab == b).sum()

        p1 = (counts + self.alpha) / (dcounts[None, :] + 2 * self.alpha)
        self.log_p1 = np.log(p1)
        self.log_p0 = np.log(1.0 - p1)
        self.log_prior = np.log(dcounts / dcounts.sum())
        self.log_sex = np.log(sex_counts / sex_counts.sum(0, keepdims=True))
        self.log_age = np.log(age_counts / age_counts.sum(0, keepdims=True))
        return self

    def log_posterior(self, atom_val: np.ndarray, atom_mask: np.ndarray,
                      age: int, sex: int) -> np.ndarray:
        ll = self.log_prior.copy()
        ll = ll + self.log_sex[min(sex, 2), :] + self.log_age[self.age_bucket(age), :]
        mask = atom_mask.astype(bool)
        if mask.any():
            v = atom_val.astype(np.float64)[mask]              # [m]
            lp1 = self.log_p1[mask]                            # [m, K]
            lp0 = self.log_p0[mask]
            contrib = v[:, None] * lp1 + (1.0 - v)[:, None] * lp0
            ll = ll + contrib.sum(0)
        return ll

    def predict_obs(self, observation: PublicObservation) -> np.ndarray:
        ll = self.log_posterior(
            observation.info["atom_val"], observation.info["atom_mask"],
            int(observation.age or 0), int(observation.sex or 0),
        )
        ll = ll - ll.max()
        p = np.exp(ll)
        return p / p.sum()

    def reset(self, observation: PublicObservation) -> BeliefState:
        return self._state(self.predict_obs(observation))

    def update(self, prev: BeliefState, observation: PublicObservation) -> BeliefState:
        # Recomputed from the observed set each turn (idempotent under duplicates).
        return self._state(self.predict_obs(observation))

    # --- persistence ----------------------------------------------------
    def save(self, path: str):
        np.savez_compressed(
            path, log_prior=self.log_prior, log_p1=self.log_p1, log_p0=self.log_p0,
            log_sex=self.log_sex, log_age=self.log_age,
            diseases=np.asarray(self.diseases, dtype=object),
            total_atoms=self.total_atoms, alpha=self.alpha,
        )

    @classmethod
    def load(cls, path: str) -> "BeliefNB":
        z = np.load(path, allow_pickle=True)
        obj = cls([str(d) for d in z["diseases"]], int(z["total_atoms"]), alpha=float(z["alpha"]))
        obj.log_prior = z["log_prior"]
        obj.log_p1 = z["log_p1"]
        obj.log_p0 = z["log_p0"]
        obj.log_sex = z["log_sex"]
        obj.log_age = z["log_age"]
        return obj
