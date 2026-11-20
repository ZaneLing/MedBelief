# ddx_validate_0097758

源标签：**Pneumonia**；参考首位：**Pneumonia**。

![轨迹](ddx_validate_0097758.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Are you experiencing shortness of breath or difficulty breathing in a significant way? **Yes** | Localized edema | 0.0000 |
| 1 | Have you had chills or shivers? **Yes** | Localized edema | 0.0000 |
| 2 | Do you have pain that is increased when you breathe in deeply? **Yes** | Pulmonary neoplasm | 0.0000 |
| 3 | Do you have nasal congestion or a clear runny nose? **Yes** | Pulmonary neoplasm | 0.0000 |
| 4 | Do you have asthma or have you ever had to use a bronchodilator in the past? **Yes** | Localized edema | 0.0000 |
| 5 | Do you have any lesions, redness or problems on your skin that you believe are related to the condition you are consulting for? **Yes**<br>What color is the rash? **pink**<br>Do your lesions peel off? **Yes**<br>Is the rash swollen? **Recorded scale value 4 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Where is the affected region located? **back of the neck; buttock(R); shoulder(L)**<br>How intense is the pain caused by the rash? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Is the lesion (or are the lesions) larger than 1cm? **No**<br>How severe is the itching? **Recorded scale value 0 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Anaphylaxis | 0.0001 |
| 6 | Do you have diffuse (widespread) muscle pain? **Yes** | SLE | 0.0001 |
| 7 | Have you traveled out of the country in the last 4 weeks? **No** | Anaphylaxis | 0.0001 |
| 8 | Have you ever had pneumonia? **Yes** | Pericarditis | 0.0001 |
| 9 | Have you been coughing up blood? **Yes** | SLE | 0.0004 |
| 10 | Do you drink alcohol excessively or do you have an addiction to alcohol? **Yes** | SLE | 0.0000 |
| 11 | Do you have a cough? **Yes** | SLE | 0.0001 |
| 12 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **a knife stroke**<br>Do you feel pain somewhere? **side of the chest(L); upper chest; breast(R); posterior chest wall(L)**<br>How intense is the pain? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 4 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Anaphylaxis | 0.0004 |
| 13 | Do you have a cough that produces colored or more abundant sputum than usual? **Yes** | Pulmonary neoplasm | 0.0010 |
| 14 | Do you have heart failure? **Yes** | Pericarditis | 0.0000 |
| 15 | Do you have a chronic obstructive pulmonary disease (COPD)? **Yes** | Anaphylaxis | 0.0006 |
