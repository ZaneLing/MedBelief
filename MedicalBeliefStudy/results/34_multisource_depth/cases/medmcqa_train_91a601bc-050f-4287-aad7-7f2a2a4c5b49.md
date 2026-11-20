# medmcqa_train_91a601bc-050f-4287-aad7-7f2a2a4c5b49

来源：MedMCQA，train，原始第14113行（零起始）。完整题目来源答案：**Ostium primum atrial septal defect.**；人为指定的错误旧诊断：**Tricuspid atresia.**。

候选：1 = Total anomalous pulmonary venous drainge；2 = Tricuspid atresia.；3 = Ostium primum atrial septal defect.；4 = Ventricular septal defect with pulmonary aerial hypeension.。

![全部四候选与逐层首选](./medmcqa_train_91a601bc-050f-4287-aad7-7f2a2a4c5b49_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./medmcqa_train_91a601bc-050f-4287-aad7-7f2a2a4c5b49.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A young female presents with history of dyspnoea on exeion. | Ostium primum atrial septal defect. | Tricuspid atresia. |
| 2 | On examination, she has wide, fixed split S2 with ejection systolic murmur (IIINI) in left second intercostal space. | Total anomalous pulmonary venous drainge | Tricuspid atresia. |
| 3 | Her ECG shows left axis detion. | Total anomalous pulmonary venous drainge | Tricuspid atresia. |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Total anomalous pulmonary venous drainge（代码总量 1） |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Total anomalous pulmonary venous drainge（代码总量 1） |
