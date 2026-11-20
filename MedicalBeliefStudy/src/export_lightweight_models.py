"""Export NB/logistic weights to plain JSON; verify inference on every test case."""
import json
import joblib
import numpy as np

from lightweight_multidataset import DATA, OUT, dump, facts, features
from lightweight_diagnosis import predict


def main():
    results={}
    for ds in ['dxy','mz4','mz10']:
        b=joblib.load(OUT/f'{ds}_selective.joblib');p=b['pipeline'];m=p[-1]
        if hasattr(m,'feature_log_prob_'):
            negative=np.log1p(-np.exp(m.feature_log_prob_))
            w=m.feature_log_prob_-negative;bias=m.class_log_prior_+negative.sum(axis=1)
        else:w=m.coef_;bias=m.intercept_
        model=dict(dataset=ds,classes=m.classes_.tolist(),features=p[0].feature_names_,weights=w.tolist(),
            intercepts=bias.tolist(),threshold=b['threshold'],states={'0':'negative','1':'positive','2':'uncertain'},
            purpose='Research benchmark classifier; full recorded findings; abstains below held-out calibration threshold')
        path=OUT/f'{ds}_portable.json';path.write_text(json.dumps(model,ensure_ascii=False,separators=(',',':'))+'\n')
        cases=json.loads((DATA/f'dxformer/data/{ds}/test_set.json').read_text())
        probs=p.predict_proba([features(c,'all_values',[]) for c in cases]);errors=[]
        for c,pr in zip(cases,probs):
            result=predict(model,facts(c));errors.append(abs(result['confidence']-pr.max()))
            assert result['highest_scoring_class']==m.classes_[pr.argmax()]
            assert result['accepted']==bool(pr.max()>=b['threshold'])
        assert max(errors)<1e-10
        results[ds]=dict(test_rows_verified=len(cases),max_probability_error=max(errors),portable_json_bytes=path.stat().st_size)
    example=json.loads((DATA/'dxformer/data/dxy/test_set.json').read_text())[0]
    dump(OUT/'example_findings.json',facts(example))
    dump(OUT/'portable_verification.json',results)
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
