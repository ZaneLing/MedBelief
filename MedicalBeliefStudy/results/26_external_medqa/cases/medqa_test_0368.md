# medqa_test_0368：Trichomonal vaginitis

来源：MedQA四选项test，第368行（零起始）。来源答案只用于完整题目评价。路径：在其他疾病间变动。下图没有用DDxPlus探针解码MedQA病名。

![逐句轨迹](medqa_test_0368.png)

Which of the following is the most likely diagnosis in this patient based on her presentation?

| 轮 | 原模型首选 | 来源答案支持 | 本轮新增原文 |
|---|---|---:|---|
| 1 | Chlamydia infection | 0.0938 | A 20-year-old woman presents with vaginal discharge, pruritus, and painful micturition for the past 5 days. |
| 2 | Chlamydia infection | 0.0000 | She is sexually active with multiple partners and admits to using barrier protection inconsistently. |
| 3 | Chlamydia infection | 0.0000 | Her last menstrual period was 2 weeks ago. |
| 4 | Chlamydia infection | 0.0000 | The patient denies any fever, chills, abdominal pain, menorrhagia, or flank pain. |
| 5 | Chlamydia infection | 0.0000 | She is afebrile and the vital signs are within normal limits. |
| 6 | Chlamydia infection | 0.0000 | Speculum examination reveals vaginal erythema with a profuse, greenish-yellow, purulent, malodorous discharge. |
| 7 | Bacterial vaginosis | 0.0000 | The vaginal pH is 5.5. |
| 8 | Bacterial vaginosis | 0.0000 | Vaginal swab and urine samples are obtained for microscopy and culture, and results are pending. |

| 完整题目控制 | 原模型首选 | 来源答案支持改变 |
|---|---|---:|
| reverse | Bacterial vaginosis | +0.0000 |
| shuffle | Bacterial vaginosis | -0.0000 |
| wrong_history | Chlamydia infection | +0.0000 |

原题选项：{"A": "Urinary tract infection", "B": "Bacterial vaginosis", "C": "Trichomonal vaginitis", "D": "Chlamydia infection"}
