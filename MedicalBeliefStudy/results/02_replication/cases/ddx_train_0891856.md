# ddx_train_0891856

队列：replication；数据标签：肺炎；新增证据组数：19。

![三种顺序的概率与后五层轨迹](ddx_train_0891856.png)

| 基础轮次 | 新证据 | 原始明确记录 |
|---|---|---|
| 0 | 有自认为与本次就诊相关的皮肤问题（同时揭示颜色、位置、程度等记录）：是（E_129） | Do you have any lesions, redness or problems on your skin that you believe are related to the condition you are consulting for? Yes；What color is the rash? pink；Do your lesions peel off? Yes；Is the rash swollen? dataset scale value 6；Where is the affected region located? commissure(L); buttock(L); flank(L); posterior chest wall(R); shoulder(L)；How intense is the pain caused by the rash? dataset scale value 0；Is the lesion (or are the lesions) larger than 1cm? No；How severe is the itching? dataset scale value 5 |
| 1 | 近四周出国旅行：否（E_204） | Have you traveled out of the country in the last 4 weeks? No |
| 2 | 近期食欲下降或更容易饱：是（E_161） | Have you recently had a loss of appetite or do you get full more quickly then usually? Yes |
| 3 | 发热：是（E_91） | Do you have a fever (either felt or measured with a thermometer)? Yes |
| 4 | 有慢性阻塞性肺疾病病史：是（E_122） | Do you have a chronic obstructive pulmonary disease (COPD)? Yes |
| 5 | BMI低于18.5或体重过低：是（E_208） | Is your BMI less than 18.5, or are you underweight? Yes |
| 6 | 咯血：是（E_45） | Have you been coughing up blood? Yes |
| 7 | 本次就诊相关疼痛（同时揭示性质、位置、程度、放射等记录）：是（E_53） | Do you have pain somewhere, related to your reason for consulting? Yes；Characterize your pain: sharp；Do you feel pain somewhere? side of the chest(R); side of the chest(L); posterior chest wall(R); posterior chest wall(L)；How intense is the pain? dataset scale value 3；Does the pain radiate to another location? nowhere；How precisely is the pain located? dataset scale value 0；How fast did the pain appear? dataset scale value 2 |
| 8 | 夜间症状更明显：是（E_219） | Are your symptoms more prominent at night? Yes |
| 9 | 有哮喘或曾用支气管扩张药：是（E_124） | Do you have asthma or have you ever had to use a bronchodilator in the past? Yes |
| 10 | 过量饮酒或酒精依赖：是（E_78） | Do you drink alcohol excessively or do you have an addiction to alcohol? Yes |
| 11 | 有心力衰竭病史：是（E_106） | Do you have heart failure? Yes |
| 12 | 明显气短或呼吸困难：是（E_66） | Are you experiencing shortness of breath or difficulty breathing in a significant way? Yes |
| 13 | 寒战：是（E_94） | Have you had chills or shivers? Yes |
| 14 | 吸烟：是（E_79） | Do you smoke cigarettes? Yes |
| 15 | 有帕金森病史：是（E_95） | Do you have Parkinson’s disease? Yes |
| 16 | 曾有肺炎：是（E_117） | Have you ever had pneumonia? Yes |
| 17 | 咳嗽，痰变色或增多：是（E_77） | Do you have a cough that produces colored or more abundant sputum than usual? Yes |
| 18 | 疫苗按时接种：是（E_209） | Are your vaccinations up to date? Yes |
| 19 | 深吸气使疼痛加重：是（E_220） | Do you have pain that is increased when you breathe in deeply? Yes |
