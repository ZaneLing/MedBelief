"""Descriptive cross-dataset and selective results; tasks are not interchangeable."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from lightweight_multidataset import OUT

names=['DXY','MZ-4','MZ-10','MedQA','MedMCQA\n(single only)']
values=[];ns=[]
for ds in ['dxy','mz4','mz10','medqa','medmcqa']:
    r=json.loads((OUT/f'{ds}_results.json').read_text())
    m=r['views']['all_values']['all_test'] if 'views' in r else r['selected']
    values.append(m['accuracy']*100);ns.append(m['n'])
s=json.loads((OUT/'transfer_selective.json').read_text())['selective']
fig,axes=plt.subplots(1,2,figsize=(12,5.7));colors=['#286a84']*3+['#b98a39']*2
bars=axes[0].bar(np.arange(5),values,color=colors,width=.64)
axes[0].bar_label(bars,fmt='%.2f%%',padding=3,fontsize=10)
axes[0].set(xticks=np.arange(5),xticklabels=[n+f'\nn={c:,}' for n,c in zip(names,ns)],ylim=(0,105),
    ylabel='Accuracy (%)',title='All cases answered')
x=np.arange(3)
for shift,key,label,color in [(-.18,'test_coverage','Coverage','#82b6b2'),(.18,'test_selective_accuracy','Accuracy on answered cases','#286a84')]:
    b=axes[1].bar(x+shift,[100*s[d][key] for d in ['dxy','mz4','mz10']],.36,label=label,color=color)
    axes[1].bar_label(b,fmt='%.1f%%',padding=3,fontsize=10)
axes[1].set(xticks=x,xticklabels=[label+f"\n{s[ds]['test_correct']} / {s[ds]['test_accepted']} correct" for ds,label in [('dxy','DXY'),('mz4','MZ-4'),('mz10','MZ-10')]],
    ylim=(0,110),ylabel='Percent',title='Abstention threshold fixed on calibration data')
axes[1].legend(loc='upper center',bbox_to_anchor=(.5,-.18),frameon=False)
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('Lightweight medical models: measured accuracy and coverage',fontsize=16,y=.98)
fig.text(.5,.045,'Different datasets and label spaces: these bars are not a GPT-6 comparison. Selective results cover only accepted cases.',ha='center',fontsize=10)
fig.subplots_adjust(left=.075,right=.98,top=.85,bottom=.3,wspace=.26)
fig.savefig(OUT/'multidataset_results.png',dpi=180)
fig.savefig(OUT/'multidataset_results.pdf')
