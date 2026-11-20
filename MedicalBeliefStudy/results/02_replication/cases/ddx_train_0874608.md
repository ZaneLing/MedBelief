# ddx_train_0874608

队列：replication；数据标签：支气管炎；新增证据组数：7。

![三种顺序的概率与后五层轨迹](ddx_train_0874608.png)

| 基础轮次 | 新证据 | 原始明确记录 |
|---|---|---|
| 0 | 咳嗽：是（E_201） | Do you have a cough? Yes |
| 1 | 本次就诊相关疼痛（同时揭示性质、位置、程度、放射等记录）：是（E_53） | Do you have pain somewhere, related to your reason for consulting? Yes；Characterize your pain: sensitive；Do you feel pain somewhere? side of the chest(R); side of the chest(L); breast(R); breast(L)；How intense is the pain? dataset scale value 5；Does the pain radiate to another location? nowhere；How precisely is the pain located? dataset scale value 1；How fast did the pain appear? dataset scale value 5 |
| 2 | 咳嗽，痰变色或增多：是（E_77） | Do you have a cough that produces colored or more abundant sputum than usual? Yes |
| 3 | 近四周出国旅行：否（E_204） | Have you traveled out of the country in the last 4 weeks? No |
| 4 | 疫苗按时接种：是（E_209） | Are your vaccinations up to date? Yes |
| 5 | 鼻塞或流清鼻涕：是（E_181） | Do you have nasal congestion or a clear runny nose? Yes |
| 6 | 有慢性阻塞性肺疾病病史：是（E_122） | Do you have a chronic obstructive pulmonary disease (COPD)? Yes |
| 7 | 明显气短或呼吸困难：是（E_66） | Are you experiencing shortness of breath or difficulty breathing in a significant way? Yes |
