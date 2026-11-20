"""Publication-style descriptive figures; no inferential population claims."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[1] / 'results/23_ddx_generator_audit'
s = json.loads((OUT / 'summary.json').read_text())
n = json.loads((OUT / 'native_challenge_summary.json').read_text())
f = json.loads((OUT / 'followup.json').read_text())
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'pdf.fonttype': 42})
fig, axes = plt.subplots(1, 3, figsize=(16, 5.7))
colors = ['#176b80', '#42a5a1', '#efb95e', '#bfc8d3', '#e0e5eb']
labels = ['1 clue', '2 clues', '3 clues', '>3 clues', 'Ambiguous']
for i, split in enumerate(['test', 'validation']):
    d = s[split]; hist = d['certificate_count_histogram']; total = d['counts']['cases']
    vals = [100 * hist.get(k, 0) / total for k in ['1', '2', '3', 'None', 'ambiguous']]
    left = 0
    for value, color, label in zip(vals, colors, labels):
        axes[0].barh(i, value, left=left, color=color, label=label if i == 0 else None)
        if value > 6:
            axes[0].text(left + value / 2, i, f'{value:.1f}%', ha='center', va='center',
                         color='white' if label in labels[:2] else '#263442', fontsize=9)
        left += value
axes[0].set(yticks=[0, 1], yticklabels=['Test\nn = 134,529', 'Validation\nn = 132,448'],
            xlim=(0, 100), xlabel='Share of all cases (%)',
            title='A. Minimal catalog certificates')
axes[0].invert_yaxis()
axes[0].legend(loc='upper center', bbox_to_anchor=(.5, -.16), ncol=2, frameon=False, fontsize=9)
axes[0].text(.0, 1.03, 'No patient training; use published catalog', transform=axes[0].transAxes, fontsize=9)

x = np.arange(2); width = .34
for offset, key, label, color in [(-width/2, 'logistic_evidence_presence', 'Question identities', colors[0]),
                                 (width/2, 'logistic_evidence_values', '+ Answer values', colors[2])]:
    vals = [100*n['challenge'][sp]['models'][key]['accuracy'] for sp in ['test', 'validate']]
    bars = axes[1].bar(x + offset, vals, width, label=label, color=color)
    axes[1].bar_label(bars, fmt='%.2f', padding=3, fontsize=9)
for i, sp in enumerate(['test', 'validate']):
    upper = 100*n['challenge'][sp]['conditional_question_only_upper_bound']
    axes[1].plot([i-.44, i+.44], [upper, upper], '--', color='#596575', linewidth=1)
axes[1].set(xticks=x, xticklabels=['Test\nn = 685', 'Validation\nn = 688'], ylim=(0, 100),
            ylabel='Accuracy (%)', title='B. Same-question native challenge')
axes[1].legend(loc='upper center', bbox_to_anchor=(.5, -.16), frameon=False, fontsize=9)
axes[1].text(0, 1.03, 'Frozen models; balanced within question groups', transform=axes[1].transAxes, fontsize=9)

vals = [100*s[sp]['reference_outside_support_mass']['mean'] for sp in ['test', 'validation']]
bars = axes[2].bar(x, vals, .55, color=['#b66767', '#bd8181'])
axes[2].bar_label(bars, fmt='%.2f', padding=3)
axes[2].set(xticks=x, xticklabels=['Test', 'Validation'], ylim=(0, 100),
            ylabel='Mean reference score mass (%)', title='C. Reference mass outside support')
axes[2].text(0, 1.03, 'Two different targets; not a clinical error rate', transform=axes[2].transAxes, fontsize=9)
fig.suptitle('DDXPlus: catalog identifiability and answer-dependent evaluation', fontsize=16, y=.99)
fig.text(.5, .02, 'Certificates are selected retrospectively from observed findings. Challenge cohorts are conditional, not representative of prevalence.',
         ha='center', fontsize=10, color='#465364')
for ax in axes:
    ax.set_title(ax.get_title(), loc='center', y=1.13, fontsize=11)
fig.subplots_adjust(left=.075, right=.985, top=.78, bottom=.26, wspace=.42)
fig.savefig(OUT / 'generator_audit.png', dpi=180)
fig.savefig(OUT / 'generator_audit.pdf')
