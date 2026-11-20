"""Construct + fit belief models from the processed DDxPlus splits.

Prefix training data is generated offline from the *fit* partition using the
FixedEvidenceGenerator. Teacher-forced prefix labels are the case-population
disease label -- this is NOT a claim about any single patient's true
intermediate posterior (section 4.5).
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..data.prefix_generator import FixedEvidenceGenerator, load_family_atoms
from .naive_bayes import BeliefNB
from .neural_update import BeliefNeuralUpdater
from .recompute import RecomputeLogReg, RecomputeMLP, features_from_arrays


def load_schema(schema_json_path: str) -> dict:
    return json.load(open(schema_json_path))


def build_prefix_dataset(split: Dict[str, np.ndarray], gen: FixedEvidenceGenerator,
                         max_reveals: int = 6, n_patients: Optional[int] = None,
                         orders_per_patient: int = 1, seed: int = 42,
                         order_mode: str = "random_valid") -> Tuple[np.ndarray, np.ndarray, List[dict]]:
    """Returns (X [R,F], y [R], seqs) where R = sum over patients of (T+1)."""
    atoms = split["atoms"]
    N = len(atoms) if n_patients is None else min(n_patients, len(atoms))
    Xs, ys, seqs = [], [], []
    for i in range(N):
        age = int(split["age"][i]); sex = int(split["sex"][i]); y = int(split["pathology_idx"][i])
        for o in range(orders_per_patient):
            s = seed * 1000003 + i * 31 + o
            order = gen.order(s, order_mode)
            prefixes = gen.prefixes(atoms[i], int(split["initial_evidence_idx"][i]), order, max_reveals)
            states = []
            for (val, mask) in prefixes:
                Xs.append(features_from_arrays(val, mask, age, sex))
                ys.append(y)
                states.append((val.astype(np.int8), mask.astype(np.int8)))
            seqs.append({"states": states, "age": age, "sex": sex, "label": y})
    X = np.stack(Xs).astype(np.float32)
    y = np.asarray(ys, dtype=np.int64)
    return X, y, seqs


def build_val_sequences(split: Dict[str, np.ndarray], gen: FixedEvidenceGenerator,
                        max_reveals: int, n_patients: int, seed: int,
                        order_mode: str = "random_valid") -> List[dict]:
    _, _, seqs = build_prefix_dataset(split, gen, max_reveals, n_patients, 1, seed, order_mode)
    return seqs


def train_nb(fit: Dict[str, np.ndarray], diseases: List[str], total_atoms: int,
             alpha: float = 1.0) -> BeliefNB:
    nb = BeliefNB(diseases, total_atoms, alpha=alpha)
    nb.fit(fit["atoms"], fit["age"], fit["sex"], fit["pathology_idx"])
    return nb


def make_generator(schema: dict, fit: Optional[Dict[str, np.ndarray]] = None,
                   K: int = 49) -> FixedEvidenceGenerator:
    scores = None
    if fit is not None:
        scores = FixedEvidenceGenerator.compute_family_scores(
            fit["atoms"], fit["pathology_idx"], schema, K)
    return FixedEvidenceGenerator(schema, scores)
