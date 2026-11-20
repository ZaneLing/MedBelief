"""DDxPlus dataset adapter (Ticket T01).

Parses the raw English DDxPlus release (figshare schema, CSV mirror on
HuggingFace) into a compact, sealed, replayable representation.

Encoding
--------
Every one of the 223 evidences is expanded into a fixed set of binary *atoms*:

* binary (B)      -> 1 atom (present/absent)
* categorical (C) -> one-hot over `possible-values`
* multi-choice (M)-> multi-hot over `value_meaning` keys

Total atoms = 972. A patient's ground-truth evidence state is the dense atom
vector obtained by starting from each evidence's `default_value` and overriding
with the tokens listed in `EVIDENCES`.

Question families
-----------------
An ASK action targets a `code_question`. Asking it reveals *all* member
evidences at once (the environment returns the associated sub-answers), which
is how DDxPlus models question dependencies. `PATHOLOGY` and
`DIFFERENTIAL_DIAGNOSIS` are held privately by the sealed environment and are
never written into any public artefact.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

csv.field_size_limit(10_000_000)


@dataclass
class EvidenceEncoding:
    data_type: str
    start: int
    count: int
    # value-representation (string) -> offset within [start, start+count)
    value_to_offset: Dict[str, int]
    default_offsets: List[int]
    code_question: str
    is_antecedent: bool
    question_en: str


class EvidenceSchema:
    """Static encoding scheme derived from release_evidences.json."""

    def __init__(self, evidences_path: str):
        raw = json.load(open(evidences_path))
        # Stable canonical ordering by evidence id (natural sort on numeric part).
        def sort_key(eid: str):
            return int(eid.split("_")[1])

        self.evidence_ids: List[str] = sorted(raw.keys(), key=sort_key)
        self.encodings: Dict[str, EvidenceEncoding] = {}
        cursor = 0
        for eid in self.evidence_ids:
            meta = raw[eid]
            dt = meta["data_type"]
            if dt == "B":
                values = ["1"]
                value_to_offset = {"1": 0}
                count = 1
                default_offsets: List[int] = []  # default 0 -> no atom set
            elif dt == "C":
                values = [str(v) for v in meta["possible-values"]]
                value_to_offset = {v: i for i, v in enumerate(values)}
                count = len(values)
                dv = str(meta["default_value"])
                default_offsets = [value_to_offset[dv]] if dv in value_to_offset else []
            else:  # M
                values = list(meta["value_meaning"].keys())
                value_to_offset = {v: i for i, v in enumerate(values)}
                count = len(values)
                dv = str(meta["default_value"])
                default_offsets = [value_to_offset[dv]] if dv in value_to_offset else []
            self.encodings[eid] = EvidenceEncoding(
                data_type=dt,
                start=cursor,
                count=count,
                value_to_offset=value_to_offset,
                default_offsets=default_offsets,
                code_question=meta["code_question"],
                is_antecedent=bool(meta.get("is_antecedent", False)),
                question_en=meta.get("question_en", ""),
            )
            cursor += count
        self.total_atoms = cursor

        # question family -> member evidence ids
        self.question_to_evidences: Dict[str, List[str]] = {}
        for eid in self.evidence_ids:
            cq = self.encodings[eid].code_question
            self.question_to_evidences.setdefault(cq, []).append(eid)
        self.question_ids: List[str] = sorted(
            self.question_to_evidences.keys(), key=lambda q: int(q.split("_")[1])
        )
        self.question_index: Dict[str, int] = {q: i for i, q in enumerate(self.question_ids)}
        self.evidence_index: Dict[str, int] = {e: i for i, e in enumerate(self.evidence_ids)}

    # -- atom helpers ------------------------------------------------------
    def default_vector(self) -> np.ndarray:
        v = np.zeros(self.total_atoms, dtype=np.int8)
        for eid in self.evidence_ids:
            enc = self.encodings[eid]
            for off in enc.default_offsets:
                v[enc.start + off] = 1
        return v

    def atoms_for_evidence(self, eid: str) -> slice:
        enc = self.encodings[eid]
        return slice(enc.start, enc.start + enc.count)

    def schema_hash(self) -> str:
        payload = json.dumps(
            {
                "evidence_ids": self.evidence_ids,
                "atoms": {e: (enc.start, enc.count, enc.data_type) for e, enc in self.encodings.items()},
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ConditionSchema:
    """Canonical disease ordering + severity (release_conditions.json)."""

    def __init__(self, conditions_path: str):
        raw = json.load(open(conditions_path))
        self.diseases: List[str] = sorted(raw.keys())
        self.index: Dict[str, int] = {d: i for i, d in enumerate(self.diseases)}
        self.severity: Dict[str, int] = {d: int(raw[d].get("severity", 0)) for d in self.diseases}
        self.K = len(self.diseases)


@dataclass
class PatientRecord:
    case_id: str
    split: str
    age: int
    sex: int  # 0=F, 1=M, 2=other
    pathology_idx: int
    initial_evidence: str
    atoms: np.ndarray  # int8 [total_atoms] ground-truth evidence state (SEALED)


def _parse_sex(s: str) -> int:
    s = (s or "").strip().upper()
    if s.startswith("F"):
        return 0
    if s.startswith("M"):
        return 1
    return 2


def parse_evidence_tokens(schema: EvidenceSchema, tokens: List[str]) -> np.ndarray:
    """Build the dense ground-truth atom vector from an EVIDENCES token list."""
    vec = schema.default_vector()
    touched: Dict[str, List[str]] = {}
    order: List[str] = []
    for tok in tokens:
        if "_@_" in tok:
            eid, val = tok.split("_@_", 1)
        else:
            eid, val = tok, "1"
        if eid not in schema.encodings:
            continue
        if eid not in touched:
            touched[eid] = []
            order.append(eid)
        touched[eid].append(val)
    # For evidences with explicit tokens, reset their atoms then set the tokens.
    for eid in order:
        enc = schema.encodings[eid]
        vec[enc.start : enc.start + enc.count] = 0
        for val in touched[eid]:
            off = enc.value_to_offset.get(str(val))
            if off is None:
                # unknown categorical/multi value -> ignore (keeps evidence cleared)
                continue
            vec[enc.start + off] = 1
        # binary with only default (no explicit present token) stays 0
    return vec


def convert_csv(
    csv_path: str,
    ev_schema: EvidenceSchema,
    cond_schema: ConditionSchema,
    split: str,
    max_patients: Optional[int] = None,
    stride: int = 1,
) -> Dict[str, np.ndarray]:
    """Stream a patient CSV into dense arrays.

    Only every `stride`-th row is considered (deterministic, spreads the sample
    across the whole file instead of biasing toward the first rows), and at most
    `max_patients` are kept. Streaming means we never hold the full 670MB train
    file's parsed objects in memory at once.
    """
    ages: List[int] = []
    sexes: List[int] = []
    path_idx: List[int] = []
    init_ev: List[int] = []
    atoms: List[np.ndarray] = []
    case_ids: List[str] = []

    n_seen = 0
    n_kept = 0
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row_i = n_seen
            n_seen += 1
            if row_i % stride != 0:
                continue
            pathology = row["PATHOLOGY"]
            if pathology not in cond_schema.index:
                continue
            try:
                tokens = ast.literal_eval(row["EVIDENCES"])
            except Exception:
                tokens = []
            vec = parse_evidence_tokens(ev_schema, tokens)
            rec_init = row.get("INITIAL_EVIDENCE", "") or ""
            rec_init_idx = ev_schema.evidence_index.get(rec_init.split("_@_")[0], -1)
            cid = f"ddx_{split}_{row_i:07d}"
            atoms.append(vec)
            ages.append(int(float(row["AGE"])))
            sexes.append(_parse_sex(row["SEX"]))
            path_idx.append(cond_schema.index[pathology])
            init_ev.append(rec_init_idx)
            case_ids.append(cid)
            n_kept += 1
            if max_patients is not None and n_kept >= max_patients:
                break

    atoms_arr = np.stack(atoms).astype(np.int8) if atoms else np.zeros((0, ev_schema.total_atoms), np.int8)
    return {
        "atoms": atoms_arr,
        "age": np.asarray(ages, dtype=np.int16),
        "sex": np.asarray(sexes, dtype=np.int8),
        "pathology_idx": np.asarray(path_idx, dtype=np.int16),
        "initial_evidence_idx": np.asarray(init_ev, dtype=np.int16),
        "case_ids": np.asarray(case_ids, dtype=object),
        "n_seen": np.asarray([n_seen]),
    }


def sha256_file(path: str, limit_bytes: Optional[int] = None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        read = 0
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            read += len(chunk)
            if limit_bytes is not None and read >= limit_bytes:
                break
    return h.hexdigest()


def save_split(out_dir: str, name: str, data: Dict[str, np.ndarray]) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.npz")
    np.savez_compressed(
        path,
        atoms=data["atoms"],
        age=data["age"],
        sex=data["sex"],
        pathology_idx=data["pathology_idx"],
        initial_evidence_idx=data["initial_evidence_idx"],
        case_ids=data["case_ids"],
    )
    return path


def load_split(path: str) -> Dict[str, np.ndarray]:
    z = np.load(path, allow_pickle=True)
    return {k: z[k] for k in z.files}
