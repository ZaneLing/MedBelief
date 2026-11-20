"""Analyze saved actual observations; never calls a model or modifies raw results."""
from pathlib import Path
import argparse, collections, csv, hashlib, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap, BoundaryNorm

ROOT = Path(__file__).resolve().parents[1]
ZH = ['肺炎', '支气管炎', '哮喘急性发作', '肺栓塞', '自发性气胸', '急性肺水肿']
COLORS = ['#c43b37', '#de952d', '#477bb5', '#8c5baa', '#35947b', '#69717d']
EVIDENCE_ZH = {
 'E_5':'曾有肺部积液', 'E_8':'目前接受透析', 'E_14':'休息时也有胸痛', 'E_21':'曾有自发性气胸',
 'E_34':'目前患有活动性癌症', 'E_45':'咯血', 'E_46':'过去一年哮喘发作至少两次', 'E_50':'出汗明显增多',
 'E_53':'本次就诊相关疼痛（同时揭示性质、位置、程度、放射等记录）', 'E_66':'明显气短或呼吸困难',
 'E_67':'夜间因憋气或气短醒来', 'E_77':'咳嗽，痰变色或增多', 'E_79':'吸烟', 'E_85':'家人有哮喘',
 'E_91':'发热', 'E_94':'寒战', 'E_95':'有帕金森病史', 'E_97':'咽痛', 'E_100':'目前服用激素',
 'E_101':'过去一年因哮喘住院', 'E_104':'有高血压或服用降压药', 'E_105':'曾有心肌梗死或有心绞痛',
 'E_106':'有心力衰竭病史', 'E_107':'曾有卒中', 'E_109':'曾有深静脉血栓',
 'E_110':'过去四周有连续超过三天不能活动或起床', 'E_116':'近两周有感冒', 'E_117':'曾有肺炎',
 'E_119':'曾被诊断慢性鼻窦炎', 'E_122':'有慢性阻塞性肺疾病病史', 'E_124':'有哮喘或曾用支气管扩张药',
 'E_129':'有自认为与本次就诊相关的皮肤问题（同时揭示颜色、位置、程度等记录）',
 'E_144':'广泛肌肉疼痛', 'E_151':'身体局部肿胀（同时揭示部位）', 'E_159':'曾失去意识',
 'E_161':'近期食欲下降或更容易饱', 'E_165':'家人曾有气胸', 'E_175':'本次出现疲倦、全身不适、肌痛或整体状态变化',
 'E_196':'近一个月接受过手术', 'E_201':'咳嗽', 'E_204':'近四周出国旅行', 'E_207':'住在大城市',
 'E_209':'疫苗按时接种', 'E_214':'呼气时有喘鸣', 'E_218':'活动时症状加重、休息时缓解',
 'E_219':'夜间症状更明显', 'E_220':'深吸气使疼痛加重', 'E_222':'每天接触二手烟', 'E_226':'更容易发生常见过敏'
}

def evidence_zh(group):
    a=group['items'][0]['answer_en'];answer={'Yes':'是','No':'否'}.get(a,a)
    return EVIDENCE_ZH.get(group['question_group_id'],group['items'][0]['question_en'])+'：'+answer

def dump(path, x): path.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def table(path, rows):
    with path.open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def win(q):
    idx=q.argmax(-1)
    return np.where((q==q.max(-1,keepdims=True)).sum(-1)==1,idx,-1)
def first_stable(correct):
    first=next((i for i,v in enumerate(correct) if v),None)
    stable=next((i for i in range(len(correct)) if all(correct[i:])),None)
    return first,stable
def display(v): return '未达到' if v is None else str(v)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',required=True);args=ap.parse_args()
    run=ROOT/'runs'/args.run_id
    completion=json.loads((run/'completion.json').read_text()); assert completion['complete']
    manifest=json.loads((run/'manifest.json').read_text())
    diseases=manifest['disease_order'];names=dict(zip(diseases,ZH))
    private={r['case_id']:r for r in map(json.loads,(ROOT/'data/pilot_cases.private.jsonl').read_text().splitlines())}
    public=list(map(json.loads,(ROOT/'data/pilot_prefixes.public.jsonl').read_text().splitlines()))
    byprefix={(r['case_id'],r['round']):r for r in public}
    records=[json.loads(p.read_text()) for p in sorted((run/'observations').glob('*.json'))]
    assert len(records)==176
    assert len({r['observation_id'] for r in records})==176
    primary=[r for r in records if r['rotation']==0];assert len(primary)==131
    # The model runner never loads this private evaluation table.
    for r in primary:
        p=byprefix[r['case_id'],r['round']];c=private[r['case_id']]
        expected=[c['initial_question_group']]+c['new_group_order'][:r['round']]
        assert [g['question_group_id'] for g in p['revealed_groups']]==expected
        assert 'gold_disease' not in p
        assert sha(run/r['states_file'])==r['states_sha256']
    for font in ['/System/Library/Fonts/Supplemental/Arial Unicode.ttf','/System/Library/Fonts/Hiragino Sans GB.ttc']:
        if Path(font).exists():
            font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();break
    plt.rcParams['axes.unicode_minus']=False
    figures=ROOT/'figures'/args.run_id;figures.mkdir(exist_ok=True)
    metrics=run/'metrics';metrics.mkdir(exist_ok=True)
    all_metrics=[];events=[];round_rows=[];layer_mass=[];case_details=[]
    for cid,c in private.items():
        rs=sorted((r for r in primary if r['case_id']==cid),key=lambda r:r['round'])
        assert len(rs)==c['selected_new_groups']+1
        arrays=[np.load(run/r['states_file']) for r in rs]
        qs=np.array([r['candidate_support'] for r in rs]); y=diseases.index(c['gold_disease'])
        lq=np.stack([a['stage_candidate_support'][:,-1] for a in arrays])
        lm=np.stack([a['stage_candidate_mass'][:,-1] for a in arrays]);layer_mass.extend(lm)
        preds=win(qs);correct=preds==y;first,stable=first_stable(correct)
        ls=win(lq);margins=lq[:,:,y]-np.max(np.delete(lq,y,axis=-1),axis=-1)
        m={'case_id':cid,'gold':c['gold_disease'],'rounds':len(rs),'first_correct':first,'stable_correct':stable,
           'regressions':int(np.sum(correct[:-1]&~correct[1:])), 'recoveries':int(np.sum(~correct[:-1]&correct[1:])),
           'initial_prediction':diseases[int(preds[0])] if preds[0]>=0 else 'tie',
           'final_prediction':diseases[int(preds[-1])] if preds[-1]>=0 else 'tie',
           'final_correct':bool(correct[-1]),'initial_gold_support':float(qs[0,y]),'final_gold_support':float(qs[-1,y]),
           'min_candidate_mass':min(r['candidate_mass'] for r in rs)}
        all_metrics.append(m)
        for t,r in enumerate(rs):
            row={'case_id':cid,'round':t,'new_question_group':r['new_question_group'],'gold':c['gold_disease'],
                 'conditional_top':r['conditional_top_disease'],'candidate_mass':r['candidate_mass'],
                 'generated_text':r['generated_text'],'strict_format_valid':r['format_valid']}
            row.update({d:float(qs[t,i]) for i,d in enumerate(diseases)});round_rows.append(row)
            if t:
                delta=qs[t]-qs[t-1];new=byprefix[cid,t]['revealed_groups'][-1]
                event={'case_id':cid,'round':t,'gold':c['gold_disease'],'new_evidence':new,
                       'previous_top':rs[t-1]['conditional_top_disease'],'current_top':r['conditional_top_disease'],
                       'gold_change':float(delta[y]),'delta':delta.tolist(),
                       'changed_readout_layers':(np.flatnonzero(ls[t]!=ls[t-1])+1).tolist(),
                       'layers_toward_gold':(np.flatnonzero(lq[t,:,y]>lq[t-1,:,y])+1).tolist(),
                       'layer_gold_changes':(lq[t,:,y]-lq[t-1,:,y]).tolist()}
                events.append(event)
        # Four panels make terminal preference, layer direction and readout strength visible.
        fig,axs=plt.subplots(4,1,figsize=(12,15),gridspec_kw={'height_ratios':[1.5,1.2,1.2,1]},constrained_layout=True)
        for d in range(6): axs[0].plot(range(len(rs)),qs[:,d],label=ZH[d]+('（数据标签）' if d==y else ''),color=COLORS[d],lw=3 if d==y else 1.6,marker='o',ms=3)
        axs[0].set(ylabel='六种候选内部的相对支持',ylim=(-.02,1.02),title='① 最终输出：每来一组证据，偏向哪种病？')
        axs[0].legend(ncol=3,fontsize=9,loc='upper center',bbox_to_anchor=(.5,1.28));axs[0].grid(alpha=.2)
        cm=ListedColormap(COLORS+['#eeeeee']);plotwin=np.where(ls.T<0,6,ls.T)
        axs[1].imshow(plotwin,origin='lower',aspect='auto',cmap=cm,norm=BoundaryNorm(np.arange(-.5,7.5),7),extent=[-.5,len(rs)-.5,.5,28.5])
        axs[1].set(ylabel='模型层（1 → 28）',title='② 每层原始读出最支持的疾病（颜色同上；尚未校准）')
        im=axs[2].imshow(margins.T,origin='lower',aspect='auto',vmin=-1,vmax=1,cmap='RdBu',extent=[-.5,len(rs)-.5,.5,28.5])
        axs[2].set(ylabel='模型层（1 → 28）',title='③ 数据标签疾病的领先幅度：蓝=领先，红=落后')
        fig.colorbar(im,ax=axs[2],label='标签疾病支持 − 最大竞争疾病支持')
        im=axs[3].imshow(np.log10(np.maximum(lm.T,1e-12)),origin='lower',aspect='auto',vmin=-8,vmax=0,cmap='viridis',extent=[-.5,len(rs)-.5,.5,28.5])
        axs[3].set(ylabel='模型层（1 → 28）',xlabel='证据轮次（第0轮为初始资料）',title='④ 读出格式质量：六个答案代码占完整词表的总概率（log10）')
        fig.colorbar(im,ax=axs[3],label='0=总概率1；−4=总概率0.0001')
        for ax in axs:ax.set_xticks(range(len(rs)));ax.set_xlim(-.5,len(rs)-.5)
        fig.suptitle(f'{cid}｜数据标签：{ZH[y]}｜末轮模型选择：{names[m["final_prediction"]]}',fontsize=15)
        for ext in ['png','pdf']:fig.savefig(figures/f'{cid}.{ext}',dpi=160)
        plt.close(fig)
        # Largest terminal change is a descriptive, post-hoc example, not a new hypothesis test.
        ce=[e for e in events if e['case_id']==cid]
        key=max(ce,key=lambda e:abs(e['gold_change']));t=key['round']
        rival=int(np.argmax(np.where(np.arange(6)==y,-np.inf,qs[t])))
        stz=arrays[t]['stage_candidate_logits'];gap=stz[:,:,y]-stz[:,:,rival]
        module={'case_id':cid,'round':t,'pair':[diseases[y],diseases[rival]],
                'attention_gap_change':(gap[:,1]-gap[:,0]).tolist(),'mlp_gap_change':(gap[:,2]-gap[:,1]).tolist()}
        dump(metrics/f'{cid}_module_example.json',module)
        fig,ax=plt.subplots(figsize=(11,4),constrained_layout=True)
        xx=np.arange(1,29);ax.bar(xx-.2,gap[:,1]-gap[:,0],.4,label='注意力阶段',color='#477bb5');ax.bar(xx+.2,gap[:,2]-gap[:,1],.4,label='MLP阶段',color='#de952d')
        ax.axhline(0,color='black',lw=.6);ax.legend();ax.set(xlabel='模型层',ylabel='投影分差的变化（logit）',title=f'{cid} 第{t}轮｜{ZH[y]} 相对 {ZH[rival]}：正值推高，负值压低\n这是同一轮内的模块读出变化，不是因果替换结果')
        fig.savefig(figures/f'{cid}_modules.png',dpi=160);plt.close(fig)
        lines=[f'### {cid}：数据标签为{ZH[y]}', '',f'末轮选择：**{names[m["final_prediction"]]}**；首次正确轮：{display(first)}；稳定正确轮：{display(stable)}；正确后又转错：{m["regressions"]}次。', '',
               f'![疾病曲线与逐层变化](../figures/{args.run_id}/{cid}.png)', '',
               '图①先看最终判断；图②再看哪个层转向；图③蓝色表示数据标签疾病领先；图④检查这些代码是否是该层输出头容易读出的内容。早层颜色不能直接当作已证实的内部诊断。', '',
               '| 轮次 | 本轮新增的原始记录 | 最终最支持的疾病 | 数据标签疾病的支持 |', '|---|---|---|---|']
        for t,r in enumerate(rs):
            g=byprefix[cid,t]['revealed_groups'][-1]
            evidence=evidence_zh(g).replace('|','/')
            lines.append(f'| {t} | {evidence} | {names[r["conditional_top_disease"]]} | {qs[t,y]:.6f} |')
        lines += ['',f'本病例数据标签疾病支持变化最大的是第{key["round"]}轮：{key["gold_change"]:+.6f}；最高支持从{names[key["previous_top"]]}转为{names[key["current_top"]]}。这是看完结果后选出的说明案例。',
                  f'逐层最高支持发生改变的层：{key["changed_readout_layers"]}。精确变化见机器可读事件表。', '',
                  f'![关键轮模块变化](../figures/{args.run_id}/{cid}_modules.png)', '']
        case_details.extend(lines)
        for a in arrays:a.close()
    table(metrics/'case_metrics.csv',all_metrics);table(metrics/'round_scores.csv',round_rows)
    dump(metrics/'case_metrics.json',all_metrics);dump(metrics/'evidence_updates.json',events)
    groups=collections.defaultdict(list)
    for r in records:groups[r['case_id'],r['round']].append(r)
    controls=[]
    for (cid,t),rr in sorted(groups.items()):
        if len(rr)!=6:continue
        rr.sort(key=lambda x:x['rotation']);qq=np.array([r['candidate_support'] for r in rr])
        controls.append({'case_id':cid,'round':t,'distinct_top_diseases':len(set(r['conditional_top_disease'] for r in rr)),
                         'top_diseases':[r['conditional_top_disease'] for r in rr],
                         'supports':qq.tolist(),'max_pair_total_variation':float(max(.5*np.abs(a-b).sum() for a in qq for b in qq))})
    assert len(controls)==9;dump(metrics/'mapping_controls.json',controls)
    changed=sum(c['distinct_top_diseases']>1 for c in controls)
    native=[r['native_check'] for r in records if r['native_check'] is not None];assert len(native)==9
    masses=np.array(layer_mass);table(metrics/'readout_mass_by_layer.csv',[{'layer':l+1,'median_mass':float(np.median(masses[:,l])),'min_mass':float(masses[:,l].min()),'max_mass':float(masses[:,l].max())} for l in range(28)])
    summary={'run_id':args.run_id,'cases':len(all_metrics),'primary_observations':len(primary),'all_observations':len(records),
             'initial_correct_cases':sum(m['initial_prediction']==m['gold'] for m in all_metrics),
             'final_correct_cases':sum(m['final_correct'] for m in all_metrics),
             'regression_cases':sum(m['regressions']>0 for m in all_metrics),
             'terminal_top_switch_events':sum(e['previous_top']!=e['current_top'] for e in events),
             'mapping_control_changed_points':changed,'mapping_control_points':len(controls),
             'strict_format_valid':sum(r['format_valid'] for r in primary),
             'native_checks':native,'max_native_abs_error':max(n['max_abs_error'] for n in native),
             'min_terminal_candidate_mass':min(r['candidate_mass'] for r in primary),
             'low_readout_mass_layers_median_below_1e_4':(np.flatnonzero(np.median(masses,axis=0)<1e-4)+1).tolist(),
             'weights_unchanged':completion['weights_unchanged'],'analysis_source_sha256':sha(__file__),'api_cost_usd':0}
    dump(metrics/'summary.json',summary)
    # Overview plots.
    fig,ax=plt.subplots(figsize=(13,4),constrained_layout=True)
    xx=np.arange(12);ax.bar(xx-.18,[m['initial_gold_support'] for m in all_metrics],.36,label='初始资料',color='#a6bccd');ax.bar(xx+.18,[m['final_gold_support'] for m in all_metrics],.36,label='全部资料',color='#477bb5')
    ax.set_xticks(xx,[ZH[diseases.index(m['gold'])]+'\n'+m['case_id'][-7:] for m in all_metrics],fontsize=9)
    ax.set(ylim=(0,1.05),ylabel='数据标签疾病的候选支持',title='同一个病人：更多证据是否把模型推向数据标签疾病？');ax.legend()
    fig.savefig(figures/'overview.png',dpi=170);fig.savefig(figures/'overview.pdf');plt.close(fig)
    fig,axs=plt.subplots(3,3,figsize=(13,10),constrained_layout=True)
    for ax,c in zip(axs.flat,controls):
        a=np.array(c['supports']);im=ax.imshow(a,aspect='auto',vmin=0,vmax=1,cmap='Blues')
        ax.set_xticks(range(6),ZH,rotation=45,ha='right',fontsize=8);ax.set_yticks(range(6),[f'映射{i}' for i in range(6)],fontsize=8)
        ax.set_title(f'{c["case_id"][-7:]} 第{c["round"]}轮｜出现{c["distinct_top_diseases"]}种首选',fontsize=10)
    fig.colorbar(im,ax=list(axs.flat),label='同一医学资料，不同选项映射下的疾病支持',shrink=.7)
    fig.savefig(figures/'mapping_controls.png',dpi=160);plt.close(fig)
    report=['# 1.7B 首轮实测：证据来了，模型各层怎样变', '',
            f'本轮已完成 **12例、131个证据时间点、28层** 的真实前向捕捉，另做45个换位观察点，共176点。模型是Qwen3-1.7B；运行于本机Apple M2 Pro GPU；API费用0美元。', '',
            '## 先说结果', '',
            f'在固定选项映射下，初始资料时选中数据标签疾病的有 **{summary["initial_correct_cases"]}/12例**，看到全部资料后有 **{summary["final_correct_cases"]}/12例**。相邻证据轮之间，最终首选疾病共切换 **{summary["terminal_top_switch_events"]}次**；**{summary["regression_cases"]}例**出现过先选对、随后又转错。', '',
            f'换位对照是本轮判断是否可信的关键：同一份医学资料，只换疾病对应的字母和列表位置，**{changed}/9个检查点**的首选疾病发生变化。'+('因此，当前单一映射轨迹混有选项呈现效应，不能把整条变化全部归因于医学证据。下一步先消除这一测量干扰，再解释疾病层面的机制。' if changed else '这9个点的首选疾病保持一致；概率变化仍需看下面的对照图。'), '',
            '我们确实测到了模型内部状态和逐层输出头分数随输入改变。这里的“支持”是六种候选内部的相对分数，不是患者患病的临床概率。是否形成了独立于答案编码、跨提示稳定的医学信念，下一阶段用对照进一步判断。', '',
            '## 一个具体病例怎么测', '',
            '例如57岁女性病例0857360，数据标签是肺炎。第0轮只有年龄、性别和深吸气加重的疼痛；后续逐组加入帕金森病史、COPD病史、咳嗽和痰等明确记录，直到第17轮看到全部已有记录。每轮重新输入累计资料，先前模型答案不带入。模型从未看到数据标签字段。', '',
            '六种固定候选是：肺炎、支气管炎、哮喘急性发作、肺栓塞、自发性气胸、急性肺水肿。每类2例。资料来自DDxPlus模拟病例；本轮没有添加或编造化验、影像。', '',
            '## 到底测了模型里面的什么', '',
            '每层保存五个向量：进入该层、注意力增量、注意力之后、MLP增量、离开该层。对进入层、注意力后、离开层的状态，使用同一个最终输出头，读取六种疾病的分数。每一层2048个数，所有28层都保存了，不是让模型口头描述自己怎么想。', '',
            '模型权重在整个实验中固定。发生变化的是输入引起的内部激活及其读出；本轮没有测量注意力分配矩阵，也没有用局部干预证明因果。', '',
            f'9个预定输入均通过正常模型与捕捉前向的一致性检查（atol=rtol=0.001；最大绝对差{summary["max_native_abs_error"]:.6f}，所有argmax一致；容差包含相对项）。131个主观察点均通过输入前缀检查、残差重建、分词边界及末层读出检查。', '',
            f'严格遵守“只输出一个字母并结束”的主观察点为{summary["strict_format_valid"]}/131；多输出解释或32词元内未结束的，保留原文并标为格式无效。下文诊断统计使用诊断位置的六类条件分数首选，不把格式无效偷偷补成有效回答。', '',
            f'早层中，候选总概率的中位数低于0.0001的层是{summary["low_readout_mass_layers_median_below_1e_4"]}。这些层的颜色尤其需要结合图④看；原始输出头并没有经过独立病例校准。', '',
            '## 全部病例结果', '',
            f'![全病例起点与终点](../figures/{args.run_id}/overview.png)', '',
            '| 病例ID | 数据标签 | 末轮首选 | 第一次正确 | 此后一直正确 | 正确后转错次数 |', '|---|---|---|---|---|---|']
    for m in all_metrics:report.append(f'| {m["case_id"]} | {names[m["gold"]]} | {names[m["final_prediction"]]} | {display(m["first_correct"])} | {display(m["stable_correct"])} | {m["regressions"]} |')
    # Concrete examples are selected after observing this pilot; save all examples' numbers.
    examples=[];story=['## 先用三个具体变化看懂模型内部', '',
        '以下是从本轮结果中挑出的说明案例，用来提出后续假设；它们还没有完成跨映射复核或因果干预。', '',
        '| 病例与新证据 | 表面上的变化 | 内部读到了什么 |', '|---|---|---|']
    fig,axs=plt.subplots(1,3,figsize=(16,4.8),constrained_layout=True)
    for ax,(cid,t) in zip(axs,[('ddx_train_0940128',1),('ddx_train_0902216',3),('ddx_train_0874944',8)]):
        rr=sorted((r for r in primary if r['case_id']==cid),key=lambda r:r['round']);before,after=rr[t-1],rr[t]
        y=diseases.index(private[cid]['gold_disease']);new=evidence_zh(byprefix[cid,t]['revealed_groups'][-1])
        with np.load(run/before['states_file']) as a,np.load(run/after['states_file']) as b:
            qa=a['stage_candidate_support'][:,-1].copy();qb=b['stage_candidate_support'][:,-1].copy()
        examples.append({'case_id':cid,'round':t,'new_evidence_zh':new,'gold':diseases[y],
                         'before_layer_support':qa.tolist(),'after_layer_support':qb.tolist()})
        for yy,label,color in [(qa[:,y],'证据到来之前','#9a9a9a'),(qb[:,y],'证据到来之后','#477bb5')]:
            ax.plot(np.arange(1,29),yy,label=label,color=color,lw=2)
        ax.set(xlim=(20,28.3),ylim=(-.03,1.03),xlabel='模型层（放大第20—28层）',ylabel=f'{names[diseases[y]]}的相对支持',
               title=f'{cid[-7:]} 第{t}轮\n{new}');ax.set_xticks(range(20,29));ax.grid(alpha=.2);ax.legend(fontsize=9)
        if cid=='ddx_train_0940128':
            description='第24—28层的首选都从哮喘转为肺栓塞；最终肺栓塞支持由约0.0007%升至98.64%。'
            assert all(win(qa)[23:]==2) and all(win(qb)[23:]==3)
        elif cid=='ddx_train_0902216':
            description='第26—28层的首选从肺炎转为肺水肿；最终肺炎支持由92.89%降到不足0.001%。'
            assert all(win(qa)[25:]==0) and all(win(qb)[25:]==5)
        else:
            description='新证据后第24—27层仍首选肺水肿，第28层却首选肺栓塞；最终肺水肿支持由75.41%降至29.40%。'
            assert all(win(qb)[23:27]==5) and win(qb)[27]==3
        story.append(f'| {cid}：{new} | {names[before["conditional_top_disease"]]} → {names[after["conditional_top_disease"]]} | {description} |')
    fig.savefig(figures/'three_examples.png',dpi=170);fig.savefig(figures/'three_examples.pdf');plt.close(fig)
    dump(metrics/'three_examples.json',examples)
    story += ['',f'![三次证据更新在后几层的变化](../figures/{args.run_id}/three_examples.png)', '',
              '**本轮给出的具体研究线索是：证据引起的疾病转向可能在后几层被加强，也可能在最后一层与前面几层的读出分开。** 下一步要确认这种分开在更换答案编码、校准读出后是否仍存在，再干预相应层检查原因。这比只统计最终答对多少更接近我们要研究的内部变化。', '']
    insert_at=report.index('## 一个具体病例怎么测');report[insert_at:insert_at]=story
    report += ['', '“正确”表示首选与数据最终标签一致；早期信息不全时，其他疾病仍可能合理。这12例是测量验证样本，不能把12例准确率当成总体医学能力。', '',
               '## 相同证据，换选项之后怎样', '',f'![换位对照](../figures/{args.run_id}/mapping_controls.png)', '',
               '每个小图是一份完全相同的医学资料；六行是六种选项映射，列按疾病名称对齐。如果深色列换了，说明答案呈现方式影响了最终疾病选择。这项对照同时改变字母映射和候选顺序，不能单独认定是字母偏好。', '',
               '## 每例逐轮结果和内部图', ''] + case_details
    report += ['## 下一阶段怎么继续', '',
               '1. 将六种映射扩到所有131个时间点，逐病例比较哪些证据转向跨映射一致；同时加入直接疾病名称评分，避免只靠答案代码。',
               '2. 先在独立病例上校准逐层读出，确认中间层的疾病信号能在留出病例上预测同轮模型判断，再谈“内部先转向”。',
               '3. 对稳定重现的证据转向做证据顺序、删除和等长替换对照，再定位哪些层真正造成最终选择改变。',
               '4. D测量可靠后加入思考前P、思考后R；不把本轮直接诊断包装为已经完成推理全过程。', '',
               '## 文件与复现', '',f'- 原始观察、完整末层logits、五处激活及版本：[runs/{args.run_id}](../runs/{args.run_id}/manifest.json)。',
               f'- [逐病例指标](../runs/{args.run_id}/metrics/case_metrics.csv)、[逐轮数值](../runs/{args.run_id}/metrics/round_scores.csv)、[逐条证据的变化](../runs/{args.run_id}/metrics/evidence_updates.json)。',
               f'- [执行程序](../src/run_direct.py)、[分析与matplotlib作图程序](../src/analyze.py)、[冻结协议](../protocol/PHASE1.md)。',
               '- 早期phase1_direct试跑因float32概率运算的舍入误差触发检查而中断，保留在原目录；正式v2使用等价的稳定完整词表softmax重新跑全部点，统计不混用试跑结果。', '']
    (ROOT/'reports/PHASE1_RESULTS.md').write_text('\n'.join(report))
    dump(metrics/'analysis_completion.json',{'complete':True,'figures_png':len(list(figures.glob('*.png'))),'figures_pdf':len(list(figures.glob('*.pdf'))),'source_sha256':sha(__file__),'report_sha256':sha(ROOT/'reports/PHASE1_RESULTS.md')})
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
