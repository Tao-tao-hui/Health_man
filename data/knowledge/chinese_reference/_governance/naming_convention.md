# 命名规范

## 文件命名模板

| 类型 | 模板 | 示例 |
|------|------|------|
| 数据集目录 | `{layer}_{source}_{cycle}_{type}` | `A_nhanes_2017_2020_demographics` |
| 原始文件 | `{source}_{table}_{cycle}.{ext}` | `nhanes_demo_j_2017.xpt` |
| 处理后文件 | `{source}_{domain}_{cycle}.parquet` | `nhanes_body_composition_2017.parquet` |
| 元数据 L0 | `{source}_{cycle}_L0_card.json` | `nhanes_2017_2020_L0_card.json` |
| 元数据 L1 | `{source}_{cycle}_L1_fields.json` | `nhanes_2017_2020_L1_fields.json` |
| 元数据 L2 | `{source}_{cycle}_L2_usage.md` | `nhanes_2017_2020_L2_usage.md` |

## 字段命名

- snake_case 英文
- 单位后缀：`_cm`, `_kg`, `_pct`, `_bpm`, `_ms`
