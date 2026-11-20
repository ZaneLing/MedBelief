"""Check downloaded source hashes, replay saved models, and validate delivery."""
import hashlib
import json
import re
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from lightweight_multidataset import ROOT, DATA, OUT, dump, features, facts, signature
from lightweight_diagnosis import predict


def main():
    sources=json.loads((DATA/'sources.json').read_text());verified=[]
    for f in sources['files']:
        p=Path(f['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'];verified.append(str(p))
    datasets={}
    for ds in ['dxy','mz4','mz10']:
        tr=json.loads((DATA/f'dxformer/data/{ds}/train_set.json').read_text())
        te=json.loads((DATA/f'dxformer/data/{ds}/test_set.json').read_text())
        r=json.loads((OUT/f'{ds}_results.json').read_text());groups=np.array([signature(c) for c in tr]);y=[c['label'] for c in tr]
        for fit,val in StratifiedGroupKFold(5,shuffle=True,random_state=20261120).split(tr,y,groups):
            assert not(set(groups[fit])&set(groups[val]))
        for view,stats in r['views'].items():
            cv=stats['cv_selection'];assert stats['selected']==max(cv,key=lambda c:c['cv_accuracy'])['model']
            p=joblib.load(OUT/f'{ds}_{view}.joblib').predict([features(c,view,r['label_named_fields_removed']) for c in te])
            stored=json.loads((OUT/f'{ds}_{view}_predictions.json').read_text())
            assert list(p)==[v['prediction'] for v in stored]
            assert sum(v['prediction']==v['gold'] for v in stored)==stats['all_test']['correct']
            with (OUT/f'{ds}_{view}_gpt_inputs.jsonl').open() as f:prompts=[json.loads(line) for line in f]
            assert len(prompts)==len(te) and all(set(p)=={'id','prompt'} for p in prompts)
        gate=json.loads((OUT/f'{ds}_portable.json').read_text())
        out=[predict(gate,facts(c)) for c in te];accepted=[(c,p) for c,p in zip(te,out) if p['accepted']]
        selective=json.loads((OUT/'transfer_selective.json').read_text())['selective'][ds]
        assert len(accepted)==selective['test_accepted']
        assert sum(c['label']==p['prediction'] for c,p in accepted)==selective['test_correct']
        conflicts=sum(k in c['imp_sxs'] and c['imp_sxs'][k]!=v for c in tr+te for k,v in c['exp_sxs'].items())
        datasets[ds]=dict(test_rows=len(te),model_replays=4,fold_fact_overlap=0,explicit_implicit_conflicting_fields=conflicts,
            portable_acceptance_reproduced=True)
    for ds in ['medqa','medmcqa']:
        r=json.loads((OUT/f'{ds}_results.json').read_text());pred=json.loads((OUT/f'{ds}_predictions.json').read_text())
        assert sum(v['gold']==v['prediction'] for v in pred)==r['selected']['correct']
        assert len(pred)==r['test_n']
        assert str(r['selected_k'])==max(['1','5','20'],key=lambda k:r['dev_accuracy'][k])
        for path,sha in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha
        with (OUT/f'{ds}_gpt_inputs.jsonl').open() as f:prompts=[json.loads(line) for line in f]
        assert len(prompts)==r['test_n'] and all(set(p)=={'id','prompt'} for p in prompts)
        datasets[ds]=dict(test_rows=len(pred),saved_accuracy_recomputed=True,prompt_labels_separate=True)
    result=dict(status='passed',download_hashes_verified=len(verified),datasets=datasets,
        code_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src').glob('*lightweight*.py')},
        protocol_hash=hashlib.sha256((ROOT/'protocol/LIGHTWEIGHT_MULTIDATASET.json').read_bytes()).hexdigest())
    dump(OUT/'verification.json',result)
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(OUT/'RESULTS.md').read_text()):
        if '://' not in target:
            assert (OUT/target).exists(),target
            links.append(target)
    result['report_links_verified']=len(links);dump(OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
