# ddx_validate_0025047

源标签：**Pancreatic neoplasm**；参考首位：**Bronchitis**。

![轨迹](ddx_validate_0025047.png)

实线为两个编码的平均分，阴影为两编码范围；逐层热图为原始投影，注意力曲线为晚5层均值。终点评价使用三个编码，可能与此处两编码轨迹不同。

| 轮 | 新证据（原始英文） | 当前首选 | 标签支持 |
|---|---|---|---|
| 0 | Do you have any lesions, redness or problems on your skin that you believe are related to the condition you are consulting for? **Yes**<br>What color is the rash? **yellow**<br>Do your lesions peel off? **No**<br>Is the rash swollen? **Recorded scale value 0 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Where is the affected region located? **epigastric**<br>How intense is the pain caused by the rash? **Recorded scale value 3 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Is the lesion (or are the lesions) larger than 1cm? **Yes**<br>How severe is the itching? **Recorded scale value 3 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Inguinal hernia | 0.0002 |
| 1 | Do you have a cough? **Yes** | HIV (initial infection) | 0.0000 |
| 2 | Have you had an involuntary weight loss over the last 3 months? **Yes** | HIV (initial infection) | 0.0001 |
| 3 | Are there members of your family who have been diagnosed with pancreatic cancer? **Yes** | Pancreatic neoplasm | 0.5000 |
| 4 | Do you smoke cigarettes? **Yes** | Pancreatic neoplasm | 0.5000 |
| 5 | Have you traveled out of the country in the last 4 weeks? **No** | Pancreatic neoplasm | 0.5000 |
| 6 | Do you have pain somewhere, related to your reason for consulting? **Yes**<br>Characterize your pain: **a cramp**<br>Do you feel pain somewhere? **hypochondrium(L); epigastric**<br>How intense is the pain? **Recorded scale value 6 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>Does the pain radiate to another location? **thoracic spine**<br>How precisely is the pain located? **Recorded scale value 1 on the dataset's 0-10 scale; endpoint meanings are unspecified**<br>How fast did the pain appear? **Recorded scale value 1 on the dataset's 0-10 scale; endpoint meanings are unspecified** | Pancreatic neoplasm | 0.5000 |
