"""Train belief models (NB, LogReg, MLP, NeuralUpdater) and save checkpoints.

Fit partition trains weights; the validate partition calibrates temperature.
The official test split is never touched here.

Usage:
  python scripts/train_belief.py --models nb,logreg,mlp,neural \
      --fit-patients 12000 --max-reveals 6 --out models
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from cbh.beliefs.build import (  # noqa: E402
    build_prefix_dataset, build_val_sequences, load_schema, make_generator, train_nb,
)
from cbh.beliefs.naive_bayes import BeliefNB  # noqa: E402
from cbh.beliefs.neural_update import BeliefNeuralUpdater  # noqa: E402
from cbh.beliefs.recompute import RecomputeLogReg, RecomputeMLP  # noqa: E402
from cbh.data.ddxplus_convert import load_split  # noqa: E402
from cbh.utils.reproducibility import set_global_seed  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--out", default="models")
    ap.add_argument("--models", default="nb,logreg,mlp,neural")
    ap.add_argument("--fit-patients", type=int, default=12000)
    ap.add_argument("--val-patients", type=int, default=1500)
    ap.add_argument("--max-reveals", type=int, default=6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--neural-epochs", type=int, default=6)
    args = ap.parse_args()

    set_global_seed(args.seed)
    os.makedirs(args.out, exist_ok=True)
    schema = load_schema(os.path.join(args.processed, "schema.json"))
    diseases = schema["diseases"]
    total_atoms = schema["total_atoms"]
    K = len(diseases)

    fit = load_split(os.path.join(args.processed, "fit.npz"))
    val = load_split(os.path.join(args.processed, "validate.npz"))
    gen = make_generator(schema, fit, K)
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    summary = {"seed": args.seed, "fit_patients": args.fit_patients,
               "max_reveals": args.max_reveals, "models": {}}

    if "nb" in models:
        t = time.time()
        nb = train_nb(fit, diseases, total_atoms, alpha=1.0)
        nb.save(os.path.join(args.out, "nb.npz"))
        summary["models"]["nb"] = {"train_sec": round(time.time() - t, 1), "alpha": 1.0}
        print(f"[nb] trained in {summary['models']['nb']['train_sec']}s")

    need_prefix = {"logreg", "mlp", "neural"} & set(models)
    X = y = seqs = None
    Xv = yv = vseqs = None
    if need_prefix:
        t = time.time()
        X, y, seqs = build_prefix_dataset(fit, gen, args.max_reveals, args.fit_patients,
                                          orders_per_patient=1, seed=args.seed)
        Xv, yv, vseqs = build_prefix_dataset(val, gen, args.max_reveals, args.val_patients,
                                             orders_per_patient=1, seed=args.seed + 1)
        print(f"[prefix] fit X={X.shape} val X={Xv.shape} in {round(time.time()-t,1)}s")
        summary["prefix"] = {"fit_rows": int(X.shape[0]), "val_rows": int(Xv.shape[0]),
                             "features": int(X.shape[1]), "build_sec": round(time.time() - t, 1)}

    if "logreg" in models:
        t = time.time()
        m = RecomputeLogReg(diseases, X.shape[1], seed=args.seed, epochs=args.epochs, lr=3e-3)
        m.fit(X, y, Xv, yv, verbose=True)
        m.save(os.path.join(args.out, "logreg.pt"))
        summary["models"]["logreg"] = {"train_sec": round(time.time() - t, 1),
                                       "temperature": round(m.temperature, 3)}
        print(f"[logreg] T={m.temperature:.3f} in {summary['models']['logreg']['train_sec']}s")

    if "mlp" in models:
        t = time.time()
        m = RecomputeMLP(diseases, X.shape[1], hidden=256, seed=args.seed,
                         epochs=args.epochs, lr=1e-3)
        m.fit(X, y, Xv, yv, verbose=True)
        m.save(os.path.join(args.out, "mlp.pt"))
        summary["models"]["mlp"] = {"train_sec": round(time.time() - t, 1),
                                    "temperature": round(m.temperature, 3)}
        print(f"[mlp] T={m.temperature:.3f} in {summary['models']['mlp']['train_sec']}s")

    if "neural" in models:
        t = time.time()
        nu = BeliefNeuralUpdater(diseases, total_atoms, d_model=128, hidden=256, seed=args.seed)
        nu.fit_prefixes(seqs, val_seqs=vseqs, epochs=args.neural_epochs, lr=1e-3,
                        batch_size=48, verbose=True, seed=args.seed)
        nu.save(os.path.join(args.out, "neural.pt"))
        summary["models"]["neural"] = {"train_sec": round(time.time() - t, 1),
                                       "temperature": round(nu.temperature, 3)}
        print(f"[neural] T={nu.temperature:.3f} in {summary['models']['neural']['train_sec']}s")

    json.dump(summary, open(os.path.join(args.out, "train_summary.json"), "w"), indent=2)
    print("saved ->", args.out)


if __name__ == "__main__":
    main()
