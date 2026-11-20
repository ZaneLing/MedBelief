# 本轮新增数据

本轮实际运行540例：MedQA 300、MedMCQA 200、MMLU 40。它们是公开考试诊断题中的原文病例，不是模型自行编造的患者。已有DDxPlus数据和此前实验保留，本轮不把那些病例再次计成新增。

| 来源 | 下载范围 | 本轮病例 | 开发 / 确认 | 完整内部轨迹 |
|---|---|---:|---:|---:|
| [MedQA](https://github.com/jind11/MedQA) | 英文四选项train/dev；从公开镜像获取并记录哈希 | 300 | 100 / 200 | 32 |
| [MedMCQA](https://github.com/medmcqa/medmcqa) | train/validation；使用单选诊断题 | 200 | 67 / 133 | 32 |
| [MMLU](https://github.com/hendrycks/test) | 下载四个医学子科目的可用split；严格诊断筛选后仅professional_medicine入选 | 40 | 14 / 26 | 30 |
| 合计 | 三个考试来源 | **540** | **181 / 359** | **94** |

MedMCQA原始train/validation分别有182822/4183行；manifest的123581为单选过滤后的行数，不是整个数据集规模。MMLU的40例不是40个新增真实患者，也不代表四个医学科目均有入选。

## 每个病例有什么

- 原始标识、来源split和行号。
- 原文分组、诊断提问、四个原始选项、原始答案。
- 预先固定的错误候选、代码映射、开发/确认分组及内部子集标记。
- 最终题目答案可以检查诊断是否正确；中间少量证据没有另行指定唯一答案。

每例2–16组，完整内部子集共537个累计前缀。实验保留原文组，不将其宣称为537次真实临床检查。该数量包括2个内部病例的任务尾语；严格文本子集为92例、521个累计前缀。

464个归一化来源答案字符串不等于464个独立病种；同病异名、上下位诊断和病理状态没有强行合并。筛选依据是原题直接询问诊断，原选项有时用病因或病理描述作答，例如“Dopamine blockade”和“Presence of endometrial glands and stroma in uterine myometrium”。因此准确的统计对象是540个诊断问答病例与其原始候选，并非540个纯病名分类题。跨病例比较使用来源答案命中、固定错误候选的分差、首选切换、患者级配对变化，避免把不同病例的原始隐藏向量直接相加当成共同疾病坐标。

## 去重与文字质量

抽样前以词和二元词TF-IDF余弦0.90过滤近重复，比较了此前1273行MedQA test，排除300条候选重复。另保留0.80阈值敏感性、答案直接出现在原文的标记。这是文本相似性检查，不能排除所有改写重复或预训练污染。

运行后再次审计原文，发现20例问题：7例末尾仅剩提问引导语；8例引用了未提供图像或报告；4例只写做了检查而没给结果；1例事实组末尾混有任务引导语。全部原结果和规则保留，严格520例作为敏感性队列；其中MedQA291、MedMCQA189、MMLU40。内部94例剩92例，确认内部48例剩47例。未提供的检查材料不补写。

原自动文本检查并不覆盖上述所有形式，其`no_task_question_in_evidence`结论已纠正为false；原检查另存。正式审计见[text_audit.json](../data/belief_v4/text_audit.json)和[逐例问题原文](../data/belief_v4/text_audit_review.json)。该审计在运行后按文本完成，不能伪称为事前排除。

## 数据与文件

[病例与来源答案](../data/belief_v4/cases.private.jsonl) · [不含标签的病例](../data/belief_v4/cases.public.jsonl) · [主清单与哈希](../data/belief_v4/manifest.json) · [抽样审查](../data/belief_v4/selection_review.md) · [质量标记](../data/belief_v4/quality_flags.csv)

数据来源各自的使用条件保持不变；本轮目录是研究派生材料，不改变原数据的许可。运行记录中的所有条件可以通过case_id回到原始病例。

## 原题自带的学科覆盖

MedQA包含119例step1与181例step2&3。MedMCQA包含19个有名称的原题学科，以及6例Unknown；这是考试学科标签，不把基础学科直接称为临床科室。没有另用模型推测或补标专业。

| MedMCQA原学科 | 例数 |
|---|---:|
| Medicine | 49 |
| Pediatrics | 23 |
| Surgery | 19 |
| Pathology | 17 |
| Ophthalmology | 12 |
| Psychiatry | 10 |
| Skin | 10 |
| Radiology | 10 |
| Gynaecology & Obstetrics | 7 |
| ENT | 6 |
| Orthopaedics | 6 |
| Unknown | 6 |
| Microbiology | 6 |
| Anatomy | 6 |
| Dental | 4 |
| Pharmacology | 3 |
| Social & Preventive Medicine | 2 |
| Anaesthesia | 2 |
| Biochemistry | 1 |
| Physiology | 1 |
