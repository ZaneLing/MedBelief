"""Run experiments: Mode A (fixed evidence), Mode B (counterfactual), Mode C (online).

Examples
--------
  # RQ1 fixed-evidence over all belief models + 3 disclosure orders
  python scripts/run_episodes.py --mode fixed --split validate --max-cases 1000

  # RQ1 paired counterfactual stress (order-swap / duplicate)
  python scripts/run_episodes.py --mode counterfactual --split validate --max-cases 400

  # RQ2 online interactive (random / EIG policies; add --llm for the LLM policy)
  python scripts/run_episodes.py --mode online --split validate --max-cases 200 --budget 6
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from cbh.agents.runner import (  # noqa: E402
    obs_from_prefix, run_fixed_case, run_fixed_split, run_online_split,
)
from cbh.beliefs.build import load_schema, make_generator  # noqa: E402
from cbh.beliefs.naive_bayes import BeliefNB  # noqa: E402
from cbh.beliefs.neural_update import BeliefNeuralUpdater  # noqa: E402
from cbh.beliefs.recompute import _TorchRecompute  # noqa: E402
from cbh.data.ddxplus_convert import load_split  # noqa: E402
from cbh.envs.ddxplus import SealedDDxEnvironment  # noqa: E402
from cbh.eval import belief as M  # noqa: E402
from cbh.policies.eig import EIGPolicy  # noqa: E402
from cbh.policies.random import RandomPolicy  # noqa: E402
from cbh.utils.logging import TrajectoryLogger  # noqa: E402
from cbh.utils.reproducibility import config_hash, set_global_seed  # noqa: E402

ORDER_MODES = ["random_valid", "greedy_eig_valid", "reverse_eig_valid"]


def load_belief(name: str, models_dir: str, schema: dict):
    diseases = schema["diseases"]
    total_atoms = schema["total_atoms"]
    if name == "nb":
        return BeliefNB.load(os.path.join(models_dir, "nb.npz"))
    if name in ("logreg", "mlp"):
        return _TorchRecompute.load(os.path.join(models_dir, f"{name}.pt"))
    if name == "neural":
        nu = BeliefNeuralUpdater(diseases, total_atoms)
        nu.load(os.path.join(models_dir, "neural.pt"))
        return nu
    raise ValueError(name)


def per_patient_nll(probs_seq: np.ndarray, labels: np.ndarray):
    """probs_seq [N,T,K] -> list of per-patient mean-NLL arrays (for bootstrap)."""
    N, T, K = probs_seq.shape
    out = []
    for i in range(N):
        p = np.clip(probs_seq[i, np.arange(T), labels[i]], 1e-12, 1)
        out.append(-np.log(p))
    return out


def plot_curves(results: dict, labels: np.ndarray, out_png: str, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for name, res in results.items():
        probs = res["probs"]           # [N, modes, T, K]
        N, modes, T, K = probs.shape
        # average over order modes and patients -> per-turn metric
        nll_t, brier_t, top3_t = [], [], []
        for t in range(T):
            pt = probs[:, :, t, :].reshape(N * modes, K)
            yt = np.repeat(labels, modes)
            nll_t.append(M.nll(pt, yt))
            brier_t.append(M.brier(pt, yt))
            top3_t.append(M.topk_accuracy(pt, yt, 3))
        axes[0].plot(range(T), nll_t, marker="o", label=name)
        axes[1].plot(range(T), brier_t, marker="o", label=name)
        axes[2].plot(range(T), top3_t, marker="o", label=name)
    axes[0].set_title("NLL vs turn"); axes[0].set_xlabel("disclosure turn t")
    axes[1].set_title("Brier vs turn"); axes[1].set_xlabel("disclosure turn t")
    axes[2].set_title("Top-3 vs turn"); axes[2].set_xlabel("disclosure turn t")
    for ax in axes:
        ax.legend(); ax.grid(alpha=0.3)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def run_fixed(args, schema, split, gen, out_dir):
    diseases = schema["diseases"]
    results = {}
    labels = split["pathology_idx"][: args.max_cases] if args.max_cases else split["pathology_idx"]
    for name in args.models.split(","):
        name = name.strip()
        if not name:
            continue
        t = time.time()
        belief = load_belief(name, args.models_dir, schema)
        res = run_fixed_split(split, gen, belief, orders_per_case=1,
                              max_reveals=args.max_reveals, order_seed=args.seed,
                              order_modes=ORDER_MODES, max_cases=args.max_cases)
        probs = res["probs"]              # [N, modes, T, K]
        N, modes, T, K = probs.shape
        # headline: average over modes -> treat each (patient,mode) as a measure
        summ = {}
        for mi, mode in enumerate(ORDER_MODES):
            summ[mode] = M.summarize(probs[:, mi].astype(np.float64), res["labels"])
        # primary pooled across modes (random order is the pre-registered primary)
        primary = M.summarize(probs[:, 0].astype(np.float64), res["labels"])
        pp = per_patient_nll(probs[:, 0].astype(np.float64), res["labels"])
        mean_nll, lo, hi = M.patient_bootstrap_ci(pp, n_boot=args.bootstrap, seed=args.seed)
        results[name] = {
            "probs": probs, "primary_random_order": primary, "by_order": summ,
            "nll_ci": {"mean": mean_nll, "lo": lo, "hi": hi},
            "train_eval_sec": round(time.time() - t, 1),
        }
        print(f"[fixed:{name}] random-order NLL={primary['nll']:.4f} "
              f"[{lo:.4f},{hi:.4f}] top1={primary['final_top1']:.3f} "
              f"top3={primary['final_top3']:.3f} ECE={primary['ece_ece']:.3f} "
              f"({results[name]['train_eval_sec']}s)")
        np.savez_compressed(os.path.join(out_dir, f"probs_{name}.npz"),
                            probs=probs, labels=res["labels"],
                            case_ids=np.asarray(res["case_ids"], dtype=object))
    metrics = {n: {k: v for k, v in r.items() if k != "probs"} for n, r in results.items()}
    json.dump(metrics, open(os.path.join(out_dir, "metrics_fixed.json"), "w"), indent=2, default=float)
    if len(results) >= 1:
        plot_curves(results, labels, os.path.join(out_dir, "fig2_fixed_curves.png"),
                    f"RQ1 fixed-evidence (split={args.split}, N={len(labels)})")
    # paired comparisons vs NB on random order
    if "nb" in results and len(results) > 1:
        base = per_patient_nll(results["nb"]["probs"][:, 0].astype(np.float64), labels)
        comp = {}
        for n, r in results.items():
            if n == "nb":
                continue
            other = per_patient_nll(r["probs"][:, 0].astype(np.float64), labels)
            comp[n] = M.paired_bootstrap_diff(other, base, n_boot=args.bootstrap, seed=args.seed)
        json.dump(comp, open(os.path.join(out_dir, "paired_vs_nb.json"), "w"), indent=2)
        print("[paired NLL vs NB] (negative = better than NB)")
        for n, c in comp.items():
            print(f"   {n}: diff={c['diff']:+.4f} CI[{c['ci_lo']:+.4f},{c['ci_hi']:+.4f}] p(a>=b)={c['p_a_ge_b']:.3f}")
    return metrics


def run_counterfactual(args, schema, split, gen, out_dir):
    """Mode B: order-swap JS and duplicate-drift JS (no LLM required)."""
    atoms = split["atoms"]; N = args.max_cases or len(atoms)
    out = {}
    for name in args.models.split(","):
        name = name.strip()
        if not name:
            continue
        belief = load_belief(name, args.models_dir, schema)
        order_js, dup_js = [], []
        for i in range(N):
            gt = atoms[i]; init = int(split["initial_evidence_idx"][i])
            age = int(split["age"][i]); sex = int(split["sex"][i])
            cid = str(split["case_ids"][i])
            # two random orders over the SAME first-T families -> same final set
            fams = gen.order(args.seed + i, "random_valid")[: args.max_reveals]
            oA = list(fams)
            oB = list(fams); np.random.default_rng(i).shuffle(oB)
            psA = run_fixed_case(gen, belief, gt, init, age, sex, oA, args.max_reveals, cid)
            psB = run_fixed_case(gen, belief, gt, init, age, sex, oB, args.max_reveals, cid)
            order_js.append(M.js_divergence(psA[-1], psB[-1]))
            # duplicate: reveal same families twice; belief should barely move
            dup_order = fams + fams
            psD = run_fixed_case(gen, belief, gt, init, age, sex, dup_order,
                                 2 * args.max_reveals, cid)
            mid = psD[args.max_reveals]
            dup_js.append(M.js_divergence(mid, psD[-1]))
        out[name] = {"order_swap_JS_mean": float(np.mean(order_js)),
                     "order_swap_JS_median": float(np.median(order_js)),
                     "duplicate_drift_JS_mean": float(np.mean(dup_js)),
                     "duplicate_drift_JS_median": float(np.median(dup_js)),
                     "n": N}
        print(f"[cf:{name}] order-swap JS={out[name]['order_swap_JS_mean']:.4f} "
              f"duplicate-drift JS={out[name]['duplicate_drift_JS_mean']:.5f} (ideal ~0)")
    json.dump(out, open(os.path.join(out_dir, "metrics_counterfactual.json"), "w"), indent=2)
    return out


def run_online(args, schema, split, gen, out_dir):
    diseases = schema["diseases"]
    didx = {d: i for i, d in enumerate(diseases)}
    total_atoms = schema["total_atoms"]
    env = SealedDDxEnvironment(os.path.join(args.processed, f"{args.split}.npz"),
                               os.path.join(args.processed, "schema.json"),
                               max_asks=args.budget)
    case_ids = env.case_ids[: args.max_cases] if args.max_cases else env.case_ids
    fit = load_split(os.path.join(args.processed, "fit.npz"))
    family_atoms = __import__("cbh.data.prefix_generator", fromlist=["load_family_atoms"]).load_family_atoms(schema)

    policy_names = [p.strip() for p in args.policies.split(",") if p.strip()]
    all_metrics = {}
    llm_client = None
    if any(p.startswith("llm") for p in policy_names):
        from cbh.utils.llm_client import OpenRouterClient
        envd = {}
        if os.path.exists(args.env_file):
            for line in open(args.env_file):
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1); envd[k.strip()] = v.strip().strip('"').strip("'")
        llm_client = OpenRouterClient(api_key=envd.get("OPENROUTER_API_KEY"),
                                      model=args.llm_model, budget_usd=args.budget_usd)
        print(f"[llm] model={args.llm_model} budget=${args.budget_usd}")

    for belief_name in args.models.split(","):
        belief_name = belief_name.strip()
        if not belief_name:
            continue
        belief = load_belief(belief_name, args.models_dir, schema)
        # NB observation model for EIG policy
        nb = belief if isinstance(belief, BeliefNB) else BeliefNB.load(os.path.join(args.models_dir, "nb.npz"))
        for pol in policy_names:
            run_id = f"online_{belief_name}_{pol}_{args.split}_s{args.seed}"
            rdir = os.path.join(out_dir, run_id)
            logger = TrajectoryLogger(rdir, run_id, f"{belief_name}+{pol}", args.llm_model,
                                      belief.version, pol, args.seed, args.config_hash)
            if pol == "random":
                policy = RandomPolicy(seed=args.seed)
            elif pol == "eig":
                policy = EIGPolicy(np.exp(nb.log_p1), family_atoms)
            elif pol == "eig_cost":
                policy = EIGPolicy(np.exp(nb.log_p1), family_atoms, cost_per_ask=0.05, cost_aware=True)
            elif pol in ("llm", "llm_belief"):
                from cbh.policies.llm import LLMPolicy
                policy = LLMPolicy(llm_client, os.path.join(args.processed, "schema.json"),
                                   os.path.join(args.raw_dir, "release_conditions.json"),
                                   os.path.join(args.raw_dir, "release_evidences.json"),
                                   diseases, use_belief=(pol == "llm_belief"), seed=args.seed)
            else:
                raise ValueError(pol)
            t = time.time()
            results = run_online_split(env, belief, policy, case_ids, args.budget, logger,
                                       args.split, verbose=True)
            acc = float(np.mean([r["correct"] for r in results]))
            top3 = float(np.mean([r["true"] in np.asarray(diseases)[np.argsort(-r["final_probs"])[:3]]
                                  for r in results]))
            costs = [r["asks"] for r in results]
            nll = M.nll(np.stack([r["final_probs"] for r in results]),
                        np.asarray([r["true_idx"] for r in results]))
            metrics = {"belief": belief_name, "policy": pol, "n": len(results),
                       "accuracy_at_B": acc, "top3_at_B": top3, "final_nll": nll,
                       "mean_asks": float(np.mean(costs)), "budget": args.budget,
                       "invalid_actions": int(sum(r["invalid"] for r in results)),
                       "sec": round(time.time() - t, 1)}
            if llm_client is not None and pol.startswith("llm"):
                metrics["llm"] = llm_client.usage_summary()
                metrics["llm_policy_stats"] = policy.stats
                logger.add_llm_usage(llm_client.calls, llm_client.total_tokens, llm_client.spent_usd)
            all_metrics[f"{belief_name}+{pol}"] = metrics
            meta = logger.close()
            json.dump(metrics, open(os.path.join(rdir, "metrics.json"), "w"), indent=2, default=float)
            print(f"[online {belief_name}+{pol}] acc@B={acc:.3f} top3={top3:.3f} "
                  f"asks={metrics['mean_asks']:.2f} nll={nll:.3f} ({metrics['sec']}s)"
                  + (f" llm$={meta['llm_cost_usd']}" if pol.startswith('llm') else ""))
    # merge with any previously-written online metrics so separate invocations
    # (e.g. non-LLM policies, then LLM policies) accumulate rather than clobber.
    mpath = os.path.join(out_dir, "metrics_online.json")
    merged = {}
    if os.path.exists(mpath):
        try:
            merged = json.load(open(mpath))
        except Exception:
            merged = {}
    merged.update(all_metrics)
    json.dump(merged, open(mpath, "w"), indent=2, default=float)
    if llm_client is not None:
        print(f"[llm TOTAL] {llm_client.usage_summary()}")
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fixed", "online", "counterfactual"], default="fixed")
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--models-dir", default="models")
    ap.add_argument("--models", default="nb,logreg,mlp,neural")
    ap.add_argument("--policies", default="random,eig")
    ap.add_argument("--split", default="validate")
    ap.add_argument("--max-cases", type=int, default=1000)
    ap.add_argument("--max-reveals", type=int, default=6)
    ap.add_argument("--budget", type=int, default=6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--bootstrap", type=int, default=500)
    ap.add_argument("--out", default=None)
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--llm-model", default="qwen/qwen3-8b")
    ap.add_argument("--budget-usd", type=float, default=3.0)
    ap.add_argument("--env-file", default=".env")
    args = ap.parse_args()
    if not args.llm and "llm" in args.policies:
        args.policies = ",".join(p for p in args.policies.split(",") if not p.startswith("llm"))

    set_global_seed(args.seed)
    schema = load_schema(os.path.join(args.processed, "schema.json"))
    cfg = {k: v for k, v in vars(args).items()}
    args.config_hash = config_hash(cfg)
    out_dir = args.out or os.path.join("runs", f"{args.mode}_{args.split}_s{args.seed}")
    os.makedirs(out_dir, exist_ok=True)
    json.dump(cfg, open(os.path.join(out_dir, "config.json"), "w"), indent=2, default=str)

    fit = load_split(os.path.join(args.processed, "fit.npz"))
    gen = make_generator(schema, fit, len(schema["diseases"]))
    split = load_split(os.path.join(args.processed, f"{args.split}.npz"))

    if args.mode == "fixed":
        run_fixed(args, schema, split, gen, out_dir)
    elif args.mode == "counterfactual":
        run_counterfactual(args, schema, split, gen, out_dir)
    else:
        run_online(args, schema, split, gen, out_dir)
    print("outputs ->", out_dir)


if __name__ == "__main__":
    main()
