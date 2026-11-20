#!/usr/bin/env bash
# End-to-end pilot: prepare -> train -> RQ1 fixed -> Mode B -> RQ2 online (+LLM) -> report.
# The LLM stage is budget-capped; set BUDGET_USD (default 3.0) and LLM_MODEL.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=src
BUDGET_USD="${BUDGET_USD:-3.0}"
LLM_MODEL="${LLM_MODEL:-qwen/qwen-2.5-7b-instruct}"
SPLIT="${SPLIT:-validate}"

echo "== prepare data =="
python3 scripts/prepare_data.py --fit 30000 --discovery 4000 --registration 4000 --validate 6000 --test 3000

echo "== train beliefs =="
python3 scripts/train_belief.py --models nb,logreg,mlp,neural --fit-patients 10000 --max-reveals 6 --out models

echo "== RQ1 fixed evidence (Mode A) =="
python3 scripts/run_episodes.py --mode fixed --split "$SPLIT" --models nb,logreg,mlp,neural --max-cases 1000 --bootstrap 2000

echo "== RQ1 mechanism stress (Mode B) =="
python3 scripts/run_episodes.py --mode counterfactual --split "$SPLIT" --models nb,logreg,mlp,neural --max-cases 400

echo "== RQ2 online, non-LLM policies (Mode C) =="
python3 scripts/run_episodes.py --mode online --split "$SPLIT" --models nb --policies random,eig,eig_cost --max-cases 300 --budget 6

echo "== RQ2 online, LLM policies (C1/C2), budget \$${BUDGET_USD} =="
python3 scripts/run_episodes.py --mode online --llm --split "$SPLIT" --models nb \
  --policies llm,llm_belief --llm-model "$LLM_MODEL" --max-cases 120 --budget 6 --budget-usd "$BUDGET_USD"

echo "== consolidate report =="
python3 scripts/evaluate.py
echo "DONE -> runs/_report/REPORT.md"
