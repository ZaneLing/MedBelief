"""New-domain follow-up, separate from the BP development/confirmation selection."""
from pathlib import Path
import json
from analyze_phase2 import cell,paired
from plot_phase2 import plt,COLORS,save
ROOT=Path(__file__).resolve().parents[1]
def main():
    run=ROOT/'runs/phase2d_partial_fact_4b';meta=json.loads((run/'metadata.json').read_text());inp={r['id']:r for r in map(json.loads,(ROOT/meta['data']).read_text().splitlines())};rows=list(map(json.loads,(run/'predictions.jsonl').read_text().splitlines()));assert len(rows)==48 and {r['id'] for r in rows}==set(inp)
    out={'overall':cell(rows),'domains':{},'errors':[{**r,'prompt':inp[r['id']]['prompt']} for r in rows if r['prediction']!=r['gold']]}
    for d in ['aki','dvt']:
        rr=[r for r in rows if r['domain']==d];items={}
        for method in ['baseline','numbers']:
            items[method]={s:cell([r for r in rr if r['method']==method and (r['usable'] if s=='usable' else not r['usable'])]) for s in ['usable','unusable']}
        for s in ['usable','unusable']:
            sub=[r for r in rr if r['usable']==(s=='usable')];items[s+'_paired']=paired(sub,'method','numbers','baseline',['family_id','current_sign','usable'])
        out['domains'][d]=items
    (run/'analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='errors'},indent=2))
    bp=json.loads((ROOT/'runs/phase2_bp_repair_analysis.json').read_text())['splits']['confirmation']['methods'];fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    for ax,status in zip(axes,['unusable','usable']):
        for j,method in enumerate(['baseline','numbers']):
            cc=[bp[method][status],out['domains']['aki'][method][status],out['domains']['dvt'][method][status]];xx=[i+(j-.5)*.3 for i in range(3)];vals=[100*c['correct']/c['n'] for c in cc]
            ax.bar(xx,vals,width=.28,color=COLORS[1+j],label=['Neutral note','Correct numerical note'][j])
            for x,v,c in zip(xx,vals,cc):ax.text(x,v+1.5,f"{c['correct']}/{c['n']}",ha='center',fontsize=9)
        ax.set_xticks(range(3),['Blood pressure','Creatinine','DVT pathway']);ax.set_ylim(0,112);ax.set_title('Report '+status)
    axes[0].set_ylabel('Correct medical judgments (%)');axes[0].legend(loc='lower left',fontsize=9)
    fig.suptitle('Can a correct partial fact harm the complete medical judgment?');fig.text(.5,.005,'BP: confirmation cases (4 families). Creatinine / DVT: exploratory new-domain follow-up (3 families each).',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.045,1,.94));save(fig,'09_partial_fact_transfer')
if __name__=='__main__':main()
