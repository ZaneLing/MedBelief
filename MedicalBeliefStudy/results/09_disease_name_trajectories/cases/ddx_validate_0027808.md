# ddx_validate_0027808

源标签：**GERD**；参考首位：**GERD**。

![疾病名轨迹](ddx_validate_0027808.png)

上图为完整疾病名的候选分数，中图为真实隐藏状态的方向变化，下图为注意力分配。中图颜色不代表某个疾病。

| 轮 | 新证据 | 名称评分首选 | 标签支持 | 贪心续写 |
|---|---|---|---|---|
| 0 | Do you have symptoms that get worse after eating? **Yes** | Acute COPD exacerbation / infection | 0.0522 | Acute bronchiolitis |
| 1 | Have you traveled out of the country in the last 4 weeks? **No** | GERD | 0.9716 | GERD |
| 2 | Have you recently thrown up blood or something resembling coffee beans? **Yes** | Boerhaave | 0.0000 | Boerhaave |
| 3 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **haunting; a knife stroke; tugging; burning; sickening**<br>Do you feel pain somewhere? **lower chest; hypochondrium(R); hypochondrium(L); epigastric**<br>How intense is the pain? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **lower chest; upper chest**<br>How precisely is the pain located? **Recorded scale value 4 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 0 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Boerhaave | 0.0000 | Boerhaave |
| 4 | Do you have a burning sensation that starts in your stomach then goes up into your throat, and can be associated with a bitter taste in your mouth? **Yes** | Boerhaave | 0.0000 | Boerhaave |
| 5 | Are your symptoms worse when lying down and alleviated while sitting up? **Yes** | Boerhaave | 0.0000 | Boerhaave |
| 6 | Do you smoke cigarettes? **Yes** | Boerhaave | 0.0000 | Boerhaave |
| 7 | Do you have a cough? **Yes** | Boerhaave | 0.0000 | Boerhaave |
| 8 | Do you have a hiatal hernia? **Yes** | Boerhaave | 0.0000 | Boerhaave |
| 9 | Do you drink alcohol excessively or do you have an addiction to alcohol? **Yes** | Boerhaave | 0.0000 | Boerhaave |
| 10 | Are you significantly overweight compared to people of the same height as you? **Yes** | Boerhaave | 0.0000 | Boerhaave |
