# ddx_validate_0093737

源标签：**URTI**；参考首位：**Pneumonia**。

![轨迹](ddx_validate_0093737.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **tedious; sensitive; heavy**<br>Do you feel pain somewhere? **forehead; cheek(R); cheek(L); occiput; temple(R)**<br>How intense is the pain? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 2 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Acute otitis media | 0.0000 |
| 1 | Do you have a cough that produces colored or more abundant sputum than usual? **Yes** | Pneumonia | 0.0000 |
| 2 | Do you have diffuse (widespread) muscle pain? **Yes** | Ebola | 0.0005 |
| 3 | Do you live with 4 or more people? **Yes** | Ebola | 0.0005 |
| 4 | Do you have a fever (either felt or measured with a thermometer)? **Yes** | Ebola | 0.0239 |
| 5 | Have you traveled out of the country in the last 4 weeks? **No** | Ebola | 0.0053 |
| 6 | Do you smoke cigarettes? **Yes** | Ebola | 0.0035 |
| 7 | Do you have nasal congestion or a clear runny nose? **Yes** | Ebola | 0.0008 |
| 8 | Are you exposed to secondhand cigarette smoke on a daily basis? **Yes** | Ebola | 0.0007 |
