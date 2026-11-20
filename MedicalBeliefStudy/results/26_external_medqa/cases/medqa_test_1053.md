# medqa_test_1053：VIPoma

来源：MedQA四选项test，第1053行（零起始）。来源答案只用于完整题目评价。路径：始终首选来源病。下图没有用DDxPlus探针解码MedQA病名。

![逐句轨迹](medqa_test_1053.png)

Which of the following is the most likely diagnosis in this patient?

| 轮 | 原模型首选 | 来源答案支持 | 本轮新增原文 |
|---|---|---:|---|
| 1 | VIPoma | 1.0000 | A 28-year-old woman presents with facial flushing, weakness, and chronic diarrhea for the past month. |
| 2 | VIPoma | 1.0000 | She denies any history of smoking, alcohol use, or recreational drug use. |
| 3 | VIPoma | 0.9999 | The patient was on a trip to Thailand 2 years ago with her family but denies any recent travel. |
| 4 | VIPoma | 0.9991 | Her blood pressure is 120/88 mm Hg, pulse is 78/min, temperature is 37.2°C (99.0°F), and respiratory rate is 16/min. |
| 5 | VIPoma | 0.9999 | Laboratory findings are unremarkable, except for a potassium level of 3.3 mmol/L and serum calcium of 11 mg/dL. |
| 6 | VIPoma | 1.0000 | The attending physician suspects that this might be a case of a genetic mutation in the menin 1 gene on chromosome 11 and orders a genetic analysis. |

| 完整题目控制 | 原模型首选 | 来源答案支持改变 |
|---|---|---:|
| reverse | VIPoma | +0.0000 |
| shuffle | VIPoma | +0.0000 |
| wrong_history | VIPoma | -0.0058 |

原题选项：{"A": "Vibrio cholera infection", "B": "VIPoma", "C": "Rotavirus", "D": "Campylobacter jejuni"}
