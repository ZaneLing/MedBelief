"""TrajectoryLogger (Ticket T03).

Writes one JSONL record per turn (section 3.3) and one summary record per
episode. Full K-dim probability vectors are saved to a compressed NPZ alongside
the JSONL so the text traces stay small; the JSONL keeps top-k for readability.
Replayable: records carry run_id, case_id, split, seed, config_hash, versions,
per-turn action/cost/budget and status.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import numpy as np


class TrajectoryLogger:
    def __init__(self, run_dir: str, run_id: str, agent_id: str, base_model: str,
                 belief_version: str, policy_version: str, seed: int,
                 config_hash: str, save_full_probs: bool = True):
        self.run_dir = run_dir
        os.makedirs(run_dir, exist_ok=True)
        self.run_id = run_id
        self.agent_id = agent_id
        self.base_model = base_model
        self.belief_version = belief_version
        self.policy_version = policy_version
        self.seed = seed
        self.config_hash = config_hash
        self.save_full_probs = save_full_probs
        self.jsonl_path = os.path.join(run_dir, "episodes.jsonl")
        self._fh = open(self.jsonl_path, "a")
        self._prob_buffer: List[np.ndarray] = []
        self._prob_index: List[Dict[str, Any]] = []
        self._t_start = time.time()
        self.llm_tokens = 0
        self.llm_cost_usd = 0.0
        self.llm_calls = 0

    def log_turn(self, *, case_id: str, source_case_id: str, split: str, turn: int,
                 evidence_ids_now: List[str], new_evidence_ids: List[str],
                 candidate_diseases: List[str], belief_probs_topk: List[float],
                 full_probs: Optional[np.ndarray], belief_entropy: float,
                 action: Dict[str, Any], action_cost: float, remaining_budget: float,
                 latency_ms: int, status: str = "success", label: Optional[str] = None,
                 rank_y: Optional[int] = None, nll_t: Optional[float] = None,
                 brier_t: Optional[float] = None, extra: Optional[Dict] = None):
        rec = {
            "run_id": self.run_id, "case_id": case_id, "source_case_id": source_case_id,
            "split": split, "turn": turn, "agent_id": self.agent_id,
            "base_model": self.base_model, "belief_version": self.belief_version,
            "policy_version": self.policy_version, "seed": self.seed,
            "config_hash": self.config_hash,
            "evidence_ids_now": evidence_ids_now, "new_evidence_ids": new_evidence_ids,
            "candidate_diseases": candidate_diseases, "belief_probs": belief_probs_topk,
            "belief_entropy": belief_entropy, "action": action, "action_cost": action_cost,
            "remaining_budget": remaining_budget, "latency_ms": latency_ms, "status": status,
        }
        if label is not None:
            rec["label"] = label
        if rank_y is not None:
            rec["rank_y"] = rank_y
        if nll_t is not None:
            rec["nll_t"] = nll_t
        if brier_t is not None:
            rec["brier_t"] = brier_t
        if extra:
            rec.update(extra)
        if self.save_full_probs and full_probs is not None:
            rec["prob_row"] = len(self._prob_buffer)
            self._prob_buffer.append(np.asarray(full_probs, dtype=np.float32))
            self._prob_index.append({"case_id": case_id, "turn": turn, "order": split})
        self._fh.write(json.dumps(rec, default=str) + "\n")
        return rec

    def log_episode_summary(self, summary: Dict[str, Any]):
        self._fh.write(json.dumps({"__episode_summary__": True, **summary}, default=str) + "\n")

    def add_llm_usage(self, calls: int, tokens: int, cost_usd: float):
        self.llm_calls += calls
        self.llm_tokens += tokens
        self.llm_cost_usd += cost_usd

    def close(self):
        self._fh.flush()
        self._fh.close()
        if self.save_full_probs and self._prob_buffer:
            np.savez_compressed(
                os.path.join(self.run_dir, "turn_probs.npz"),
                probs=np.stack(self._prob_buffer),
                index=json.dumps(self._prob_index),
            )
        meta = {
            "run_id": self.run_id, "agent_id": self.agent_id, "base_model": self.base_model,
            "belief_version": self.belief_version, "policy_version": self.policy_version,
            "seed": self.seed, "config_hash": self.config_hash,
            "elapsed_sec": round(time.time() - self._t_start, 1),
            "llm_calls": self.llm_calls, "llm_tokens": self.llm_tokens,
            "llm_cost_usd": round(self.llm_cost_usd, 4),
        }
        json.dump(meta, open(os.path.join(self.run_dir, "run_meta.json"), "w"), indent=2)
        return meta
