"""OpenRouter LLM client with strict USD budget accounting.

The protocol caps the experiment spend. This client enforces a hard budget:
every call is preceded by a check, and cumulative cost is estimated from token
usage and a per-model price table (falling back to OpenRouter's reported cost
when present). When the cap would be exceeded it raises `BudgetExceeded` rather
than silently spending.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# USD per 1M tokens (prompt, completion). Conservative estimates; OpenRouter's
# returned cost is preferred when the response includes it.
PRICE_TABLE: Dict[str, tuple] = {
    "qwen/qwen3-8b": (0.10, 0.30),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "meta-llama/llama-3.1-8b-instruct": (0.05, 0.08),
    "google/gemini-flash-1.5-8b": (0.02, 0.04),
    "mistralai/mistral-7b-instruct": (0.06, 0.06),
}
DEFAULT_PRICE = (0.20, 0.60)


class BudgetExceeded(RuntimeError):
    pass


def load_env(path: str = ".env") -> Dict[str, str]:
    env: Dict[str, str] = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    model: str
    ok: bool
    error: Optional[str] = None


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen/qwen3-8b",
                 budget_usd: float = 3.0, timeout: int = 60, max_retries: int = 2,
                 env_path: str = ".env"):
        if api_key is None:
            env = load_env(env_path)
            api_key = env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        self.api_key = api_key
        self.model = model
        self.budget_usd = float(budget_usd)
        self.spent_usd = 0.0
        self.total_tokens = 0
        self.calls = 0
        self.failures = 0
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def remaining(self) -> float:
        return self.budget_usd - self.spent_usd

    def _price(self, model: str):
        return PRICE_TABLE.get(model, DEFAULT_PRICE)

    def _cost(self, model: str, pt: int, ct: int, reported: Optional[float]) -> float:
        if reported is not None:
            return float(reported)
        pp, pc = self._price(model)
        return pt / 1e6 * pp + ct / 1e6 * pc

    def chat(self, messages: List[dict], model: Optional[str] = None,
             max_tokens: int = 512, temperature: float = 0.0,
             json_mode: bool = False, preallocate_usd: float = 0.002) -> LLMResponse:
        model = model or self.model
        if not self.api_key:
            return LLMResponse("", 0, 0, 0.0, model, False, "no_api_key")
        if self.spent_usd + preallocate_usd > self.budget_usd:
            raise BudgetExceeded(
                f"budget {self.budget_usd:.2f} would be exceeded (spent {self.spent_usd:.4f})"
            )
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": temperature}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                   "HTTP-Referer": "https://localhost/clinical-belief-harness",
                   "X-Title": "ClinicalBeliefHarness"}
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=self.timeout)
                if r.status_code == 402 or r.status_code == 429:
                    last_err = f"http_{r.status_code}"
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if r.status_code != 200:
                    last_err = f"http_{r.status_code}:{r.text[:120]}"
                    time.sleep(1.0 * (attempt + 1))
                    continue
                data = r.json()
                text = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage", {}) or {}
                pt = int(usage.get("prompt_tokens", 0))
                ct = int(usage.get("completion_tokens", 0))
                cost = self._cost(model, pt, ct, usage.get("cost"))
                self.spent_usd += cost
                self.total_tokens += pt + ct
                self.calls += 1
                return LLMResponse(text, pt, ct, cost, model, True, None)
            except Exception as e:  # network/parse
                last_err = f"{type(e).__name__}:{str(e)[:120]}"
                time.sleep(1.0 * (attempt + 1))
        self.failures += 1
        return LLMResponse("", 0, 0, 0.0, model, False, last_err)

    def usage_summary(self) -> dict:
        return {"calls": self.calls, "failures": self.failures,
                "total_tokens": self.total_tokens, "spent_usd": round(self.spent_usd, 4),
                "budget_usd": self.budget_usd, "remaining_usd": round(self.remaining, 4)}
