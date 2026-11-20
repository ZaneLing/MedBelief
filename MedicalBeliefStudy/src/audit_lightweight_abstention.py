"""Replay fixed selective classifiers with and without the acceptance threshold.

No fitting or test-based threshold selection: compare the same saved model.
"""
import json

import joblib
import numpy as np

from lightweight_multidataset import DATA, OUT, dump, features


def main():
    results = {}
    reference = json.loads((OUT / 'transfer_selective.json').read_text())['selective']
    for ds in ['dxy', 'mz4', 'mz10']:
        cases = json.loads((DATA / f'dxformer/data/{ds}/test_set.json').read_text())
        saved = joblib.load(OUT / f'{ds}_selective.joblib')
        model, threshold = saved['pipeline'], saved['threshold']
        probabilities = model.predict_proba([features(c, 'all_values', []) for c in cases])
        prediction = model.classes_[probabilities.argmax(axis=1)]
        correct = prediction == np.array([c['label'] for c in cases])
        accepted = probabilities.max(axis=1) >= threshold
        result = dict(
            threshold=float(threshold), total=len(cases),
            ungated_correct=int(correct.sum()), ungated_accuracy=float(correct.mean()),
            accepted=int(accepted.sum()), accepted_correct=int(correct[accepted].sum()),
            selective_accuracy=float(correct[accepted].mean()),
            abstained=int((~accepted).sum()),
            abstained_argmax_correct=int(correct[~accepted].sum()),
            abstained_argmax_accuracy=float(correct[~accepted].mean()),
            coverage=float(accepted.mean()),
        )
        assert result['accepted'] == reference[ds]['test_accepted']
        assert result['accepted_correct'] == reference[ds]['test_correct']
        assert result['ungated_correct'] == result['accepted_correct'] + result['abstained_argmax_correct']
        results[ds] = result
    dump(OUT / 'abstention_audit.json', results)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
