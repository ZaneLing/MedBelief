"""Generate exact numerical inclusions and bibliography for the v0.6 manuscript."""
import re,shutil,csv
from belief_v3_analysis import *
def n(z):return f"{round(z['mean']*z['cases'])}/{z['cases']}"
def ci(z):return f"{z['mean']:.3f} [{z['low']:.3f}, {z['high']:.3f}]"
def pct(z):return f"{100*z['mean']:.1f} points (95\\% CI [{100*z['low']:.1f},{100*z['high']:.1f}])"
def pval(p):return '$<0.0001$' if p<.0001 else f'{p:.4f}'
def main():
 d=ROOT/'acl_paper/v06_building';s=read(ROOT/'results/23_new_patients/summary.json');b=read(ROOT/'results/28_new_4b_replication/summary.json');a=read(ROOT/'results/24_natural_update_causality/summary.json');r=read(ROOT/'results/24_natural_update_causality/replication/summary.json');h=read(ROOT/'results/25_history_and_evidence/summary.json');x=read(ROOT/'results/29_external_internal_causality/summary.json');role=read(ROOT/'results/30_role_binding/summary.json');e=read(ROOT/'results/26_external_medqa/summary.json');z=read(ROOT/'results/27_building_synthesis/synthesis.json')
 for f in ['acl.sty','acl_natbib.bst']:shutil.copy2(ROOT/'acl_paper/submission'/f,d/f)
 rep=z['replicated_natural_layers'];ca='Disease-component removal has a replicated, direction-specific native-score effect at layer'+('s ' if len(rep)>1 else ' ')+', '.join(rep)+'.' if rep else 'The disease-component effect does not meet the same-layer replication criterion in both cohorts.'
 xs=z['external_natural_layers'];ext='Old-state replacement produces Holm-significant positive attenuation relative to random displacement at layer'+('s ' if len(xs)>1 else ' ')+', '.join(xs)+'.' if xs else 'No layer shows Holm-significant positive attenuation relative to random displacement.'
 ct=h['context'];context=f"Of {ct['eligible']} eligible non-negligible updates, {ct['opposite_events']} have opposite directions; the patient-mean fraction is {100*ct['opposite_rate']['mean']:.1f}\\% (95\\% CI [{100*ct['opposite_rate']['low']:.1f},{100*ct['opposite_rate']['high']:.1f}])."
 (d/'numbers.tex').write_text('\\newcommand{\\CausalAbstract}{'+ca+'}\n\\newcommand{\\ExternalCausalResult}{'+ext+'}\n\\newcommand{\\ContextResult}{'+context+'}\n')
 t=['\\begin{tabular}{lrrr}\\toprule','Configuration & Native 49 & Native 24 & Readout\\\\\\midrule']
 for label,v,L in [('1.7B sequential',s['endpoints']['append'],28),('1.7B panel',s['endpoints']['panel'],28),('4B sequential',b['endpoints']['append'],36)]:t.append(f'{label} & {n(v["native49"])} & {n(v["native24"])} & {n(v["layers"][str(L)])}\\\\')
 t.append('\\bottomrule\\end{tabular}');(d/'endpoint_table.tex').write_text('\n'.join(t))
 t=['\\begin{tabular}{lrrrr}\\toprule','Layer & First 24: effect [95\\% CI] & Holm $p$ & Independent 48: effect [95\\% CI] & Holm $p$\\\\\\midrule']
 for L in ['14','21','28']:t.append(f'{L} & {ci(a["layers"][L]["target_minus_random"])} & {pval(a["layers"][L]["p_holm"])} & {ci(r["layers"][L]["target_minus_random"])} & {pval(r["layers"][L]["p_holm"])}\\\\')
 t.append('\\bottomrule\\end{tabular}');(d/'causal_table.tex').write_text('\n'.join(t))
 t=ca+' Table~\\ref{tab:causal} reports all three predetermined layers in both cohorts. '
 t+=f"At layer 28, target removal changes the top-49 diagnosis in {a['layers']['28']['conditions']['remove_target']['top_changes']}/24 initial and {r['layers']['28']['conditions']['remove_target']['top_changes']}/48 replication patients. Equal-norm random changes do so in {a['layers']['28']['conditions']['random_matched']['top_changes']}/24 and {r['layers']['28']['conditions']['random_matched']['top_changes']}/48. All zero controls reproduce their corresponding baselines (maximum log-score errors {a['sham_max_logp_error']:.6f} and {r['sham_max_logp_error']:.6f}). Score attenuation is therefore evaluated separately from diagnostic boundary crossing."
 (d/'causal_text.tex').write_text(t+'\n')
 t=[]
 for stage,label in [('middle','middle prefix'),('final','full case')]:
  hh=h['history'][stage];t.append(f"At the {label}, correct versus wrong history yields {n(hh['gold_history_matches_gold'])} versus {n(hh['wrong_history_matches_gold'])} source-label matches. Native top choices change in {n(hh['native_matched_top_change'])} pairs, while the last-layer 24-class readout top changes in {n(hh['probe_matched_top_change'])}. The two switch rates have different candidate ranges and are reported separately.")
 t.append('The full-case minus middle-prefix change in the matched wrong-versus-source native-margin gain is '+ci(h['history']['final_minus_middle_gain'])+'; positive values indicate stronger relative historical influence with the additional facts.')
 t.append('At the full case, wrong history worsens the source disease\'s final-layer readout rank by '+ci(h['history']['final']['gold_rank_change_last'])+' positions on average. Thus the history effect reaches decodable internal information, although the readout may partly encode the inserted disease name rather than a calibrated diagnostic belief. Both histories explicitly state that the preceding assessment may be wrong and request reassessment using only current findings.')
 (d/'history_text.tex').write_text(' '.join(t)+'\n')
 (d/'context_text.tex').write_text(f"Across 72 DDxPlus patients, reversing subsequent evidence groups changes {n(h['order']['reverse']['switched'])} endpoint top choices, and deterministic shuffling changes {n(h['order']['shuffle']['switched'])}. Repeating the middle evidence group changes {n(h['evidence_controls']['repeat_middle']['switched'])} choices in the 24-patient mechanism subset. Repetition adds no new fact, but changes emphasis and position.\n")
 bb=b['endpoints']['append'];(d/'scale_text.tex').write_text(f"The 4B configuration identifies {n(bb['native49'])} source labels among 49 diseases, a paired gain of {pct(b['paired_4b_minus_1p7b_native49'])} over 1.7B. In the matched 24-disease comparison, native scoring identifies {n(bb['native24'])} while its final-layer readout identifies {n(bb['layers']['36'])}, a gap of {pct(bb['probe_minus_native24'])}. Final-layer natural-update correlation is {ci(b['deep']['update_alignment_last'])}. The paired 4B-minus-1.7B native switch-rate difference is {ci(b['paired_trajectory_4b_minus_1p7b']['switch_rate'])}; the interval includes zero.\n")
 rc=role['conditions'];gain=rc['correct']['paired_change_vs_neutral']['native49_hit'];t=f"Correct, unspecified, and swapped roles yield {n(rc['correct']['native49_hit'])}, {n(rc['neutral']['native49_hit'])}, and {n(rc['swapped']['native49_hit'])} native source-label matches. The paired correct-minus-unspecified change is {pct(gain)}. "
 t+=('Correct role labeling improves aggregate native accuracy.' if gain['low']>0 else ('Correct role labeling lowers aggregate native accuracy.' if gain['high']<0 else 'Correct role labeling does not yield a clear aggregate accuracy improvement.'))
 t+=f" Final-layer readout matches in the same three conditions are {n(rc['correct']['probe28_hit'])}, {n(rc['neutral']['probe28_hit'])}, and {n(rc['swapped']['probe28_hit'])}."
 (d/'role_text.tex').write_text(t+'\n')
 fam=list(csv.DictReader((ROOT/'results/23_new_patients/family_endpoints.csv').open()));t=['\\begin{table}[H]\\centering\\small','\\begin{tabular}{lrrr}\\toprule','Group & $N$ & Native 24 & Readout 28\\\\\\midrule']
 for row in fam:
  if row['view']=='append':t.append(f"{row['family'].capitalize()} & {row['patients']} & {row['native24_correct']} & {row['probe_last_correct']}\\\\")
 t+=['\\bottomrule\\end{tabular}','\\caption{New-patient endpoint counts by research disease group, 1.7B sequential input.}\\end{table}'];(d/'groups_table.tex').write_text('\n'.join(t))
 names=['Always source','Reach and retain','Leave and return','Leave at end','Always another','Switch among others'];t=['\\begin{table}[H]\\centering\\small','\\begin{tabular}{lrr}\\toprule','Trajectory & DDxPlus & MedQA\\\\\\midrule']
 for key,label in zip(PATTERNS,names):t.append(f"{label} & {s['deep']['patterns'].get(key,0)} & {e['patterns'].get(key,0)}\\\\")
 t+=['\\bottomrule\\end{tabular}','\\caption{All 72 DDxPlus and 87 MedQA trajectories. Source refers to the final source label, not a ground-truth intermediate posterior.}\\end{table}'];(d/'patterns_table.tex').write_text('\n'.join(t))
 bib=(ROOT/'acl_paper/submission/references.bib').read_text();bib=re.sub(r'@article\{marinescu2025,.*?(?=\n@)', '',bib,flags=re.S)
 bib+='''
@inproceedings{medicalmaps,
 author={Marinescu, Razvan and Gruber, Victoria-Elisabeth and Fajardo Vargas, Diego},
 title={Medical Interpretability and Knowledge Maps of Large Language Models},
 booktitle={International Conference on Learning Representations},year={2026},
 url={https://proceedings.iclr.cc/paper_files/paper/2026/hash/17aa70697d6cd35835f201c6fb0a2fd5-Abstract-Conference.html}}
@article{medqa,
 author={Jin, Di and Pan, Eileen and Oufattole, Nassim and Weng, Wei-Hung and Fang, Hanyi and Szolovits, Peter},
 title={What Disease Does This Patient Have? A Large-Scale Open Domain Question Answering Dataset from Medical Exams},
 journal={arXiv preprint arXiv:2009.13081},year={2020},url={https://arxiv.org/abs/2009.13081}}
@inproceedings{medstress,
 author={Xiao, Boyu and Tian, Xiuqi and Song, Xuwen and Wang, Haochun and Song, Guanchun and Zhao, Sendong and Qin, Bing},
 title={When Correct Beliefs Collapse: Epistemic Resilience of {LLMs} under Clinical Pressure},
 booktitle={Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
 year={2026},pages={8720--8764},doi={10.18653/v1/2026.acl-long.395},url={https://aclanthology.org/2026.acl-long.395/}}
@inproceedings{medeinst,
 author={Chen, Wenting and Huang, Guolin and Wang, Wenxuan and Zhu, Zhongrui},
 title={{MedEinst}: Benchmarking the Einstellung Effect in Medical {LLMs} through Counterfactual Differential Diagnosis},
 booktitle={Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
 year={2026},pages={39778--39798},url={https://aclanthology.org/2026.acl-long.1847/}}
@article{medevm,
 author={Feng, Kehua and Lu, Yunsheng and Qiao, Yitong and He, Tiantian and Liu, Lei and Shen, Yue and Wang, Jian and Gu, Jinjie},
 title={Can {LLMs} Value the Right Evidence? Evidence-Value Misalignment in Dynamic Medical Diagnosis},
 journal={arXiv preprint arXiv:2609.35627},year={2026},url={https://arxiv.org/abs/2609.35627}}
@article{beliefgeometry,
 author={Balcells, Daniel and Lee, Andrew Jun and Rastogi, Chirag and Riechers, Paul M. and Shai, Adam and Poncini, Xavier},
 title={Large Language Models Develop Belief State Geometry In-Context},
 journal={arXiv preprint arXiv:2609.17376},year={2026},note={Version 2; accepted at NeurIPS 2026},url={https://arxiv.org/abs/2609.17376}}
@article{minpair,
 author={Yu, Zhengqiu and Ding, Yueping and Liu, Xiangrong},
 title={Probing conflict resolution between contextual and parametric knowledge in medical language models},
 journal={Expert Systems with Applications},volume={332},pages={133720},year={2027},
 note={Available online 2026; issue year 2027},doi={10.1016/j.eswa.2026.133720},url={https://www.sciencedirect.com/science/article/pii/S095741742602628X}}
'''
 (d/'references.bib').write_text(bib)
 (d/'README.md').write_text('''# 医学信念论文 v0.6

先读[PAPER_ZH.md](PAPER_ZH.md)。它从一个病例开始，依次解释群体路径、内部疾病信息、自然更新、历史与证据背景、局部因果、跨来源与配置复核。

英文稿：[main.tex](main.tex)；编译后为[main.pdf](main.pdf)。当前为完整工作稿，不以页数或排版替代投稿前的作者核查。旧v0.5保留，数字不混用。

统计与图来自src/phase33_paper.py和phase34_manuscript.py，依赖各阶段已完成summary.json和最终validation.json。使用本地.tools/tectonic在本目录编译main.tex。所有图有PNG与PDF版本。

全部病例与分阶段结果见[完整结果](../../research_v3/RESULTS_AND_STORY.md)。
''')
 print('Generated exact v0.6 numerical inclusions and bibliography.',flush=True)
if __name__=='__main__':main()
