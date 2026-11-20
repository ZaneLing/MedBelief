# ddx_validate_0117624

源标签：**Pericarditis**；参考首位：**Pericarditis**。

![轨迹](ddx_validate_0117624.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **a knife stroke; sharp**<br>Do you feel pain somewhere? **lower chest; upper chest; breast(R)**<br>How intense is the pain? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **posterior chest wall(R)**<br>How precisely is the pain located? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 9 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Boerhaave | 0.4446 |
| 1 | Do you have pain that is increased when you breathe in deeply? **Yes** | Pericarditis | 0.4967 |
| 2 | Are your symptoms worse when lying down and alleviated while sitting up? **Yes** | Pericarditis | 0.4999 |
| 3 | Are you experiencing shortness of breath or difficulty breathing in a significant way? **Yes** | Pericarditis | 0.4998 |
| 4 | Have you ever had a pericarditis? **Yes** | Boerhaave | 0.4523 |
| 5 | Have you traveled out of the country in the last 4 weeks? **No** | Boerhaave | 0.4993 |
| 6 | Have you recently had a viral infection? **Yes** | Pericarditis | 0.4993 |
| 7 | Do you feel your heart is beating fast (racing), irregularly (missing a beat) or do you feel palpitations? **Yes** | Boerhaave | 0.4789 |
