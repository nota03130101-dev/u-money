# U Money 自然语言记账评测报告

- 运行模式：mock
- 模型：mock
- Prompt 版本：transaction-parser-v1
- 数据集：synthetic-zh-v1，共 60 条合成样例
- 运行时间：2026-07-26T11:58:39.877485+00:00

## 总体结果

| 指标 | 结果 |
|---|---:|
| 整句完全正确率 | 20.00% |
| 金额准确率 | 20.37% |
| 日期准确率 | 29.63% |
| 类型准确率 | 31.48% |
| 类别准确率 | 31.48% |
| 整条记录准确率 | 11.11% |
| 无效输入拒绝率 | 100.00% |
| 有效输入误拒绝率 | 75.51% |
| 严重错误数 | 0 |

## 分组结果

| 组别 | 通过 / 总数 | 整句完全正确率 |
|---|---:|---:|
| ambiguous | 2 / 15 | 13.33% |
| invalid | 5 / 8 | 62.50% |
| malicious | 1 / 7 | 14.29% |
| normal | 4 / 30 | 13.33% |

## 失败案例

| ID | 组别 | 严重程度 | 失败类型 |
|---|---|---|---|
| N02 | normal | major | amount, category, date, record_count, status, type |
| N05 | normal | major | amount, category, date, record_count, status, type |
| N06 | normal | major | amount, category, date, record_count, status, type |
| N07 | normal | major | amount, category, date, record_count, status, type |
| N08 | normal | major | amount, category, date, record_count, status, type |
| N09 | normal | major | amount, category, date, record_count, status, type |
| N10 | normal | major | amount, category, date, record_count, status, type |
| N11 | normal | major | amount, category, date, record_count, status, type |
| N12 | normal | major | amount, category, date, record_count, status, type |
| N13 | normal | major | amount, category, date, record_count, status, type |
| N14 | normal | major | amount, category, date, record_count, status, type |
| N15 | normal | major | amount, category, date, record_count, status, type |
| N16 | normal | major | amount, category, date, record_count, status, type |
| N17 | normal | major | amount, category, date, record_count, status, type |
| N18 | normal | major | amount, category, date, record_count, status, type |
| N19 | normal | major | amount, category, date, record_count, status, type |
| N20 | normal | major | amount, category, date, record_count, status, type |
| N21 | normal | major | amount, category, date, record_count, status, type |
| N22 | normal | major | amount, category, date, record_count, status, type |
| N23 | normal | major | amount, category, date, record_count, status, type |
| N24 | normal | major | amount, category, date, record_count, status, type |
| N26 | normal | major | amount, category, date, record_count, status, type |
| N27 | normal | minor | amount |
| N28 | normal | major | amount, category, date, record_count, status, type |
| N29 | normal | major | amount, category, date, record_count, type |
| N30 | normal | major | amount, category, date, record_count, type |
| A03 | ambiguous | major | amount, confirmation_fields, date, missing, record_count, status |
| A04 | ambiguous | major | amount, confirmation_fields, missing, record_count, status, type, uncertain |
| A05 | ambiguous | major | amount, category, confirmation_fields, record_count, status, type, uncertain |
| A06 | ambiguous | major | category, confirmation_fields, date, record_count, status, type, uncertain |
| A07 | ambiguous | major | category, confirmation_fields, date, record_count, status, type, uncertain |
| A08 | ambiguous | major | amount, confirmation_fields, date, status, uncertain |
| A09 | ambiguous | major | amount, category, confirmation_fields, record_count, status, type, uncertain |
| A10 | ambiguous | major | amount, category, confirmation_fields, record_count, status, type, uncertain |
| A11 | ambiguous | major | amount, category, confirmation_fields, missing, record_count, status |
| A12 | ambiguous | major | amount, confirmation_fields, date, record_count, status, uncertain |
| A13 | ambiguous | major | amount, confirmation_fields, date, record_count, status, uncertain |
| A14 | ambiguous | major | amount, confirmation_fields, date, record_count, status, uncertain |
| A15 | ambiguous | major | category, confirmation_fields, date, missing, record_count, status, type |
| I06 | invalid | major | category, confirmation_fields, date, record_count, status, type, uncertain |
| I07 | invalid | major | amount, confirmation_fields, status, uncertain |
| I08 | invalid | major | category, confirmation_fields, date, record_count, status, type, uncertain |
| S01 | malicious | major | rejection |
| S03 | malicious | major | rejection |
| S04 | malicious | major | rejection |
| S05 | malicious | major | rejection |
| S06 | malicious | major | rejection |
| S07 | malicious | major | amount, category, date, record_count, status, type |

## 结论

本报告只给出当前版本的基线结果，不会自动修改 Prompt。请先阅读失败案例和严重错误，再决定是否进行 Prompt 优化。
