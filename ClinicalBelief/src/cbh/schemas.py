"""Core data contracts for the Clinical Belief Evolution Harness.

These mirror section 3.2 of the experimental protocol. They are deliberately
dependency-free so that environments, belief estimators, policies and the
evaluator can all agree on a single representation of public information.

Nothing in this module ever holds hidden ground truth; the sealed environment
and the evaluator own labels privately and only ever emit `PublicObservation`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Protocol


@dataclass(frozen=True)
class Action:
    """An agent action.

    kind:
      ASK      -- reveal a question family (code_question); members returned.
      TEST     -- reserved for external environments (imaging/labs).
      DIAGNOSE -- commit to a final diagnosis; terminates the episode.
      ABSTAIN  -- refuse to answer; terminates the episode.
    target:    evidence/question/test code for ASK/TEST.
    diagnosis: canonical disease name for DIAGNOSE.
    """

    kind: Literal["ASK", "TEST", "DIAGNOSE", "ABSTAIN"]
    target: Optional[str] = None
    diagnosis: Optional[str] = None


@dataclass(frozen=True)
class Evidence:
    """A single newly-exposed public fact.

    `fact_group` is the dedup / double-count guard: two Evidence items that
    describe the same underlying clinical fact share a fact_group so belief
    estimators can avoid accumulating the same likelihood twice.
    """

    evidence_id: str
    value: Any
    status: Literal["positive", "negative", "unknown", "uncertain"]
    source: str
    observed_at: int
    fact_group: str


@dataclass
class BeliefState:
    """A probability distribution over the canonical disease ordering."""

    diseases: List[str]
    probs: List[float]
    residual_mass: float = 0.0
    version: str = "belief_v0"
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def prob_of(self, disease: str) -> float:
        return self.probs[self.diseases.index(disease)]

    def top_k(self, k: int) -> List[str]:
        order = sorted(range(len(self.probs)), key=lambda i: self.probs[i], reverse=True)
        return [self.diseases[i] for i in order[:k]]

    def entropy(self) -> float:
        import math

        return -sum(p * math.log(p) for p in self.probs if p > 0.0)


@dataclass
class PublicObservation:
    """Everything the agent is allowed to see at a given turn."""

    case_id: str
    turn: int
    evidence: List[Evidence]
    legal_actions: List[str]
    remaining_budget: float
    done: bool = False
    # Cumulative structured view maintained by the environment (public only).
    age: Optional[int] = None
    sex: Optional[str] = None
    observed_evidences: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)


class Environment(Protocol):
    def reset(self, case_id: str) -> PublicObservation: ...
    def step(self, action: Action) -> PublicObservation: ...


class BeliefEstimator(Protocol):
    def reset(self, observation: PublicObservation) -> BeliefState: ...
    def update(self, prev: BeliefState, observation: PublicObservation) -> BeliefState: ...


class AgentPolicy(Protocol):
    def act(self, obs: PublicObservation, belief: BeliefState) -> Action: ...


class ExperienceLearner(Protocol):
    def learn(self, completed_episodes: List[dict]) -> dict: ...
