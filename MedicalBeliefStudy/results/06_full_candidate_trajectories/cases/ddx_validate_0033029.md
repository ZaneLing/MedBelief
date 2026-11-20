# ddx_validate_0033029

源标签：**Acute otitis media**；参考首位：**Bronchitis**。

![轨迹](ddx_validate_0033029.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Are you more irritable or has your mood been very unstable recently? **Yes** | Inguinal hernia | 0.0000 |
| 1 | Are your vaccinations up to date? **Yes** | Inguinal hernia | 0.0000 |
| 2 | Do you have a cough? **Yes** | Inguinal hernia | 0.0018 |
| 3 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **sensitive; sharp**<br>Do you feel pain somewhere? **ear(R); ear(L)**<br>How intense is the pain? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Ebola | 0.0030 |
| 4 | Are you currently being treated or have you recently been treated with an oral antibiotic for an ear infection? **Yes** | Acute otitis media | 0.4997 |
| 5 | Have you traveled out of the country in the last 4 weeks? **No** | Larygospasm | 0.4901 |
