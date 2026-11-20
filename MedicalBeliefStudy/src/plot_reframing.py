"""Render a research design diagram; does not run or simulate experiments."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from analyze_stages import setup, savefig


def main():
    setup()
    dest = Path(__file__).resolve().parents[1] / 'acl_paper/v07_reframing/figures'
    dest.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 9))
    fig.subplots_adjust(left=.025, right=.98, top=.98, bottom=.025)
    ax.set(xlim=(0, 14), ylim=(0, 9))
    ax.axis('off')
    ink, muted = '#172c3d', '#536877'
    ax.text(.35, 8.65, '模型有医学信念吗？', fontsize=26, weight='bold', color=ink)
    ax.text(.35, 8.13, '先前诊断改变的是最后的答案，还是模型处理新证据的方式？',
            fontsize=19, color=ink)
    ax.add_patch(FancyBboxPatch((.35, 7.31), 13.1, .53,
        boxstyle='round,pad=0.08', facecolor='#eaf0f4', edgecolor='none'))
    ax.text(6.9, 7.57, '相同患者 · 相同当前事实 · 相同诊断候选 · 比较不同先前诊断',
            ha='center', va='center', fontsize=16, color=ink)
    x0, width, gap = 2.9, 3.38, .19
    colors = ['#e7eef8', '#fff0d9', '#e0f1e9']
    edge = ['#4778a9', '#bd812b', '#39876a']
    headings = ['解释一｜知识不足', '解释二｜证据作用被改变', '解释三｜输出被带走']
    rows = [
        ('4 适用范围', ['哪些证据受知识限制？', '哪些先前诊断容易带偏？', '哪些输出方式更易受影响？']),
        ('3 因果区分', ['补充相关知识\n是否更有帮助？', '替换新证据处理状态\n能否解除影响？', '替换输出位置状态\n能否修复答案？']),
        ('2 内部定位', ['事实内容有没有保留？\n疾病信息能否可靠读出？', '同一条新证据\n在内部怎样变化？', '内部信息与最终选择\n从哪里开始分开？']),
        ('1 表面现象', ['没有旧诊断\n也处理不好', '旧诊断不同\n同一新证据作用不同', '内部读出与答案\n出现不同步'])
    ]
    for j in range(3):
        x = x0 + j*(width+gap)
        ax.add_patch(Rectangle((x, 6.45), width, .57, facecolor=edge[j], edgecolor='none'))
        ax.text(x+width/2, 6.735, headings[j], ha='center', va='center', fontsize=16, color='white')
    for i, (label, cells) in enumerate(rows):
        y = 5.24 - i*1.22
        ax.text(.55, y+.54, label, fontsize=18, color=ink, va='center', weight='bold')
        for j in range(3):
            x = x0 + j*(width+gap)
            ax.add_patch(Rectangle((x, y), width, 1.08, facecolor=colors[j], edgecolor='white'))
            ax.text(x+width/2, y+.54, cells[j], ha='center', va='center',
                    fontsize=15, linespacing=1.65, color=ink)
    ax.annotate('', xy=(.3, 6.32), xytext=(.3, 1.62),
                arrowprops={'arrowstyle': '->', 'color': muted, 'lw': 1.8})
    ax.text(.55, 1.0, '宽度：不同疾病、证据类型、病例来源和模型，都使用同一套比较。',
            fontsize=16, color=ink)
    ax.text(.55, .45, '研究设计图：三列是待区分的解释，四层是证据深度；不是已证实的机制分类。',
            fontsize=13, color=muted)
    savefig(fig, dest/'research_architecture')
    print(dest/'research_architecture.png')


if __name__ == '__main__':
    main()
