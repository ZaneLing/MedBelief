"""Figures from completed stage 2 outputs, with primary/diagnostic scopes kept separate."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'figures/phase2';OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
COLORS=['#9aa9b6','#3477ab','#d67e35','#6a5798']
TASKS=['current_report_numerical_direction','current_report_usable','old_report_numerical_direction','old_report_direction_facts_only']
TITLES=['New report: numerical direction','New report: usable for this patient?','Old report: numerical direction','Old report: facts-only history']
def read(p):return json.loads((ROOT/p).read_text())
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');plt.close(fig)

def behavior():
    for rid,name,title in [('phase2_pilot_4b','01_behavior_2a','Phase 2A: retained old judgment and current evidence'),('phase2b_confirm_4b','02_behavior_2b','Phase 2B: new cases and a new reason evidence is unusable')]:
        if not (ROOT/'runs'/rid/'analysis_v2.json').exists():continue
        data=read('runs/'+rid+'/analysis_v2.json');scope=data['subsets']['primary_aki_dvt'];cells=scope['cells']
        if rid=='phase2_pilot_4b':sources=['both_valid','relevant_withdrawn','irrelevant_withdrawn'];labels=['New report usable','New report belongs\nto another patient','Unrelated height report\nbelongs to another patient']
        else:sources=['valid','wrong_patient','not_qualified'];labels=['New report usable','New report belongs\nto another patient','Failed calibration /\nunassessed score']
        hs=[h for h in ['current_only','old_facts','own_judgment_summary','own_raw_final'] if any(c['history']==h for c in cells)]
        fig,ax=plt.subplots(figsize=(10,4.7));width=.8/len(hs)
        for j,h in enumerate(hs):
            cc=[next(c for c in cells if c['history']==h and c['source']==s) for s in sources];values=np.array([c['correct']/c['n'] for c in cc])*100;xx=np.arange(3)+(j-(len(hs)-1)/2)*width
            ax.bar(xx,values,width*.9,color=COLORS[j],label=['Current record only','Old facts retained','Own assessment summary','Own assessment prose'][j])
            for x,v,c in zip(xx,values,cc):ax.text(x,v+1.3,f"{c['correct']}/{c['n']}",ha='center',fontsize=8)
        ax.set_xticks(range(3),labels);ax.set_ylim(0,111);ax.set_ylabel('Correct decisions (%)');ax.set_title(title);ax.legend(loc='lower left',fontsize=9)
        note='AKI + DVT primary analysis; 8 case families. Counts are trials, not independent patients.'
        if rid=='phase2b_confirm_4b':note+='\nProse condition uses only opposed old/new reports; compare with its matched facts-only subset.'
        else:note+='\nBlood pressure is diagnostic only and excluded from these bars.'
        fig.text(.5,.005,note,ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.09,1,1));save(fig,name)

def repairs():
    data=read('runs/phase2_bp_repair_analysis.json');methods=['baseline','numbers','source','binding','quality_wording'];names=['Neutral\nnote','Numerical\ncomparison','Source\nstatus','Eligibility\nfirst','Quality\nwording']
    fig,axes=plt.subplots(1,2,figsize=(11,4.4),sharey=True)
    for ax,split in zip(axes,['development','confirmation']):
        items=data['splits'][split]['methods'];mm=[m for m in methods if m in items]
        for j,key in enumerate(['usable','unusable']):
            vv=[100*items[m][key]['correct']/items[m][key]['n'] for m in mm];xx=np.arange(len(mm))+(j-.5)*.32
            ax.bar(xx,vv,width=.3,color=COLORS[1+j],label=['Report usable','Report unusable'][j])
            for x,v,m in zip(xx,vv,mm):c=items[m][key];ax.text(x,v+1.5,f"{c['correct']}/{c['n']}",ha='center',fontsize=8)
        ax.set_xticks(range(len(mm)),[names[methods.index(m)] for m in mm],fontsize=9);ax.set_title(split.title()+' (4 new families)');ax.set_ylim(0,112)
    axes[0].set_ylabel('Correct decisions (%)');axes[0].legend(loc='lower left',fontsize=9)
    fig.suptitle('Blood-pressure diagnosis: can additional information repair errors?');fig.text(.5,.01,data['selection']['reason']+'.',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.05,1,.95));save(fig,'03_bp_repairs')

def readouts():
    a=read('runs/phase2_pilot_4b/probes_primary/results.json');controls=read('runs/phase2_pilot_4b/strong_text_controls.json')['scopes']['primary']
    b=read('runs/phase2b_confirm_4b/transfer_from_2a/results.json') if (ROOT/'runs/phase2b_confirm_4b/transfer_from_2a/results.json').exists() else {}
    for result,transfer,name in [(a,False,'04_internal_readouts_2a'),(b,True,'05_readout_transfer_2b')]:
        if not result:continue
        fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,sharey=True)
        for ax,task,title in zip(axes.flat,TASKS,TITLES):
            rr=result[task];xx=[r['layer'] for r in rr['layers']];null=np.array([r['random_label_scores'] for r in rr['layers']])
            ax.plot(xx,[r['balanced_accuracy'] for r in rr['layers']],color=COLORS[1],lw=2,label='Hidden-state readout')
            ax.plot(xx,null.mean(1),color='#888',lw=1,label='Shuffled labels (5)');ax.fill_between(xx,null.min(1),null.max(1),color='#888',alpha=.13)
            cc=rr['text_controls'] if transfer else controls[task]['controls']
            for kind,color,label in [('words_with_numbers',COLORS[2],'Text: words + numbers'),('character_3_to_5',COLORS[3],'Text: character sequences')]:ax.axhline(cc[kind]['balanced_accuracy'],color=color,linestyle='--',lw=1.2,label=label)
            ax.set_title(title,fontsize=10);ax.set_xlim(1,36);ax.set_ylim(0,1.04);ax.axhline(.5,color='#aaa',linestyle=':',lw=.8)
        axes[0,0].legend(loc='lower right',fontsize=8);axes[1,0].set_xlabel('Transformer layer');axes[1,1].set_xlabel('Transformer layer');axes[0,0].set_ylabel('Balanced accuracy');axes[1,0].set_ylabel('Balanced accuracy')
        title='Transfer: train on 2A, test only on new 2B families' if transfer else 'Phase 2A: train on 4 families, test on 4 different families'
        fig.suptitle(title);fig.text(.5,.005,'All 36 layers shown; final layer prespecified for summaries. Decoding information does not establish belief or causal use.',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.025,1,.96));save(fig,name)

def source_transfer():
    data=read('runs/phase2b_confirm_4b/transfer_from_2a/results.json')['current_report_usable'];sources=['valid','wrong_patient','not_qualified'];labels=['Report usable','Wrong patient','Calibration failed /\nscore unassessed']
    items=[('Last-layer hidden state',data['layers'][-1]),('Text: words + numbers',data['text_controls']['words_with_numbers']),('Text: characters',data['text_controls']['character_3_to_5'])]
    fig,ax=plt.subplots(figsize=(9,4.1))
    for j,(name,rr) in enumerate(items):
        xx=np.arange(3)+(j-1)*.25;values=[rr['by_source'][s]['accuracy']*100 for s in sources];ax.bar(xx,values,width=.23,color=COLORS[j+1],label=name)
        for x,v in zip(xx,values):ax.text(x,v+1.2,f'{v:.1f}',ha='center',fontsize=9)
    ax.set_xticks(range(3),labels);ax.set_ylim(0,112);ax.set_ylabel('Correct usability labels (%)');ax.set_title('Does an evidence-usability readout transfer to a new failure cause?');ax.legend(loc='lower left',fontsize=9)
    fig.text(.5,.005,'Every readout is trained only on 2A. Trials per condition: '+', '.join(str(data['layers'][-1]['by_source'][s]['n']) for s in sources)+'. New case families only.',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.04,1,1));save(fig,'06_source_transfer')
if __name__=='__main__':behavior();repairs();readouts();source_transfer()
