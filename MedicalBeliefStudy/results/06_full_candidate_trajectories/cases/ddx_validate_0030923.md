# ddx_validate_0030923

源标签：**GERD**；参考首位：**GERD**。

![轨迹](ddx_validate_0030923.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **sensitive; burning; sickening**<br>Do you feel pain somewhere? **lower chest; upper chest; hypochondrium(R); hypochondrium(L); epigastric**<br>How intense is the pain? **Recorded scale value 7 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **lower chest; upper chest**<br>How precisely is the pain located? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Acute otitis media | 0.0203 |
| 1 | Do you have a burning sensation that starts in your stomach then goes up into your throat, and can be associated with a bitter taste in your mouth? **Yes** | GERD | 0.5000 |
| 2 | Have you traveled out of the country in the last 4 weeks? **No** | Acute otitis media | 0.4963 |
| 3 | Have you recently thrown up blood or something resembling coffee beans? **Yes** | Acute otitis media | 0.5000 |
| 4 | Do you have a hiatal hernia? **Yes** | GERD | 0.5000 |
| 5 | Do you have symptoms that get worse after eating? **Yes** | GERD | 0.5000 |
| 6 | Do you have a cough? **Yes** | GERD | 0.5000 |
