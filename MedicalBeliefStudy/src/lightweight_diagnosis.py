"""Standard-library inference for exported research classifiers, with abstention.

Input: a JSON object mapping exact dataset symptom names to '0', '1', or '2'.
This preserves the benchmark's structured input; it is not a free-text clinical tool.
"""
import argparse
import json
import math
from pathlib import Path


def predict(model, findings):
    encoded={k+'='+str(v) for k,v in findings.items()}
    indices=[i for i,k in enumerate(model['features']) if k in encoded]
    scores=[b+sum(w[i] for i in indices) for b,w in zip(model['intercepts'],model['weights'])]
    mx=max(scores);ex=[math.exp(v-mx) for v in scores];total=sum(ex);probs=[v/total for v in ex]
    best=max(range(len(probs)),key=probs.__getitem__);confidence=probs[best]
    accepted=confidence>=model['threshold']
    return dict(prediction=model['classes'][best] if accepted else None,
        highest_scoring_class=model['classes'][best],confidence=confidence,accepted=accepted,
        matched_features=len(indices),unrecognized_features=sorted(encoded-set(model['features'])))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(predict(json.loads(args.model.read_text()),json.loads(args.input.read_text())),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
