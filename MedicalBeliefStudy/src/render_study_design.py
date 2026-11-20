"""Publication-style design diagram; no invented experimental values."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from analyze_stages import ROOT,setup,savefig
def main():
    setup();dest=ROOT/'acl_paper/figures';dest.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(12,6));ax.set(xlim=(0,12),ylim=(0,6));ax.axis('off')
    def box(x,y,w,h,title,body,color):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.10',facecolor=color,edgecolor='#667085',linewidth=1))
        ax.text(x+w/2,y+h-.32,title,ha='center',va='center',fontsize=13,fontweight='bold');ax.text(x+w/2,y+h/2-.2,body,ha='center',va='center',fontsize=10,linespacing=1.6)
    def arrow(x,y,xx,yy,color='#475467'):ax.add_patch(FancyArrowPatch((x,y),(xx,yy),arrowstyle='-|>',mutation_scale=15,color=color,linewidth=1.5))
    box(.25,2.6,2.15,2.4,'同一患者逐条证据','年龄、性别\n逐条揭示症状、病史等\n每轮保留此前资料\n不放入前轮模型回答','#eff8ff')
    box(3.05,2.6,2.7,2.4,'冻结模型的内部计算','1.7B：28层\n4B 8-bit：36层\n记录attention与MLP前后状态\n模型参数不更新','#f0fdf4')
    box(6.45,3.75,2.3,1.25,'内部能读出什么？','其他患者训练线性读出器\n24病种分数与排名','#f5f3ff')
    box(6.45,1.95,2.3,1.25,'模型实际选什么？','49个完整病名序列评分\n另保留实际续写','#fff7ed')
    box(9.4,2.6,2.25,2.4,'把两条轨迹对应','逐渐增强还是突然转向\n内部与输出是否同步\n改变内部方向后\n诊断是否随之改变','#fff1f2')
    arrow(2.5,3.8,2.95,3.8);arrow(5.85,4.35,6.35,4.35);arrow(5.85,3.2,6.35,2.65);arrow(8.85,4.3,9.3,4.0);arrow(8.85,2.6,9.3,3.1)
    box(.25,.25,5.5,1.1,'输入对照','相同事实不同顺序 · 固定223问题 · 同字段Yes / No / Unknown','#f9fafb')
    box(6.45,.25,5.2,1.1,'因果与输出对照','第21/28层 · 目标/反向/随机方向 · 首词元/后续词元','#f9fafb')
    arrow(2.4,1.45,2.0,2.5);arrow(6.5,1.45,5.1,2.5,color='#c2410c')
    ax.text(6,5.65,'模型有医学信念吗？从证据、内部信息到诊断使用',ha='center',fontsize=17,fontweight='bold')
    fig.tight_layout();savefig(fig,dest/'study_design')
if __name__=='__main__':main()
