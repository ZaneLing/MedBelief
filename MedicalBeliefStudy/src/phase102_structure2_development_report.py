"""Report all attempted methods, including catastrophic development failures."""
import matplotlib.pyplot as plt
from structure2_analysis import *
from structure2_scoring import surface_choice
from analyze_stages import setup,savefig
def main():
    setup();spec=read(RUN/'confirmation_selection.json');rows=spec['development_rows'];out=ROOT/'results/47_structure_search';trainout=ROOT/'results/48_adapter_training'
    for d in [out,trainout]:(d/'figures').mkdir(parents=True,exist_ok=True)
    base=next(r['parameter_stats']['parameters'] for r in rows if r['configuration']['name']=='baseline');flat=[]
    for r in rows:
        n=r['configuration']['name'];flat.append(dict(candidate=n,parameters=r['parameter_stats']['parameters'],parameter_reduction=1-r['parameter_stats']['parameters']/base,neutral_accuracy=r['accuracy']['neutral'],wrong_accuracy=r['accuracy']['wrong'],neutral_listed=r['listed']['neutral'],wrong_listed=r['listed']['wrong']))
    for r in flat:
        n=r['candidate'];folder='structure_development' if (RUN/'structure_development'/n).exists() else 'adapter_development';count=collections.Counter()
        for c in cases():
            if c['cohort']!='development':continue
            for ob in read(RUN/folder/n/(c['case_id']+'.json'))['conditions']:count[ob['condition']]+=int(surface_choice(c,ob)==c['gold_index'])
        r.update(normalized_neutral_correct=count['neutral'],normalized_wrong_correct=count['wrong'])
    csvwrite(out/'development_results.csv',flat);write(out/'summary.json',dict(cases=80,attempts=len(rows),primary_candidate=spec['primary_candidate'],rows=rows,normalized_scoring_sensitivity=flat))
    fig,axs=plt.subplots(1,3,figsize=(16,10),layout='constrained',sharey=True);yy=np.arange(len(rows))
    for cond,col,off in [('neutral','#317f9e',-.15),('wrong','#bc534c',.15)]:
        for ax,key in zip(axs[:2],['accuracy','listed']):ax.barh(yy+off,[r[key][cond] for r in rows],height=.28,color=col,label='中性历史' if cond=='neutral' else '错误历史')
    axs[2].barh(yy,[100*(1-r['parameter_stats']['parameters']/base) for r in rows],color='#61a17e');axs[0].set(yticks=yy,yticklabels=[LABELS[r['configuration']['name']] for r in rows]);axs[0].invert_yaxis();axs[0].set(title='实际完整候选答对率',xlabel='80例开发集');axs[1].set(title='能否生成合法候选名称',xlabel='合法候选比例');axs[2].set(title='实际模型参数减少',xlabel='相对原模型 (%)')
    axs[0].legend();axs[1].legend();savefig(fig,out/'figures/development_matrix')
    lines=['# 结构与适配器：全部开发尝试\n\n80例开发集，MedQA/MedMCQA各40例；每例中性与错误历史，直接生成完整候选。下表用于选方案，不当作最终确认性能。全部22个配置保留，包括无法输出合法名称的失败配置。\n\n![开发矩阵](figures/development_matrix.png)\n\n| 方法 | 参数减少 | 中性答对/80 | 错误历史答对/80 | 中性合法/80 | 错误历史合法/80 |\n|---|---:|---:|---:|---:|---:|\n']
    for r in flat:lines.append(f'| {LABELS[r["candidate"]]} | {r["parameter_reduction"]*100:.2f}% | {round(r["neutral_accuracy"]*80)} | {round(r["wrong_accuracy"]*80)} | {round(r["neutral_listed"]*80)} | {round(r["wrong_listed"]*80)} |\n')
    lines.append('\n最终主候选按开发表现冻结为：**'+LABELS[spec['primary_candidate']]+'**。确认集固定方法、代码散列和全部选择记录见[冻结清单](../../runs/structural_v2/confirmation_selection.json)。\n\n削减整层、削减通道、加输出适配器、约束解码是不同操作；候选约束会直接保证格式，不把它的合法率改善当作模型已学会医学知识。所有指标都与生成的原文一起保存。\n')
    lines.append('\n后续源文本复核标记了5例开发病例；本表保留最初80例的实际选型记录，没有在确认运行后重选。来源质量敏感性见[审计](../../research_v6_adapters/SOURCE_AUDIT.md)。\n')
    lines.append('\n## 结果后统一写法的敏感性\n\n上表和方案选择使用原逐字评分。下表对22配置同样清理表面写法，要求唯一匹配原候选；不据此重选方案。[规则](../../research_v6_adapters/SCORING_AUDIT.md)。\n\n| 方法 | 规范化中性命中/80 | 规范化错误历史命中/80 |\n|---|---:|---:|\n')
    for r in flat:lines.append(f'| {LABELS[r["candidate"]]} | {r["normalized_neutral_correct"]} | {r["normalized_wrong_correct"]} |\n')
    (out/'RESULTS.md').write_text(''.join(lines));plan=read(RUN/'adapter_plan.json');training=[]
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for cfg in plan['adapters']:
        s=read(RUN/'adapters'/cfg['name']/'completion.json');training.append(s);ax=axs[1 if cfg['name']=='exit20_adapter16' else 0];ax.plot([r['step'] for r in s['history']],[r['development_loss'] for r in s['history']],'-o',label=LABELS[cfg['name']])
    for ax,title in zip(axs,['保留28层：训练未必改善开发损失','仅前20层：损失下降是否能恢复诊断']):ax.set(xlabel='训练更新次数',ylabel='开发集完整词表交叉熵（越低越好）',title=title);ax.legend(fontsize=8)
    savefig(fig,trainout/'figures/learning_curves');write(trainout/'summary.json',dict(adapters=training,bridge=read(RUN/'bridge/completion.json'),plan=plan))
    lines=['# 小适配器与尾部桥接训练\n\n400例训练，80例开发选择检查点；未使用400例确认病例。冻结原模型，只训练小模块；所有原模型文件保持不变。完整词表151936维交叉熵，真实来源候选及JSON结束符/EOS作为目标。每个序列总权重相同，首个候选词元占一半，后续词元共享另一半。\n\n![训练曲线](figures/learning_curves.png)\n\n| 方法 | 训练参数 | 所选更新步 | 初始开发损失 | 最佳开发损失 |\n|---|---:|---:|---:|---:|\n']
    for s in training:lines.append(f'| {LABELS[s["configuration"]["name"]]} | {s["trainable_parameters"]:,} | {s["best_step"]} | {s["initial_development_loss"]:.3f} | {s["best_development_loss"]:.3f} |\n')
    reverted=[LABELS[s['configuration']['name']] for s in training if s['best_step']==0]
    if reverted:lines.append('\n**没有得到有效训练收益、最终退回零初始化的配置：'+ '、'.join(reverted)+'。** 这些名称虽然含“适配器”，实际所选小模块的输出改变量为零；不能将它们与原骨干的相同结果称为适配器修复成功。\n')
    bridge=read(RUN/'bridge/completion.json');lines.append(f'\n秩64桥接用{bridge["parameters"]:,}个参数替代8个尾层，拟合第20层到第28层的教师状态。开发加权MSE由直接使用第20层的{bridge["development"]["identity_mse"]:.4f}降至{bridge["development"]["weighted_mse"]:.4f}；状态接近不自动等于诊断正确，需看实际生成。\n\n适配器直接学习来源答案，因此其改善可能包含新增的医学对应关系。不能将所有修复解释为原模型本来就会。桥接不采用额外疾病分类损失，但教师强制前缀仍使用来源答案。\n')
    lines.append('\n后续源文本复核标记训练9例、开发5例；本轮保留原训练和选型，不把它们称为重新清洁后训练的模型。[来源复核](../../research_v6_adapters/SOURCE_AUDIT.md)。\n')
    (trainout/'RESULTS.md').write_text(''.join(lines));print(json.dumps(dict(complete=True,methods=len(rows),train_cases=400,development_cases=80)))
if __name__=='__main__':main()
