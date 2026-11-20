# ddx_validate_0041143

源标签：**Pneumonia**；参考首位：**Bronchitis**。

![轨迹](ddx_validate_0041143.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have diffuse (widespread) muscle pain? **Yes** | SLE | 0.0004 |
| 1 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **sharp**<br>Do you feel pain somewhere? **side of the chest(L); upper chest; breast(R); posterior chest wall(R); posterior chest wall(L)**<br>How intense is the pain? **Recorded scale value 7 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 7 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Inguinal hernia | 0.0000 |
| 2 | Do you have asthma or have you ever had to use a bronchodilator in the past? **Yes** | Anemia | 0.0000 |
| 3 | Do you have a cough that produces colored or more abundant sputum than usual? **Yes** | Anemia | 0.0000 |
| 4 | Have you ever had pneumonia? **Yes** | Viral pharyngitis | 0.0000 |
| 5 | Do you have heart failure? **Yes** | Acute pulmonary edema | 0.0000 |
| 6 | Have you traveled out of the country in the last 4 weeks? **No** | Acute pulmonary edema | 0.0000 |
| 7 | Is your BMI less than 18.5, or are you underweight? **Yes** | Acute pulmonary edema | 0.0000 |
| 8 | Do you drink alcohol excessively or do you have an addiction to alcohol? **Yes** | Acute pulmonary edema | 0.0000 |
| 9 | Do you smoke cigarettes? **Yes** | Acute pulmonary edema | 0.0000 |
| 10 | Have you ever had a stroke? **Yes** | Acute pulmonary edema | 0.0000 |
| 11 | Have you had chills or shivers? **Yes** | Acute pulmonary edema | 0.0000 |
| 12 | Do you have a chronic obstructive pulmonary disease (COPD)? **Yes** | Acute pulmonary edema | 0.0000 |
| 13 | Have you noticed any new fatigue, generalized and vague discomfort, diffuse (widespread) muscle aches or a change in your general well-being related to your consultation today? **Yes** | Anemia | 0.0030 |
| 14 | Are your symptoms more prominent at night? **Yes** | Pericarditis | 0.0002 |
| 15 | Do you have any lesions, redness or problems on your skin that you believe are related to the condition you are consulting for? **Yes**<br>What color is the rash? **pink**<br>Do your lesions peel off? **Yes**<br>Is the rash swollen? **Recorded scale value 3 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Where is the affected region located? **back of the neck; side of the neck(L); buttock(R)**<br>How intense is the pain caused by the rash? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Is the lesion (or are the lesions) larger than 1cm? **No**<br>How severe is the itching? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Anemia | 0.0000 |
| 16 | Are your vaccinations up to date? **Yes** | Pericarditis | 0.0002 |
