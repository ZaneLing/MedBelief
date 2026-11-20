"""Prepare DDxPlus splits + provenance manifest (Sprint 0 / T01).

Official split boundaries are respected: everything derived from `train` stays
in train, `validate` stays validate, `test` stays test and is only ever run
once at the very end (blind). Within `train` we carve a secondary
fit / discovery / registration partition by patient index (stable, no leakage
across the official boundary).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from cbh.data.ddxplus_convert import (  # noqa: E402
    ConditionSchema,
    EvidenceSchema,
    convert_csv,
    save_split,
    sha256_file,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--out-dir", default="data/processed")
    ap.add_argument("--manifest-dir", default="data/manifests")
    ap.add_argument("--fit", type=int, default=30000)
    ap.add_argument("--discovery", type=int, default=4000)
    ap.add_argument("--registration", type=int, default=4000)
    ap.add_argument("--validate", type=int, default=6000)
    ap.add_argument("--test", type=int, default=3000)
    ap.add_argument("--full", action="store_true", help="convert entire files (slow)")
    args = ap.parse_args()

    t0 = time.time()
    ev = EvidenceSchema(os.path.join(args.raw_dir, "release_evidences.json"))
    co = ConditionSchema(os.path.join(args.raw_dir, "release_conditions.json"))
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.manifest_dir, exist_ok=True)

    manifest = {
        "dataset": "ddxplus-en (figshare schema, HF csv mirror aai530-group6/ddxplus)",
        "license": "CC-BY-4.0",
        "schema_hash": ev.schema_hash(),
        "total_atoms": ev.total_atoms,
        "n_questions": len(ev.question_ids),
        "n_diseases": co.K,
        "disease_order": co.diseases,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "raw_sha256": {},
        "splits": {},
    }

    raw_files = {
        "release_evidences.json": os.path.join(args.raw_dir, "release_evidences.json"),
        "release_conditions.json": os.path.join(args.raw_dir, "release_conditions.json"),
    }
    for split_file in ["train", "validate", "test"]:
        p = os.path.join(args.raw_dir, f"{split_file}.csv")
        if os.path.exists(p):
            raw_files[f"{split_file}.csv"] = p
    for name, p in raw_files.items():
        manifest["raw_sha256"][name] = sha256_file(p)
        print(f"sha256 {name}: {manifest['raw_sha256'][name][:16]}...")

    # --- train -> fit / discovery / registration (secondary partition) ---
    train_need = args.fit + args.discovery + args.registration
    n_train = None
    if os.path.exists(os.path.join(args.raw_dir, "train.csv")):
        # stride so the sample is spread across the ~1.1M row file
        stride = 1 if args.full else max(1, 1_100_000 // max(train_need, 1))
        tr = convert_csv(
            os.path.join(args.raw_dir, "train.csv"), ev, co, "train",
            max_patients=train_need, stride=stride,
        )
        n_train = int(tr["n_seen"][0])
        idx = np.arange(len(tr["case_ids"]))
        fit_i = idx[: args.fit]
        disc_i = idx[args.fit : args.fit + args.discovery]
        reg_i = idx[args.fit + args.discovery : train_need]
        for nm, sel in [("fit", fit_i), ("discovery", disc_i), ("registration", reg_i)]:
            sub = {k: (v[sel] if k != "n_seen" else v) for k, v in tr.items()}
            path = save_split(args.out_dir, nm, sub)
            manifest["splits"][nm] = {"source": "train", "n": len(sel), "path": path}
            print(f"saved {nm}: {len(sel)} patients -> {path}")

    # --- validate (model selection / calibration) ---
    va = convert_csv(os.path.join(args.raw_dir, "validate.csv"), ev, co, "validate",
                     max_patients=args.validate,
                     stride=1 if args.full else max(1, 130_000 // max(args.validate, 1)))
    path = save_split(args.out_dir, "validate", va)
    manifest["splits"]["validate"] = {"source": "validate", "n": len(va["case_ids"]), "path": path}
    print(f"saved validate: {len(va['case_ids'])} -> {path}")

    # --- test (BLIND; run once at the end) ---
    te = convert_csv(os.path.join(args.raw_dir, "test.csv"), ev, co, "test",
                     max_patients=args.test,
                     stride=1 if args.full else max(1, 130_000 // max(args.test, 1)))
    path = save_split(args.out_dir, "test", te)
    manifest["splits"]["test"] = {"source": "test", "n": len(te["case_ids"]), "path": path, "blind": True}
    print(f"saved test (BLIND): {len(te['case_ids'])} -> {path}")

    # static schema artefacts needed by env/beliefs at runtime
    np.savez_compressed(
        os.path.join(args.out_dir, "schema.npz"),
        question_ids=np.asarray(ev.question_ids, dtype=object),
        evidence_ids=np.asarray(ev.evidence_ids, dtype=object),
        diseases=np.asarray(co.diseases, dtype=object),
        severity=np.asarray([co.severity[d] for d in co.diseases], dtype=np.int8),
    )
    json.dump(
        {
            "encodings": {
                e: {
                    "data_type": enc.data_type,
                    "start": enc.start,
                    "count": enc.count,
                    "code_question": enc.code_question,
                    "value_to_offset": enc.value_to_offset,
                    "default_offsets": enc.default_offsets,
                    "is_antecedent": enc.is_antecedent,
                    "question_en": enc.question_en,
                }
                for e, enc in ev.encodings.items()
            },
            "question_to_evidences": ev.question_to_evidences,
            "total_atoms": ev.total_atoms,
            "diseases": co.diseases,
            "severity": co.severity,
        },
        open(os.path.join(args.out_dir, "schema.json"), "w"),
    )
    manifest["n_train_rows_seen"] = n_train
    manifest["elapsed_sec"] = round(time.time() - t0, 1)
    mpath = os.path.join(args.manifest_dir, "ddxplus_v1.json")
    json.dump(manifest, open(mpath, "w"), indent=2)
    print(f"manifest -> {mpath}  ({manifest['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
