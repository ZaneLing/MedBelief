"""Re-score published GPT-6/decision-model outputs against our exact MedQA file.

This is a reanalysis of author-released selected answers, not new API inference
or an independent validation of the author's private request/response logs.
"""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/lightweight_multidataset/public_reference/github'
OUT = ROOT / 'results/24_lightweight_multidataset'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((DATA / 'data_manifest.json').read_text())
    checked = {}
    for name in ['study.json', 'outcomes.jsonl.gz']:
        checked[name] = digest(DATA / name)
        assert checked[name] == manifest['files']['data/' + name]
    study = json.loads((DATA / 'study.json').read_text())
    test_path = ROOT / 'data/external_medqa/test.jsonl'
    test_hash = digest(test_path)
    assert test_hash == study['source_test_sha256']
    with test_path.open() as handle:
        test = [json.loads(line) for line in handle]
    local = json.loads((OUT / 'medqa_predictions.json').read_text())
    assert len(test) == len(study['items']) == len(local) == 1273
    items = {}
    for i, (case, meta, prediction) in enumerate(zip(test, study['items'], local)):
        # Author preserves the upstream source-row order, with one-based IDs.
        expected_id = f'medqa-us-evaluation-{test_hash[:16]}-{i+1:06d}'
        assert meta['item_id'] == expected_id
        assert list(case['options']) == meta['labels'] == list('ABCD')
        assert prediction['id'] == str(i)
        assert prediction['gold'] == list('ABCD').index(case['answer_idx'])
        items[expected_id] = (i, case['answer_idx'], list('ABCD')[prediction['prediction']])
    runs = {r['run_id']: r for r in study['runs']}
    configs = {c['config_id']: c for c in study['configurations']}
    expected = {'G01': 1233, 'G02': 1199, 'G03': 1212, 'D01': 1124, 'D02': 1134}
    rows = {key: {} for key in expected}
    total_outcomes = 0
    with gzip.open(DATA / 'outcomes.jsonl.gz', 'rt') as handle:
        for line in handle:
            outcome = json.loads(line)
            total_outcomes += 1
            identity = outcome['identity']
            key = identity['config_id']
            if key not in rows or runs[identity['run_id']]['replicate'] != 1:
                continue
            assert runs[identity['run_id']]['role'] == 'primary'
            item_id = identity['item_id']
            index, gold, local_answer = items[item_id]
            assert item_id not in rows[key]
            correct = outcome['status'] == 'valid' and outcome['selected_label'] == gold
            assert correct == outcome['correct']
            rows[key][item_id] = dict(
                source_row_zero_based=index, item_id=item_id, gold=gold,
                local_answer=local_answer, local_correct=local_answer == gold,
                public_answer=outcome['selected_label'], public_status=outcome['status'],
                public_correct=correct,
            )
    assert total_outcomes == study['outcomes'] == 68742
    summary = {}
    for key, values in rows.items():
        assert len(values) == 1273
        values = list(values.values())
        public_correct = sum(r['public_correct'] for r in values)
        local_correct = sum(r['local_correct'] for r in values)
        assert public_correct == expected[key] and local_correct == 460
        summary[key] = dict(
            model=configs[key], n=len(values), public_correct=public_correct,
            public_accuracy=public_correct / len(values),
            local_correct=local_correct, local_accuracy=local_correct / len(values),
            difference_percentage_points=100 * (public_correct - local_correct) / len(values),
            both_correct=sum(r['public_correct'] and r['local_correct'] for r in values),
            public_only_correct=sum(r['public_correct'] and not r['local_correct'] for r in values),
            local_only_correct=sum(not r['public_correct'] and r['local_correct'] for r in values),
            both_wrong=sum(not r['public_correct'] and not r['local_correct'] for r in values),
            unanswered=sum(r['public_status'] != 'valid' for r in values),
        )
    result = dict(
        status='passed', api_calls=0, author_commit=json.loads((DATA / 'provenance.json').read_text())['commit'],
        verified_public_data_hashes=checked, source_test_sha256=test_hash,
        alignment='Exact upstream file SHA-256; preserved row order; all selected labels rescored with local gold.',
        limitation='Author-released outputs reanalyzed. Private API logs and model training data not independently verified. Different inference pipelines; no matched runtime/cost experiment.',
        models=summary,
    )
    (OUT / 'public_medqa_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'public_medqa_paired_predictions.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
