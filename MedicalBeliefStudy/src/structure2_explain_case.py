"""A post-result illustration; population conclusions remain the400-case analysis."""
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from structure2_analysis import *
from structure2_scoring import surface_choice
from analyze_stages import setup,savefig

def main():
    setup();cid='medqa_train_04812';c=next(c for c in cases() if c['case_id']==cid);names=['baseline','pruned_adapter16'];names_zh=['完整模型','局部缩窄模型'];obs={n:[r for r in read(RUN/'trajectories'/(cid+'_'+n+'.json'))['conditions'] if r['condition']=='wrong'] for n in names};T=len(c['sentences']);gold=c['gold_index'];q={n:np.array([r['q_sequence'][gold] for r in obs[n]]) for n in names};colors=['#aaaaaa','#d38837','#bc534c','#317f9e'];zh=['正常老化','阿尔茨海默病痴呆','路易体痴呆','血管性痴呆']
    with np.load(RUN/'trajectories'/(cid+'_baseline.npz')) as a,np.load(RUN/'trajectories'/(cid+'_pruned_adapter16.npz')) as b:
        distance=[]
        for t in range(1,T+1):
            x=a[f'wrong_t{t}_layers'].astype(float);y=b[f'wrong_t{t}_layers'].astype(float);distance.append(np.clip(1-np.sum(x*y,axis=1)/(np.linalg.norm(x,axis=1)*np.linalg.norm(y,axis=1)),0,2))
        distance=np.stack(distance,axis=1);max_first16=max(float(np.max(np.abs(a[f'wrong_t{t}_layers'][:16]-b[f'wrong_t{t}_layers'][:16]))) for t in range(1,T+1))
    fig,axs=plt.subplots(3,1,figsize=(12,10),gridspec_kw={'height_ratios':[2,1,2]},layout='constrained')
    for n,label,color in zip(names,names_zh,['#bc534c','#317f9e']):axs[0].plot(range(1,T+1),q[n]*100,'-o',label=label,color=color)
    axs[0].set(xticks=range(1,T+1),ylim=(-3,103),ylabel='最终来源答案的候选相对支持 (%)',title='同一病例、同一错误旧诊断：是否会重新回到血管性痴呆？');axs[0].legend();axs[0].axvline(9,color='gray',ls=':',alpha=.7)
    mat=np.array([[surface_choice(c,r) for r in obs[n]] for n in names]);axs[1].imshow(mat,aspect='auto',cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(-.5,4),4));axs[1].set(yticks=[0,1],yticklabels=names_zh,xticks=range(T),xticklabels=range(1,T+1),title='实际生成的候选身份：血管 / 路易 / 阿尔茨海默')
    for i in range(2):
        for j in range(T):axs[1].text(j,i,['正常','阿尔茨','路易','血管'][mat[i,j]],ha='center',va='center',color='white',fontsize=10)
    im=axs[2].imshow(distance,origin='lower',aspect='auto',cmap='viridis',vmin=0);axs[2].axhline(15.5,color='white',ls='--');axs[2].set(xticks=range(T),xticklabels=range(1,T+1),yticks=[0,7,15,16,23,27],yticklabels=[1,8,16,17,24,28],xlabel='累计证据轮次',ylabel='模型层号',title='局部缩窄后，每层状态相对完整模型改变多少');fig.colorbar(im,ax=axs[2],label='余弦距离；不是疾病概率')
    figdir=ROOT/'results/50_structure_trajectories/figures';savefig(fig,figdir/'vascular_case_explained')
    facts=['66岁男性，因行为改变由女儿送诊。','昨天比平时更困惑，反复问同样的问题。','这些症状持续24小时没有改善。','去年一系列跌倒后，生活自理能力下降。','之后不能自己做饭或缴费，其余情况直到这次发作前相对稳定。','既往有心肌梗死、高血压、糖尿病等疾病。','提供包括降压药、降糖药在内的当前用药。','查体时困惑，个人照料较差。','腿上有淤青，步态不稳。','对人物、地点有定向力，但部分回答不恰当。','脉搏90次/分，血压170/100 mmHg。']
    lines=['# 用一个病例看清：结构改变了哪一步\n\n原题最终答案是**血管性痴呆**。给两个模型的全部事实完全相同，额外放入同一个错误旧诊断：**路易体痴呆**。比较完整模型与后12层MLP通道减半的模型；后者所选适配器为零增量，因此这个例子测到的是结构变化。两者都使用普通自由生成，避免把输出约束造成的差异混进来。\n\n这个例子在结果后选作解释，属于预先固定24例图谱的一员，不代表总体效果。\n\n![病例解释](../results/50_structure_trajectories/figures/vascular_case_explained.png)\n\n## 先看它说出了什么\n\n完整模型在第6轮已经选中最终来源答案，第9轮因加入“腿上淤青、步态不稳”又回到路易体痴呆，最终停在那里。压缩模型第9轮也偏回去，但第10轮重新回到血管性痴呆，并保持到最后。\n\n所以，这个病例并不是原模型从未生成过正确诊断。它曾经到达正确候选，后来又离开；改变部分计算，使它后面的轨迹不同。单个病例不能证明被裁掉的模块普遍有害，400例仍会同时出现修复和损坏。\n\n## 每条事实到来后的实际记录\n\n候选支持是四个完整名称的相对模型分数，不是患者真实患病概率。两个模型此处使用相同评分公式。\n\n| 轮次 | 新增来源事实的中文摘要 | 完整模型实际名称 | 压缩模型实际名称 | 完整模型对血管性痴呆的支持 | 压缩模型的支持 |\n|---|---|---|---|---:|---:|\n']
    for i in range(T):lines.append(f'| {i+1} | {facts[i]} | {zh[surface_choice(c,obs[names[0]][i])]} | {zh[surface_choice(c,obs[names[1]][i])]} | {100*q[names[0]][i]:.2f}% | {100*q[names[1]][i]:.2f}% |\n')
    lines.append(f'\n## 模型里面测到了什么\n\n每次读完当前累计证据，我们取出每层作答位置的2048维向量。前16层没有改动，两个模型这些位置的状态最大绝对差为{max_first16:.6g}；从第17层开始出现差异，因为裁剪从这里开始。最后一轮，第28层两模型状态的余弦距离为{distance[27,-1]:.5f}；最终候选支持则从完整模型的{100*q[names[0]][-1]:.2f}%变为压缩模型的{100*q[names[1]][-1]:.2f}%。\n\n这说明结构改动确实改变了后半段内部状态，也改变了最终候选选择。热图本身只显示变化幅度，不能把黄色直接叫作“更相信血管性痴呆”。还没有从这个例子单独定位出一个专门负责该病的层或神经元。\n\n[完整英文原文、四候选与两种历史](../results/50_structure_trajectories/cases/'+cid+'.md) · [全部24例汇总](../results/50_structure_trajectories/RESULTS.md) · [独立400例表现](../results/49_structure_confirmation/RESULTS.md)。\n')
    (DOC/'ONE_CASE_EXPLAINED.md').write_text(''.join(lines));print(json.dumps(dict(complete=True,case=cid,all_first16_identical=max_first16==0)))
if __name__=='__main__':main()
