"""Chinese case figures and brief reading notes; frozen numerical results untouched."""
import json
import numpy as np
import matplotlib.pyplot as plt
from phase14_analyze import ROOT,RUN,cases,record
from analyze_stages import setup,savefig
ZH={'Acute COPD exacerbation / infection':'慢阻肺急性加重/感染','Acute dystonic reactions':'急性肌张力障碍反应','Acute laryngitis':'急性喉炎','Acute otitis media':'急性中耳炎','Acute pulmonary edema':'急性肺水肿','Acute rhinosinusitis':'急性鼻窦炎','Allergic sinusitis':'过敏性鼻窦炎','Anaphylaxis':'严重过敏反应','Anemia':'贫血','Atrial fibrillation':'心房颤动','Boerhaave':'自发性食管破裂','Bronchiectasis':'支气管扩张','Bronchiolitis':'细支气管炎','Bronchitis':'支气管炎','Bronchospasm / acute asthma exacerbation':'支气管痉挛/哮喘急性发作','Chagas':'查加斯病','Chronic rhinosinusitis':'慢性鼻窦炎','Cluster headache':'丛集性头痛','Croup':'哮吼','Ebola':'埃博拉病','Epiglottitis':'会厌炎','GERD':'胃食管反流病','Guillain-Barré syndrome':'吉兰-巴雷综合征','HIV (initial infection)':'HIV初期感染','Influenza':'流感','Inguinal hernia':'腹股沟疝','Larygospasm':'喉痉挛','Localized edema':'局部水肿','Myasthenia gravis':'重症肌无力','Myocarditis':'心肌炎','PSVT':'阵发性室上性心动过速','Pancreatic neoplasm':'胰腺肿瘤','Panic attack':'惊恐发作','Pericarditis':'心包炎','Pneumonia':'肺炎','Possible NSTEMI / STEMI':'可能的心肌梗死','Pulmonary embolism':'肺栓塞','Pulmonary neoplasm':'肺部肿瘤','SLE':'系统性红斑狼疮','Sarcoidosis':'结节病','Scombroid food poisoning':'鱼类组胺中毒','Spontaneous pneumothorax':'自发性气胸','Spontaneous rib fracture':'自发性肋骨骨折','Stable angina':'稳定型心绞痛','Tuberculosis':'结核病','URTI':'上呼吸道感染','Unstable angina':'不稳定型心绞痛','Viral pharyngitis':'病毒性咽炎','Whooping cough':'百日咳'}
def main():
    setup();dest=ROOT/'results/14_fixed_panel';scores=np.load(dest/'prefix_readout_scores.npz');classes=scores['classes'].tolist();diseases=json.loads((RUN/'manifest.json').read_text())['candidate_diseases'];_,test=cases()
    summary=json.loads((dest/'summary.json').read_text());fig,ax=plt.subplots(figsize=(9,5))
    for view,label,color in [('append','逐条追加','#2878b5'),('panel','固定问卷','#e07b21')]:
        r=summary['endpoints'][view];ax.plot(range(1,29),r['layer_accuracy'],color=color,label=label+'：外部读出')
        ax.axhline(r['native24']['mean'],color=color,ls='--',label=label+'：模型自身病名评分')
    ax.set(xlabel='模型层数',ylabel='新120例准确率（统一24病）',ylim=(0,1),xticks=[1,7,14,21,28]);ax.legend(fontsize=9);fig.tight_layout();savefig(fig,dest/'figures/heldout_layers')
    for c in [c for c in test if c['deep_capture']]:
        cid=c['case_id'];T=len(c['orders']['base']);gi=diseases.index(c['gold_disease']);yi=classes.index(c['gold_disease']);views={};chosen={}
        for view in ['append','panel']:
            q=np.array([record(c,view,t)[1]['q_sequence'] for t in range(T+1)]);s=scores[f'{cid}_{view}'];rank=1+(s>s[:,:,yi,None]).sum(-1);views[view]=(q,s,rank)
            picks=sorted(set(q.argmax(-1).tolist()+[gi]),key=lambda d:-q[:,d].max())[:6]
            if gi not in picks:picks[-1]=gi
            chosen[view]=picks
        union=sorted(set(chosen['append']+chosen['panel']));colors={d:plt.get_cmap('tab20')(i/20) for i,d in enumerate(union)};colors[gi]='black'
        fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for vi,view in enumerate(['append','panel']):
            q,s,rank=views[view]
            for d in chosen[view]:axs[0,vi].plot(range(T+1),q[:,d],marker='s' if d==gi else 'o',ms=3,lw=2.2 if d==gi else 1.4,color=colors[d],label=ZH.get(diseases[d],diseases[d])+('【来源标签】' if d==gi else ''),zorder=10 if d==gi else 2)
            axs[0,vi].set(title={'append':'逐条追加资料','panel':'固定问卷，逐条填写答案'}[view],xlabel='新增证据轮次',ylabel='模型输出：疾病名相对支持',ylim=(-.02,1.02),xticks=range(T+1));axs[0,vi].legend(fontsize=8,loc='best')
            im=axs[1,vi].imshow(rank.T,origin='lower',aspect='auto',extent=[-.5,T+.5,.5,28.5],vmin=1,vmax=24,cmap='viridis_r');axs[1,vi].set(xlabel='新增证据轮次',ylabel='模型层数',title='内部读出：来源标签排第几？（黄色=靠前）',xticks=range(T+1),yticks=[1,7,14,21,28])
        fig.colorbar(im,ax=axs[1,:].tolist(),label='外部读出排名；不是疾病概率',ticks=[1,6,12,18,24],shrink=.85)
        fig.suptitle(f'{cid}｜来源标签：{ZH.get(c["gold_disease"],c["gold_disease"])}',fontsize=14);savefig(fig,dest/'cases'/cid)
        notes=[]
        for view,label in [('append','逐条追加'),('panel','固定问卷')]:
            q,s,rank=views[view];out=ZH.get(diseases[q[-1].argmax()],diseases[q[-1].argmax()]);reader=classes[s[-1,27].argmax()];notes.append(f'- {label}终点：模型输出首选**{out}**；第28层外部读出首选**{ZH.get(reader,reader)}**。')
        path=dest/'cases'/f'{cid}.md';content=path.read_text();marker='\n## 图怎么读\n';content=content.split(marker)[0]
        content+=marker+'\n上排看模型实际更支持哪种病，黑线是来源标签；下排看每层内部状态经独立训练的读出器后，来源标签排第几，黄色更靠前。两张图测量的对象不同，下排不代表模型自己报出的概率。\n\n'+'\n'.join(notes)+'\n';path.write_text(content)
    intro=dest/'CASE_ATLAS.md';text=intro.read_text();text=text.replace('上排为最终输出，下面为28层读出中的源标签排名。每例均展示两种呈现方式和完整证据。','上排看模型的疾病支持，黑线是来源标签；下排看每层外部读出中来源标签排第几，黄色更靠前。下排不是模型自己报告的概率。每例提供中文图例、完整英文源证据及终点的中文解释。');intro.write_text(text)
    (dest/'disease_display_names.json').write_text(json.dumps(ZH,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
