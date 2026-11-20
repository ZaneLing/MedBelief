"""Belief estimator base + shared public-state encoding.

All belief estimators consume the *public* numeric state emitted by the sealed
environment (`atom_val`, `atom_mask`, age, sex). They never see the private
ground-truth atom vector or the pathology label at inference time; labels are
used only during offline fitting on the `fit` partition.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np

from ..schemas import BeliefState, PublicObservation

AGE_NORM = 100.0


def public_features(obs: PublicObservation) -> np.ndarray:
    """Dense feature vector for a single public observation.

    Layout: [atom_val(972) | atom_mask(972) | age/100 | sex one-hot(3)]
    Unobserved atoms contribute 0 to `atom_val` and 0 to `atom_mask`, so the
    classifier can distinguish "absent" from "never asked".
    """
    val = obs.info["atom_val"].astype(np.float32)
    mask = obs.info["atom_mask"].astype(np.float32)
    sex = int(obs.sex or 0)
    sex_oh = np.zeros(3, dtype=np.float32)
    sex_oh[min(sex, 2)] = 1.0
    age = np.array([float(obs.age or 0) / AGE_NORM], dtype=np.float32)
    return np.concatenate([val, mask, age, sex_oh])


def stack_features(obs_list: List[PublicObservation]) -> np.ndarray:
    return np.stack([public_features(o) for o in obs_list]).astype(np.float32)


class BeliefModel(ABC):
    """Interface: reset on the first observation, then update per turn."""

    version = "belief_v0"

    def __init__(self, diseases: List[str]):
        self.diseases = diseases
        self.K = len(diseases)

    @abstractmethod
    def reset(self, observation: PublicObservation) -> BeliefState: ...

    @abstractmethod
    def update(self, prev: BeliefState, observation: PublicObservation) -> BeliefState: ...

    # convenience: probability vector from a single public observation
    def predict_obs(self, observation: PublicObservation) -> np.ndarray:
        raise NotImplementedError

    def _state(self, probs: np.ndarray, **diag) -> BeliefState:
        probs = np.asarray(probs, dtype=np.float64)
        probs = np.clip(probs, 1e-12, None)
        probs = probs / probs.sum()
        return BeliefState(
            diseases=list(self.diseases),
            probs=[float(p) for p in probs],
            version=self.version,
            diagnostics=diag,
        )
