"""Shared fixtures/helpers for tests. Runs standalone or under pytest."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

PROCESSED = os.path.join(ROOT, "data", "processed")
RAW = os.path.join(ROOT, "data", "raw")
SCHEMA_JSON = os.path.join(PROCESSED, "schema.json")


def have_data() -> bool:
    return os.path.exists(SCHEMA_JSON) and os.path.exists(os.path.join(PROCESSED, "validate.npz"))


def tiny_nb():
    import json
    from cbh.beliefs.build import load_schema, train_nb
    from cbh.data.ddxplus_convert import load_split
    schema = load_schema(SCHEMA_JSON)
    fit = load_split(os.path.join(PROCESSED, "fit.npz"))
    # subsample for speed
    n = min(3000, len(fit["atoms"]))
    sub = {k: v[:n] for k, v in fit.items()}
    return train_nb(sub, schema["diseases"], schema["total_atoms"]), schema
