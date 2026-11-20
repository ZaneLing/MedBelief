"""Render verified probe outputs with one-based layer labels and a separate colorbar."""
import json,csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from analyze_stages import ROOT,setup,savefig
def main():
    setup();dest=ROOT/'results/11_disease_information';s=json.loads((dest/'summary.json').read_text())
    fig,ax=plt.subplots(figsize=(11,6))
    for k,label in [('name_to_name','疾病名：同接口读出'),('code0_to_code0','字母编码：同映射读出'),('code0_to_code16','字母编码：换映射读出'),('code0_to_name','编码训练 → 疾病名测试')]:ax.plot(range(1,29),s['layer_accuracy'][k],label=label)
    ax.plot(range(1,29),s['null_mean_accuracy'],color='gray',ls=':',label='打乱训练标签')
    ax.axhline(s['text_accuracy']['mean'],color='black',ls='--',label='病例文本分类')
    ax.axhline(s['native_restricted24_accuracy']['mean'],color='darkred',ls='-.',label='模型自身评分（同24病）')
    ax.set(xlabel='模型层',ylabel='未见病例准确率（24种疾病）',ylim=(0,1.05),xlim=(1,28),xticks=[1,7,14,21,28]);ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(fontsize=9,loc='upper left',ncol=2);fig.tight_layout();savefig(fig,dest/'figures/heldout_disease_information')
    cases=[json.loads(x) for x in (ROOT/'data/full49_v1/cases.private.jsonl').read_text().splitlines()];chosen=[c for c in cases if c['deep_capture']][:4];rows=list(csv.DictReader((dest/'heldout_trajectory_readouts.csv').open()))
    labels={'HIV (initial infection)':'急性HIV感染','Viral pharyngitis':'病毒性咽炎','Acute otitis media':'急性中耳炎','URTI':'上呼吸道感染'}
    fig,axes=plt.subplots(2,2,figsize=(11,8));fig.subplots_adjust(left=.08,right=.83,bottom=.08,top=.92,hspace=.4,wspace=.22)
    for ax,c in zip(axes.flat,chosen):
        T=len(c['orders']['base']);mat=np.zeros((28,T+1))
        for r in rows:
            if r['case_id']==c['case_id']:mat[int(r['layer'])-1,int(r['round'])]=int(r['gold_rank'])
        assert mat.min()>=1 and mat.max()<=24
        im=ax.imshow(mat,origin='lower',aspect='auto',vmin=1,vmax=24,cmap='viridis_r',extent=[-.5,T+.5,.5,28.5])
        ax.set(title=labels.get(c['gold_disease'],c['gold_disease']),xlabel='证据轮次（0为初始资料）',ylabel='模型层',yticks=[1,7,14,21,28])
    cax=fig.add_axes([.875,.18,.025,.65]);fig.colorbar(im,cax=cax,ticks=[1,5,10,15,20,24],label='最终标签在24病中的排名（1最好）');savefig(fig,dest/'figures/heldout_readout_examples')

if __name__=='__main__':main()
