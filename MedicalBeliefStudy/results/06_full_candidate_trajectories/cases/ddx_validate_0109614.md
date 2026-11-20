# ddx_validate_0109614

源标签：**Pulmonary embolism**；参考首位：**Pulmonary embolism**。

![轨迹](ddx_validate_0109614.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Have you been coughing up blood? **Yes** | Ebola | 0.0000 |
| 1 | Have you ever had deep vein thrombosis (DVT)? **Yes** | Ebola | 0.4989 |
| 2 | Have you had surgery within the last month? **Yes** | Ebola | 0.4981 |
| 3 | Have you traveled out of the country in the last 4 weeks? **No** | Ebola | 0.4990 |
| 4 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **a knife stroke; sharp**<br>Do you feel pain somewhere? **side of the chest(R); side of the chest(L); scapula(R); posterior chest wall(R); posterior chest wall(L)**<br>How intense is the pain? **Recorded scale value 9 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **side of the chest(R); side of the chest(L); scapula(R); scapula(L); posterior chest wall(R)**<br>How precisely is the pain located? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 7 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Boerhaave | 0.0495 |
| 5 | Do you have swelling in one or more areas of your body? **Yes**<br>Where is the swelling located? **calf(R); calf(L)** | Boerhaave | 0.1431 |
| 6 | Do you currently take hormones? **Yes** | Boerhaave | 0.0034 |
| 7 | Do you have an active cancer? **Yes** | Boerhaave | 0.0192 |
| 8 | Did you lose consciousness? **Yes** | Boerhaave | 0.0118 |
