# 评分核查：写对病名，与逐字照抄候选要分开

本轮原预定评分要求模型生成的名称与来源候选逐字一致。查看实际回答后发现，这会把已经表达出正确病名的部分回答计错。因此增加一套固定、对所有方法相同的写法规范化评分；不改变原始生成、训练、选型或原评分结果。

## 一个直接的例子

来源候选是 `Inferior wall myocardial infarction `，末尾有一个空格。模型输出 `Inferior wall myocardial infarction`，原评分判错；候选约束强迫它输出含末尾空格的版本，原评分变对。这是输出格式被修好，不能据此说模型此前不认识下壁心肌梗死。

## 统一规则

1. 优先使用JSON解析得到的名称；解析失败时，取原续写第一个右花括号之前的文字。
2. 统一Unicode宽度、大小写，去掉开头a/an/the，清理空格及表面标点；保留所有字母、数字与 `+-−/<>=%` 符号。
3. 与**全部四个候选**用同一规则比对，只接受唯一的完整规范化匹配。
4. 不使用正确答案来决定如何解析；不做模糊匹配、疾病同义词扩展或模型裁判。880例不存在规范化候选碰撞。

登记与代码散列：[SCORING_AMENDMENT.json](SCORING_AMENDMENT.json)；实现：[structure2_scoring.py](../src/structure2_scoring.py)。这是**结果后的敏感性分析**，不是原先预定指标。

## 对结论的影响

同一压缩骨干加候选约束后，28个原逐字评分的修复中，18个原回答在规范化后已经正确。剩余10个仍混合了拼写、简称与疾病用词变化，不能全部当成新的医学判断。

原模型在400例的中性/错误历史下，逐字答对210/163例，规范化后216/168例。压缩加约束为216/180例。两种历史平均增益由2.875个百分点缩至1.50个百分点，规范化后的配对检验不再支持稳健显著改善。完整8配置、严格366例、区间与校正检验见[确认报告](../results/49_structure_confirmation/RESULTS.md)。

更小的实际权重矩阵与更短的测量耗时不受评分规则影响；“模型医学判断更好”必须以合理评分下仍成立的证据支持。

## 所有28个原逐字修复

下表按病例—历史记录；同病例两个历史可能重复。

| 病例 | 历史 | 原始续写 | 来源答案 | 规范化后原本已正确 |
|---|---|---|---|---|
| medmcqa_train_e675b134-430c-4e38-8e06-89dec30f728e | neutral | `Idiopathic (immune) thrombocytopenic purpura (ITP")"}` | `Idiopathic (immune) thrombocytopenic purpura (ITP)` | 是 |
| medmcqa_train_e675b134-430c-4e38-8e06-89dec30f728e | wrong | `Idiopathic (immune) thrombocytopenic purpura (ITP")"}` | `Idiopathic (immune) thrombocytopenic purpura (ITP)` | 是 |
| medqa_train_02066 | neutral | `Inferior wall myocardial infarction"}` | `Inferior wall myocardial infarction ` | 是 |
| medqa_train_03631 | neutral | `Discoid lupus erythematosus (DLE")"}` | `Discoid lupus erythematosus (DLE)` | 是 |
| medqa_train_03631 | wrong | `Discoid lupus erythematosus (DLE")"}` | `Discoid lupus erythematosus (DLE)` | 是 |
| medmcqa_train_c555e8f8-3cd9-4625-bba3-4897bbc0021b | neutral | `Congenital adrenal hyperplasia(CAH")` | `Congenital adrenal hyperplasia(CAH)` | 是 |
| medmcqa_train_c555e8f8-3cd9-4625-bba3-4897bbc0021b | wrong | `Congenital adrenal hyperplasia(CAH")` | `Congenital adrenal hyperplasia(CAH)` | 是 |
| medmcqa_train_8d747f94-fa97-4ab8-9f19-e0087c503392 | neutral | `G glycogen storage diseases"}` | `Glycogen storage diseases` | 否 |
| medmcqa_train_8d747f94-fa97-4ab8-9f19-e0087c503392 | wrong | `G glycogen storage diseases"}` | `Glycogen storage diseases` | 否 |
| medmcqa_train_93353f21-df7b-491c-a359-30a55a6ea6a4 | neutral | `Thyroglossal duct cyst"}` | `A thyroglossal duct cyst` | 是 |
| medmcqa_train_93353f21-df7b-491c-a359-30a55a6ea6a4 | wrong | `Thyroglossal duct cyst"}` | `A thyroglossal duct cyst` | 是 |
| medmcqa_train_8e68b9dc-53d8-4c22-b6e0-b8a6a5d9adae | neutral | `functional pituitary tumor"}` | `a functional pituitary tumor` | 是 |
| medmcqa_train_61ed1226-15b2-4f01-97e8-ce055ba04384 | neutral | `Pemphigus vulgaris"}` | `Pemphigus vulgaris.` | 是 |
| medqa_train_07093 | neutral | `Primary hyperaldosteronism (Conn’s syndrome")"}` | `Primary hyperaldosteronism (Conn’s syndrome)` | 是 |
| medmcqa_train_b4036396-7310-4f28-bf56-4acdf8e6b64a | neutral | `Incomplete aboion"}` | `Inevitable aboion` | 否 |
| medmcqa_train_b4036396-7310-4f28-bf56-4acdf8e6b64a | wrong | `Incomplete aboion"}` | `Inevitable aboion` | 否 |
| medmcqa_train_2a0e0ad5-e7a9-441e-beec-63e0e51e28a9 | wrong | `phenylketonuria"}` | `Phenylketonuria` | 是 |
| medmcqa_train_33d23960-2b26-44d6-897a-3cd6d3f3d1e4 | neutral | `Asthia"}` | `Asthma` | 否 |
| medmcqa_train_33d23960-2b26-44d6-897a-3cd6d3f3d1e4 | wrong | `Asthasia"}` | `Asthma` | 否 |
| medmcqa_train_053a2505-107e-4168-abab-565f43cf2d57 | neutral | `Ne Neonatal Alveolar Proteinosis"}` | `Neonatal Alveolar Proteinosis` | 否 |
| medmcqa_train_0593c2e0-741a-4350-a5ab-1a610056af6a | neutral | `Ganzmann thrombasthenia"}` | `Glanzmann thrombasthenia` | 否 |
| medmcqa_train_0593c2e0-741a-4350-a5ab-1a610056af6a | wrong | `Ganzmann thrombasthenia"}` | `Glanzmann thrombasthenia` | 否 |
| medmcqa_train_d93522e3-8ae1-451e-a688-daec2e5dfe08 | neutral | `McArdle disease (glycogen storage disease")"}` | `McArdle disease (glycogen storage disease)` | 是 |
| medmcqa_train_d93522e3-8ae1-451e-a688-daec2e5dfe08 | wrong | `McArdle disease (glycogen storage disease")"}` | `McArdle disease (glycogen storage disease)` | 是 |
| medmcqa_train_8c3ffe54-362a-45ab-8b4d-a4947e674b45 | wrong | `trigeminal neuralgia"}` | `Trigeminal neuralgia` | 是 |
| medqa_train_06667 | neutral | `Autosomal dominant polycystic kidney disease (ADPKD")` | `Autosomal dominant polycystic kidney disease (ADPKD)` | 是 |
| medqa_train_06667 | wrong | `Autosomal dominant polycystic kidney disease (ADPKD")` | `Autosomal dominant polycystic kidney disease (ADPKD)` | 是 |
| medmcqa_train_01da52da-4def-4d88-9d75-694686a35f68 | neutral | `Chronic intestinal ischemia"}` | `Chronic intestinal ischemia (intestinal angina)` | 否 |
