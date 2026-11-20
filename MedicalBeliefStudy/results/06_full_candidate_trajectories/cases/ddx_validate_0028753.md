# ddx_validate_0028753

源标签：**Bronchitis**；参考首位：**Pneumonia**。

![轨迹](ddx_validate_0028753.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have a cough that produces colored or more abundant sputum than usual? **Yes** | Anemia | 0.0000 |
| 1 | Are your vaccinations up to date? **Yes** | Anemia | 0.0000 |
| 2 | Do you have a cough? **Yes** | Anemia | 0.0001 |
| 3 | Are you experiencing shortness of breath or difficulty breathing in a significant way? **Yes** | Anemia | 0.0004 |
| 4 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **sensitive; burning**<br>Do you feel pain somewhere? **lower chest; side of the chest(R); posterior chest wall(R)**<br>How intense is the pain? **Recorded scale value 4 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 3 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Anemia | 0.0018 |
| 5 | Do you have a chronic obstructive pulmonary disease (COPD)? **Yes** | Anemia | 0.0005 |
| 6 | Do you have a fever (either felt or measured with a thermometer)? **Yes** | Anemia | 0.0029 |
| 7 | Do you have a sore throat? **Yes** | Anemia | 0.0012 |
| 8 | Have you traveled out of the country in the last 4 weeks? **No** | Anemia | 0.0001 |
