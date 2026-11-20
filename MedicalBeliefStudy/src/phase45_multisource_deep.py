"""Full round-by-layer atlas, mapping checks and matched 4B replication."""
import csv,gzip,json,textwrap
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from phase41_multisource_analyze import ROOT,DATA,RUN,read,write,csvwrite,stat,fmt,SOURCES,obs,top,margin
from analyze_stages import setup,savefig

EXTRA=ROOT/'runs/belief_v4_layer_trajectories';R4=ROOT/'runs/belief_v4_4b';DEST=ROOT/'results/34_multisource_depth'
def codeobs(c,cond,t,rot):
    if t==len(c['sentences']) and cond!='mention':return obs(c,cond,t,mode='code',rot=rot)
    return read(EXTRA/f'{c["case_id"]}_{cond}_code_r{rot}_base_t{t:02d}.json')
def model4(c,cond,t=None):
    t=t or len(c['sentences']);return read(R4/'observations'/f'{c["case_id"]}_{cond}_name_r0_base_t{t:02d}.json')

def case_layer_table(c,grids,mapping,mass):
    lines=['\n## 关键层的投影读表\n\n每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。\n']
    for cond,label in [('neutral','中性历史'),('wrong','错误历史')]:
        lines.append('\n### '+label+'\n\n| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |\n|---:|---|---|---|---|\n')
        for t in range(len(c['sentences'])):
            cells=[]
            for l in [7,14,21,28]:
                if not mapping[cond][t,l-1]:cells.append('映射不一致');continue
                d=c['candidates'][int(grids[cond][t,l-1].argmax())].replace('|','/')
                cells.append(f'{d}（代码总量 {mass[cond][t,l-1]:.2g}）')
            lines.append(f'| {t+1} | '+' | '.join(cells)+' |\n')
    return ''.join(lines)

def main():
    assert read(EXTRA/'completion.json')['complete'] and read(R4/'completion.json')['complete']
    for sub in ['figures','cases']:(DEST/sub).mkdir(parents=True,exist_ok=True)
    setup();cases=[c for c in map(json.loads,(DATA/'cases.private.jsonl').read_text().splitlines()) if c['mechanism_capture']];layers=[];comparisons=[];index=[];atlas=[];attention=[];mention=[]
    audit={r['case_id']:r for r in read(DATA/'text_audit.json')['rows']}
    colors=['#3882ac','#d59435','#62a07b','#a5689f']
    with gzip.open(DEST/'all_round_layer_candidates.csv.gz','wt',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['case_id','dataset','cohort','round','condition','rotation','layer','candidate','relative_code_support','total_code_mass'])
        for ci,c in enumerate(cases):
            T=len(c['sentences']);g=c['gold_index'];w=c['wrong_index'];grids={};mapping={};mass={};names={}
            for cond in ['neutral','wrong']:
                qq=[];ag=[];mm=[];names[cond]=[obs(c,cond,t) for t in range(1,T+1)]
                for t in range(1,T+1):
                    rr=[codeobs(c,cond,t,rot) for rot in [0,2]];arr=[np.asarray(r['layer_code_support']) for r in rr];qq.append(np.mean(arr,axis=0));ag.append(arr[0].argmax(1)==arr[1].argmax(1));mm.append(np.mean([r['layer_code_candidate_mass'] for r in rr],axis=0))
                    for rot,r,a in zip([0,2],rr,arr):
                        for l in range(28):
                            for k,d in enumerate(c['candidates']):writer.writerow([c['case_id'],c['dataset'],c['cohort'],t,cond,rot,l+1,d,a[l,k],r['layer_code_candidate_mass'][l]])
                grids[cond]=np.asarray(qq);mapping[cond]=np.asarray(ag);mass[cond]=np.asarray(mm)
                n_top=np.array([top(r) for r in names[cond]])
                for l in range(28):
                    cp=grids[cond][:,l].argmax(1);native_switch=n_top[1:]!=n_top[:-1];inside_switch=cp[1:]!=cp[:-1]
                    layers.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],condition=cond,layer=l+1,source_support_final=float(grids[cond][-1,l,g]),source_top_final=int(cp[-1]==g),switches=int(inside_switch.sum()),native_switches=int(native_switch.sum()),joint_switch_fraction=float(np.mean(native_switch & inside_switch)),native_only_switch_fraction=float(np.mean(native_switch & ~inside_switch)),code_only_switch_fraction=float(np.mean(~native_switch & inside_switch)),mapping_agreement=float(mapping[cond][:,l].mean()),code_mass=float(mass[cond][:,l].mean())))
                endpoint=names[cond][-1];state=np.load(RUN/endpoint['state_file']);groups=state['token_groups'];count=np.bincount(groups,minlength=5);att=state['attention_by_group']
                for l in range(28):
                    for h in range(att.shape[1]):
                        for gi,label in enumerate(['format','old_facts','new_fact','prior','candidates']):attention.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],condition=cond,layer=l+1,head=h+1,group=label,tokens=int(count[gi]),attention_total=float(att[l,h,gi]),attention_per_token=float(att[l,h,gi]/max(count[gi],1))))
            # Matched case comparison: the two configurations differ in size and precision.
            r=dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],gold=c['gold_disease'])
            for tag,loader in [('1.7B',obs),('4B8bit',model4)]:
                final={k:loader(c,k) for k in ['none','neutral','wrong','mention','gold']};before={k:loader(c,k,T-1) for k in ['neutral','wrong']}
                for k in final:r[tag+'_'+k+'_correct']=int(top(final[k])==g)
                r[tag+'_history_accuracy_change']=r[tag+'_wrong_correct']-r[tag+'_neutral_correct']
                r[tag+'_history_margin_change']=margin(final['wrong'],c)-margin(final['neutral'],c)
                r[tag+'_update_interaction']=(margin(final['wrong'],c)-margin(before['wrong'],c))-(margin(final['neutral'],c)-margin(before['neutral'],c))
            comparisons.append(r)
            mr=dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'])
            for cond in ['neutral','wrong','mention']:
                cr=[codeobs(c,cond,T,rot) for rot in [0,2]]
                mr[cond+'_accuracy']=float(np.mean([top(v)==g for v in cr]));mr[cond+'_margin']=float(np.mean([margin(v,c) for v in cr]))
            mr['mention_minus_neutral']=mr['mention_accuracy']-mr['neutral_accuracy'];mr['wrong_minus_neutral']=mr['wrong_accuracy']-mr['neutral_accuracy'];mr['mention_minus_wrong']=mr['mention_accuracy']-mr['wrong_accuracy'];mention.append(mr)
            # Four panels, with candidate colors explicitly mapped in the case document.
            fig,axs=plt.subplots(2,2,figsize=(12.5,8.0),layout='constrained');xx=np.arange(1,T+1)
            for cond,col,label in [('neutral','#317f9e','尚无先前判断'),('wrong','#bd534c','错误先前判断')]:axs[0,0].plot(xx,[z['q_sequence'][g] for z in names[cond]],'-o',ms=3,c=col,label=label)
            axs[0,0].set(xlabel='原文证据组',ylabel='来源答案相对支持',ylim=(-.03,1.03),title='原模型完整病名评分');axs[0,0].legend(fontsize=9)
            top_grid=np.array([[top(z) for z in names[k]] for k in ['neutral','wrong']]);axs[0,1].imshow(top_grid,aspect='auto',cmap=ListedColormap(colors),vmin=-.5,vmax=3.5,extent=(.5,T+.5,1.5,-.5));axs[0,1].set(yticks=[0,1],yticklabels=['中性历史','错误历史'],xticks=xx,xlabel='原文证据组',title='原模型首选：数字对应下方候选')
            for iy in range(2):
                for ix in range(T):axs[0,1].text(ix+1,iy,str(int(top_grid[iy,ix])+1),ha='center',va='center',color='white',fontsize=10)
            for ax,cond,label in [(axs[1,0],'neutral','中性历史'),(axs[1,1],'wrong','错误历史')]:
                im=ax.imshow(grids[cond][:,:,g].T,aspect='auto',origin='lower',vmin=0,vmax=1,cmap='viridis',extent=(.5,T+.5,.5,28.5));ax.set(xlabel='原文证据组',ylabel='层',xticks=xx,yticks=[1,7,14,21,28],title=f'{label}：来源诊断的逐层代码投影');fig.colorbar(im,ax=ax,label='候选内支持')
            fig.suptitle(c['case_id']+'\n'+textwrap.fill('来源答案：'+c['gold_disease']+' ｜ 注入旧诊断：'+c['wrong_disease'],100),fontsize=11)
            savefig(fig,DEST/'cases'/c['case_id'])
            # Show all four diseases, not only the source answer. Grey cells
            # explicitly mark layers where the two code mappings disagree.
            fig,axs=plt.subplots(2,2,figsize=(12.5,8),layout='constrained')
            for col,(cond,label) in enumerate([('neutral','中性历史'),('wrong','错误历史')]):
                for k in range(4):
                    lab=str(k+1)+('（来源答案）' if k==g else '（旧诊断）' if k==w else '')
                    axs[0,col].plot(xx,[z['q_sequence'][k] for z in names[cond]],'-o',ms=2.5,lw=1.7 if k==g else 1.1,c=colors[k],label=lab)
                axs[0,col].set(xlabel='原文证据组',ylabel='四候选内相对支持',ylim=(-.03,1.03),xticks=xx,title=label+'：所有候选病名的输出支持');axs[0,col].legend(fontsize=8)
                winners=grids[cond].argmax(2).T.copy();winners[~mapping[cond].T]=4
                axs[1,col].imshow(winners,aspect='auto',origin='lower',vmin=-.5,vmax=4.5,cmap=ListedColormap(colors+['#d4d6d8']),extent=(.5,T+.5,.5,28.5))
                axs[1,col].set(xlabel='原文证据组',ylabel='层',xticks=xx,yticks=[1,7,14,21,28],title=label+'：逐层首选；灰色为两映射不一致')
            fig.suptitle(c['case_id']+'\n数字与病例正文的四个疾病一一对应；颜色在四图中相同',fontsize=11)
            savefig(fig,DEST/'cases'/(c['case_id']+'_all_candidates'))
            predn=c['candidates'][top(names['neutral'][-1])];predw=c['candidates'][top(names['wrong'][-1])]
            status='both_correct' if predn==c['gold_disease'] and predw==c['gold_disease'] else 'history_harms' if predn==c['gold_disease'] else 'history_helps' if predw==c['gold_disease'] else 'both_wrong'
            index.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],gold=c['gold_disease'],neutral=predn,wrong_history=predw,pattern=status,rounds=T))
            with (DEST/'cases'/(c['case_id']+'.md')).open('w') as f:
                f.write(f'# {c["case_id"]}\n\n来源：{c["dataset"]}，{c["source_split"]}，原始第{c["source_index"]}行（零起始）。完整题目来源答案：**{c["gold_disease"]}**；人为指定的错误旧诊断：**{c["wrong_disease"]}**。\n\n')
                if not audit[c['case_id']]['strict_keep']:f.write('**文本审计标记：本例末尾含任务引导语；原始分组完整保留，不将该轮解释为新增医学事实。严格敏感性分析排除此例。**\n\n')
                f.write('候选：'+ '；'.join(f'{k+1} = {d}' for k,d in enumerate(c['candidates']))+'。\n\n')
                f.write(f'![全部四候选与逐层首选](./{c["case_id"]}_all_candidates.png)\n\n上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。\n\n![逐轮与逐层](./{c["case_id"]}.png)\n\n上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。\n\n| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |\n|---:|---|---|---|\n')
                for t in range(1,T+1):f.write(f'| {t} | '+c['sentences'][t-1].replace('|','/').replace('\n','<br>')+' | '+c['candidates'][top(names['neutral'][t-1])]+' | '+c['candidates'][top(names['wrong'][t-1])]+' |\n')
                f.write(case_layer_table(c,grids,mapping,mass))
            if ci==0 or (ci+1)%10==0:print('atlas',ci+1,len(cases),flush=True)
    csvwrite(DEST/'layer_patient_metrics.csv',layers);csvwrite(DEST/'matched_models.csv',comparisons);csvwrite(DEST/'case_index.csv',index)
    csvwrite(DEST/'mention_code_followup.csv',mention)
    with gzip.open(DEST/'attention_by_case_layer_head.csv.gz','wt',newline='') as f:
        wri=csv.DictWriter(f,fieldnames=list(attention[0]));wri.writeheader();wri.writerows(attention)
    # Compare native code readouts at matched endpoints, keeping model depth explicit.
    model_layers=[]
    fig,axs=plt.subplots(2,3,figsize=(14,7.5),layout='constrained')
    for mi,model in enumerate(['1.7B','4B8bit']):
        for cond,col,label in [('neutral','#317f9e','中性历史'),('wrong','#bd534c','错误历史')]:
            patient=[]
            for c in cases:
                T=len(c['sentences'])
                zz=[codeobs(c,cond,T,rot) if model=='1.7B' else read(R4/'observations'/f'{c["case_id"]}_{cond}_code_r{rot}_base_t{T:02d}.json') for rot in [0,2]]
                aa=[np.array(z['layer_code_support']) for z in zz];q=np.mean(aa,axis=0);ma=np.mean([z['layer_code_candidate_mass'] for z in zz],axis=0);ag=(aa[0].argmax(1)==aa[1].argmax(1)).astype(float)
                for l in range(len(q)):model_layers.append(dict(case_id=c['case_id'],dataset=c['dataset'],cohort=c['cohort'],model=model,condition=cond,layer=l+1,total_layers=len(q),source_correct=int(q[l].argmax()==c['gold_index']),source_support=q[l,c['gold_index']],mapping_agreement=ag[l],code_mass=ma[l]))
                patient.append(np.array([(q.argmax(1)==c['gold_index']).astype(float),ag,ma]))
            pp=np.array(patient);xx=np.arange(1,pp.shape[-1]+1)
            for j in range(3):
                vv=[stat(pp[:,j,l]) for l in range(pp.shape[-1])];axs[mi,j].plot(xx,[v['mean'] for v in vv],c=col,label=label);axs[mi,j].fill_between(xx,[v['low'] for v in vv],[v['high'] for v in vv],color=col,alpha=.13);axs[mi,j].set(xlabel='层',title=model+' · '+['投影首选命中','两映射是否同一疾病','四代码全词表概率总量'][j]);axs[mi,j].legend(fontsize=8)
            axs[mi,0].set_ylim(0,1);axs[mi,1].set_ylim(0,1);axs[mi,2].set(yscale='log',ylim=(1e-8,1))
    fig.suptitle('相同94例、完整输入的跨配置内部读表｜1.7B为28层，4B为36层')
    savefig(fig,DEST/'figures/cross_configuration_readout');csvwrite(DEST/'cross_configuration_layers.csv',model_layers)
    models=[]
    for ds in SOURCES+['all']:
        for cohort in ['all','development','confirmation']:
            rr=[r for r in comparisons if (ds=='all' or r['dataset']==ds) and (cohort=='all' or r['cohort']==cohort)]
            if not rr:continue
            item=dict(dataset=ds,cohort=cohort,n=len(rr))
            for field in comparisons[0]:
                if field.startswith(('1.7B','4B8bit')):item[field]=stat([r[field] for r in rr])
            item['paired_accuracy_gain_none']=stat([r['4B8bit_none_correct']-r['1.7B_none_correct'] for r in rr]);models.append(item)
    mention_stats=[]
    for ds in SOURCES+['all']:
        for cohort in ['all','development','confirmation']:
            rr=[r for r in mention if (ds=='all' or r['dataset']==ds) and (cohort=='all' or r['cohort']==cohort)]
            if rr:mention_stats.append(dict(dataset=ds,cohort=cohort,n=len(rr),**{k:stat([r[k] for r in rr]) for k in ['neutral_accuracy','wrong_accuracy','mention_accuracy','mention_minus_neutral','wrong_minus_neutral','mention_minus_wrong']}))
    write(DEST/'summary.json',dict(patients=len(cases),rounds=sum(len(c['sentences']) for c in cases),projection_conditions=4*sum(len(c['sentences']) for c in cases),layer_candidate_rows=4*4*28*sum(len(c['sentences']) for c in cases),model_comparison=models,mention_code_followup=mention_stats,patterns=dict(__import__('collections').Counter(r['pattern'] for r in index)),api_cost_usd=0))
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for cond,col,label in [('neutral','#317f9e','中性历史'),('wrong','#bd534c','错误历史')]:
        ss=[];mass=[]
        for l in range(1,29):
            subset=[r for r in layers if r['condition']==cond and r['layer']==l];ss.append(stat([r['mapping_agreement'] for r in subset]));mass.append(stat([r['switches'] for r in subset]))
        for ax,vals in zip(axs,[ss,mass]):ax.plot(range(1,29),[v['mean'] for v in vals],label=label,c=col);ax.fill_between(range(1,29),[v['low'] for v in vals],[v['high'] for v in vals],color=col,alpha=.15)
    axs[0].set(title='换一套代码，是否仍选择同一疾病',xlabel='层',ylabel='每病例的映射一致率',ylim=(0,1));axs[1].set(title='新证据逐步加入时，投影首选换了几次',xlabel='层',ylabel='每病例切换次数');axs[0].legend();axs[1].legend();savefig(fig,DEST/'figures/layer_transition_and_mapping')
    with (DEST/'CASE_ATLAS.md').open('w') as f:
        f.write('# 全部94例的逐轮、逐层医学判断图谱\n\n每个病例有原文证据、原模型首选及逐层代码投影。没有按异常大小删选病例。\n\n| 来源 | 病例 | 来源答案 | 中性终点 | 错误历史终点 |\n|---|---|---|---|---|\n')
        for r in index:f.write(f'| {r["dataset"]} | [{r["case_id"]}](cases/{r["case_id"]}.md) | {r["gold"]} | {r["neutral"]} | {r["wrong_history"]} |\n')
    with (DEST/'RESULTS.md').open('w') as f:
        f.write(f'# 逐轮逐层展开与模型复核\n\n本阶段覆盖同{len(cases)}例，共{sum(len(c["sentences"]) for c in cases)}个累计证据前缀。每个前缀均有中性/错误历史、两种代码映射、28层、四候选的投影支持。完整病名的原生评分另行保留。\n\n')
        f.write('## 同病例跨配置复核\n\n| 来源 | 例数 | 1.7B无历史正确 | 4B无历史正确 | 1.7B错误−中性变化 | 4B错误−中性变化 |\n|---|---:|---:|---:|---|---|\n')
        for r in models:
            if r['cohort']=='all' and r['dataset']!='all':f.write(f'| {r["dataset"]} | {r["n"]} | {round(r["1.7B_none_correct"]["mean"]*r["n"])} | {round(r["4B8bit_none_correct"]["mean"]*r["n"])} | {fmt(r["1.7B_history_accuracy_change"],True)} | {fmt(r["4B8bit_history_accuracy_change"],True)} |\n')
        f.write('\n1.7B为FP16，4B为8-bit，大小与精度共同变化。两者使用相同病例和候选；本表不将差异单独归因于参数规模。\n\n## 每轮每层究竟读到了什么\n\n![逐层转移与映射](figures/layer_transition_and_mapping.png)\n\n模型中间层没有天然命名为疾病的概率槽。此处把最终输出头接到中间状态，读取四个代码的相对支持；两种映射一致性帮助判断读表受代码本身影响的程度。它与原先训练的DDxPlus疾病读出器不同。\n\n[全部病例图谱](CASE_ATLAS.md) · [每轮每层全部候选分数](all_round_layer_candidates.csv.gz) · [每病例逐层指标](layer_patient_metrics.csv) · [逐层逐头注意力](attention_by_case_layer_head.csv.gz) · [同病例模型比较](matched_models.csv)\n\n![同病例两配置内部读表](figures/cross_configuration_readout.png)\n\n[跨配置逐层数据](cross_configuration_layers.csv)\n')
        f.write('\n## 未采纳病名的代码作答复核\n\n这是开发集观察后追加的检验；每患者对两种预定代码映射取平均，区间按患者计算。\n\n| 确认集来源 | 病例数 | 中性准确率 | 错误历史准确率 | 仅提及准确率 | 提及−中性及95%CI |\n|---|---:|---|---|---|---|\n')
        for r in mention_stats:
            if r['cohort']=='confirmation':f.write(f'| {r["dataset"]} | {r["n"]} | {fmt(r["neutral_accuracy"],True)} | {fmt(r["wrong_accuracy"],True)} | {fmt(r["mention_accuracy"],True)} | {fmt(r["mention_minus_neutral"],True)} |\n')

if __name__=='__main__':main()
