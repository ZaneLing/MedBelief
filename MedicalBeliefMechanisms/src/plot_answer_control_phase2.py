from pathlib import Path
import json
import numpy as np
from plot_phase2 import plt,COLORS,save,ROOT

def main():
    data=json.loads((ROOT/'runs/phase2c_answer_control_4b/answer_control_readout/results.json').read_text())
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,sharey=True)
    for i,scope in enumerate(['all_2a_histories','2a_current_only']):
        rr=data['results'][scope];xx=np.arange(1,37)
        for j,stratum in enumerate(['no_backup','backup_present']):
            ax=axes[i,j];layers=rr['layers'];null=np.array([x['random_label_scores'][stratum] for x in layers])
            ax.plot(xx,[x['strata'][stratum]['balanced_accuracy'] for x in layers],color=COLORS[1],lw=2,label='Hidden-state readout')
            ax.plot(xx,null.mean(1),color='#888',lw=1,label='Shuffled labels (5)');ax.fill_between(xx,null.min(1),null.max(1),alpha=.12,color='#888')
            for kind,color,label in [('words_with_numbers',COLORS[2],'Text: words + numbers'),('character_3_to_5',COLORS[3],'Text: character sequences')]:ax.axhline(rr['text_controls'][kind]['strata'][stratum]['balanced_accuracy'],color=color,ls='--',lw=1.2,label=label)
            if i==0:
                selected=json.loads((ROOT/'protocol/phase2c_layer_candidate.json').read_text())['selected_layer']
                ax.axvline(selected,color='#ad4961',ls=':',lw=1,label='2B-selected candidate layer')
            ax.set_ylim(0,1.04);ax.set_xlim(1,36);ax.axhline(.5,color='#aaa',ls=':',lw=.8)
            ax.set_title(('No backup: R1 status changes correct answer' if j==0 else 'Backup present: correct answer stays the same'),fontsize=10)
            if j==0:ax.set_ylabel(('Train: all 2A histories' if i==0 else 'Train: 2A current-only')+'\nBalanced accuracy')
            if i==1:ax.set_xlabel('Transformer layer')
    axes[0,0].legend(loc='lower right',fontsize=8);fig.suptitle('Can the readout recover R1 status independently of the final answer?')
    fig.text(.5,.005,'New 2C cases; 8 families, 32 trials per panel. Parameters fixed before 2C outputs. Failure is a measurement limit, not proof of absent information.',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.03,1,.96));save(fig,'07_answer_confound_control')
    a=json.loads((ROOT/'runs/phase2c_answer_control_4b/analysis.json').read_text());fig,ax=plt.subplots(figsize=(8.5,4))
    for j,usable in enumerate([True,False]):
        cc=[[x for x in a['cells'] if x['backup_available']==b and x['target_usable']==usable] for b in [False,True]];ns=[sum(x['n'] for x in group) for group in cc];cs=[sum(x['correct'] for x in group) for group in cc];v=np.array(cs)/ns*100;xx=np.arange(2)+(j-.5)*.3
        ax.bar(xx,v,width=.28,label=['R1 usable','R1 belongs to another patient'][j],color=COLORS[1+j])
        for x,y,c,n in zip(xx,v,cs,ns):ax.text(x,y+1.3,f'{c}/{n}',ha='center')
    ax.set_xticks([0,1],['No other usable report','Independent usable backup R2']);ax.set_ylim(0,112);ax.set_ylabel('Correct medical judgments (%)');ax.set_title('Does the model use the remaining valid evidence?');ax.legend(loc='lower left',fontsize=9)
    fig.text(.5,.005,'R1 and R2 numerical directions agree; R1 status changes but R2 can preserve the same correct answer.',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.04,1,1));save(fig,'08_backup_report_behavior')
if __name__=='__main__':main()
