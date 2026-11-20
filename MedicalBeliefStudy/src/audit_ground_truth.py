"""Audit endpoint labels and reference differential coverage; no model inference."""
import ast
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cases = [json.loads(x) for x in (ROOT / 'data/cases.private.jsonl').read_text().splitlines()]
jobs = [json.loads(x) for x in (ROOT / 'data/jobs.public.jsonl').read_text().splitlines()]
cohorts = {r['case_id']: r['cohort'] for r in jobs}
candidates = set(jobs[0]['candidate_diseases'])
lookup = {r['source_row_zero_based']: r for r in cases}
source = ROOT.parent / 'ClinicalBelief/data/raw/train.csv'
records = []
with source.open() as handle:
    for index, row in enumerate(csv.DictReader(handle)):
        if index not in lookup:
            continue
        case = lookup[index]
        differential = dict(ast.literal_eval(row['DIFFERENTIAL_DIAGNOSIS']))
        total = sum(differential.values())
        assert abs(total - 1) < 1e-6, total
        assert case['gold_disease'] == row['PATHOLOGY']
        records.append({
            'case_id': case['case_id'], 'cohort': cohorts[case['case_id']],
            'gold_disease': case['gold_disease'], 'gold_matches_raw': True,
            'gold_is_reference_max': differential.get(case['gold_disease'], -1) == max(differential.values()),
            'reference_candidate_coverage': sum(p for d, p in differential.items() if d in candidates),
            'reference_differential': differential,
        })
assert len(records) == len(cases)
groups = defaultdict(list)
for record in records:
    groups[record['cohort']].append(record)
summary = {key: {
    'cases': len(values),
    'gold_matches_raw': sum(r['gold_matches_raw'] for r in values),
    'gold_is_reference_max': sum(r['gold_is_reference_max'] for r in values),
    'mean_reference_candidate_coverage': sum(r['reference_candidate_coverage'] for r in values) / len(values),
} for key, values in groups.items()}
result = {'method': 'Endpoint source-data audit; not a model experiment or clinical posterior validation.',
          'source': str(source.relative_to(ROOT.parent)),
          'source_size_bytes': source.stat().st_size,
          'cases_sha256': hashlib.sha256((ROOT / 'data/cases.private.jsonl').read_bytes()).hexdigest(),
          'summary': summary, 'records': records}
destination = ROOT / 'protocol/ground_truth_audit.json'
destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
