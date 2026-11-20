"""Decode DDXPlus catalog support without fitting any patient data.

This is a simulator audit. Missing catalog relations are not clinical exclusions.
Only evidence identities are used; answer values, age and sex are ignored.
"""
import argparse
import ast
import csv
import itertools
import json
from pathlib import Path


RAW = Path(__file__).resolve().parents[2] / 'ClinicalBelief/data/raw'


def decode(evidence_ids, conditions):
    allowed = {d['condition_name']: set(d['symptoms']) | set(d['antecedents'])
               for d in conditions.values()}
    ids = set(evidence_ids)
    unknown = ids - set().union(*allowed.values())
    if unknown:
        return {'status': 'unknown_evidence', 'unknown': sorted(unknown)}

    def candidates(keys):
        return sorted(d for d, support in allowed.items() if set(keys) <= support)

    result = candidates(ids)
    proof = None
    if len(result) == 1:
        for size in range(1, min(3, len(ids)) + 1):
            proof = next((list(keys) for keys in itertools.combinations(sorted(ids), size)
                          if candidates(keys) == result), None)
            if proof is not None:
                break
        # Above three, all observed IDs are a valid certificate, not a minimum.
        proof = proof or sorted(ids)
    return {'status': 'unique' if len(result) == 1 else 'abstain',
            'candidates': result, 'certificate': proof,
            'patient_training_cases': 0, 'uses_published_condition_metadata': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=['train', 'test', 'validate'], default='test')
    parser.add_argument('--row', type=int, default=3, help='zero-based source row')
    args = parser.parse_args()
    if args.row < 0:
        parser.error('--row must be nonnegative')
    with (RAW / f'{args.split}.csv').open() as handle:
        row = next(itertools.islice(csv.DictReader(handle), args.row, None), None)
    if row is None:
        parser.error('--row exceeds source length')
    ids = {token.partition('_@_')[0] for token in ast.literal_eval(row['EVIDENCES'])}
    result = decode(ids, json.loads((RAW / 'release_conditions.json').read_text()))
    # Gold is attached only after decoding, for human verification.
    result.update(source_split=args.split, source_row=args.row, observed_ids=sorted(ids),
                  gold_for_evaluation_only=row['PATHOLOGY'])
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
