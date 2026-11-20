# ddx_train_0897400

队列：replication；数据标签：支气管炎；新增证据组数：9。

![三种顺序的概率与后五层轨迹](ddx_train_0897400.png)

| 基础轮次 | 新证据 | 原始明确记录 |
|---|---|---|
| 0 | 咳嗽，痰变色或增多：是（E_77） | Do you have a cough that produces colored or more abundant sputum than usual? Yes |
| 1 | 近四周出国旅行：否（E_204） | Have you traveled out of the country in the last 4 weeks? No |
| 2 | 明显气短或呼吸困难：是（E_66） | Are you experiencing shortness of breath or difficulty breathing in a significant way? Yes |
| 3 | 咳嗽：是（E_201） | Do you have a cough? Yes |
| 4 | 本次就诊相关疼痛（同时揭示性质、位置、程度、放射等记录）：是（E_53） | Do you have pain somewhere, related to your reason for consulting? Yes；Characterize your pain: sensitive；Do you feel pain somewhere? lower chest; side of the chest(L); pharynx; breast(R)；How intense is the pain? dataset scale value 3；Does the pain radiate to another location? nowhere；How precisely is the pain located? dataset scale value 4；How fast did the pain appear? dataset scale value 1 |
| 5 | 夜间症状更明显：是（E_219） | Are your symptoms more prominent at night? Yes |
| 6 | 呼气时有喘鸣：是（E_214） | Have you noticed a wheezing sound when you exhale? Yes |
| 7 | 吸烟：是（E_79） | Do you smoke cigarettes? Yes |
| 8 | 发热：是（E_91） | Do you have a fever (either felt or measured with a thermometer)? Yes |
| 9 | 有慢性阻塞性肺疾病病史：是（E_122） | Do you have a chronic obstructive pulmonary disease (COPD)? Yes |
