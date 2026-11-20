"""LLM action policy (C1 interactive / C2 LLM-reported belief) via OpenRouter.

Receives the SAME public clinical history as every other agent. Two variants:
  * use_belief=False -> C1: the LLM only sees evidence text and decides.
  * use_belief=True  -> C2: text belief (top-k calibrated probabilities) is
    injected into the prompt alongside the evidence text.

The action space is restricted to question families that are (a) not yet asked
and (b) plausibly relevant to the current top-k candidate diseases (union of
their DDxPlus symptoms/antecedents), which keeps prompts small and realistic.

Every response must be JSON. Parse failures / invalid targets are counted and
fall back to a safe default (ask the highest-EIG-free default question, or
diagnose the belief argmax), so a run never crashes and the failure rate is
auditable (section 6.1).
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

import numpy as np

from ..schemas import Action, BeliefState, PublicObservation
from ..utils.llm_client import BudgetExceeded, OpenRouterClient


class LLMPolicy:
    version = "llm_v1"

    def __init__(self, client: OpenRouterClient, schema_json_path: str, conditions_path: str,
                 evidences_path: str, diseases: List[str], use_belief: bool = False,
                 top_k: int = 8, max_questions: int = 24, max_tokens: int = 256, seed: int = 0):
        self.client = client
        self.diseases = diseases
        self.use_belief = use_belief
        self.top_k = top_k
        self.max_questions = max_questions
        self.max_tokens = max_tokens
        raw_ev = json.load(open(evidences_path))
        schema = json.load(open(schema_json_path))
        enc = schema["encodings"]
        # Combined per-evidence metadata: geometry (start/count) + English text.
        self.ev: Dict[str, dict] = {}
        for eid, e in enc.items():
            raw = raw_ev.get(eid, {})
            value_keys = list(e["value_to_offset"].keys())
            self.ev[eid] = {
                "data_type": e["data_type"], "start": e["start"], "count": e["count"],
                "code_question": e["code_question"], "question_en": e.get("question_en", eid),
                "value_keys": value_keys, "value_meaning": raw.get("value_meaning", {}),
            }
        # question family -> member evidence ids (from schema)
        self.q_members: Dict[str, List[str]] = schema["question_to_evidences"]
        co = json.load(open(conditions_path))
        self.disease_evidences: Dict[str, set] = {
            d: set(co[d].get("symptoms", {}).keys()) | set(co[d].get("antecedents", {}).keys())
            for d in co
        }
        self.stats = {"calls": 0, "parse_failures": 0, "invalid_target": 0,
                      "budget_stops": 0, "fallbacks": 0}
        self._rng = np.random.default_rng(seed)

    def _q_text(self, qid: str) -> str:
        return self.ev.get(qid, {}).get("question_en", qid)

    def _finding_text(self, eid: str, value) -> str:
        e = self.ev.get(eid, {})
        q = e.get("question_en", eid)
        dt = e.get("data_type")
        if dt == "B":
            return f"- {q} -> {'YES' if value == 1 else 'NO'}"
        vm = e.get("value_meaning", {})
        if isinstance(value, list):
            parts = [vm.get(v, {}).get("en", str(v)) for v in value]
            return f"- {q} -> {', '.join(parts) if parts else 'none/default'}"
        return f"- {q} -> {vm.get(value, {}).get('en', value)}"

    def _relevant_questions(self, obs: PublicObservation, belief: BeliefState) -> List[str]:
        asked = set(obs.info.get("asked_questions", []))
        b = np.asarray(belief.probs)
        topd = [belief.diseases[i] for i in np.argsort(-b)[: self.top_k]]
        relevant: set = set()
        for d in topd:
            relevant |= self.disease_evidences.get(d, set())
        fams: List[str] = []
        seen = set()
        for a in obs.legal_actions:
            if not a.startswith("ASK:"):
                continue
            q = a.split(":", 1)[1]
            if q in asked or q in seen:
                continue
            members = set(self.q_members.get(q, []))
            if members & relevant:
                fams.append(q)
                seen.add(q)
            if len(fams) >= self.max_questions:
                break
        if not fams:  # fallback: any unasked family
            for a in obs.legal_actions:
                if a.startswith("ASK:"):
                    q = a.split(":", 1)[1]
                    if q not in asked:
                        fams.append(q)
                    if len(fams) >= self.max_questions:
                        break
        return fams

    def _finding_text_generic(self, obs: PublicObservation, eid: str) -> str:
        meta = self.ev[eid]
        dt = meta["data_type"]
        q = meta["question_en"]
        val = obs.info["atom_val"]
        start, count = meta["start"], meta["count"]
        seg = val[start:start + count]
        if dt == "B":
            return f"- {q} -> {'YES' if seg[0] == 1 else 'NO'}"
        keys = meta["value_keys"]
        vm = meta["value_meaning"]
        active = [keys[i] for i in range(len(seg)) if seg[i] == 1 and i < len(keys)]
        if dt == "M":
            txt = ", ".join(vm.get(a, {}).get("en", a) for a in active) or "none"
        else:
            txt = ", ".join(vm.get(a, {}).get("en", a) for a in active) or "none"
        return f"- {q} -> {txt}"

    def _build_prompt(self, obs: PublicObservation, belief: BeliefState,
                      questions: List[str]) -> List[dict]:
        sex = {0: "F", 1: "M", 2: "other"}.get(int(obs.sex or 0), "?")
        lines = [f"Patient: {obs.age} y/o {sex}.", "Findings so far:"]
        if obs.observed_evidences:
            for eid in obs.observed_evidences:
                lines.append(self._finding_text_generic(obs, eid))
        else:
            lines.append("- (only the initial complaint)")
        b = np.asarray(belief.probs)
        order = np.argsort(-b)[: self.top_k]
        cand = [belief.diseases[i] for i in order]
        lines.append("")
        if self.use_belief:
            lines.append("Current diagnostic belief (calibrated probabilities):")
            for i in order:
                lines.append(f"- {belief.diseases[i]}: {b[i]:.3f}")
        else:
            lines.append("Candidate diagnoses: " + ", ".join(cand))
        lines.append("")
        lines.append("Available questions (ask ONE):")
        for q in questions:
            lines.append(f"- {q}: {self._q_text(q)}")
        lines.append("")
        lines.append(
            'Reply with JSON only. Either {"action":"ASK","target":"<question_id>"} '
            'or {"action":"DIAGNOSE","diagnosis":"<one candidate>"}.'
        )
        return [
            {"role": "system", "content": "You are a careful diagnostic agent in a closed-world "
             "49-disease simulation. Ask high-value questions, then commit to a single diagnosis."},
            {"role": "user", "content": "\n".join(lines)},
        ]

    def act(self, obs: PublicObservation, belief: BeliefState) -> Action:
        b = np.asarray(belief.probs)
        default_dx = belief.diseases[int(np.argmax(b))]
        if obs.remaining_budget <= 0:
            return Action(kind="DIAGNOSE", diagnosis=default_dx)
        questions = self._relevant_questions(obs, belief)
        if not questions:
            return Action(kind="DIAGNOSE", diagnosis=default_dx)
        messages = self._build_prompt(obs, belief, questions)
        self.stats["calls"] += 1
        try:
            resp = self.client.chat(messages, max_tokens=self.max_tokens, temperature=0.0,
                                    json_mode=True)
        except BudgetExceeded:
            self.stats["budget_stops"] += 1
            return Action(kind="DIAGNOSE", diagnosis=default_dx)
        if not resp.ok:
            self.stats["parse_failures"] += 1
            self.stats["fallbacks"] += 1
            return Action(kind="ASK", target=questions[0])
        parsed = self._parse(resp.text)
        if parsed is None:
            self.stats["parse_failures"] += 1
            self.stats["fallbacks"] += 1
            return Action(kind="ASK", target=questions[0])
        act = parsed.get("action", "").upper()
        if act == "DIAGNOSE":
            dx = parsed.get("diagnosis")
            if dx in self.diseases:
                return Action(kind="DIAGNOSE", diagnosis=dx)
            # try fuzzy match
            match = self._match_disease(dx)
            if match:
                return Action(kind="DIAGNOSE", diagnosis=match)
            self.stats["invalid_target"] += 1
            return Action(kind="DIAGNOSE", diagnosis=default_dx)
        if act == "ASK":
            tgt = parsed.get("target")
            if tgt in questions:
                return Action(kind="ASK", target=tgt)
            self.stats["invalid_target"] += 1
            self.stats["fallbacks"] += 1
            return Action(kind="ASK", target=questions[0])
        self.stats["parse_failures"] += 1
        return Action(kind="ASK", target=questions[0])

    def _match_disease(self, dx: Optional[str]) -> Optional[str]:
        if not dx:
            return None
        dxl = dx.strip().lower()
        for d in self.diseases:
            if d.lower() == dxl:
                return d
        for d in self.diseases:
            if dxl and (dxl in d.lower() or d.lower() in dxl):
                return d
        return None

    @staticmethod
    def _parse(text: str) -> Optional[dict]:
        text = text.strip()
        # strip code fences
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except Exception:
            pass
        i, j = text.find("{"), text.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except Exception:
                return None
        return None
