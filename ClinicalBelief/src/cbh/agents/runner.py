"""Episode runner: Mode A (fixed evidence) and Mode C (online interactive).

Mode A drives belief models over precomputed disclosure prefixes (no policy),
which isolates belief quality for RQ1. Mode C runs the full agent loop
(belief + policy + sealed env) for RQ2, with a hard budget, forced final
decision on exhaustion, invalid-action handling and per-turn JSONL logging.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

import numpy as np

from ..data.prefix_generator import FixedEvidenceGenerator
from ..schemas import Action, BeliefState, PublicObservation
from ..utils.logging import TrajectoryLogger


def obs_from_prefix(case_id: str, turn: int, val: np.ndarray, mask: np.ndarray,
                    age: int, sex: int, remaining_budget: float = 0.0,
                    asked: Optional[List[str]] = None) -> PublicObservation:
    return PublicObservation(
        case_id=case_id, turn=turn, evidence=[], legal_actions=[],
        remaining_budget=remaining_budget, done=False, age=age, sex=sex,
        observed_evidences=[],
        info={"atom_val": val.astype(np.int8), "atom_mask": mask.astype(np.int8),
              "asked_questions": asked or [], "duplicate": False},
    )


def run_fixed_case(gen: FixedEvidenceGenerator, belief, gt_atoms: np.ndarray,
                   init_idx: int, age: int, sex: int, order: List[str],
                   max_reveals: int, case_id: str) -> np.ndarray:
    """Return probs_seq [T+1, K] for one patient under one disclosure order."""
    prefixes = gen.prefixes(gt_atoms, init_idx, order, max_reveals)
    probs_seq = []
    state: Optional[BeliefState] = None
    for t, (val, mask) in enumerate(prefixes):
        obs = obs_from_prefix(case_id, t, val, mask, age, sex)
        if t == 0:
            state = belief.reset(obs)
        else:
            state = belief.update(state, obs)
        probs_seq.append(np.asarray(state.probs, dtype=np.float64))
    return np.stack(probs_seq)


def run_fixed_split(split: Dict[str, np.ndarray], gen: FixedEvidenceGenerator,
                    belief, orders_per_case: int = 1, max_reveals: int = 6,
                    order_seed: int = 42, order_modes: Optional[List[str]] = None,
                    max_cases: Optional[int] = None, verbose: bool = False):
    """Run Mode A over a split. Returns dict with probs [N, modes, T+1, K], labels,
    case_ids."""
    order_modes = order_modes or ["random_valid"]
    atoms = split["atoms"]
    N = len(atoms) if max_cases is None else min(max_cases, len(atoms))
    K = belief.K
    T = max_reveals + 1
    all_probs = np.zeros((N, len(order_modes), T, K), dtype=np.float32)
    labels = split["pathology_idx"][:N]
    case_ids = [str(c) for c in split["case_ids"][:N]]
    for i in range(N):
        for m, mode in enumerate(order_modes):
            seed = order_seed * 100003 + i * 17 + m
            order = gen.order(seed, mode)
            ps = run_fixed_case(gen, belief, atoms[i], int(split["initial_evidence_idx"][i]),
                                int(split["age"][i]), int(split["sex"][i]), order,
                                max_reveals, case_ids[i])
            # pad/truncate to T
            if ps.shape[0] < T:
                pad = np.repeat(ps[-1:], T - ps.shape[0], axis=0)
                ps = np.concatenate([ps, pad], 0)
            all_probs[i, m] = ps[:T]
        if verbose and (i + 1) % 500 == 0:
            print(f"    fixed {i+1}/{N}")
    return {"probs": all_probs, "labels": labels, "case_ids": case_ids,
            "order_modes": order_modes}


def run_episode(env, belief, policy, case_id: str, max_budget: int,
                logger: Optional[TrajectoryLogger] = None, split: str = "?",
                disease_index: Optional[Dict[str, int]] = None):
    """Mode C online loop with budget exhaustion + forced final decision."""
    obs = env.reset(case_id)
    belief_state = belief.reset(obs)
    t0 = time.time()
    turns = 0
    diagnosis = None
    invalid = 0
    while not obs.done and obs.remaining_budget > 0:
        action = policy.act(obs, belief_state)
        if action.kind in ("DIAGNOSE", "ABSTAIN"):
            diagnosis = action.diagnosis
            obs = env.step(action)
            _log_turn(logger, env, obs, belief_state, action, 0.0, case_id, split, turns, diagnosis)
            break
        if action.kind == "ASK" and (action.target is None or
                                     f"ASK:{action.target}" not in obs.legal_actions):
            invalid += 1
            # invalid action: forced diagnose (no free retry, per section 5.2)
            diagnosis = belief_state.diseases[int(np.argmax(belief_state.probs))]
            obs = env.step(Action(kind="DIAGNOSE", diagnosis=diagnosis))
            _log_turn(logger, env, obs, belief_state, Action(kind="DIAGNOSE", diagnosis=diagnosis),
                      0.0, case_id, split, turns, diagnosis, status="invalid_action")
            break
        next_obs = env.step(action)
        turns += 1
        belief_state = belief.update(belief_state, next_obs)
        _log_turn(logger, env, next_obs, belief_state, action, 1.0, case_id, split, turns, None)
        obs = next_obs
    if diagnosis is None:
        # budget exhausted -> forced final decision
        diagnosis = belief_state.diseases[int(np.argmax(belief_state.probs))]
        obs = env.step(Action(kind="DIAGNOSE", diagnosis=diagnosis))
        _log_turn(logger, env, obs, belief_state, Action(kind="DIAGNOSE", diagnosis=diagnosis),
                  0.0, case_id, split, turns, diagnosis, status="budget_forced")
    gt = env.ground_truth(case_id)
    latency = int((time.time() - t0) * 1000)
    return {
        "case_id": case_id, "split": split, "diagnosis": diagnosis,
        "true": gt["pathology"], "correct": diagnosis == gt["pathology"],
        "final_probs": np.asarray(belief_state.probs), "true_idx": gt["pathology_idx"],
        "asks": turns, "invalid": invalid, "latency_ms": latency,
        "top1_belief": belief_state.diseases[int(np.argmax(belief_state.probs))],
    }


def _log_turn(logger, env, obs, belief_state, action, cost, case_id, split, turn, diagnosis,
              status="success"):
    if logger is None:
        return
    probs = np.asarray(belief_state.probs)
    order = np.argsort(-probs)[:8]
    logger.log_turn(
        case_id=case_id, source_case_id=case_id, split=split, turn=turn,
        evidence_ids_now=list(obs.observed_evidences),
        new_evidence_ids=[e.evidence_id for e in obs.evidence],
        candidate_diseases=[belief_state.diseases[i] for i in order],
        belief_probs_topk=[float(probs[i]) for i in order],
        full_probs=probs, belief_entropy=belief_state.entropy(),
        action={"kind": action.kind, "target": action.target, "diagnosis": diagnosis},
        action_cost=cost, remaining_budget=obs.remaining_budget, latency_ms=0,
        status=status,
    )


def run_online_split(env, belief, policy, case_ids: List[str], max_budget: int,
                     logger: Optional[TrajectoryLogger] = None, split: str = "?",
                     verbose: bool = False):
    results = []
    for j, cid in enumerate(case_ids):
        r = run_episode(env, belief, policy, cid, max_budget, logger, split)
        results.append(r)
        if verbose and (j + 1) % 25 == 0:
            acc = np.mean([x["correct"] for x in results])
            extra = ""
            if logger is not None:
                extra = f" | llm ${logger.llm_cost_usd:.4f}"
            print(f"    online {j+1}/{len(case_ids)} acc={acc:.3f}{extra}")
    return results
