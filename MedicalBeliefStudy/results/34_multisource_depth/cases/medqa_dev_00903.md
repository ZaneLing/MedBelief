# medqa_dev_00903

来源：MedQA，dev，原始第903行（零起始）。完整题目来源答案：**Aortic regurgitation**；人为指定的错误旧诊断：**Mitral stenosis**。

候选：1 = Mitral valve insufficiency；2 = Aortic regurgitation；3 = Mitral stenosis；4 = Aortic stenosis。

![全部四候选与逐层首选](./medqa_dev_00903_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./medqa_dev_00903.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 65-year-old male presents to his cardiologist to discuss increasing episodes of dyspnea after climbing stairs. | Aortic stenosis | Mitral stenosis |
| 2 | He also now needs three pillows at night to sleep. | Aortic regurgitation | Mitral stenosis |
| 3 | Physical examination reveals an early diastolic murmur best appreciated at the left sternal border with bounding peripheral pulses. | Mitral valve insufficiency | Mitral stenosis |
| 4 | The cardiologist is very concerned and immediately refers the patient for a surgical workup. | Aortic regurgitation | Mitral stenosis |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Mitral valve insufficiency（代码总量 1） |
| 4 | 映射不一致 | 映射不一致 | 映射不一致 | Mitral valve insufficiency（代码总量 1） |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Mitral stenosis（代码总量 1） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Mitral stenosis（代码总量 1） |
| 3 | 映射不一致 | 映射不一致 | 映射不一致 | Mitral stenosis（代码总量 1） |
| 4 | 映射不一致 | 映射不一致 | 映射不一致 | Mitral stenosis（代码总量 1） |
