# mmlu_professional_medicine_test_0244

来源：MMLU，test，原始第244行（零起始）。完整题目来源答案：**Chronic lymphocytic thyroiditis (Hashimoto disease)**；人为指定的错误旧诊断：**Graves disease**。

候选：1 = Chronic lymphocytic thyroiditis (Hashimoto disease)；2 = Defect in thyroxine (T4) biosynthesis；3 = Graves disease；4 = Multinodular goiter。

![全部四候选与逐层首选](./mmlu_professional_medicine_test_0244_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./mmlu_professional_medicine_test_0244.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 67-year-old woman has had fatigue, dry skin, brittle hair, swelling of the ankles, and cold intolerance for 1 year; she has gained 9 kg (20 lb) during this period. | Chronic lymphocytic thyroiditis (Hashimoto disease) | Graves disease |
| 2 | Her pulse is 55/min, and blood pressure is 150/90 mm Hg. | Chronic lymphocytic thyroiditis (Hashimoto disease) | Graves disease |
| 3 | She appears lethargic. | Chronic lymphocytic thyroiditis (Hashimoto disease) | Graves disease |
| 4 | Examination shows dry skin and a nontender thyroid gland that is enlarged to two times its normal size. | Chronic lymphocytic thyroiditis (Hashimoto disease) | Graves disease |
| 5 | There is mild edema of the ankles bilaterally. | Chronic lymphocytic thyroiditis (Hashimoto disease) | Graves disease |
| 6 | The relaxation phase of the Achilles reflex is greatly prolonged. | Graves disease | Graves disease |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic lymphocytic thyroiditis (Hashimoto disease)（代码总量 1） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic lymphocytic thyroiditis (Hashimoto disease)（代码总量 1） |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic lymphocytic thyroiditis (Hashimoto disease)（代码总量 1） |
| 4 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic lymphocytic thyroiditis (Hashimoto disease)（代码总量 1） |
| 5 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic lymphocytic thyroiditis (Hashimoto disease)（代码总量 1） |
| 6 | 映射不一致 | 映射不一致 | 映射不一致 | Chronic lymphocytic thyroiditis (Hashimoto disease)（代码总量 1） |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Graves disease（代码总量 1） |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Graves disease（代码总量 1） |
| 4 | 映射不一致 | 映射不一致 | 映射不一致 | Graves disease（代码总量 1） |
| 5 | 映射不一致 | 映射不一致 | 映射不一致 | Graves disease（代码总量 1） |
| 6 | 映射不一致 | 映射不一致 | 映射不一致 | Graves disease（代码总量 1） |
