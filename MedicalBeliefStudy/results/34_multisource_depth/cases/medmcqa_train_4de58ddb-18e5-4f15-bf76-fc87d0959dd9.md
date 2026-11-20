# medmcqa_train_4de58ddb-18e5-4f15-bf76-fc87d0959dd9

来源：MedMCQA，train，原始第100051行（零起始）。完整题目来源答案：**Ankylosing spondylitis**；人为指定的错误旧诊断：**Gouty arthritis**。

候选：1 = Rheumatoid arthritis；2 = Oteoarthritis；3 = Gouty arthritis；4 = Ankylosing spondylitis。

![全部四候选与逐层首选](./medmcqa_train_4de58ddb-18e5-4f15-bf76-fc87d0959dd9_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./medmcqa_train_4de58ddb-18e5-4f15-bf76-fc87d0959dd9.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 27-year old male presents with low backache, that occurs early in the morning, associated with stiffness, and persists for more than 30 minutes. | Ankylosing spondylitis | Ankylosing spondylitis |
| 2 | On examination, his chest expansion is also restricted. | Ankylosing spondylitis | Ankylosing spondylitis |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Ankylosing spondylitis（代码总量 0.65） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Ankylosing spondylitis（代码总量 0.54） |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Ankylosing spondylitis（代码总量 0.64） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Ankylosing spondylitis（代码总量 0.51） |
