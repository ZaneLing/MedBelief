# ddx_train_0940128

队列：pilot；数据标签：肺栓塞；新增证据组数：8。

![三种顺序的概率与后五层轨迹](ddx_train_0940128.png)

| 基础轮次 | 新证据 | 原始明确记录 |
|---|---|---|
| 0 | 深吸气使疼痛加重：是（E_220） | Do you have pain that is increased when you breathe in deeply? Yes |
| 1 | 曾有深静脉血栓：是（E_109） | Have you ever had deep vein thrombosis (DVT)? Yes |
| 2 | 本次就诊相关疼痛（同时揭示性质、位置、程度、放射等记录）：是（E_53） | Do you have pain somewhere, related to your reason for consulting? Yes；Characterize your pain: sensitive; a knife stroke; sharp；Do you feel pain somewhere? side of the chest(R); side of the chest(L); scapula(R); scapula(L); posterior chest wall(R)；How intense is the pain? dataset scale value 2；Does the pain radiate to another location? side of the chest(R); side of the chest(L); scapula(R); scapula(L); posterior chest wall(R)；How precisely is the pain located? dataset scale value 8；How fast did the pain appear? dataset scale value 10 |
| 3 | 目前服用激素：是（E_100） | Do you currently take hormones? Yes |
| 4 | 目前患有活动性癌症：是（E_34） | Do you have an active cancer? Yes |
| 5 | 身体局部肿胀（同时揭示部位）：nowhere（E_151） | Where is the swelling located? nowhere |
| 6 | 咯血：是（E_45） | Have you been coughing up blood? Yes |
| 7 | 近一个月接受过手术：是（E_196） | Have you had surgery within the last month? Yes |
| 8 | 近四周出国旅行：否（E_204） | Have you traveled out of the country in the last 4 weeks? No |
