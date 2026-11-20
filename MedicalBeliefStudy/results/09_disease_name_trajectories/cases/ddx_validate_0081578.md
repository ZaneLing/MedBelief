# ddx_validate_0081578

源标签：**Bronchitis**；参考首位：**Pneumonia**。

![疾病名轨迹](ddx_validate_0081578.png)

上图为完整疾病名的候选分数，中图为真实隐藏状态的方向变化，下图为注意力分配。中图颜色不代表某个疾病。

| 轮 | 新证据 | 名称评分首选 | 标签支持 | 贪心续写 |
|---|---|---|---|---|
| 0 | Are you experiencing shortness of breath or difficulty breathing in a significant way? **Yes** | Acute pulmonary edema | 0.0000 | Acute pulmonary edema |
| 1 | Have you noticed a wheezing sound when you exhale? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 2 | Do you have a sore throat? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 3 | Do you have a cough? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 4 | Have you traveled out of the country in the last 4 weeks? **No** | Acute COPD exacerbation / infection | 0.0000 | Acute bronchiolitis |
| 5 | Do you have a fever (either felt or measured with a thermometer)? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 6 | Do you smoke cigarettes? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute bronchiolitis |
| 7 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **sensitive**<br>Do you feel pain somewhere? **breast(L); posterior chest wall(R)**<br>How intense is the pain? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 3 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 1 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Acute COPD exacerbation / infection | 0.0000 | Acute bronchiolitis |
| 8 | Do you have a cough that produces colored or more abundant sputum than usual? **Yes** | Bronchiolitis | 0.0000 | Acute bronchiolitis |
| 9 | Are your symptoms more prominent at night? **Yes** | Bronchiolitis | 0.0000 | Acute bronchiolitis |
