# ddx_validate_0045404

源标签：**Pancreatic neoplasm**；参考首位：**Pancreatic neoplasm**。

![轨迹](ddx_validate_0045404.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **sensitive**<br>Do you feel pain somewhere? **belly**<br>How intense is the pain? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **nowhere**<br>How precisely is the pain located? **Recorded scale value 5 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 0 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Cluster headache | 0.0000 |
| 1 | Are you significantly overweight compared to people of the same height as you? **Yes** | Cluster headache | 0.0000 |
| 2 | Do you have chronic pancreatitis? **Yes** | Cluster headache | 0.0375 |
| 3 | Do you have any lesions, redness or problems on your skin that you believe are related to the condition you are consulting for? **Yes**<br>What color is the rash? **yellow**<br>Do your lesions peel off? **No**<br>Is the rash swollen? **Recorded scale value 0 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Where is the affected region located? **epigastric**<br>How intense is the pain caused by the rash? **Recorded scale value 0 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Is the lesion (or are the lesions) larger than 1cm? **Yes**<br>How severe is the itching? **Recorded scale value 4 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Boerhaave | 0.0007 |
| 4 | Do you constantly feel fatigued or do you have non-restful sleep? **Yes** | Cluster headache | 0.0006 |
| 5 | Do you smoke cigarettes? **Yes** | GERD | 0.0000 |
| 6 | Are there members of your family who have been diagnosed with pancreatic cancer? **Yes** | Pancreatic neoplasm | 0.5000 |
| 7 | Do you have a cough? **Yes** | Acute rhinosinusitis | 0.5000 |
| 8 | Do you have diabetes? **Yes** | Acute rhinosinusitis | 0.5000 |
| 9 | Have you traveled out of the country in the last 4 weeks? **No** | Acute rhinosinusitis | 0.4920 |
| 10 | Have you had diarrhea or an increase in stool frequency? **Yes** | Acute rhinosinusitis | 0.4977 |
