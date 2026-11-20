"""Random and fixed-order policies (Sprint 0 baseline; no LLM)."""
from __future__ import annotations

from typing import List, Optional

import numpy as np

from ..schemas import Action, BeliefState, PublicObservation


class RandomPolicy:
    """Sprint 0 baseline: uniformly random legal ASK until budget, then diagnose
    the belief argmax. Requires no LLM and no trained model."""

    version = "random_v1"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def act(self, obs: PublicObservation, belief: BeliefState) -> Action:
        asks = [q for q in obs.legal_actions if q.startswith("ASK:")]
        if obs.remaining_budget <= 0 or not asks:
            b = np.asarray(belief.probs)
            return Action(kind="DIAGNOSE", diagnosis=belief.diseases[int(np.argmax(b))])
        choice = asks[int(self.rng.integers(0, len(asks)))]
        return Action(kind="ASK", target=choice.split(":", 1)[1])


class FixedOrderPolicy:
    """Asks a precomputed family order (from FixedEvidenceGenerator) then
    diagnoses the belief argmax. Used to drive Mode A inside the online runner."""

    version = "fixed_order_v1"

    def __init__(self, order: List[str]):
        self.order = order
        self.i = 0

    def reset(self):
        self.i = 0

    def act(self, obs: PublicObservation, belief: BeliefState) -> Action:
        asked = set(obs.info.get("asked_questions", []))
        while self.i < len(self.order) and self.order[self.i] in asked:
            self.i += 1
        if obs.remaining_budget <= 0 or self.i >= len(self.order):
            b = np.asarray(belief.probs)
            return Action(kind="DIAGNOSE", diagnosis=belief.diseases[int(np.argmax(b))])
        q = self.order[self.i]
        self.i += 1
        return Action(kind="ASK", target=q)
