# ddx_validate_0103610

源标签：**GERD**；参考首位：**GERD**。

![疾病名轨迹](ddx_validate_0103610.png)

上图为完整疾病名的候选分数，中图为真实隐藏状态的方向变化，下图为注意力分配。中图颜色不代表某个疾病。

| 轮 | 新证据 | 名称评分首选 | 标签支持 | 贪心续写 |
|---|---|---|---|---|
| 0 | Do you have a cough? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 1 | Do you have symptoms that get worse after eating? **Yes** | Acute rhinosinusitis | 0.0000 | Acute rhinosinusitis |
| 2 | Do you smoke cigarettes? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 3 | Have you traveled out of the country in the last 4 weeks? **No** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 4 | Do you drink alcohol excessively or do you have an addiction to alcohol? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 5 | Are your symptoms worse when lying down and alleviated while sitting up? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 6 | Do you have a hiatal hernia? **Yes** | GERD | 1.0000 | GERD |
| 7 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **haunting; sensitive; tugging; burning; scary**<br>Do you feel pain somewhere? **lower chest; hypochondrium(R); hypochondrium(L); epigastric**<br>How intense is the pain? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **lower chest; upper chest**<br>How precisely is the pain located? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified** | GERD | 1.0000 | GERD |
| 8 | Do you have a burning sensation that starts in your stomach then goes up into your throat, and can be associated with a bitter taste in your mouth? **Yes** | GERD | 1.0000 | GERD |
