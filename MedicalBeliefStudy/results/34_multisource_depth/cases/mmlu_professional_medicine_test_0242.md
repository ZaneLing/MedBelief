# mmlu_professional_medicine_test_0242

来源：MMLU，test，原始第242行（零起始）。完整题目来源答案：**Hemopneumothorax, not under tension**；人为指定的错误旧诊断：**Pneumothorax, not under tension**。

候选：1 = Hemopneumothorax, not under tension；2 = Hemothorax, not under tension；3 = Pneumothorax, not under tension；4 = Tension hemopneumothorax。

![全部四候选与逐层首选](./mmlu_professional_medicine_test_0242_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./mmlu_professional_medicine_test_0242.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 16-year-old boy is admitted to the emergency department because of a knife wound to the left side of his chest. | Hemopneumothorax, not under tension | Hemopneumothorax, not under tension |
| 2 | An x-ray of the chest shows an air-fluid level in the left side of the chest, partial collapse of the left lung, and elevation of the stomach bubble. | Hemopneumothorax, not under tension | Hemopneumothorax, not under tension |
| 3 | The mediastinum is in the midline. | Hemopneumothorax, not under tension | Hemopneumothorax, not under tension |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Hemopneumothorax, not under tension（代码总量 0.97） |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Hemothorax, not under tension（代码总量 0.99） |
