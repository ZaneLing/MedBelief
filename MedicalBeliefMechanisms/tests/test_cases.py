import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cases import build_cases, rule_answer


def test_aki_boundaries_and_withdrawal():
    assert rule_answer("aki", {"baseline": 80, "current": 106, "hours": 48}) == "yes"
    assert rule_answer("aki", {"baseline": 80, "current": 105, "hours": 48}) == "no"
    assert rule_answer("aki", {"baseline": 80, "current": 106, "hours": 49}) == "no"
    assert rule_answer("aki", {"baseline": 80, "current": 106, "hours": 48}, False) == "unknown"


def test_bp_quality_and_either_component():
    f = dict(clinic_s=150, clinic_d=95, abpm_s=135, abpm_d=70, n_daytime=14, per_hour=2)
    assert rule_answer("bp", f) == "yes"
    assert rule_answer("bp", dict(f, abpm_s=120, abpm_d=85)) == "yes"
    assert rule_answer("bp", dict(f, n_daytime=13)) == "unknown"
    assert rule_answer("bp", dict(f, per_hour=1)) == "unknown"


def test_dvt_boundary():
    assert rule_answer("dvt", {"wells": 1}) == "no"
    assert rule_answer("dvt", {"wells": 2}) == "yes"
    assert rule_answer("dvt", None) == "unknown"


def test_pairing_and_sealed_splits():
    rows = build_cases()
    assert len(rows) == 864
    assert len({r["record_id"] for r in rows}) == len(rows)
    groups = {}
    for r in rows:
        groups.setdefault(r["base_id"], set()).add(r["split"])
        assert r["gold_token"] == r["label_tokens"][r["gold"]]
        if r["stage"] in ["initial", "withdrawn"]:
            assert r["gold"] == "unknown"
        else:
            assert (r["gold"] == "yes") == r["positive_report"]
    assert all(len(s) == 1 for s in groups.values())
    assert len({r['prompt_sha256'] for r in rows}) == 756


def test_mapping_balance_and_preserved_evidence():
    rows = build_cases()
    for domain in ["aki", "bp", "dvt"]:
        for gold in ["yes", "no", "unknown"]:
            counts = [sum(r["gold_token"] == t and r["domain"] == domain and r["gold"] == gold for r in rows) for t in "ABC"]
            assert len(set(counts)) == 1
    for domain in ["aki", "bp", "dvt"]:
        selected = [r for r in rows if r["base_id"] == domain+"_00" and r["positive_report"] and r["mapping"] == 0 and r["stage"] == "evidence"]
        assert len({r['evidence_text'] for r in selected}) == 1
