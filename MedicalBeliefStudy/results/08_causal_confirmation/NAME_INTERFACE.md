# 疾病名与自由诊断控制：预定24例

病例在观察模型结果之前按哈希选定，使用基础顺序终点。移除候选列表，评分49个规范疾病名加EOS的完整序列概率，并单列每token平均分；另贪心生成最多64token的自由诊断。每例用完整前向核对一条候选的缓存序列分数。

| 指标 | 病例比例 [95%区间] |
|---|---|
| 编码接口命中标签 | 4.17% [0.00, 12.50] |
| 完整疾病名序列评分命中标签 | 33.33% [16.67, 54.17] |
| 每token平均评分命中标签 | 37.50% [20.83, 58.33] |
| 编码与完整疾病名首选一致 | 4.17% [0.00, 12.50] |
| 完整序列与每token平均首选一致 | 58.33% [37.50, 79.17] |

自由输出有21/24未严格匹配规范疾病名；未匹配不自动算医学错误，以下保留完整文本。两个接口还同时改变候选列表与输出形式，因此测量的是接口稳健性，并非只隔离字母效应。

| 病例 | 标签 | 编码首选 | 名称序列首选 | 自由诊断 |
|---|---|---|---|---|
| ddx_validate_0000493 | Pulmonary embolism | Boerhaave | Pulmonary embolism |  **Acute myocardial infarction (AMI)**. |
| ddx_validate_0006948 | URTI | Myasthenia gravis | Cluster headache |  **Muscle pain with sore throat**. |
| ddx_validate_0021109 | Guillain-Barré syndrome | Cluster headache | Guillain-Barré syndrome |  **Multiple sclerosis (MS)**. |
| ddx_validate_0021192 | Atrial fibrillation | Pericarditis | Unstable angina |  **Atrial Fibrillation with Heart Failure**. |
| ddx_validate_0024213 | Acute otitis media | Acute otitis media | Acute otitis media |  **Acute otitis media**. |
| ddx_validate_0025292 | Spontaneous pneumothorax | Acute otitis media | Pulmonary embolism |  **Pneumothorax**. |
| ddx_validate_0027808 | GERD | Boerhaave | Spontaneous pneumothorax |  **Gastroesophageal Reflux Disease (GERD)**. |
| ddx_validate_0029473 | Cluster headache | Scombroid food poisoning | Cluster headache |  **Cluster headache**. |
| ddx_validate_0030584 | SLE | Anaphylaxis | Sarcoidosis |  **Erythema multiforme**. |
| ddx_validate_0036829 | Myasthenia gravis | Localized edema | Myasthenia gravis |  **Multiple sclerosis (MS)**. |
| ddx_validate_0038557 | Bronchitis | Acute COPD exacerbation / infection | Pneumonia |  **Acute Bronchitis**. |
| ddx_validate_0049731 | GERD | Tuberculosis | Pulmonary embolism |  Gastroesophageal Reflux Disease (GERD) with upper abdominal pain and associated symptoms. |
| ddx_validate_0054038 | Viral pharyngitis | Acute laryngitis | Epiglottitis |  Tonsillitis. |
| ddx_validate_0070577 | GERD | Boerhaave | Pulmonary embolism |  **Gastroesophageal Reflux Disease (GERD)**  **Explanation**: The patient has multiple features consistent with GERD: - **Burning sensation starting in the stomach and going up into the throat** (E_213). - **Epigastric pain** (E_215 |
| ddx_validate_0077267 | Guillain-Barré syndrome | Acute laryngitis | Guillain-Barré syndrome |  **Multiple sclerosis (MS)**. |
| ddx_validate_0081578 | Bronchitis | Bronchospasm / acute asthma exacerbation | Pneumonia |  **Pneumonia**. |
| ddx_validate_0082663 | Anemia | Boerhaave | Pulmonary embolism |  **Deep vein thrombosis (DVT)**. |
| ddx_validate_0083651 | HIV (initial infection) | Cluster headache | Sarcoidosis |  **Lymphadenopathy with systemic symptoms** (based on fever, fatigue, swollen lymph nodes, and generalized muscle pain). |
| ddx_validate_0086034 | Acute dystonic reactions | Cluster headache | Myasthenia gravis |  **Essential Tremor**. |
| ddx_validate_0088111 | Anemia | Acute pulmonary edema | Pulmonary embolism |  **Pregnancy-related syndrome with systemic symptoms**.  **Explanation**: The patient presents with multiple systemic symptoms consistent with pregnancy, including:  - **Pain** (back of head, temple) and **dizziness** (lightheadedness, feeling like about to faint). - **Fatigue** (so |
| ddx_validate_0090190 | Viral pharyngitis | Acute otitis media | Viral pharyngitis |  Pharyngitis. |
| ddx_validate_0100269 | Acute otitis media | Larygospasm | Acute otitis media |  Otitis externa (external otitis) with acute ear infection. |
| ddx_validate_0103610 | GERD | Tuberculosis | Sarcoidosis |  Gastroesophageal Reflux Disease (GERD) with chronic symptoms. |
| ddx_validate_0114238 | Acute otitis media | Pericarditis | Acute rhinosinusitis |  Acute appendicitis. |

[完整表](name_interface_cases.csv) · [精确结果](name_interface_summary.json)
