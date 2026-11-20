# mmlu_professional_medicine_test_0077

来源：MMLU，test，原始第77行（零起始）。完整题目来源答案：**adjustment disorder with anxious mood**；人为指定的错误旧诊断：**major depressive disorder, single episode, moderate**。

候选：1 = adjustment disorder with anxious mood；2 = generalized anxiety disorder；3 = major depressive disorder, single episode, moderate；4 = obsessive-compulsive personality disorder。

![全部四候选与逐层首选](./mmlu_professional_medicine_test_0077_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./mmlu_professional_medicine_test_0077.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 29-year-old male presents to the office with the complaints of a pounding heart, poor sleep, and a generalized feeling of restlessness. | generalized anxiety disorder | generalized anxiety disorder |
| 2 | He relocated 2 months ago to take a promotion and has found himself unable to concentrate on his new duties. | generalized anxiety disorder | generalized anxiety disorder |
| 3 | He worries about his ability to adapt to his increase in responsibility at work and states that he has called in sick 3 days within the past 2 weeks. | adjustment disorder with anxious mood | adjustment disorder with anxious mood |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
