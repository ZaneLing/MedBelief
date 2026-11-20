"""Verify saved audit provenance, native challenge inputs, predictions, and links."""
import ast
import collections
import csv
import hashlib
import json
from pathlib import Path
import re

from ddx_support_decoder import RAW, decode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/23_ddx_generator_audit'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    summary = json.loads((OUT / 'summary.json').read_text())
    native = json.loads((OUT / 'native_challenge_summary.json').read_text())
    follow = json.loads((OUT / 'followup.json').read_text())
    verified_hashes = []
    for rel, expected in summary['hashes'].items():
        assert sha(ROOT.parent / rel) == expected, rel
        verified_hashes.append(rel)
    for source, expected in [('ddx_native_challenge.py', native['source_code_sha256']),
                             ('ddx_generator_followup.py', follow['source_code_sha256'])]:
        assert sha(ROOT / 'src' / source) == expected, source
        verified_hashes.append(source)
    prior = json.loads((OUT / 'prior_work/manifest.json').read_text())
    for f in prior['files']:
        assert sha(OUT / 'prior_work' / Path(f['path']).name) == f['sha256']
    identities = {}; challenge_checks = {}
    for split in ['test', 'validate']:
        cases = [json.loads(s) for s in (OUT / f'native_challenge_{split}.jsonl').read_text().splitlines()]
        groups = collections.defaultdict(list)
        facts = collections.defaultdict(collections.Counter)
        indexed = {c['source_row_zero_based']: c for c in cases}
        seen = 0
        with (RAW / f'{split}.csv').open() as handle:
            for i, row in enumerate(csv.DictReader(handle)):
                if i not in indexed:
                    continue
                c = indexed[i]
                assert row['PATHOLOGY'] == c['gold']
                assert sorted(set(ast.literal_eval(row['EVIDENCES']))) == c['tokens']
                assert {t.partition('_@_')[0] for t in c['tokens']} == set(c['keys'])
                seen += 1
        assert seen == len(cases)
        for c in cases:
            groups[c['question_group_id']].append(c)
            facts[tuple(c['tokens'])][c['gold']] += 1
        for cs in groups.values():
            assert len({tuple(c['keys']) for c in cs}) == 1
            assert len({c['gold'] for c in cs}) == len(cs)
        predictions = list(csv.DictReader((OUT / f'native_challenge_{split}_predictions.csv').open()))
        assert [p['case_id'] for p in predictions] == [c['case_id'] for c in cases]
        for model, result in native['challenge'][split]['models'].items():
            correct = sum(p[model] == p['gold'] for p in predictions)
            assert correct == result['correct']
            assert abs(correct / len(cases) - result['accuracy']) < 1e-12
        identities[split] = dict(n=len(cases), unique_full_facts=len(facts),
            full_fact_conflict_groups=sum(len(v) > 1 for v in facts.values()),
            empirical_full_fact_ceiling=sum(max(v.values()) for v in facts.values()) / len(cases),
            question_groups_all_identical_values=sum(len({tuple(c['tokens']) for c in cs}) == 1 for cs in groups.values()))
        challenge_checks[split] = dict(original_rows_verified=seen, groups=len(groups),
                                      saved_prediction_models_verified=len(native['challenge'][split]['models']))
    (OUT / 'native_challenge_identifiability.json').write_text(json.dumps(identities, indent=2) + '\n')
    conditions = json.loads((RAW / 'release_conditions.json').read_text())
    demo = decode(['E_212', 'E_49'], conditions)
    assert demo['candidates'] == ['Acute laryngitis']
    assert decode([], conditions)['status'] == 'abstain'
    assert decode(['unknown-id'], conditions)['status'] == 'unknown_evidence'
    (OUT / 'decoder_demo.json').write_text(json.dumps(demo, indent=2) + '\n')
    # Create the result before checking links, since RESULTS links to verification itself.
    result = dict(status='passed', hashes_verified=verified_hashes,
                  prior_notebooks_verified=len(prior['files']), native_challenge_checks=challenge_checks,
                  standalone_decoder_checks=['two-clue original example', 'empty input abstains', 'unknown field abstains'],
                  independent_full_validation_rule=follow['independent_set_rule_validation'],
                  independent_certificates=follow['independently_verified_certificates'])
    destination = OUT / 'verification.json'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    links = []
    for path in [OUT / 'RESULTS.md']:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            target_path = (path.parent / target.split('#')[0]).resolve()
            assert target_path.exists(), target
            links.append(target)
    result['local_report_links_verified'] = len(links)
    result['source_sha256'] = sha(Path(__file__))
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
