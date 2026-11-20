"""Plot only completed, analyzed runs; never simulated model outcomes."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})

def save(fig,folder,name):
    p=ROOT/'figures'/folder;p.mkdir(parents=True,exist_ok=True)
    fig.savefig(p/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(p/(name+'.pdf'),bbox_inches='tight');plt.close(fig)

def calibration():
    candidates=['phase1b_confirm_1p7b','phase1b_confirm_4b','phase1b_confirm_4b_direct']
    names=[n for n in candidates if (ROOT/'runs'/n/'analysis.json').exists()]
    if len(names)<2:return
    data=[json.loads((ROOT/'runs'/n/'analysis.json').read_text()) for n in names]
    fig,axes=plt.subplots(1,3,figsize=(12,3.5),sharey=True)
    titles=['Overall accuracy','Accuracy when evidence is insufficient','Agreement across option rotations']
    thresholds=[.9,.8,.95]
    for k,ax in enumerate(axes):
        for j,run in enumerate(data):
            vals=[]
            for d in ['aki','bp','dvt']:
                v=run['domains'][d];vals.append(v['accuracy'] if k==0 else v['classes']['unknown']['accuracy'] if k==1 else v['rotation_consistency'])
            offset=(j-(len(names)-1)/2)*.26
            ax.bar(np.arange(3)+offset,100*np.array(vals),width=.24,color=['#4076ad','#d08137','#40886b'][j],label=['1.7B / thinking / FP16','4B / thinking / 8-bit','4B / direct / 8-bit'][j])
            for i,v in enumerate(vals):ax.text(i+offset,100*v+1.4,f'{100*v:.0f}',ha='center',fontsize=8)
        ax.axhline(thresholds[k]*100,color='#555',linestyle='--',linewidth=1)
        ax.set_title(titles[k],fontsize=10);ax.set_xticks(range(3),['Creatinine','Blood pressure','DVT pathway']);ax.set_ylim(0,113)
    axes[0].set_ylabel('Percent');axes[0].legend(loc='lower left',fontsize=8)
    fig.suptitle('Frozen calibration set: 162 trials per configuration',y=1.03)
    fig.tight_layout();save(fig,'phase1b','01_calibration')

def behavior():
    p=ROOT/'runs/phase2_pilot_4b/analysis.json'
    if not p.exists():return
    data=json.loads(p.read_text());fig,ax=plt.subplots(figsize=(8,4))
    hs=['current_only','old_facts','own_judgment_summary'];sources=['both_valid','relevant_withdrawn','irrelevant_withdrawn']
    for j,h in enumerate(hs):
        cells=[next(c for c in data['cells'] if c['domain']=='all' and c['history']==h and c['source']==s) for s in sources]
        values=np.array([c['correct']/c['n'] for c in cells])*100
        ax.bar(np.arange(3)+(j-1)*.25,values,width=.23,label=['Current evidence only','Old facts retained','Own prior assessment retained'][j],color=['#9cabb8','#4076ad','#d08137'][j])
        for i,(v,c) in enumerate(zip(values,cells)):ax.text(i+(j-1)*.25,v+1.2,f"{c['correct']}/{c['n']}",ha='center',fontsize=8)
    ax.set_xticks(range(3),['Both current reports valid','Relevant report withdrawn','Irrelevant report withdrawn']);ax.set_ylabel('Correct judgments (%)');ax.set_ylim(0,113)
    ax.set_title('Does the judgment track its evidence?');ax.legend(loc='lower left',fontsize=9);fig.tight_layout();save(fig,'phase2_pilot','01_behavior')

def source_failure():
    p=ROOT/'runs/phase1b_confirm_1p7b/source_failure_pattern.json'
    if not p.exists():return
    data=json.loads(p.read_text());fig,ax=plt.subplots(figsize=(6.5,3.7))
    values=[data[k]['correct']/data[k]['n']*100 for k in ['report_absent','present_but_unusable']]
    ax.bar([0,1],values,width=.55,color=['#4076ad','#d08137'])
    for i,k in enumerate(['report_absent','present_but_unusable']):
        v=data[k];ax.text(i,values[i]+2,f"{v['correct']}/{v['n']}",ha='center')
    ax.set_xticks([0,1],['Required report absent','Report visible but unusable']);ax.set_ylim(0,113)
    ax.set_ylabel('Correctly says insufficient evidence (%)');ax.set_title('Qwen3-1.7B: missing data vs unusable data')
    fig.text(.5,-.02,'Post-hoc description; wording and case families are not fully matched.',ha='center',fontsize=9,color='#555')
    fig.tight_layout();save(fig,'phase1b','02_source_failure')

def probes():
    p=ROOT/'runs/phase2_pilot_4b/probes/results.json'
    if not p.exists():return
    data=json.loads(p.read_text());fig,axes=plt.subplots(1,3,figsize=(12,3.5),sharey=True)
    for ax,(task,title) in zip(axes,[('current_report_numerical_direction','What does the new report say?'),('current_report_usable','Can the new report be used?'),('old_report_numerical_direction','What did the old report say?')]):
        r=data[task];layers=r['layers'];xx=[x['layer'] for x in layers];null=np.array([x['random_label_scores'] for x in layers])
        ax.plot(xx,[x['balanced_accuracy'] for x in layers],color='#4076ad',label='Held-out-family readout')
        ax.plot(xx,null.mean(1),color='#888',label='Shuffled-label control (5)');ax.fill_between(xx,null.min(1),null.max(1),alpha=.12,color='#888')
        ax.axhline(r['lexical_balanced_accuracy'],color='#d08137',linestyle='--',label='Word/ngram text baseline')
        ax.axhline(.5,color='#555',linestyle=':',linewidth=.8);ax.set_title(title,fontsize=10);ax.set_xlabel('Layer');ax.set_ylim(.25,1.04)
    axes[0].set_ylabel('Balanced accuracy');axes[0].legend(loc='lower left',fontsize=7)
    fig.suptitle('Before answer generation; 6 families for training, 6 held out',y=1.03);fig.tight_layout();save(fig,'phase2_pilot','02_readouts')

def decomposition():
    p=ROOT/'runs/phase1b_bp_decomposition/analysis.json'
    if not p.exists():return
    data=json.loads(p.read_text())['groups']['present_but_unusable']
    fields=['numeric_correct','source_correct','decision_seed1_correct','decision_seed2_correct']
    labels=['Read report numbers','Identify unusable report','Patient judgment\n(original seed)','Patient judgment\n(second seed)']
    fig,ax=plt.subplots(figsize=(9,3.8));values=[data[k]/data['n']*100 for k in fields]
    ax.bar(range(4),values,width=.6,color=['#4076ad','#40886b','#d08137','#bd6544'])
    for i,k in enumerate(fields):ax.text(i,values[i]+2,f"{data[k]}/{data['n']}",ha='center')
    ax.set_xticks(range(4),labels);ax.set_ylim(0,113);ax.set_ylabel('Correct (%)')
    ax.set_title('Same unusable BP reports, separate questions (Qwen3-4B)')
    fig.text(.5,-.025,'12 option variants from 4 case families; exploratory, separate question branches.',ha='center',fontsize=9,color='#555')
    fig.tight_layout();save(fig,'phase1b','03_evidence_decomposition')

if __name__=='__main__':calibration();source_failure();decomposition();behavior();probes()
