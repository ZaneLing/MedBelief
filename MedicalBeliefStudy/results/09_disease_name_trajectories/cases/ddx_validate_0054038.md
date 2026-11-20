# ddx_validate_0054038

源标签：**Viral pharyngitis**；参考首位：**Possible NSTEMI / STEMI**。

![疾病名轨迹](ddx_validate_0054038.png)

上图为完整疾病名的候选分数，中图为真实隐藏状态的方向变化，下图为注意力分配。中图颜色不代表某个疾病。

| 轮 | 新证据 | 名称评分首选 | 标签支持 | 贪心续写 |
|---|---|---|---|---|
| 0 | Do you have a fever (either felt or measured with a thermometer)? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute COPD exacerbation / infection |
| 1 | Have you traveled out of the country in the last 4 weeks? **No** | Acute rhinosinusitis | 0.0024 | Acute rhinosinusitis |
| 2 | Do you attend or work in a daycare? **Yes** | Acute rhinosinusitis | 0.0000 | Acute rhinosinusitis |
| 3 | Have you been coughing up blood? **Yes** | Acute rhinosinusitis | 0.0000 | Acute bronchiolitis |
| 4 | Do you live with 4 or more people? **Yes** | Acute COPD exacerbation / infection | 0.0000 | Acute bronchiolitis |
| 5 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **sensitive**<br>Do you feel pain somewhere? **tonsil(R); tonsil(L); thyroid cartilage; palace; pharynx**<br>How intense is the pain? **Recorded scale value 9 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Acute rhinosinusitis | 0.0250 | Acute rhinosinusitis |
