# Clinical Belief Evolution Harness (pilot implementation)

A reproducible harness for studying whether a medical agent can maintain a
reliable **diagnostic belief state**, use it to choose **information-gathering
actions**, and — later — improve its **belief-update mechanism** across cases.

This repository implements the engineering foundation and the **RQ1 (belief)**
and **RQ2 (action)** pilots from
`Clinical_Belief_Evolution_Harness_Experimental_Protocol.md` on **DDxPlus**.
RQ3 (evolution) and RQ4 (verified RSI) scaffolding is stubbed but not the focus
of this delivery; the protocol is explicit that RQ1 → RQ2 → RQ3 must be proven
in order.

> **Honesty note (per protocol §0.2 / §10).** Nothing here claims the model
> softmax equals a true clinical prevalence, that DDxPlus per-case
> `DIFFERENTIAL_DIAGNOSIS` is a true intermediate posterior, or that any learned
> increment is a clinical log-likelihood. All results are offline, simulated and
> retrospective. The headline pilot finding is reported as-is even where the
> research model does **not** beat a simple baseline.

---

## What is implemented

| Protocol ticket | Component | File | Status |
|---|---|---|---|
| T01 | `DDxPlusDatasetAdapter` (223 evidences → 972 binary atoms; B/C/M values; question families) | `src/cbh/data/ddxplus_convert.py` | done |
| T02 | `SealedDDxEnvironment` (private labels, reset/step, no future leak, dup/illegal handling, unknown≠negative) | `src/cbh/envs/ddxplus.py` | done |
| T03 | `TrajectoryLogger` (per-turn JSONL + full-prob NPZ + run meta) | `src/cbh/utils/logging.py` | done |
| T04 | `FixedEvidenceGenerator` (random / greedy-EIG / reverse-EIG orders; split-inheriting) | `src/cbh/data/prefix_generator.py` | done |
| T05 | `BeliefNB` (smoothed priors/likelihoods, duplicate-invariant) | `src/cbh/beliefs/naive_bayes.py` | done |
| T06 | Recompute classifiers (`RecomputeLogReg`, `RecomputeMLP`, temperature calibration) | `src/cbh/beliefs/recompute.py` | done |
| T07 | `NeuralBeliefUpdater` (`log b + Δ`, BPTT, explicit old state, clipping) | `src/cbh/beliefs/neural_update.py` | done |
| T08 | `BeliefMetrics` (NLL/Brier/ECE/Top-k/JS/recovery/re-entry + patient bootstrap) | `src/cbh/eval/belief.py` | done |
| T09 | `EIGPolicy`, `RandomPolicy`, `FixedOrderPolicy`, `LLMPolicy` (C1/C2) | `src/cbh/policies/` | done |
| — | Mode A/B/C runner | `src/cbh/agents/runner.py` | done |
| T10–T14 | External baselines, adapters, experience engine, RSI registry, external validators | `src/cbh/{adapters,evolve}` | stubbed (later sprints) |

Control conditions from §1.2 that are runnable today: **C0** (direct, via
final-turn belief), **C3** (Naive Bayes), **C4** (recompute MLP/LogReg),
**C5** (neural updater), **C1/C2** (interactive LLM / LLM-reported belief),
with **fixed-EIG** and **random** action policies.

---

## Data & leakage defence

* Source: DDxPlus **English** release (figshare schema; CSV mirror
  `aai530-group6/ddxplus`, CC-BY-4.0). Raw SHA256 recorded in
  `data/manifests/ddxplus_v1.json`.
* Official `train`/`validate`/`test` boundaries are **never** crossed.
  `train` is sub-split by patient into `fit` / `discovery` / `registration`;
  `validate` is used only for model selection / temperature calibration;
  `test` is **blind** (run once, at the end).
* Initial state per case = `AGE`, `SEX`, `INITIAL_EVIDENCE` only. `PATHOLOGY`,
  `DIFFERENTIAL_DIAGNOSIS` and un-revealed `EVIDENCES` stay sealed inside the
  environment and are reachable only through `ground_truth()` (evaluator-only).
* `unknown` (never asked) is encoded by the observation **mask** and is distinct
  from `negative` (asked, value absent). Closed-world negative fill is flagged
  `synthetic_closed_world=True` and must not be ported to real EHR.
* Asking a question family twice returns the same public atoms and flags
  `duplicate=True`; belief estimators key off the observed **set**, so repeat
  questions cannot double-count likelihood (asserted in tests).

Encoding: 208 binary evidences → 1 atom each; 10 categorical → one-hot;
5 multi-choice → multi-hot. **972 atoms**, **209 question families**, **49
diseases**. An `ASK` targets a `code_question` and reveals all member
evidences (this is how DDxPlus question dependencies are honoured).

---

## Install & run

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -e ".[train,dev]"                          # numpy/torch/matplotlib

# 1) prepare splits + provenance manifest (streams the raw CSVs)
PYTHONPATH=src python3 scripts/prepare_data.py \
  --fit 30000 --discovery 4000 --registration 4000 --validate 6000 --test 3000

# 2) train belief models (fit trains, validate calibrates temperature)
PYTHONPATH=src python3 scripts/train_belief.py \
  --models nb,logreg,mlp,neural --fit-patients 10000 --max-reveals 6 --out models

# 3) RQ1 fixed-evidence (Mode A) + Fig.2 curves + paired bootstrap vs NB
PYTHONPATH=src python3 scripts/run_episodes.py --mode fixed \
  --split validate --models nb,logreg,mlp,neural --max-cases 1000 --bootstrap 2000

# 4) RQ1 mechanism stress tests (Mode B): order-swap JS, duplicate-drift JS
PYTHONPATH=src python3 scripts/run_episodes.py --mode counterfactual \
  --split validate --models nb,logreg,mlp,neural --max-cases 400

# 5) RQ2 online interactive (Mode C): random vs EIG vs cost-aware EIG
PYTHONPATH=src python3 scripts/run_episodes.py --mode online \
  --split validate --models nb --policies random,eig,eig_cost --max-cases 300 --budget 6

# 6) RQ2 with the LLM policy (C1 = llm, C2 = llm_belief). HARD $ cap enforced.
PYTHONPATH=src python3 scripts/run_episodes.py --mode online --llm \
  --split validate --models nb --policies llm,llm_belief \
  --llm-model qwen/qwen-2.5-7b-instruct --max-cases 120 --budget 6 --budget-usd 3.0

# 7) consolidate everything into runs/_report/{REPORT.md,*.png,results_summary.json}
PYTHONPATH=src python3 scripts/evaluate.py

# tests (25 assertions across secrecy / oracle / beliefs / splits / replay / metrics)
cd tests && for t in test_*.py; do python3 $t; done
```

`.env` supplies `OPENROUTER_API_KEY`. The LLM client tracks cumulative spend and
raises `BudgetExceeded` before any call that would cross `--budget-usd`.

---

## Pilot results (development split = `validate`; NOT the blind test)

Numbers below are from the committed pilot run
(`runs/_report/REPORT.md`). They are **development** results: the official
`test` split is held blind for a single final evaluation.

### RQ1 — fixed-evidence belief quality (random disclosure order, T=6, N=1000)

| belief model | final NLL ↓ | Brier ↓ | Top-1 ↑ | Top-3 ↑ | ECE ↓ | NLL 95% CI |
|---|---|---|---|---|---|---|
| **Naive Bayes (C3)** | **1.4711** | **0.5388** | **0.548** | **0.747** | 0.033 | [1.377, 1.564] |
| Recompute LogReg (C4) | 1.7564 | 0.6162 | 0.475 | 0.675 | 0.028 | [1.668, 1.845] |
| Recompute MLP (C4) | 1.6686 | 0.5878 | 0.492 | 0.688 | 0.033 | [1.581, 1.763] |
| Neural Updater (C5) | 1.6711 | 0.5950 | 0.483 | 0.680 | **0.026** | [1.583, 1.762] |

**Interpretation (reported honestly, per §10 Gate 1).** Naive Bayes is the
strongest belief model on DDxPlus. This is expected, not a bug: DDxPlus patients
are synthesized by a rule-based system in which evidences are close to
conditionally independent given the pathology, so NB is near the data-generating
optimum by construction. The recompute MLP/LogReg and the recurrent neural
updater do **not** beat it under this pilot's training budget. The neural
updater, after adding early-stopping / best-validate checkpoint selection to
curb overfitting, lands at NLL 1.6711 — statistically indistinguishable from the
recompute MLP (1.6686) and clearly behind NB. Per the protocol we therefore do
**not** claim a belief-update breakthrough; the neural updater needs more
capacity/training and a mechanism-level diagnostic before any such claim.
Paired patient-level bootstraps (2000 resamples, clustered by patient) put all
three challengers behind NB with p = 1.000 (Δ NLL: LogReg +0.2852, MLP +0.1975,
neural +0.2000), confirming the NB advantage is not a tie.

### RQ1 — mechanism stress tests (Mode B)

| belief model | order-swap JS | duplicate-drift JS |
|---|---|---|
| Naive Bayes | 0.00000 | 0.000000 |
| Recompute MLP | 0.00000 | 0.000000 |
| **Neural Updater** | **0.02404** | **0.039376** |

The recompute models (NB/MLP) are **order-invariant by construction** (they read
the observed set, not a running state), so swapping disclosure order leaves the
final belief unchanged (JS = 0), and re-asking causes no drift (JS = 0) — the
desired no-double-count behaviour. The recurrent neural updater, in contrast,
shows measurable **order-dependence** (order-swap JS = 0.024) and
**duplicate-drift** (JS = 0.039): re-stating the same fact moves its belief even
though no new information arrived. This is a concrete mechanism defect, not a
tie — it is exactly the anchoring/double-counting failure the protocol's Mode B
is designed to surface, and it is the first thing to fix before scaling the
neural updater.

### RQ2 — online interactive (budget B=6, N=300)

| belief + policy | Accuracy@B ↑ | Top-3@B ↑ | mean asks ↓ | final NLL ↓ | invalid |
|---|---|---|---|---|---|
| NB + random | 0.573 | 0.740 | 6.00 | 1.304 | 0 |
| **NB + EIG** | **0.943** | **0.977** | 3.43 | 0.181 | 0 |
| **NB + cost-aware EIG** | **0.943** | **0.977** | **1.99** | 0.181 | 0 |

**Interpretation.** Holding the belief fixed (NB) and only changing the action
policy isolates the belief→action link: expected-information-gain questioning
lifts accuracy from 57% to 94% **and** cuts the number of questions, and the
cost-aware variant matches accuracy at ~2 asks/patient. This is the cleanest
positive result of the pilot and directly supports RQ2's causal question.

### RQ2 — LLM policy (C1 vs C2, Qwen-2.5-7B-instruct)

| belief + policy | Accuracy@B ↑ | Top-3@B ↑ | mean asks ↓ | final NLL ↓ | invalid |
|---|---|---|---|---|---|
| NB + LLM (C1, no belief text) | 0.733 | 0.867 | 5.92 | 0.807 | 0 |
| NB + LLM-belief (C2, belief in prompt) | 0.733 | **0.892** | 5.88 | **0.782** | 0 |

The OpenRouter-backed LLM policy (Qwen-2.5-7B-instruct, the closest available
backbone to the protocol's Qwen3-8B) sits between random and EIG. Injecting the
calibrated NB belief into the prompt (C2) gives a small Top-3 / NLL edge over the
no-belief LLM (C1) but does not close the gap to EIG — the LLM asks far more
questions and still under-selects the highest-information one. Both variants ran
with 0 invalid actions and 0 JSON parse failures. Total LLM spend across both
conditions was **$0.1485** (well under the $3 cap).

### Failure audit (§10, random disclosure order)

| belief model | wrong-initial-pool | re-entry given wrong pool | overconfident-wrong | correct→wrong drift | recovery (wrong@t0) |
|---|---|---|---|---|---|
| Naive Bayes | 0.258 | **0.314** | 0.082 | **0.026** | **0.178** |
| Recompute LogReg | 0.241 | 0.461 | 0.089 | 0.189 | 0.164 |
| Recompute MLP | 0.241 | 0.473 | 0.081 | 0.162 | 0.164 |
| Neural Updater | 0.239 | 0.285 | **0.104** | 0.150 | 0.144 |

NB shows by far the lowest **correct→wrong drift** (0.026 vs 0.15–0.19 for the
learned models) and the best recovery from a wrong initial pool. The neural
updater has the highest **overconfident-wrong** rate (0.104), consistent with the
Mode-B finding that its recurrent state can lock onto an early anchor.

---

## Go / No-Go decision (protocol §10 gates)

* **Gate 1 — belief quality (RQ1): NO-GO for a belief-update claim.** The
  neural updater does not beat Naive Bayes (Δ NLL +0.2000, p = 1.000) and only
  ties the recompute MLP. Mode B further shows it is order-dependent and
  duplicate-unstable. We do **not** promote the neural belief mechanism; the
  next iteration must fix duplicate-invariance (e.g. set-pooled Δ over the
  observed set) and add capacity/training before re-testing.
* **Gate 2 — belief→action (RQ2): GO.** With belief held fixed, EIG questioning
  cleanly improves accuracy (0.573→0.943) and reduces cost. The harness, sealed
  environment, EIG observation model and LLM-budget plumbing are all validated
  and reusable, so the action-policy track is cleared to proceed.
* **Overall:** the *engineering foundation* (sealed env, leakage defence,
  metrics, patient-level bootstrap, budget-safe LLM) is delivered and tested;
  the *scientific* belief-update hypothesis is **not yet supported** and is
  reported as such rather than overclaimed. RQ3/RQ4 remain stubbed pending a
  Gate-1 pass.

---

## Design decisions worth flagging

* **NB as a real competitor, not a strawman.** On synthetic DDxPlus, NB is close
  to optimal; treating it as the bar to beat is the scientifically honest move.
* **Recompute vs recurrent.** The recompute classifiers (C4) exist specifically
  to catch a recurrent updater that accumulates its own errors; the neural
  updater (C5) is the research model and is held to that control.
* **Set-based beliefs are order-invariant.** This is why order-swap JS is ~0 for
  NB/MLP; order/anchoring stress tests target the recurrent model.
* **EIG observation model is fit-train only.** The predictive outcome
  distribution used by `EIGPolicy` comes from the NB likelihoods fitted on
  `fit`; it never queries a test patient's hidden answers.
* **Patient-level statistics.** CIs and paired tests resample whole patients,
  never `(patient, turn)` pairs, because orders/turns are repeated measures.

---

## Limitations (must be stated in any write-up)

Synthetic→real domain gap; missingness is not at random in real EHR; the 49-way
closed softmax cannot represent comorbidity or unknown disease; disclosure turn
≠ physiological time; probabilities ≠ explanations; LLM-reported numbers can be
miscalibrated; potential pretraining contamination of public cases; the
high-risk-utility proxy is a simulated cost model, not real harm. See protocol
§12. This delivery does **not** run on real patients and does **not** provide
diagnosis.

---

## Layout

```
src/cbh/
  schemas.py                 Action / Evidence / BeliefState / PublicObservation + Protocols
  data/ddxplus_convert.py    CSV -> sealed atom arrays + schema + manifest (T01)
  data/prefix_generator.py   disclosure orders + prefix states (T04)
  envs/ddxplus.py            SealedDDxEnvironment (T02)
  beliefs/{base,naive_bayes,recompute,neural_update,build}.py   (T05-T07)
  policies/{eig,random,llm}.py                                  (T09)
  agents/runner.py           Mode A / Mode C episode loops
  eval/belief.py             metrics + patient bootstrap (T08)
  utils/{llm_client,logging,reproducibility}.py
scripts/{prepare_data,train_belief,run_episodes,evaluate}.py
tests/test_{secrecy,ddx_oracle,beliefs,split_integrity,replay,metrics}.py
configs/experiments/{rq1_fixed,rq2_online}.yaml
data/{raw,processed,manifests}/   models/   runs/<experiment>/
```
