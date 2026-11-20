"""Static method diagram, generated with the same scientific plotting setup."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from analyze_stages import setup,savefig

def main():
    setup();out=Path(__file__).resolve().parents[1]/'research_v5_structural/figures';out.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(14,6));ax.set(xlim=(0,14),ylim=(0,6));ax.axis('off')
    def box(x,y,w,h,txt,color='#e9f2f5',fs=11):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06',facecolor=color,edgecolor='#52656b',linewidth=1.1));ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=fs)
    def arrow(x1,y1,x2,y2):ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=13,color='#52656b',linewidth=1.3))
    box(.2,4.4,2.3,1.1,'同一病例\n累计事实＋固定历史');box(3.1,4.4,3.2,1.1,'28层：注意力 → MLP\n每一层都留下当前状态');box(6.9,4.4,3.2,1.1,'最终归一化＋输出头\n四候选支持 / 生成诊断');box(10.7,4.4,3.1,1.1,'两个检查\n与原模型一致？来源答案对？')
    for x1,x2 in [(2.5,3.1),(6.3,6.9),(10.1,10.7)]:arrow(x1,4.95,x2,4.95)
    box(.2,2.1,3.5,1.3,'观察\n每轮 × 每层的候选投影\n每个头读历史、事实的比例','#edf1f7');box(4.2,2.1,4.0,1.3,'干预\n逐层删注意力 / MLP / 整层\n逐头移除最后输入位置的贡献','#fbefdf');box(8.8,2.1,5,1.3,'真实结构替换\nMLP：约3775万参数 → 约7万参数\n2048 → 16 → 2048，后续层继续运行','#e6f2e9')
    arrow(4.7,4.35,2,3.45);arrow(4.7,4.35,6.2,3.45);arrow(8.25,2.75,8.75,2.75)
    box(2.1,.2,9.8,1.15,'最后答得一样 ≠ 每一步都一样\n345例检查终点；47例逐条加入事实，比较改结构前后的整条诊断路径','#f1edf5',12)
    arrow(6.2,2.05,6.2,1.4);ax.text(7,5.9,'测量 → 改动 → 重新运行 → 比较诊断',ha='center',va='center',fontsize=16)
    savefig(fig,out/'measurement_map');fig.savefig(out/'measurement_map.svg',bbox_inches='tight')

if __name__=='__main__':main()
