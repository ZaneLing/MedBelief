# mmlu_professional_medicine_test_0087

来源：MMLU，test，原始第87行（零起始）。完整题目来源答案：**Herpes zoster**；人为指定的错误旧诊断：**Chronic relapsing pancreatitis**。

候选：1 = Acalculous cholecystitis；2 = Chronic relapsing pancreatitis；3 = Diverticulitis of the cecum；4 = Herpes zoster。

![全部四候选与逐层首选](./mmlu_professional_medicine_test_0087_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./mmlu_professional_medicine_test_0087.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 75-year-old woman comes to the office because she has band-like, burning pain in her right upper abdomen extending from the epigastrium around to the midline of the back. | Herpes zoster | Chronic relapsing pancreatitis |
| 2 | Physical examination discloses no abdominal tenderness to palpation. | Herpes zoster | Chronic relapsing pancreatitis |
| 3 | Findings on ultrasonography of the gallbladder are normal. | Herpes zoster | Chronic relapsing pancreatitis |
| 4 | Serum amylase concentration is within the reference range. | Acalculous cholecystitis | Acalculous cholecystitis |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic relapsing pancreatitis（代码总量 0.99） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic relapsing pancreatitis（代码总量 1） |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 4 | 映射不一致 | 映射不一致 | 映射不一致 | Acalculous cholecystitis（代码总量 1） |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic relapsing pancreatitis（代码总量 1） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic relapsing pancreatitis（代码总量 1） |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic relapsing pancreatitis（代码总量 1） |
| 4 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic relapsing pancreatitis（代码总量 1） |
