"""Controlled clinical-rule stimuli, not patient diagnosis or a released benchmark.

Synthetic cases; guideline-derived subtask labels; no claim of clinician review.
Each base_id is a cluster. Numeric/label/expectation variants stay in one split.
"""
from pathlib import Path
import hashlib
import itertools
import json

ROOT = Path(__file__).resolve().parents[1]
STAGES = ["initial", "evidence", "confirmed", "withdrawn"]
PRIOR = {
    "none": "There is no preceding assessment.",
    "yes": "A preceding tentative assessment favored YES for the target question. It was made without the pending report and contains no additional patient facts.",
    "no": "A preceding tentative assessment favored NO for the target question. It was made without the pending report and contains no additional patient facts.",
}
SOURCES = {
    "aki": {"guideline": "NICE NG148", "section": "1.3.1", "url": "https://www.nice.org.uk/guidance/ng148/chapter/Recommendations"},
    "bp": {"guideline": "NICE NG136", "section": "1.2.6 and 1.2.8", "url": "https://www.nice.org.uk/guidance/ng136/chapter/recommendations"},
    "dvt": {"guideline": "NICE NG158", "section": "1.1.3 and 1.1.8", "url": "https://www.nice.org.uk/guidance/ng158/chapter/recommendations"},
}
RULES = {
    "aki": "Scope: the absolute creatinine-rise criterion only, not all AKI criteria and not the cause of illness. A rise in serum creatinine of at least 26 micromol/L within 48 hours satisfies this criterion. Both measurements must be usable measurements for this patient.",
    "bp": "Scope: confirmation by the specified clinic-plus-ABPM rule, not absence of all hypertension. Clinic BP must be at least 140 systolic or 90 diastolic, and the valid daytime ABPM average at least 135 systolic or 85 diastolic (mmHg). ABPM requires at least 2 readings per waking hour and an average of at least 14 daytime readings.",
    "dvt": "Scope: the initial investigation in an adult with suspected DVT and no prior tests. Use the independently assessed two-level DVT Wells score. A score of 2 or more selects proximal leg-vein ultrasound first. A score of 1 or less selects D-dimer first. Both tests can be completed within 4 hours; delayed-test branches do not apply.",
}


def rule_answer(domain, facts, usable=True):
    if not usable or facts is None:
        return "unknown"
    if domain == "aki":
        return "yes" if facts["current"]-facts["baseline"] >= 26 and facts["hours"] <= 48 else "no"
    if domain == "bp":
        if facts["n_daytime"] < 14 or facts["per_hour"] < 2:
            return "unknown"
        clinic = facts["clinic_s"] >= 140 or facts["clinic_d"] >= 90
        abpm = facts["abpm_s"] >= 135 or facts["abpm_d"] >= 85
        return "yes" if clinic and abpm else "no"
    if domain == "dvt":
        return "yes" if facts["wells"] >= 2 else "no"
    raise ValueError(domain)


def scenario(domain, b, positive):
    age = 42 + b * 3
    if domain == "aki":
        f = {"baseline": 70+b*7, "current": 70+b*7 + (30+b if positive else 8+b), "hours": 24+b*2}
        return f, f"An adult aged {age}. No usable creatinine values are available yet.", (
            f"Report R1: serum creatinine was {f['baseline']} micromol/L and is now {f['current']} micromol/L, measured {f['hours']} hours apart."), (
            "Does the available record establish that this patient's measurements satisfy the specified absolute creatinine-rise criterion?")
    if domain == "bp":
        f = {"clinic_s": 148+b, "clinic_d": 94+b, "abpm_s": 140+b if positive else 124+b,
             "abpm_d": 89+b if positive else 74+b, "n_daytime": 16+b*2, "per_hour": 2}
        return f, f"An adult aged {age}, not pregnant, with properly measured clinic BP {f['clinic_s']}/{f['clinic_d']} mmHg. No valid ABPM result is available yet.", (
            f"Report R1: daytime ABPM mean {f['abpm_s']}/{f['abpm_d']} mmHg, based on {f['n_daytime']} waking readings at {f['per_hour']} readings per hour, with all other measurement requirements met."), (
            "Does the available record meet the specified clinic-plus-ABPM rule for confirming hypertension?")
    f = {"wells": 2+b if positive else 1-b}
    return f, f"An adult aged {age}, not pregnant, with suspected DVT. No tests have been done. The independently assessed Wells score is pending. Ultrasound and D-dimer are each available within 4 hours.", (
        f"Report R1: the independently assessed two-level DVT Wells score is {f['wells']}."), (
        "Does the available record place this patient on the ultrasound-first initial investigation pathway?")


def build_cases(n_bases_per_domain=4):
    out = []
    # Full option-token counterbalancing across yes/no/unknown, without 6-fold inflation.
    permutations = [("yes", "no", "unknown"), ("unknown", "yes", "no"), ("no", "unknown", "yes")]
    for domain, b in itertools.product(RULES, range(n_bases_per_domain)):
        base_id = f"{domain}_{b:02}"
        split = "development" if b % 2 == 0 else "instrument_validation"
        for positive, prior, mapping in itertools.product([False, True], PRIOR, range(3)):
            facts, initial, evidence, question = scenario(domain, b, positive)
            order = permutations[mapping]
            labels = dict(zip(order, "ABC"))
            options = "\n".join(f"{labels[s]}: {v}" for s, v in [
                ("yes", "YES: the target rule/pathway is established."),
                ("no", "NO: usable evidence establishes that the target rule/pathway is not met."),
                ("unknown", "INSUFFICIENT: the required usable evidence is missing.")])
            # Sort by displayed label so list position and token are rotated together.
            options = "\n".join(sorted(options.splitlines()))
            trajectory = f"{base_id}_{int(positive)}_{prior}_m{mapping}"
            for stage in STAGES:
                parts = ["This is a synthetic rule-application study. Answer the narrowly scoped target question using only the supplied rule and usable patient evidence. A tentative prior assessment is not additional evidence.",
                         "RULE\n"+RULES[domain], "INITIAL RECORD\n"+initial,
                         "PRECEDING ASSESSMENT\n"+PRIOR[prior]]
                evidence_text = ""
                source_text = ""
                if stage != "initial":
                    evidence_text = evidence
                    source_text = "Source verification: R1 belongs to this patient and is valid for the stated measurements or assessment."
                    parts.extend(["NEW REPORT\n"+evidence_text, source_text])
                if stage == "confirmed":
                    source_text = "Later source audit: R1 is confirmed as correctly assigned to this patient; all its values remain usable. No new clinical measurement was made."
                    parts.append(source_text)
                elif stage == "withdrawn":
                    source_text = "Later source audit: R1 was assigned to the wrong patient and is withdrawn in full. None of its values are usable for this patient. No replacement report exists. The initial record remains valid."
                    parts.append(source_text)
                gold = rule_answer(domain, facts, usable=stage in ["evidence", "confirmed"])
                prompt = "\n\n".join(parts+["TARGET QUESTION\n"+question, "OPTIONS\n"+options,
                    "Return exactly one uppercase letter, A, B, or C. Do not add an explanation."])
                out.append({"record_id": trajectory+"_"+stage, "base_id": base_id, "trajectory_id": trajectory,
                    "domain": domain, "split": split, "positive_report": positive, "prior": prior,
                    "mapping": mapping, "stage": stage, "gold": gold, "gold_token": labels[gold],
                    "label_tokens": labels, "facts": facts, "prompt": prompt,
                    "evidence_text": evidence_text, "source_text": source_text,
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "source": SOURCES[domain], "clinical_review": "not_yet_independently_reviewed"})
    return out


if __name__ == "__main__":
    rows = build_cases()
    dest = ROOT / "data/phase1_cases.jsonl"
    dest.write_text("".join(json.dumps(x, ensure_ascii=False)+"\n" for x in rows))
    stats = {"records": len(rows), "base_cases": len({r['base_id'] for r in rows}),
        "trajectories": len({r['trajectory_id'] for r in rows}),
        "unique_prompts": len({r['prompt_sha256'] for r in rows}),
        "stage_order": STAGES, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "synthetic": True, "independent_clinical_review": False}
    (ROOT / "data/phase1_manifest.json").write_text(json.dumps(stats, indent=2)+"\n")
    print(json.dumps(stats, indent=2))
