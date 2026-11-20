"""Consolidate run outputs into a single report + figures (section 7.5).

Reads runs/<mode>_<split>_s<seed>/ directories produced by run_episodes.py and
emits:
  * results_summary.json -- headline metrics across modes/models/policies
  * fig2_fixed_curves.png (already written by run_episodes; regenerated here)
  * fig4_accuracy_cost.png -- Accuracy@B vs mean asks for online policies
  * reliability_diagram.png -- top-label reliability for the fixed-evidence run
  * REPORT.md -- human-readable summary with the Go/No-Go framing
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from cbh.eval import belief as M  # noqa: E402


def reliability_plot(probs: np.ndarray, labels: np.ndarray, out_png: str, title: str, n_bins: int = 15):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    conf = probs.max(1)
    acc = (probs.argmax(1) == labels).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    xs, ys, ns = [], [], []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (conf >= lo) & (conf < hi) if i < n_bins - 1 else (conf >= lo) & (conf <= hi)
        if m.sum() == 0:
            continue
        xs.append((lo + hi) / 2); ys.append(acc[m].mean()); ns.append(m.sum())
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "k--", label="perfect")
    ax.bar(xs, ys, width=1.0 / n_bins, alpha=0.6, label="model")
    ax.set_xlabel("confidence"); ax.set_ylabel("accuracy"); ax.set_title(title)
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_png, dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--out", default="runs/_report")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    summary = {}

    fixed_dirs = sorted(glob.glob(os.path.join(args.runs_root, "fixed_*")))
    online_dirs = sorted(glob.glob(os.path.join(args.runs_root, "online_*")))
    cf_dirs = sorted(glob.glob(os.path.join(args.runs_root, "counterfactual_*")))

    # ---- fixed (RQ1) ----
    for d in fixed_dirs:
        mp = os.path.join(d, "metrics_fixed.json")
        if os.path.exists(mp):
            summary.setdefault("fixed", {})[os.path.basename(d)] = json.load(open(mp))
        pp = os.path.join(d, "paired_vs_nb.json")
        if os.path.exists(pp):
            summary.setdefault("paired_vs_nb", {})[os.path.basename(d)] = json.load(open(pp))
        # reliability diagram from the primary (random-order) probs of each model
        for npz in glob.glob(os.path.join(d, "probs_*.npz")):
            z = np.load(npz, allow_pickle=True)
            probs = z["probs"][:, 0].astype(np.float64)  # random order
            labels = z["labels"]
            name = os.path.basename(npz)[len("probs_"):-4]
            N, T, K = probs.shape
            reliability_plot(probs[:, -1].reshape(N, K), labels,
                             os.path.join(args.out, f"reliability_{name}.png"),
                             f"{name} final-turn reliability")
            from cbh.eval.failure_audit import audit_fixed
            summary.setdefault("failure_audit", {})[name] = audit_fixed(probs, labels)

    # ---- counterfactual (RQ1 mechanism) ----
    for d in cf_dirs:
        mp = os.path.join(d, "metrics_counterfactual.json")
        if os.path.exists(mp):
            summary.setdefault("counterfactual", {})[os.path.basename(d)] = json.load(open(mp))

    # ---- online (RQ2) ----
    pts = []
    for d in online_dirs:
        # read the preserved per-run metrics.json files (robust to the
        # consolidated metrics_online.json being rewritten by a later invocation)
        per_run = {}
        for sub in sorted(glob.glob(os.path.join(d, "online_*"))):
            mpath = os.path.join(sub, "metrics.json")
            if os.path.exists(mpath):
                m = json.load(open(mpath))
                key = f"{m['belief']}+{m['policy']}"
                per_run[key] = m
        if not per_run:
            mp = os.path.join(d, "metrics_online.json")
            if os.path.exists(mp):
                per_run = json.load(open(mp))
        if per_run:
            summary.setdefault("online", {})[os.path.basename(d)] = per_run
            for k, v in per_run.items():
                pts.append((k, v["mean_asks"], v["accuracy_at_B"]))
    if pts:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 5))
        for k, x, y in pts:
            ax.scatter(x, y, s=70)
            ax.annotate(k, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
        ax.set_xlabel("mean asks (cost)"); ax.set_ylabel("Accuracy@B")
        ax.set_title("RQ2: Accuracy vs Cost by belief+policy")
        ax.grid(alpha=0.3); ax.set_ylim(0, 1)
        fig.tight_layout(); fig.savefig(os.path.join(args.out, "fig4_accuracy_cost.png"), dpi=110)
        plt.close(fig)

    json.dump(summary, open(os.path.join(args.out, "results_summary.json"), "w"), indent=2, default=float)

    # ---- REPORT.md ----
    lines = ["# Pilot results summary", ""]
    if "fixed" in summary:
        lines += ["## RQ1 - fixed-evidence belief quality (random disclosure order)", "",
                  "| model | NLL | Brier | Top-1 | Top-3 | ECE | NLL 95% CI |", "|---|---|---|---|---|---|---|"]
        for run, models in summary["fixed"].items():
            for name, r in models.items():
                p = r["primary_random_order"]; ci = r["nll_ci"]
                lines.append(f"| {name} | {p['nll']:.4f} | {p['brier']:.4f} | {p['final_top1']:.3f} | "
                             f"{p['final_top3']:.3f} | {p['ece_ece']:.3f} | [{ci['lo']:.3f},{ci['hi']:.3f}] |")
        lines.append("")
    if "counterfactual" in summary:
        lines += ["## RQ1 - mechanism stress tests (Mode B)", "",
                  "| model | order-swap JS | duplicate-drift JS |", "|---|---|---|"]
        for run, models in summary["counterfactual"].items():
            for name, r in models.items():
                lines.append(f"| {name} | {r['order_swap_JS_mean']:.5f} | {r['duplicate_drift_JS_mean']:.6f} |")
        lines.append("")
    if "online" in summary:
        lines += ["## RQ2 - online interactive (belief + policy)", "",
                  "| belief+policy | Acc@B | Top-3@B | mean asks | final NLL | invalid |", "|---|---|---|---|---|---|"]
        for run, models in summary["online"].items():
            for name, r in models.items():
                lines.append(f"| {name} | {r['accuracy_at_B']:.3f} | {r['top3_at_B']:.3f} | "
                             f"{r['mean_asks']:.2f} | {r['final_nll']:.3f} | {r['invalid_actions']} |")
        lines.append("")
    if "failure_audit" in summary:
        lines += ["## Failure audit (section 10, random disclosure order)", "",
                  "| model | wrong-initial-pool | re-entry given wrong pool | overconfident-wrong | correct->wrong | recovery(wrong@t0) |",
                  "|---|---|---|---|---|---|"]
        for name, a in summary["failure_audit"].items():
            lines.append(f"| {name} | {a['wrong_initial_pool_rate']:.3f} | "
                         f"{a['reentry_given_wrong_pool']:.3f} | {a['overconfident_wrong_rate']:.3f} | "
                         f"{a['correct_to_wrong_rate']:.3f} | {a['recovery_rate_wrong0']:.3f} |")
        lines.append("")
    open(os.path.join(args.out, "REPORT.md"), "w").write("\n".join(lines))
    print("report ->", args.out)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
