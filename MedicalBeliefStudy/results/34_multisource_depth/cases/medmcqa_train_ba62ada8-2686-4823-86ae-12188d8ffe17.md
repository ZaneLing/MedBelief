# medmcqa_train_ba62ada8-2686-4823-86ae-12188d8ffe17

来源：MedMCQA，train，原始第63227行（零起始）。完整题目来源答案：**Mantle cell Lymphoma (MCL)**；人为指定的错误旧诊断：**Hairy cell leukemia**。

候选：1 = Hairy cell leukemia；2 = Mantle cell Lymphoma (MCL)；3 = Chronic Lymphocytic Leukemia (CLL)；4 = Follicular Lymphoma。

![全部四候选与逐层首选](./medmcqa_train_ba62ada8-2686-4823-86ae-12188d8ffe17_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./medmcqa_train_ba62ada8-2686-4823-86ae-12188d8ffe17.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 63 year old man presents with splenomgaly and lymphadenopathy. | Chronic Lymphocytic Leukemia (CLL) | Chronic Lymphocytic Leukemia (CLL) |
| 2 | Immunophenotype was positive for CD 19, CD79b and FMC7. | Mantle cell Lymphoma (MCL) | Chronic Lymphocytic Leukemia (CLL) |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
