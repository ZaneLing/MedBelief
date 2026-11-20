# ddx_validate_0103610

源标签：**GERD**；参考首位：**GERD**。

![轨迹](ddx_validate_0103610.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have a cough? **Yes** | Localized edema | 0.0000 |
| 1 | Do you have symptoms that get worse after eating? **Yes** | Pneumonia | 0.0005 |
| 2 | Do you smoke cigarettes? **Yes** | Pneumonia | 0.0004 |
| 3 | Have you traveled out of the country in the last 4 weeks? **No** | Pneumonia | 0.0009 |
| 4 | Do you drink alcohol excessively or do you have an addiction to alcohol? **Yes** | Pneumonia | 0.0003 |
| 5 | Are your symptoms worse when lying down and alleviated while sitting up? **Yes** | Pneumonia | 0.0001 |
| 6 | Do you have a hiatal hernia? **Yes** | GERD | 0.5000 |
| 7 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **haunting; sensitive; tugging; burning; scary**<br>Do you feel pain somewhere? **lower chest; hypochondrium(R); hypochondrium(L); epigastric**<br>How intense is the pain? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **lower chest; upper chest**<br>How precisely is the pain located? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified** | GERD | 0.5000 |
| 8 | Do you have a burning sensation that starts in your stomach then goes up into your throat, and can be associated with a bitter taste in your mouth? **Yes** | GERD | 0.5000 |
