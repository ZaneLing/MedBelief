"""SealedDDxEnvironment (Ticket T02).

A single-diagnosis, closed-world DDxPlus interaction environment.

Sealing guarantees
------------------
* The full ground-truth atom vector and the pathology label are held privately
  and are only reachable through `ground_truth()` (evaluator-only).
* `reset`/`step` emit `PublicObservation` whose numeric encoding
  (`atom_val`/`atom_mask`) contains ONLY revealed evidence: unobserved atoms
  are 0 with mask 0, so no future evidence can leak through the default fill.
* Asking a question family twice returns the same public atoms and flags
  `duplicate=True`; belief estimators key off the observed *set* so repeat
  questions cannot double-count likelihood.
* `unknown` (never asked) is distinct from `negative` (asked, value absent):
  the mask records which is which.

Closed-world mode: a binary evidence absent from the patient record is treated
as negative when its family is asked (`synthetic_closed_world=True`). This rule
is a property of the synthetic dataset and must not be ported to real EHR.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import numpy as np

from ..schemas import Action, Evidence, PublicObservation
from .base import BaseEnvironment


class SealedDDxEnvironment(BaseEnvironment):
    def __init__(
        self,
        split_path: str,
        schema_json_path: str,
        max_asks: int = 6,
        synthetic_closed_world: bool = True,
    ):
        z = np.load(split_path, allow_pickle=True)
        self._atoms = z["atoms"].astype(np.int8)          # PRIVATE ground truth
        self._age = z["age"]
        self._sex = z["sex"]
        self._path = z["pathology_idx"]                    # PRIVATE label
        self._init_ev = z["initial_evidence_idx"]
        self._case_ids: List[str] = [str(c) for c in z["case_ids"]]
        self.case_index: Dict[str, int] = {c: i for i, c in enumerate(self._case_ids)}

        schema = json.load(open(schema_json_path))
        self.encodings = schema["encodings"]
        self.question_to_evidences: Dict[str, List[str]] = schema["question_to_evidences"]
        self.question_ids: List[str] = sorted(
            self.question_to_evidences.keys(), key=lambda q: int(q.split("_")[1])
        )
        self.diseases: List[str] = schema["diseases"]
        self.total_atoms: int = schema["total_atoms"]
        self.synthetic_closed_world = synthetic_closed_world

        self.max_asks = max_asks
        self._cur: Optional[int] = None
        self._cur_case: Optional[str] = None
        self._pub_val: Optional[np.ndarray] = None
        self._pub_mask: Optional[np.ndarray] = None
        self._asked: List[str] = []
        self._observed_ev: List[str] = []
        self._turn = 0
        self._done = False
        self._asks_used = 0
        self._last_duplicate = False
        self._history: List[dict] = []

    # ------------------------------------------------------------------
    @property
    def case_ids(self) -> List[str]:
        return self._case_ids

    def reset(self, case_id: str) -> PublicObservation:
        if case_id not in self.case_index:
            raise KeyError(f"unknown case_id {case_id}")
        i = self.case_index[case_id]
        self._cur = i
        self._cur_case = case_id
        self._pub_val = np.zeros(self.total_atoms, dtype=np.int8)
        self._pub_mask = np.zeros(self.total_atoms, dtype=np.int8)
        self._asked = []
        self._observed_ev = []
        self._turn = 0
        self._done = False
        self._asks_used = 0
        self._last_duplicate = False
        self._history = []

        # INITIAL_EVIDENCE revealed for free at turn 0 (part of initial state).
        init_idx = int(self._init_ev[i])
        new_ev: List[Evidence] = []
        if init_idx >= 0:
            eid = self._evidence_by_index(init_idx)
            if eid is not None:
                new_ev = self._reveal_evidences([eid], source="initial", turn=0)
        return self._obs(new_ev)

    def _evidence_by_index(self, idx: int) -> Optional[str]:
        # recover evidence id from atom index via encodings
        for eid, enc in self.encodings.items():
            if enc["start"] <= idx < enc["start"] + enc["count"]:
                return eid
        return None

    def _gt(self) -> np.ndarray:
        return self._atoms[self._cur]

    def _reveal_evidences(self, eids: List[str], source: str, turn: int) -> List[Evidence]:
        gt = self._gt()
        out: List[Evidence] = []
        for eid in eids:
            enc = self.encodings[eid]
            s, c = enc["start"], enc["count"]
            if self._pub_mask[s] == 1 and c == 1:
                continue  # already observed
            if c > 1 and self._pub_mask[s : s + c].all():
                continue
            self._pub_val[s : s + c] = gt[s : s + c]
            self._pub_mask[s : s + c] = 1
            if eid not in self._observed_ev:
                self._observed_ev.append(eid)
            # build a human/struct-readable Evidence record
            if enc["data_type"] == "B":
                val = int(gt[s])
                status = "positive" if val == 1 else "negative"
            else:
                active = [
                    k for k, off in enc["value_to_offset"].items() if gt[s + off] == 1
                ]
                val = active if enc["data_type"] == "M" else (active[0] if active else None)
                status = "positive" if active else "negative"
            out.append(
                Evidence(
                    evidence_id=eid,
                    value=val,
                    status=status,
                    source=source,
                    observed_at=turn,
                    fact_group=enc["code_question"],
                )
            )
        return out

    def _legal_actions(self) -> List[str]:
        acts = [f"ASK:{q}" for q in self.question_ids if q not in self._asked]
        acts += ["DIAGNOSE", "ABSTAIN"]
        return acts

    def _obs(self, new_evidence: List[Evidence]) -> PublicObservation:
        return PublicObservation(
            case_id=self._cur_case or "",
            turn=self._turn,
            evidence=new_evidence,
            legal_actions=self._legal_actions(),
            remaining_budget=float(self.max_asks - self._asks_used),
            done=self._done,
            age=int(self._age[self._cur]),
            sex=int(self._sex[self._cur]),
            observed_evidences=list(self._observed_ev),
            info={
                "atom_val": self._pub_val.copy(),
                "atom_mask": self._pub_mask.copy(),
                "asked_questions": list(self._asked),
                "duplicate": self._last_duplicate,
                "budget_exhausted": self._asks_used >= self.max_asks,
                "synthetic_closed_world": self.synthetic_closed_world,
            },
        )

    def step(self, action: Action) -> PublicObservation:
        if self._cur is None:
            raise RuntimeError("must reset() before step()")
        if self._done:
            raise RuntimeError("episode already done")
        self._last_duplicate = False
        new_ev: List[Evidence] = []

        if action.kind in ("DIAGNOSE", "ABSTAIN"):
            self._done = True
            self._turn += 1
            self._history.append({"turn": self._turn, "action": action.kind,
                                  "diagnosis": action.diagnosis})
            return self._obs([])

        if action.kind in ("ASK", "TEST"):
            q = action.target
            if q is None or q not in self.question_to_evidences:
                raise ValueError(f"illegal action target: {q!r}")
            if self._asks_used >= self.max_asks:
                raise ValueError("budget exhausted; cannot ASK")
            if q in self._asked:
                # duplicate question: same public atoms, no new evidence, still costs
                self._last_duplicate = True
                self._asks_used += 1
                self._turn += 1
                self._history.append({"turn": self._turn, "action": "ASK", "target": q,
                                      "duplicate": True})
                return self._obs([])
            self._asked.append(q)
            self._asks_used += 1
            self._turn += 1
            new_ev = self._reveal_evidences(
                self.question_to_evidences[q], source="ask", turn=self._turn
            )
            self._history.append({"turn": self._turn, "action": "ASK", "target": q,
                                  "new_evidence": [e.evidence_id for e in new_ev]})
            return self._obs(new_ev)

        raise ValueError(f"unknown action kind {action.kind}")

    # --- evaluator-only -------------------------------------------------
    def ground_truth(self, case_id: str) -> dict:
        i = self.case_index[case_id]
        return {
            "pathology_idx": int(self._path[i]),
            "pathology": self.diseases[int(self._path[i])],
            "atoms": self._atoms[i].copy(),
            "age": int(self._age[i]),
            "sex": int(self._sex[i]),
        }

    def public_trajectory(self) -> List[dict]:
        return list(self._history)
