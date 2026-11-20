# medmcqa_validation_dc918205-fb3a-42a9-805e-ec2c3e1c7352

来源：MedMCQA，validation，原始第2205行（零起始）。完整题目来源答案：**Renal cell carcinoma**；人为指定的错误旧诊断：**Seminoma**。

候选：1 = Epididymitis；2 = Seminoma；3 = Renal cell carcinoma；4 = Carcinoma lung。

![全部四候选与逐层首选](./medmcqa_validation_dc918205-fb3a-42a9-805e-ec2c3e1c7352_all_candidates.png)

上排分别显示两种历史下四种候选的病名支持；下排颜色为逐层代码首选，灰色表示两套代码没有指向同一疾病，不能稳定命名该层倾向。

![逐轮与逐层](./medmcqa_validation_dc918205-fb3a-42a9-805e-ec2c3e1c7352.png)

上排是原模型病名评分，下面是未训练输出头的代码投影、两种映射平均；二者接口不同。来源标签只评价完整题目。

| 轮 | 新增原文证据组 | 中性历史首选 | 错误历史首选 |
|---:|---|---|---|
| 1 | A 49 years old male with 35 pack years presented with painless mass in left scrotal sac and microscopic hematuria. | Seminoma | Seminoma |
| 2 | On laboratory investigation, Alphafetoprotein and lactate dehydrogenase was negative. | Seminoma | Seminoma |

## 关键层的投影读表

每格先检查两套答案代码是否指向同一候选；不一致就不命名。括号内为四个答案代码在全词表中的概率总量，接近0时说明输出头尚不适合在该层读取答案。映射一致本身不等于医学判断正确。

### 中性历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Renal cell carcinoma（代码总量 1） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | Renal cell carcinoma（代码总量 1） |

### 错误历史

| 轮 | 第7层 | 第14层 | 第21层 | 第28层 |
|---:|---|---|---|---|
| 1 | 映射不一致 | 映射不一致 | 映射不一致 | Renal cell carcinoma（代码总量 0.97） |
| 2 | 映射不一致 | 映射不一致 | 映射不一致 | 映射不一致 |
