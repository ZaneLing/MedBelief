# ddx_validate_0023832

源标签：**Bronchitis**；参考首位：**Bronchitis**。

![轨迹](ddx_validate_0023832.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **burning**<br>Do you feel pain somewhere? **lower chest; breast(L)**<br>How intense is the pain? **Recorded scale value 3 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 3 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Cluster headache | 0.0014 |
| 1 | Have you traveled out of the country in the last 4 weeks? **No** | Cluster headache | 0.1222 |
| 2 | Do you have a cough? **Yes** | URTI | 0.2958 |
| 3 | Are your vaccinations up to date? **Yes** | Inguinal hernia | 0.0089 |
| 4 | Do you have a chronic obstructive pulmonary disease (COPD)? **Yes** | Acute COPD exacerbation / infection | 0.4301 |
| 5 | Are you experiencing shortness of breath or difficulty breathing in a significant way? **Yes** | Acute COPD exacerbation / infection | 0.3533 |
| 6 | Do you have a cough that produces colored or more abundant sputum than usual? **Yes** | Acute COPD exacerbation / infection | 0.4274 |
