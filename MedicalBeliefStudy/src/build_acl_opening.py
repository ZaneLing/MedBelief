import json,numpy as np,matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases
from analyze_stages import savefig
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42})
cid='ddx_test_0041136';ds=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];s=np.load(ROOT/'results/14_fixed_panel/prefix_readout_scores.npz');cl=s['classes'].tolist();g=ds.index('Acute otitis media');y=cl.index('Acute otitis media');fig,ax=plt.subplots(2,2,figsize=(7,3.8),layout='constrained')
for col,(v,title) in enumerate([('append','Same facts: append'),('panel','Same facts: fixed questionnaire')]):
 q=np.array([json.loads((RUN/'observations'/f'{cid}_{v}_base_t{t:02d}.json').read_text())['q_sequence'] for t in range(6)])
 for name,color in [('Acute otitis media','#1675a9'),('Acute COPD exacerbation / infection','#d2782b'),('Acute laryngitis','#6a8e64')]:ax[0,col].plot(range(6),q[:,ds.index(name)],'-o',ms=3,label=name.replace('Acute COPD exacerbation / infection','COPD exacerbation/infection'),color=color)
 ax[0,col].set(title=title,ylim=(-.02,1.04),ylabel='Native support' if col==0 else '',xticks=range(6));ax[0,col].axvline(1,color='gray',lw=.8,ls=':')
 z=s[f'{cid}_{v}'];rank=1+(z>z[:,:,y,None]).sum(-1);im=ax[1,col].imshow(rank.T,aspect='auto',origin='lower',extent=[-.5,5.5,.5,28.5],vmin=1,vmax=24,cmap='viridis_r');ax[1,col].set(xlabel='Evidence round',ylabel='Layer' if col==0 else '',xticks=range(6),yticks=[1,7,14,21,28])
ax[0,0].legend(fontsize=6,loc='center right');fig.colorbar(im,ax=list(ax[1]),ticks=[1,12,24],label='Label rank (readout)',shrink=.85);savefig(fig,ROOT/'acl_paper/submission/figures/opening_case')
