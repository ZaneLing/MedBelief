# ddx_validate_0107153

源标签：**Spontaneous pneumothorax**；参考首位：**Spontaneous pneumothorax**。

![轨迹](ddx_validate_0107153.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Are you experiencing shortness of breath or difficulty breathing in a significant way? **Yes** | Acute pulmonary edema | 0.0000 |
| 1 | Do you have pain that is increased when you breathe in deeply? **Yes** | Localized edema | 0.0000 |
| 2 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **heartbreaking**<br>Do you feel pain somewhere? **lower chest; side of the chest(R); side of the chest(L); breast(R); breast(L)**<br>How intense is the pain? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Pericarditis | 0.0005 |
| 3 | Have you traveled out of the country in the last 4 weeks? **No** | Pericarditis | 0.0000 |
| 4 | Have any of your family members ever had a pneumothorax? **Yes** | Pericarditis | 0.3802 |
| 5 | Have you ever had a spontaneous pneumothorax? **Yes** | Pericarditis | 0.0981 |
| 6 | Do you smoke cigarettes? **Yes** | Pericarditis | 0.0063 |
| 7 | Do you have symptoms that are increased with physical exertion but alleviated with rest? **Yes** | Pericarditis | 0.0442 |
| 8 | Do you have a chronic obstructive pulmonary disease (COPD)? **Yes** | Pericarditis | 0.0000 |
