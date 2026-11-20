# 来源文本复核与运行修正

初始正则审计漏掉了“图在下方”等引用。确认运行至第130例时，候选首字符的引号触发分词断言，查看该病例也暴露了未提供的X光图。随后只根据源文本复核材料引用、无报告的检查，以及被当成新事实的题干尾语；不读取模型答案来决定排除。原880例、训练、开发选择和400例确认全部保留，另外报告严格子集。

| 本实验分组 | 原样本 | 来源复核保留 | 再排除相似度≥0.80病例（含确认集内部重复） |
|---|---:|---:|---:|
| train | 400 | 391 | 391 |
| development | 80 | 75 | 75 |
| confirmation | 400 | 386 | 366 |

相似度复核是新的敏感性分析，不更改原来的全库0.90去重，也不宣称所有语义近重复已经排除。确认集内部也按病例散列顺序、同一0.80阈值贪心去重。训练/开发中的来源问题仍属于本次训练与选型记录；本轮没有重新训练一个声称完全清洁的模型。带有“如下”的实验室表格若数据在后文实际提供，保持纳入。

## 标记的源文本

### medqa_train_06823（confirmation，missing_referenced_material）

A 40-year-old chronic smoker presents to the office complaining of a cough and pleuritic chest pain.

He also has had pain in his right shoulder for the past 2 weeks.

He denies fever, night sweats, but has noticed a 2.2 kg (5 lb) weight loss in the last month.

He has no recent history of travel.

Past medical history is unremarkable.

On cardiopulmonary examination, bilateral velcro-like crackles are auscultated in the upper to middle lung fields, with normal heart sounds.

There is a 3 x 3 cm swelling on the right shoulder with a normal range of motion and intact sensation.

5/5 muscular strength in all extremities is noted.

Chest X-ray reveals bilateral nodular opacities in the upper lung lobes and a lytic lesion on the right humeral head.

Electron microscopy of the lung biopsy shows the following.

### medqa_train_05721（confirmation，missing_referenced_material）

A 4-year-old boy presents with a recent history of frequent falls.

The images below depict his movements when he tries to get up from the floor.

### medmcqa_train_2034031b-c816-400f-bc77-9e7cfbb73c19（confirmation，missing_referenced_material）

A 7-year-old child from West Bengal presented with high grade fever with chills and rigor.

Peripheral smear examination revealed Plasmodium vivax.

He was given treatment for the same.

But he again presented with jaundice, and a repeat peripheral smear showed following.

### medmcqa_train_6dd7cc2c-1704-4e8f-aa1b-fb30c061f8c9（confirmation，missing_referenced_material）

A 4-year-old boy presents with recurrent fractures, hyperextensible joints and hearing problems.

His X-ray of lower limbs show the following.

### medmcqa_train_1bba25d9-7512-458e-b47c-65a5a78c975f（confirmation，missing_referenced_material）

A 40-year-old immunocompromised patient presented with complaints of dysphagia.

Upper GI endoscopy showed multiple serpiginous ulcers in the distal esophagus.

Biopsy from the esophagus showed the following.

### medmcqa_train_87f606b2-8e1c-423e-9a9c-8c887c4c4323（confirmation，missing_referenced_material）

A 50-year-old man complains of swelling of the neck and shoness of breath for 7 days.

He has noticed some nasal stuffiness with hoarseness of his voice for about 4 weeks and had attributed these symptoms to an upper respiratory infection.

He denies the use of alcohol but has smoked two packs of cigarettes per day for 35 years.

Lately, he feels as though something is pushing against his throat.

On physical examination, the patient's face appears ruddy and swollen.

The jugular veins are distended.

Following sign is observed in the patient.

Chest x ray was done with the following findings.

### medmcqa_train_202cb4ea-c9ef-4e19-868c-eaae7fca2262（confirmation，missing_referenced_material）

An 8-year-old child presents with the history of cough for 7 months.

He also gives a history of hemoptysis for 1 month and fever for 4 days.

The X-ray is given below.

### medqa_train_04038（confirmation，missing_referenced_material）

An 18-month-old girl is brought to the emergency room by her mother because of wheezing for 1 day.

The baby has never had similar symptoms.

She also has a runny nose and a cough.

She is not feeding well.

Her immunizations are up-to-date.

Her rectal temperature is 38.8°C (101.8°F), the heart rate is 120/min, and the respiratory rate is 23/min.

On examination, a clear nasal discharge is noticed with intercostal retractions.

Chest auscultation reveals bilateral fine rales and diffuse fine wheezing.

A chest X-ray is given in the exhibit.

### medqa_train_01503（confirmation，procedure_without_report）

A 34-year-old woman presents to the emergency department with moderate right wrist pain after falling on her outstretched hand.

She has numbness in the 3 medial digits.

The patient has no known previous medical conditions.

Her family history is not pertinent, and she currently takes no medications.

Physical examination shows her blood pressure is 134/82 mm Hg, the respirations are 14/min, the pulse is 87/min, and the temperature is 36.7°C (98.0°F).

When asked to make a fist, the patient is able to flex only the lateral 2 digits.

Tapping the anterior portion of her wrist elicits tingling in the medial 3 digits.

The patient is taken to get an X-ray.

### medqa_train_07093（confirmation，task_only_evidence_round）

A 63-year-old woman presents to your outpatient clinic complaining of headaches, blurred vision, and fatigue.

She has a blood pressure of 171/91 mm Hg and heart rate of 84/min.

Physical examination is unremarkable.

Her lab results include K+ of 3.1mEq/L and a serum pH of 7.51.

Of the following,

### medqa_train_05615（confirmation，task_only_evidence_round）

A 34-year-old woman with no significant prior medical history presents to the clinic with several days of bloody stool.

She also complains of constipation and straining, but she has no other symptoms.

She has no family history of colorectal cancer or inflammatory bowel disease.

She does not smoke or drink alcohol.

Her vital signs are as follows: blood pressure is 121/81 mm Hg, heart rate is 77/min, and respiratory rate is 15/min.

There is no abdominal discomfort on physical exam, and a digital rectal exam reveals bright red blood.

Of the following,

### medmcqa_train_673357fb-4a08-4e56-b846-b67c0cb8ec3b（confirmation，missing_referenced_material）

A 50 yr. old male presented with chronic breathlessness and intermittent jaundice.

He denies smoking and alcohol abuse.

Lung and liver specimens revealed the following findings respectively

### medmcqa_train_b980ef1f-f337-435c-8922-82b0b58535a4（confirmation，missing_referenced_material）

A 2-year-old child presented with recurrent pain abdomen, failure to thrive and iron deficiency anemia refractory to Iron therapy.

His anti TTG anti-body titres were 300 U/L.

An upper GI endoscopy was done and duodenal biopsy was taken which showed the following.

### medqa_train_06038（confirmation，procedure_without_report）

A 45-year-old woman presents to the office because of shortness of breath and chest tightness on exertion which she noticed for the past 2 months.

She was diagnosed with asthma 1 month ago but says that the asthma medication has not improved her breathing.

She does not smoke and works as a hotel manager.

Examination shows mildly jaundiced conjunctivae, several spider nevi on her upper torso, and a barrel-chested appearance.

A chest X-ray is obtained.

### medmcqa_validation_ccca9015-2ce5-40cf-bed4-187f9428d984（development，missing_referenced_material）

A 55 yr old patient presented to the opd with complaint of pain in back.

On examination his limbs seemed to be bent with overlying warm and thick skin.

Patient also complain of decreased hearing over a few days.

On biochemical analysis his serum ALP was raised.

X-ray obtained showed the following features.

### medmcqa_train_b8f2180c-8e26-45df-8306-66865eae4bc1（development，missing_referenced_material）

A teenager has a progressively increasing soft reddish swelling on his chest.

Its histological appearance is given below.

### medmcqa_train_e20b8e6c-221c-4b87-9876-378740bb8cea（development，task_only_evidence_round）

A 36-year-old man presents to his primary care physician complaining of painless enlargement of the testis.

Fuher laboratory studies reveal an increase in serum hCG.

Of the following,

### medmcqa_train_7cf6e2d1-35af-4b06-a98e-789e5ed50f80（development，missing_referenced_material）

A 25 years old female presented with a complaint of acute pain in the abdomen for the past 12 hours.

On examination, there is severe tenderness in the right iliac fossa.

The patient denied any history of tuberculosis.

On CBC, neutrophil count appears to be raised.

The X-ray of the abdomen did not show any evidence of bowel obstruction.

An ultrasound abdomen was performed and given below.

### medmcqa_train_fcdea38d-dcee-4c77-866c-136e55daf419（development，missing_referenced_material）

Newborn male baby presented with congestive heart failure.

On examination enlarged fontanelles, a loud cranial bruit and following radiological finding was noted -

### medmcqa_train_1701b45f-25de-4c77-9166-a843d1af0844（train，missing_referenced_material）

An x-ray of an asymptomatic 64- year-old male executive coming in for his regular annual medical checkup.

He had an anterior Q wave MI 4 years ago.

### medqa_dev_00188（train，procedure_without_report）

A 44-year-old man presents to the emergency department due to sudden chest pain and difficulty breathing for the past 3 hours.

The pain is felt in the retrosternal area and radiates up to his left shoulder and arm; it worsens on inspiration, and is relieved when he is leaning forward.

His heart rate is 61/min, respiratory rate is 16/min, temperature is 36.5°C (97.7°F), and blood pressure is 115/78 mm Hg.

Physical examination shows no abnormalities.

Pericardial friction rub is heard on auscultation.

Laboratory results show elevated erythrocyte sedimentation rate (ESR) and C-reactive protein (CRP) levels.

An ECG is performed.

### medmcqa_train_d974f874-5222-4597-b7ff-5377c3cec88b（train，missing_referenced_material）

40-year-old immunocompromized patient presented with complaints of dysphagia.

UGI scopy showed multiple ulcers in the distal esophagus.

Biopsy from the esophagus showed the following.

### medmcqa_train_56aa938d-40f2-4917-9866-8bc915c61f90（train，missing_referenced_material）

40 year-old immunocompromized came with C/o dysphagia.

UGI scopy showed multiple ulcers in the distal esophagus.

Biopsy from the esophagus showed the following.

### medmcqa_train_cd4d2102-2c63-4399-8b39-de47f52bf8bf（train，missing_referenced_material）

A 3-year-old child presented with anemia and thrombocytopenia.

On examination, there was massive splenomegaly.

A bone marrow aspiration revealed the following cells.

### medmcqa_train_e4498791-b38f-49c4-b7bf-3287bdd4ab47（train，missing_referenced_material）

A 60 yr old lady presented with mild hearing loss & pulsatile tinnitus of right ear.

Otoscopy revealed following findings.

### medmcqa_train_7cffb021-2110-41d1-963f-50936f881550（train，missing_referenced_material）

A 76 year old male with a history of dyspnoea on exeion was subjected to x-ray chest by the treating physician.

The findings on the chest X-ray are given below.

There is a history of fever with significant loss of weight and occasional bloody diarrhoea for the past 3 months.

### medmcqa_train_e0ca5a07-a1ad-499c-a92d-719a7ff1af01（train，missing_referenced_material）

A mother brings her child to clinic with short stature.

On examination following physical findings are seen.

Doctor advises for the below investigations.

Calcium - Normal, Phosphorous - Increased, PTH - Increased, Alvaline Phosphatase - Increased.

### medmcqa_train_6c36cef4-fde7-41c9-8412-c9ad468514a7（train，missing_referenced_material）

5-year old male child presented to AIIMS pediatrics OPD with severe transfusion requiring anemia and Jaundice.

On examination Liver and spleen were palpable 5 cm below the costal margin.

Peripheral smear analysis showed the following?

## 分词修正

[修正清单](TOKENIZATION_AMENDMENT.json)保留原提示文本和词元；只在候选文本跨越已固定JSON前缀发生BPE合并时，把后续字符串作为续写单独编码。全880例×3种历史核查，只有一例的一个候选受影响；先前129例共258个回答的提示与续写编码均不变。原核心、解码器、模型权重和已冻结的方案选择不变。
