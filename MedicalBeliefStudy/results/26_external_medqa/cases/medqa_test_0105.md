# medqa_test_0105：Borderline personality disorder

来源：MedQA四选项test，第105行（零起始）。来源答案只用于完整题目评价。路径：始终首选来源病。下图没有用DDxPlus探针解码MedQA病名。

![逐句轨迹](medqa_test_0105.png)

Which of the following is the most likely diagnosis in this patient?

| 轮 | 原模型首选 | 来源答案支持 | 本轮新增原文 |
|---|---|---:|---|
| 1 | Borderline personality disorder | 1.0000 | A 28-year-old woman presents following a suicide attempt 2 days ago. |
| 2 | Borderline personality disorder | 1.0000 | She says that her attempt was a result of a fight with her boyfriend and that she slit her wrists in an attempt to keep him from breaking up with her. |
| 3 | Borderline personality disorder | 1.0000 | In the past, she has had many turbulent relationships, both romantic and in her family life. |
| 4 | Borderline personality disorder | 1.0000 | Her family members describe her as being very impulsive and frequently acting to manipulate people’s feelings. |
| 5 | Borderline personality disorder | 1.0000 | Since she was admitted to the hospital, she has spit at several staff members and alternated between sobbing and anger. |
| 6 | Borderline personality disorder | 1.0000 | She has no significant past medical history. |
| 7 | Borderline personality disorder | 1.0000 | The patient denies any history of smoking, alcohol use, or recreational drug use. |

| 完整题目控制 | 原模型首选 | 来源答案支持改变 |
|---|---|---:|
| reverse | Borderline personality disorder | +0.0000 |
| shuffle | Borderline personality disorder | -0.0000 |
| wrong_history | Borderline personality disorder | -0.0000 |

原题选项：{"A": "Histrionic personality disorder", "B": "Borderline personality disorder", "C": "Dependent personality disorder", "D": "Narcissistic personality disorder"}
