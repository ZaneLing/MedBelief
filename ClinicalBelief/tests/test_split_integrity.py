"""Split integrity + leakage defence (section 2.2)."""
from __future__ import annotations

import json
import os
import sys

from conftest import PROCESSED, have_data

import numpy as np


def test_official_boundaries_respected():
    if not have_data():
        print("SKIP"); return
    man = json.load(open(os.path.join(os.path.dirname(PROCESSED), "manifests", "ddxplus_v1.json")))
    splits = man["splits"]
    # fit/discovery/registration derive from train; validate/test from their own
    assert splits["fit"]["source"] == "train"
    assert splits["discovery"]["source"] == "train"
    assert splits["registration"]["source"] == "train"
    assert splits["validate"]["source"] == "validate"
    assert splits["test"]["source"] == "test"
    assert splits["test"].get("blind") is True


def test_train_subsplit_disjoint():
    if not have_data():
        print("SKIP"); return
    from cbh.data.ddxplus_convert import load_split
    ids = {}
    for nm in ["fit", "discovery", "registration"]:
        p = os.path.join(PROCESSED, f"{nm}.npz")
        if os.path.exists(p):
            ids[nm] = set(str(c) for c in load_split(p)["case_ids"])
    keys = list(ids)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            inter = ids[keys[i]] & ids[keys[j]]
            assert not inter, f"{keys[i]} and {keys[j]} overlap: {len(inter)}"


def test_test_split_isolated():
    if not have_data():
        print("SKIP"); return
    from cbh.data.ddxplus_convert import load_split
    test_ids = set(str(c) for c in load_split(os.path.join(PROCESSED, "test.npz"))["case_ids"])
    for nm in ["fit", "discovery", "registration", "validate"]:
        p = os.path.join(PROCESSED, f"{nm}.npz")
        if os.path.exists(p):
            other = set(str(c) for c in load_split(p)["case_ids"])
            assert not (test_ids & other), f"test leaks into {nm}"
    # case_id prefixes encode the source split
    assert all(c.startswith("ddx_test_") for c in list(test_ids)[:10])


if __name__ == "__main__":
    for fn in [test_official_boundaries_respected, test_train_subsplit_disjoint,
               test_test_split_isolated]:
        fn(); print("ok:", fn.__name__)
