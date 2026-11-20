# 阶段2：完整数字表

本表由已完成的原始记录生成；主要解释见[通俗报告](PHASE2_READ_FIRST.md)。病例变体不等于独立患者。

| 运行 | 记录数 | 正确数 | 未产生可判分答案 | 生成词元数 |
|---|---:|---:|---:|---:|
| phase2_initial_4b | 24 | 24 | 0 | 11792 |
| phase2_pilot_4b | 360 | 359 | 0 | 196461 |
| phase2_bp_repair_dev | 80 | 77 | 0 | 55288 |
| phase2_bp_repair_confirm | 80 | 75 | 0 | 55471 |
| phase2b_initial_4b | 16 | 15 | 0 | 5398 |
| phase2b_confirm_4b | 288 | 284 | 0 | 122022 |
| phase2c_answer_control_4b | 64 | 64 | 0 | 32522 |
| phase2d_partial_fact_4b | 48 | 48 | 0 | 22387 |

合计960条记录，42个数值病例骨架，752份内部状态。API支出0美元。

## 历史对照

| 组别 | 范围 | 保留判断后更差的配对数 | 更好的配对数 | 配对数 | 错误率差，百分点 | 病例重采样95%区间，百分点 |
|---|---|---:|---:|---:|---:|---|
| phase2a old_judgment_effect | primary_aki_dvt | 1 | 0 | 96 | 1.04 | 0.00—3.12 |
| phase2a old_judgment_effect | diagnostic_bp | 0 | 0 | 48 | 0.00 | 0.00—0.00 |
| phase2b old_judgment_effect | primary_aki_dvt | 2 | 0 | 96 | 2.08 | 0.00—5.21 |
| phase2b raw_answer_effect | primary_aki_dvt | 0 | 0 | 48 | 0.00 | 0.00—0.00 |

零宽度区间来自小样本中所有差值恰好为零，不是总体等效性证明。

## 血压修正

| 组别 | 方法 | 报告可用 | 报告不可用 |
|---|---|---:|---:|
| development | baseline | 8/8 | 8/8 |
| development | binding | 7/8 | 8/8 |
| development | numbers | 8/8 | 6/8 |
| development | quality_wording | 8/8 | 8/8 |
| development | source | 8/8 | 8/8 |
| confirmation | baseline | 8/8 | 7/8 |
| confirmation | binding | 8/8 | 8/8 |
| confirmation | numbers | 8/8 | 6/8 |
| confirmation | quality_wording | 7/8 | 8/8 |
| confirmation | source | 7/8 | 8/8 |

## 内部读出：预定最后一层

| 数据 | 目标 | 内部向量 | 词和数字 | 字符片段 |
|---|---|---:|---:|---:|
| readout_last_layer_2a | current_report_numerical_direction | 63.3% | 50.0% | 65.0% |
| readout_last_layer_2a | current_report_usable | 99.4% | 100.0% | 100.0% |
| readout_last_layer_2a | old_report_numerical_direction | 71.9% | 75.0% | 71.9% |
| readout_last_layer_2a | old_report_direction_facts_only | 58.3% | 50.0% | 68.8% |
| readout_last_layer_transfer | current_report_numerical_direction | 53.8% | 57.5% | 63.7% |
| readout_last_layer_transfer | current_report_usable | 68.4% | 50.0% | 50.0% |
| readout_last_layer_transfer | old_report_numerical_direction | 54.2% | 75.0% | 61.5% |
| readout_last_layer_transfer | old_report_direction_facts_only | 51.0% | 59.4% | 62.5% |

## 最终答案相同的对照

| 训练范围 | 是否有替代报告 | 内部向量 | 词和数字 | 字符片段 |
|---|---|---:|---:|---:|
| all_2a_histories | no_backup | 75.0% | 50.0% | 0.0% |
| all_2a_histories | backup_present | 81.2% | 50.0% | 50.0% |
| 2a_current_only | no_backup | 53.1% | 50.0% | 50.0% |
| 2a_current_only | backup_present | 68.8% | 50.0% | 50.0% |

## 读出方法修正：未见病例结果

| 训练方法 | 替代报告 | 内部向量 | 词和数字 | 字符片段 |
|---|---|---:|---:|---:|
| train_2a_2b_test_2c | no_backup | 56.2% | 50.0% | 50.0% |
| train_2a_2b_test_2c | backup_present | 84.4% | 50.0% | 50.0% |
| train_2c_half_test_other_half | no_backup | 100.0% | 100.0% | 100.0% |
| train_2c_half_test_other_half | backup_present | 100.0% | 100.0% | 100.0% |

## 正确局部事实的跨任务复查

| 任务 | 说明 | 报告可用 | 报告不可用 |
|---|---|---:|---:|
| aki | baseline | 6/6 | 6/6 |
| aki | numbers | 6/6 | 6/6 |
| dvt | baseline | 6/6 | 6/6 |
| dvt | numbers | 6/6 | 6/6 |
