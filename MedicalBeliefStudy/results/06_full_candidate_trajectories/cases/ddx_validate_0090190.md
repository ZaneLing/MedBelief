# ddx_validate_0090190

源标签：**Viral pharyngitis**；参考首位：**Viral pharyngitis**。

![轨迹](ddx_validate_0090190.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have nasal congestion or a clear runny nose? **Yes** | Acute otitis media | 0.0001 |
| 1 | Have you been in contact with a person with similar symptoms in the past 2 weeks? **Yes** | Ebola | 0.0000 |
| 2 | Are you immunosuppressed? **Yes** | Acute rhinosinusitis | 0.0000 |
| 3 | Have you traveled out of the country in the last 4 weeks? **No** | Acute otitis media | 0.0000 |
| 4 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **burning**<br>Do you feel pain somewhere? **tonsil(R); tonsil(L); thyroid cartilage; palace; pharynx**<br>How intense is the pain? **Recorded scale value 8 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Viral pharyngitis | 0.4165 |
| 5 | Do you have a fever (either felt or measured with a thermometer)? **Yes** | Acute otitis media | 0.0001 |
| 6 | Do you attend or work in a daycare? **Yes** | Acute otitis media | 0.0071 |
