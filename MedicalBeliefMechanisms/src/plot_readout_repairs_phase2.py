from pathlib import Path
import json
import numpy as np
from plot_phase2 import ROOT,plt,COLORS,save

def main():
    data=json.loads((ROOT/'runs/phase2c_answer_control_4b/source_readout_repairs/results.json').read_text())['results'];fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,sharey=True)
    names=['train_2a_2b_test_2c','train_2c_half_test_other_half']
    for i,name in enumerate(names):
        rr=data[name];layers=rr['layers'];xx=np.arange(1,37)
        for j,stratum in enumerate(['no_backup','backup_present']):
            ax=axes[i,j];null=np.array([x['random_label_scores'][stratum] for x in layers])
            ax.plot(xx,[x['strata'][stratum]['balanced_accuracy'] for x in layers],color=COLORS[1],lw=2,label='Hidden-state readout');ax.plot(xx,null.mean(1),color='#888',lw=1,label='Shuffled labels (5)');ax.fill_between(xx,null.min(1),null.max(1),color='#888',alpha=.12)
            for kind,color,label in [('words_with_numbers',COLORS[2],'Text: words + numbers'),('character_3_to_5',COLORS[3],'Text: character sequences')]:ax.axhline(rr['text_controls'][kind]['strata'][stratum]['balanced_accuracy'],color=color,ls='--',lw=1.2,label=label)
            ax.set_xlim(1,36);ax.set_ylim(0,1.04);ax.axhline(.5,color='#aaa',ls=':',lw=.8);ax.set_title(('No usable backup' if j==0 else 'Usable backup: same correct answer')+f" (n={layers[-1]['strata'][stratum]['n']})",fontsize=10)
            if j==0:ax.set_ylabel(('Train: 2A + 2B' if i==0 else 'Train: half of 2C')+'\nBalanced accuracy')
            if i==1:ax.set_xlabel('Transformer layer')
    axes[0,0].legend(loc='lower right',fontsize=8);fig.suptitle('Readout repairs tested on unseen 2C numerical families')
    fig.text(.5,.005,'Exploratory repairs fixed before 2C outputs. Bottom row shares a template across train/test; no causal or belief claim.',ha='center',fontsize=9,color='#555');fig.tight_layout(rect=(0,.03,1,.96));save(fig,'10_readout_repairs')
if __name__=='__main__':main()
