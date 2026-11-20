"""Exact teacher MLP anchor input/outputs, only development cases."""
from structural_v1_core import *
def main():
    assert read(DEST/'screen/completion.json')['complete'];screen,tune,_=groups();model,tok=load_model();dest=DEST/'linear';dest.mkdir(exist_ok=True)
    rows=[];xx=[];yy=[]
    for split,cs in [('train',screen),('tune',tune)]:
        for c in cs:
            for cond in ['neutral','wrong']:
                for rot in [0,2]:
                    T=len(c['sentences']);z=read(ROOT/'runs/belief_v4/observations'/f'{c["case_id"]}_{cond}_code_r{rot}_base_t{T:02d}.json')
                    with np.load(ROOT/'runs/belief_v4'/z['state_file']) as a:st=a['residual_stages'].astype(np.float16)
                    x=mx.stack([b.post_attention_layernorm(mx.array(st[l,2])) for l,b in enumerate(model.model.layers)]);mx.eval(x)
                    xx.append(np.array(x));yy.append(st[:,3]);rows.append(dict(case_id=c['case_id'],split=split,condition=cond,rotation=rot))
    np.savez_compressed(dest/'anchors.npz',x=np.stack(xx),y=np.stack(yy));write_json(dest/'anchor_rows.json',rows)
    write_json(dest/'anchors_complete.json',dict(complete=True,train_cases=18,tune_cases=27,records=len(rows),new_model_prefills=0))
    print(json.dumps(dict(records=len(rows),new_model_prefills=0)))
if __name__=='__main__':main()

