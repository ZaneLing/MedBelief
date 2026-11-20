"""Base environment interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import Action, PublicObservation


class BaseEnvironment(ABC):
    @abstractmethod
    def reset(self, case_id: str) -> PublicObservation: ...

    @abstractmethod
    def step(self, action: Action) -> PublicObservation: ...

    # --- evaluator-only access (never called by an agent/policy) ---
    @abstractmethod
    def ground_truth(self, case_id: str) -> dict: ...
