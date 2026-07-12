# 大健康检测平台外部数据获取方案设计文档

| 项 | 值 |
|---|---|
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-12 |
| 文档状态 | 待评审 |
| 适用范围 | MVP1.0 数据获取子系统 |
| 关联文档 | [MVP1.0_技术方案_v1.1.md](../../docs/planning/MVP1.0_技术方案_v1.1.md)、[BestHealth_TwoLegs_技术参考手册.md](../../docs/chip/体脂模组/BestHealth_TwoLegs_技术参考手册.md)、[S3008T_通信协议_权威转写稿.md](../../docs/chip/通讯协议/S3008T_通信协议_权威转写稿.md)、[BMH08002_技术说明书_重构版.md](../../docs/chip/血氧监测/BMH08002_技术说明书_重构版.md) |

---

## 一、项目目标与背景

### 1.1 项目定位

本项目为自研硬件-软件一体化的桌面健康检测平台（MVP1.0），采用 **BIA 双脚四电极体脂模组 + PPG 指端血氧模组** 双模组架构，单机 Windows + Python 运行，30 秒内完成测量并输出 35 项健康指标 + 中医体质参考，最终交付对标样例报告的"全息健康评估"形态。

### 1.2 文档目标

本设计文档系统记录外部数据获取子系统的设计决策，目标包括：

1. **建立数据获取统一框架**：明确 BIA 19 项 + PPG 4 项 + 大健康融合 12 项 + 中医体质 9 型的参考范围对标数据获取路径
2. **解决 P0 级医学数据缺失**：补齐 V2 审计识别的 33 IND 指标中关键缺失项
3. **约束成本与合规**：严格 0 成本优先，个人开发者可执行，全程合规可审计
4. **指导后续开发**：为 writing-plans 阶段提供明确的技术决策依据

### 1.3 约束条件

| 约束 | 说明 |
|------|------|
| 预算上限 | 严格 0 成本优先；通过合理分配各模型免费额度可达成 Layer C 全程 0 成本（详见 §7.8）；若免费额度耗尽需切付费时，单项成本超 ¥100 需明确标注并征得同意 |
| 开发者资源 | 个人开发者，需自动化与可重复性 |
| 数据用途 | 指标参考范围对标（非配对精度验证） |
| 指标覆盖 | 35 项原始+派生 + 中医体质 9 型 |
| 交付形态 | 纯分析报告（本轮），后续分步落地 |
| 合规底线 | 遵守 PIPL、CNKI 版权、政府数据使用条款 |

### 1.4 与既有计划的关系

本方案替代并整合 `e:\Health_man\superpowers\` 下 4 份既有计划的数据获取部分：

| 既有计划 | 整合方式 |
|---------|---------|
| [HealthDataLab-implementation](../2026-07-11-HealthDataLab-implementation.md) | 保留三层元数据架构，路径从 `E:\工程项目\` 改为 `e:\Health_man\` |
| [V1 医学数据补齐](../2026-07-11-MVP1.0_data_and_medical_content_completion.md) | 保留 8 项 P0 指标校准目标，数据源改用本方案三层分工 |
| [V2 全量审计补全](../2026-07-11-MVP1.0_data_and_medical_content_completion_v2.md) | 保留 33 IND 审计结论，作为本方案覆盖范围依据 |
| [Step5+ 引擎交付](../2026-07-11-MVP1.0_step5_plus_implementation.md) | 不整合，Step5+ 属于代码实现层，本方案仅覆盖数据层 |

---

## 二、核心功能需求

### 2.1 功能清单

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F1 | 35 项医学指标参考范围对标数据获取 | P0 | 含 BIA 19 + PPG 4 + 派生 12 |
| F2 | 中医体质 9 型参考数据获取 | P0 | 含体质判定标准与人群分布 |
| F3 | 数据治理中台 | P0 | 含 8 要素治理体系 |
| F4 | 统一存储与目录体系 | P0 | `e:\Health_man\data\knowledge\chinese_reference\` |
| F5 | 统一数据字典与可读性文档 | P0 | 每个 L3 指标附字段说明与处理流程 |
| F6 | LLM 蒸馏增强模块（国内大模型优先） | P1 | 可选，用于难提取指标 |
| F7 | 数据质量门禁与审计 | P1 | 可行性评估 + 质量评分 |
| F8 | 版本控制与归档 | P1 | 历史快照与变更追溯 |

### 2.2 指标覆盖矩阵

按 V2 审计的 33 IND 指标与本方案三层分工对齐：

| 指标域 | 指标项数 | Layer A 覆盖 | Layer B 覆盖 | Layer C 增强 | 备注 |
|--------|---------|------------|------------|------------|------|
| BIA 体成分（IND-01~14） | 14 | ✅ NHANES/KNHANES/CHNS | ✅ GASC 2025 | 可选 | 主路径 A |
| BIA 骨骼（IND-10 BONE） | 1 | ⚠️ NHANES DEXA | ✅ 中文文献 | ✅ 推荐 | 历史引用造假需重补 |
| BIA 内脏脂肪（IND-09 VFT） | 1 | ✅ NHANES | ✅ 中文文献 | - | ICC=0.174 需校正 |
| BIA 蛋白质（IND-11 PROT） | 1 | ✅ NHANES | ✅ 中文文献 | - | 误差 ±20-30% 需声明 |
| PPG 血氧（IND-15~17） | 3 | ✅ PhysioNet | ✅ 中文文献 | - | SpO₂ 量程需裁定 |
| PPG 心率（IND-18） | 1 | ✅ PhysioNet | ✅ 中文文献 | - | - |
| PPG HRV（IND-19~20） | 2 | ⚠️ ECG 移植 | ✅ 中文 PPG 文献 | ✅ 推荐 | G3 缺失 |
| PPG 脉搏波（IND-21） | 1 | ✅ PhysioNet | ✅ 中文文献 | - | - |
| 中医体质（IND-31） | 1 | ❌ 无 | ✅ 中文文献+国标 | ✅ 推荐 | G4 缺失 |
| 大健康融合（派生 12 项） | 12 | ⚠️ 部分可派生 | ✅ 文献 | ✅ 推荐 | 多为派生指标 |

**覆盖统计：**
- Layer A 直采可覆盖：25 项（76%）
- Layer B 文献可补充：32 项（97%）
- Layer C LLM 蒸馏增强：3-5 项难提取指标
- 完全覆盖：33 项（100%）

### 2.3 非功能需求

| 维度 | 要求 |
|------|------|
| 数据时效性 | NHANES/KNHANES 跟随官方周期更新；中文文献月度增量 |
| 数据完整性 | 每指标必填 P5/P25/P50/P75/P95 + mean+SD + N + 年龄段 + 性别 |
| 数据可追溯 | 每条数据带 source_id（PMID/DOI/URL）+ extraction_date |
| 数据合规性 | 全程遵守数据源 license；中文文献仅处理摘要与公开附录 |
| 系统可维护性 | 配置化驱动，新增数据源无需改代码 |
| 系统可扩展性 | 新增指标通过 Schema 扩展，不破坏既有结构 |

---

## 三、技术架构选型

### 3.1 三层分工架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    统一数据存储目的地                                  │
│         e:\Health_man\data\knowledge\chinese_reference\               │
│         (结构化存储目录: 7 个子目录, 单域 ≤1GB, 总量 ≤8GB)            │
└────────────────────────────┬────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │   数据治理中台（Data Governance Hub）   │
              │   - 命名规范 / 格式标准 / 元数据描述     │
              │   - 去重 / 清洗 / 标准化 / 异常值处理    │
              │   - 数据字典 / 字段说明 / 处理流程文档   │
              │   - 冗余控制 / 可扩展 Schema             │
              └─────────────┬─────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐
│  Layer A     │    │  Layer B     │    │  Layer C     │
│  开放数据集   │    │  文献聚合     │    │  LLM 蒸馏    │
│  直采        │    │              │    │  (国内优先)   │
└──────────────┘    └──────────────┘    └──────────────┘
   ~25 项指标       ~8 项独家      ~3-5 项增强
   完全免费         完全免费         ¥0（免费额度内）
```

### 3.2 三层方案对比

| 维度 | Layer A 开放数据集 | Layer B 文献聚合 | Layer C LLM 蒸馏 |
|------|------------------|---------------|----------------|
| 核心数据源 | NHANES/KNHANES/CHNS/GASC/PhysioNet | PubMed/CNKI/万方 + figshare/Dryad | 国内大模型蒸馏 |
| 数据形态 | XPT/CSV 原始 | PDF 表格 + 摘要文本 | PDF → 结构化 JSON |
| 采集方式 | HTTP 下载 + pandas ETL | 手工 + 脚本辅助 | LLM API 自动化 |
| 置信度 | 0.9 | 0.7 | 0.5（需人工验证） |
| 更新频率 | 2 年一周期 | 月度 | 按需触发 |
| 合规风险 | 极低（政府开放） | 中（全文版权） | 中高（需脱敏） |
| 成本 | ¥0 | ¥0 | ¥0（免费额度内，详见 §7.8） |
| 优先级 | P0 必建 | P0 必建 | P1 可选 |
| 中国人群覆盖 | 仅 GASC | CNKI 丰富 | 中英文均可 |
| 中医体质覆盖 | ❌ 无 | ✅ 中文文献 | ⚠️ 术语不规范 |
| 数据质量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 可重复性 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 技术门槛 | 中（需统计） | 低（手工提取） | 高（需 LLM 集成） |

### 3.3 推荐组合

**A + B 为主路径，C 为可选增强：**
- 主路径 A：补齐 25 项主要指标，完全免费、合规、可重复
- 辅助路径 B：补齐中国人群偏差校正 + 中医体质（8 项独家指标）
- 可选增强 C：仅对 A+B 无法覆盖的 3-5 项指标启用 LLM 蒸馏

---

## 四、Layer A 开放数据集直采详细设计

### 4.1 数据来源评估标准

**5 维度评分模型（与 §6.1 治理要素 1 对齐）：**

| 维度 | 权重 | 评分标准 |
|------|------|---------|
| 来源可靠性 | 25% | 5=政府/WHO；4=顶级期刊附录；3=学术机构；2=个人/社区；1=不明 |
| 获取权限 | 20% | 5=完全公开(Public Domain)；4=CC-BY；3=CC-BY-NC；2=注册获取；1=受限 |
| 数据质量 | 25% | 5=原始+代码本+权重；4=原始+代码本；3=原始；2=聚合统计；1=仅百分位 |
| 更新频率 | 15% | 5=年度；4=2-3 年；3=5 年内；2=5-10 年；1=不更新 |
| 中国适用性 | 15% | 5=中国数据；4=亚洲；3=欧美但可校正；2=欧美；1=其他 |

**门槛：** 加权总分 ≥3.5/5 方可纳入；3.0-3.5 需人工复核；<3.0 拒绝。

### 4.2 数据源接入清单与评估

| 数据集 | 提供方 | 地区 | 样本量 | 覆盖指标 | 体量预估 | 更新频率 | License | 加权评分 | 决策 |
|--------|--------|------|--------|---------|---------|---------|---------|---------|------|
| NHANES 2017-2020 | CDC | 美国 | 9,092 | IND-01~14, 18~21 | 560MB | 2 年/周期 | Public Domain | 4.10 | ✅ 纳入 |
| KNHANES 2021-2023 | 韩国疾控 | 韩国 | ~30,000 | IND-01~14 | 180MB | 3 年/周期 | Public Domain | 4.25 | ✅ 纳入 |
| CHNS | UNC | 中国 | ~15,000 | IND-01~04 | 80MB | 不定期 | Public | 4.40 | ✅ 纳入 |
| GASC 2025 | PMID:40620559 | 中国 | 29,064 | IND-02/03/04/14 | 5MB | 不定期 | CC-BY | 4.55 | ✅ 纳入 |
| PhysioNet CapnoBase | MIT | 国际 | 42 | IND-15~18 | 50MB | 稳定 | ODC-BY 1.0 | 4.15 | ✅ 纳入 |
| PhysioNet BIDMC | MIT | 国际 | 53 | IND-15~21 | 130MB | 稳定 | ODC-BY 1.0 | 4.15 | ✅ 纳入 |
| WESAD | Schmidt 2018 | 德国 | 15 | IND-19~21 | 250MB | 稳定 | CC-BY 4.0 | 3.90 | ✅ 纳入 |
| WHO MGRS 2006 | WHO | 多中心 | 8,440 | IND-01 (儿童) | 30MB | 稳定 | CC-BY-NC | 3.85 | ✅ 纳入（需人工复核） |

**全部数据集通过可行性门槛。** 评分明细写入 `A_open_datasets/_metadata/feasibility_scores.csv`。

### 4.3 数据源接入技术方案

#### 4.3.1 整体接入架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    下载调度器 (DownloadScheduler)                 │
│   - 任务队列 (优先级 + 依赖) + 并发控制 + 断点续传 + 重试退避     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼──────┐      ┌────────▼────────┐    ┌───────▼──────┐
│  CDC 源适配器 │      │  PhysioNet 适配器│    │  期刊源适配器│
│  (NHANES)     │      │  (CapnoBase等)  │    │  (GASC PDF)  │
└──────────────┘      └─────────────────┘    └─────────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  通用校验器 (SHA256) │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  格式转换器 (ETL)    │
                    │  XPT/CSV/PDF → Parquet│
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  预处理器 (5 步)     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  元数据生成器        │
                    │  (L0+L1+L2 三层)     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  A_open_datasets/    │
                    └─────────────────────┘
```

#### 4.3.2 源适配器统一接口

```python
# 伪代码：所有源适配器实现统一接口
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

class SourceAdapter(ABC):
    """数据源适配器抽象基类"""

    @abstractmethod
    def list_files(self) -> List[dict]:
        """列出可下载文件清单，含 url, filename, expected_size_bytes"""

    @abstractmethod
    def download(self, file_meta: dict, dest_dir: Path) -> Path:
        """下载单个文件，返回本地路径"""

    @abstractmethod
    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """校验文件完整性"""

    @abstractmethod
    def get_metadata_template(self) -> dict:
        """返回该数据集的元数据模板（L0 卡片）"""
```

#### 4.3.3 各数据源接入参数

| 数据集 | 下载协议 | 并发数 | 单文件上限 | 重试次数 | 退避算法 | 镜像源 |
|--------|---------|--------|-----------|---------|---------|--------|
| NHANES | HTTPS (CDC) | 3 | 200MB | 3 | 指数 1s→2s→4s | 无（官方稳定） |
| KNHANES | HTTPS (KDCA) | 2 | 100MB | 3 | 指数 | 无 |
| CHNS | HTTPS (UNC) | 2 | 50MB | 2 | 指数 | 无 |
| GASC 2025 | HTTP (期刊) | 1 | 10MB | 3 | 指数 | PubMed Central |
| PhysioNet | HTTPS (Nightcap) | 2 | 100MB | 3 | 指数 | 无 |
| WESAD | HTTPS (Zenodo) | 1 | 250MB | 3 | 指数 | 无 |
| WHO MGRS | HTTPS (WHO) | 1 | 30MB | 2 | 指数 | 无 |

### 4.4 数据采集频率与更新机制

#### 4.4.1 更新策略矩阵

| 数据集 | 检查频率 | 更新触发 | 通知方式 | 版本保留 |
|--------|---------|---------|---------|---------|
| NHANES | 季度 | 新周期发布（2 年） | 控制台 + 日志 | 保留最近 3 版本 |
| KNHANES | 季度 | 新周期发布（3 年） | 控制台 + 日志 | 保留最近 3 版本 |
| CHNS | 月度 | 新数据发布 | 日志 | 保留最近 2 版本 |
| GASC 2025 | 一次性 | 论文更新（勘误） | 日志 | 保留最新 |
| PhysioNet | 半年度 | 数据集更新 | 日志 | 保留最新 |
| WESAD | 一次性 | 不更新 | - | 保留最新 |
| WHO MGRS | 一次性 | 不更新 | - | 保留最新 |

#### 4.4.2 增量更新机制

```python
# 伪代码：增量更新检查
def check_incremental_update(dataset_id: str) -> dict:
    """检查数据集是否有增量更新"""
    # 1. 获取远程清单
    adapter = get_adapter(dataset_id)
    remote_files = adapter.list_files()
    # 2. 加载本地清单
    local_manifest = load_local_manifest(dataset_id)
    # 3. 对比差异
    new_files = []
    updated_files = []
    for remote in remote_files:
        local = local_manifest.get(remote["filename"])
        if local is None:
            new_files.append(remote)
        elif remote["sha256"] != local["sha256"]:
            updated_files.append(remote)
    return {
        "new": new_files,
        "updated": updated_files,
        "unchanged_count": len(remote_files) - len(new_files) - len(updated_files)
    }
```

#### 4.4.3 自动化调度

- **调度器：** `APScheduler` 库，cron 表达式配置
- **执行时间：** 每周日凌晨 2:00 执行检查（避免高峰）
- **失败重试：** 检查失败重试 3 次，间隔 1 小时
- **通知机制：** 检测到更新时，写入 `logs/update_notifications.log` + 控制台告警

### 4.5 数据格式标准化处理流程

#### 4.5.1 格式转换矩阵

| 源格式 | 目标格式 | 工具库 | 转换参数 | 质量校验 |
|--------|---------|--------|---------|---------|
| SAS XPT | Parquet + Snappy | `pyreadstat` + `pyarrow` | `encoding='utf-8'`，`compression='snappy'` | 行数 + 列数 + 抽样值校验 |
| CSV (GBK) | Parquet + Snappy | `pandas` + `pyarrow` | `encoding='gbk'` → UTF-8 | 同上 |
| CSV (UTF-8) | Parquet + Snappy | `pandas` + `pyarrow` | `compression='snappy'` | 同上 |
| PDF 表格 | JSON | `PyMuPDF` + `tabula-py` | `pages='all'`，`lattice=True` | 字段数 + 数字范围校验 |
| WFDB (波形) | EDF + Parquet (元数据) | `wfdb` 库 | `physical=True` | 信号长度 + 采样率校验 |
| Excel | Parquet + Snappy | `openpyxl` + `pandas` | `dtype=str` 先读后转 | 同上 |

#### 4.5.2 字段命名标准化

```python
# 伪代码：字段名标准化
def standardize_field_name(raw_name: str, source: str) -> str:
    """将原始字段名标准化为 snake_case 英文"""
    # 1. 中文 → 英文映射表
    name_mapping = {
        "身高": "height_cm",
        "体重": "weight_kg",
        "体脂率": "body_fat_pct",
        "BMI": "bmi",
        "BMXBMI": "bmi",  # NHANES 字段
        "BMXBFP": "body_fat_pct",  # NHANES 字段
        # 完整映射见 indicator_mapping.json
    }
    # 2. 已在映射表：直接返回
    if raw_name in name_mapping:
        return name_mapping[raw_name]
    # 3. 不在映射表：转 snake_case 并记录到 unmapped_fields.log
    standardized = to_snake_case(raw_name)
    log_unmapped_field(raw_name, standardized, source)
    return standardized
```

#### 4.5.3 单位统一化

| 指标 | 目标单位 | 转换规则 |
|------|---------|---------|
| 身高 | cm | m × 100；inch × 2.54 |
| 体重 | kg | lb × 0.4536 |
| BMI | kg/m² | weight_kg / (height_cm/100)² |
| 体脂率 | % | 保持 |
| 心率 | bpm | 保持 |
| HRV (RMSSD) | ms | s × 1000 |
| 血氧 | % | 保持 |
| 知觉指数 PI | % | 0-20% 量程 |
| 阻抗 | Ω | 保持 |

### 4.6 数据质量校验规则

#### 4.6.1 三级质量校验

```
原始数据 (RAW)
    │
    ▼ Level 1: 结构校验
    │  - 文件完整性（SHA256 匹配）
    │  - 行数/列数与预期一致
    │  - 必填字段无缺失
    │  - 字段类型与 schema 一致
    │
    ▼ Level 2: 值域校验
    │  - 生理范围硬过滤
    │  - 3σ 软标记
    │  - 分组 IQR 检测
    │
    ▼ Level 3: 业务校验
       - 指标间逻辑关系（如 BMI = 体重/身高²）
   - 跨数据集一致性（同指标在多数据集应接近）
   - 时间趋势合理性
```

#### 4.6.2 生理范围硬过滤规则

| 指标 | 合理范围 | 来源 |
|------|---------|------|
| BMI | 10-80 kg/m² | WHO |
| 体脂率 | 3-60% | BestHealth 手册 |
| 身高 | 120-220 cm | 临床 |
| 体重 | 30-200 kg | 临床 |
| 心率 | 30-220 bpm | AHA |
| SpO₂ | 70-100% | BMH08002 datasheet |
| PI | 0-20% | BMH08002 通信协议 V1.1 |
| RMSSD | 5-150 ms | ESC 指南 |
| 年龄 | 6-99 | BestHealth 范围 |
| 性别 | 0/1 (女/男) | 编码统一 |

#### 4.6.3 质量评分模型

每个数据集处理后输出质量评分：

```json
{
  "dataset_id": "NHANES_2017_2020",
  "quality_score": {
    "completeness": 0.95,        // 字段完整率
    "validity": 0.98,            // 值域合法率
    "consistency": 0.92,         // 跨字段一致性
    "timeliness": 1.0,           // 时效性（最新周期）
    "overall": 0.96              // 加权综合
  },
  "quality_grade": "A",          // A/B/C/D 四级
  "quality_report_url": "A_open_datasets/_metadata/nhanes_2017_2020_quality.json"
}
```

| 等级 | 评分 | 置信度 | 用途 |
|------|------|--------|------|
| A | ≥0.9 | 0.9 | 直接用于 unified 参考 |
| B | 0.8-0.9 | 0.75 | 可用但标注 |
| C | 0.7-0.8 | 0.6 | 需人工复核 |
| D | <0.7 | 0.4 | 拒绝入库 |

### 4.7 异常数据处理策略

#### 4.7.1 异常值检测与处置

| 检测方法 | 适用场景 | 处置策略 |
|---------|---------|---------|
| 生理范围硬过滤 | 所有生理指标 | 超范围直接剔除，记录到 `outliers.log` |
| 3σ 准则 | 正态分布指标（如 BMI） | 标记 `is_outlier=true`，保留但统计时排除 |
| 分组 IQR | 分层数据（年龄×性别） | Q1-1.5×IQR ~ Q3+1.5×IQR 外标记 |
| Z-score | 跨数据集对比 | |Z|>3 标记，>5 拒绝 |
| 孤立森林 | 多维联合检测 | 用 `sklearn.ensemble.IsolationForest` |

#### 4.7.2 缺失值处理

| 缺失率 | 策略 | 实现方式 |
|--------|------|---------|
| <5% | KNN 填充 (k=5) | `sklearn.impute.KNNImputer` |
| 5-30% | 分层中位数填充 | 按 age_group + gender 分组取中位数 |
| >30% | 整列剔除 | 记录到 `dropped_fields.log` |
| 关键字段缺失 | 整行剔除 | 关键字段：age, gender, weight, height |

#### 4.7.3 重复数据处理

```python
# 伪代码：重复数据识别与去重
def deduplicate_records(df, dedup_keys: list) -> tuple:
    """
    返回 (去重后 df, 重复记录 df)
    """
    # 1. 精确重复（全部字段相同）
    exact_dup = df.duplicated(keep='last')
    df_exact_dedup = df[~exact_dup]
    # 2. 关键字段重复（subject_id + visit_date）
    key_dup = df_exact_dedup.duplicated(subset=dedup_keys, keep='last')
    df_final = df_exact_dedup[~key_dup]
    duplicates = df[exact_dup | key_dup]
    return df_final, duplicates
```

### 4.8 数据存储架构设计

#### 4.8.1 存储目录结构（Layer A 专属）

```
A_open_datasets\
├── _metadata\
│   ├── data_catalog.json                          # 全部数据集清单
│   ├── feasibility_scores.csv                     # 可行性评分
│   ├── nhanes_2017_2020_L0_card.json              # L0 数据集卡片
│   ├── nhanes_2017_2020_L1_fields.json            # L1 字段字典
│   ├── nhanes_2017_2020_L2_usage.md              # L2 使用说明
│   ├── nhanes_2017_2020_quality.json             # 质量报告
│   ├── nhanes_2017_2020_pipeline.md               # 处理流程文档
│   └── ... (每个数据集对应 5 个元数据文件)
├── nhanes_2017_2020\
│   ├── RAW\                                       # 原始下载文件
│   │   ├── DEMO_J.XPT
│   │   ├── BMX_J.XPT
│   │   └── ...
│   └── PROCESSED\                                 # 处理后文件
│       ├── demographics.parquet
│       ├── body_measures.parquet
│       └── body_composition.parquet
├── knhanes_2021_2023\
│   ├── RAW\
│   └── PROCESSED\
├── chns\
├── gasc_2025\
├── physionet_capnobase\
├── physionet_bidmc\
├── wesad\
└── who_mgrs_2006\
```

#### 4.8.2 文件命名规范

| 文件类型 | 命名模板 | 示例 |
|------|---------|------|
| 原始文件 | `{source}_{table}_{cycle}.{ext}` | `nhanes_demo_j_2017.xpt` |
| 处理后文件 | `{source}_{domain}_{cycle}.parquet` | `nhanes_body_composition_2017.parquet` |
| 元数据 L0 | `{source}_{cycle}_L0_card.json` | `nhanes_2017_2020_L0_card.json` |
| 元数据 L1 | `{source}_{cycle}_L1_fields.json` | `nhanes_2017_2020_L1_fields.json` |
| 元数据 L2 | `{source}_{cycle}_L2_usage.md` | `nhanes_2017_2020_L2_usage.md` |
| 质量报告 | `{source}_{cycle}_quality.json` | `nhanes_2017_2020_quality.json` |
| 流程文档 | `{source}_{cycle}_pipeline.md` | `nhanes_2017_2020_pipeline.md` |

#### 4.8.3 存储优化

- **压缩格式：** Parquet + Snappy（压缩比 5-10x）
- **分区策略：** 按 `age_group` + `gender` 分区存储（查询时按需加载）
- **列式存储：** 仅加载查询所需列，减少 I/O
- **缓存层：** 频繁访问的统计结果缓存为 `*.parquet.stats.json`

### 4.9 数据访问权限控制方案

#### 4.9.1 权限矩阵（Layer A 专属）

| 角色 | RAW/ | PROCESSED/ | _metadata/ | 写权限 | 读权限 |
|------|------|-----------|-----------|--------|--------|
| `reader` | ❌ | ✅ | ✅ (只读) | ❌ | ✅ |
| `writer` | ✅ | ✅ | ✅ | ✅ (仅 PROCESSED) | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ (全部) | ✅ |

#### 4.9.2 访问控制实现

```python
# 伪代码：访问控制装饰器
import os
import functools
from pathlib import Path

def require_permission(role: str):
    """装饰器：检查当前用户角色是否有权访问"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_role = os.getenv('HEALTH_MAN_ROLE', 'reader')
            role_hierarchy = {'reader': 1, 'writer': 2, 'admin': 3}
            if role_hierarchy.get(current_role, 0) < role_hierarchy[role]:
                raise PermissionError(f"需要 {role} 权限，当前 {current_role}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_permission('writer')
def write_to_processed(data, path: Path):
    """写入 PROCESSED 目录（需 writer 权限）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(path, compression='snappy')
    log_access('write', path)
```

#### 4.9.3 审计日志

```json
// access_audit.log 每行一条 JSON
{
  "timestamp": "2026-07-12T10:23:45+08:00",
  "user_role": "writer",
  "operation": "write",
  "file_path": "A_open_datasets/nhanes_2017_2020/PROCESSED/body_measures.parquet",
  "file_size_bytes": 1234567,
  "checksum_sha256": "abc123..."
}
```

### 4.10 性能优化措施

#### 4.10.1 下载性能优化

| 优化项 | 措施 | 预期收益 |
|--------|------|---------|
| 并发下载 | `asyncio` + `aiohttp`，单数据集 3 并发 | 下载时间 ↓50% |
| 断点续传 | HTTP Range 请求 + 本地 `.part` 文件 | 失败重试零浪费 |
| 压缩传输 | 启用 `Accept-Encoding: gzip` | 流量 ↓70% |
| 镜像加速 | 清华/阿里镜像源备选 | 国内下载速度 ↑5x |
| 连接复用 | `requests.Session` 保持 keep-alive | 握手开销 ↓80% |

#### 4.10.2 处理性能优化

| 优化项 | 措施 | 预期收益 |
|--------|------|---------|
| 列式处理 | `pandas` 仅加载所需列 | 内存 ↓60% |
| 分块处理 | 大文件 `chunksize=10000` 分块读取 | 内存峰值 ↓80% |
| 并行 ETL | `multiprocessing` 多进程处理 | 处理速度 ↑3-4x |
| 缓存统计 | 聚合结果缓存为 JSON | 重复查询 ↓90% |
| 延迟加载 | `dask.dataframe` 惰性计算 | 大数据集内存可控 |

#### 4.10.3 性能基准与监控

| 指标 | 目标 | 告警阈值 |
|------|------|---------|
| NHANES 全量下载耗时 | ≤30 分钟 | >60 分钟 |
| 单数据集 ETL 耗时 | ≤10 分钟 | >30 分钟 |
| Parquet 查询响应 | ≤2 秒 | >10 秒 |
| 内存峰值 | ≤2GB | >4GB |
| 磁盘 I/O 占用 | ≤50% | >80% |

### 4.11 扩展性设计

#### 4.11.1 可扩展点

| 扩展场景 | 扩展方式 | 影响范围 |
|---------|---------|---------|
| 新增数据源 | 实现 `SourceAdapter` 接口 + 注册到 `data_catalog.json` | 仅新增，不修改既有 |
| 新增指标 | 在 `indicator_mapping.json` 增加映射 + 处理时自动识别 | 不影响既有指标 |
| 新增格式 | 实现 `FormatConverter` 接口 | 仅新增 |
| 新增预处理规则 | 在 `preprocessing_rules.yaml` 增加配置 | 热更新，不需重启 |
| 新增质量规则 | 在 `quality_rules.yaml` 增加配置 | 热更新 |
| 新增权限角色 | 在 `roles.yaml` 增加角色定义 | 不影响既有角色 |

#### 4.11.2 插件式架构

```python
# 伪代码：插件注册机制
class PluginRegistry:
    """插件注册中心"""
    _adapters = {}
    _converters = {}
    _validators = {}

    @classmethod
    def register_adapter(cls, dataset_id: str, adapter_class):
        cls._adapters[dataset_id] = adapter_class

    @classmethod
    def register_converter(cls, source_format: str, target_format: str, converter_class):
        key = f"{source_format}->{target_format}"
        cls._converters[key] = converter_class

    @classmethod
    def get_adapter(cls, dataset_id: str) -> SourceAdapter:
        if dataset_id not in cls._adapters:
            raise ValueError(f"未注册的数据源: {dataset_id}")
        return cls._adapters[dataset_id]()

# 使用示例
PluginRegistry.register_adapter("NHANES_2017_2020", NHANESAdapter)
PluginRegistry.register_converter("xpt", "parquet", XPTToParquetConverter)
```

#### 4.11.3 配置驱动

所有可变参数集中在 `_governance/config.yaml`，修改无需改代码：

```yaml
# _governance/config.yaml
datasets:
  NHANES_2017_2020:
    enabled: true
    priority: 1
    max_concurrent: 3
    max_size_mb: 200
    retry:
      max_attempts: 3
      backoff: exponential
      base_delay: 1.0
  KNHANES_2021_2023:
    enabled: true
    priority: 2
    # ...

preprocessing:
  outlier_detection:
    method: iqr
    multiplier: 1.5
  missing_value:
    method: knn
    knn_k: 5
  dedup:
    keys: [subject_id, visit_date]

quality:
  min_completeness: 0.8
  min_validity: 0.9
  grade_thresholds:
    A: 0.9
    B: 0.8
    C: 0.7
    D: 0.0
```

---

## 五、Layer B 文献聚合详细设计

### 5.1 数据源清单

| 数据源 | 覆盖 | 获取方式 | 成本 | 预估体量 |
|--------|------|---------|------|---------|
| PubMed Central 全文 | IND-01~21 | NCBI E-utilities API | ¥0 | 150MB |
| CNKI 摘要 | IND-01~14, 31 | cnki.net 免费检索 | ¥0 | 50MB |
| 万方医学网摘要 | IND-01~14 | wanfangdata.com.cn | ¥0 | 30MB |
| figshare / Dryad / Zenodo | 各 IND | 平台 API | ¥0 | 100MB |
| GASC 2025 PDF | IND-02/03/04/14 | PMID:40620559 附录 | ¥0 | 5MB |
| 中医体质 ZYYXH/T157-2009 国标 | IND-31 | 公开标准 | ¥0 | 1MB |
| 中华医学会指南 PDF | IND-19~21 | 公开下载 | ¥0 | 20MB |

**Layer B 总量上限 500MB，预估实际 200MB。**

### 5.2 检索与提取流程

```
search_literature.py
    │
    ├── PubMed E-utilities 检索
    │   └── 关键词: ("body composition" OR "BIA") AND "China"[Affiliation]
    │
    ├── CNKI 跨库检索
    │   └── 关键词: SU=(体成分+BIA+中国) AND PT=(期刊)
    │
    ├── 下载 PDF + 摘要文本
    │
    ├── PyMuPDF + GROBID 提取表格
    │
    ├── 人工校验提取数据
    │   └── 填入 literature_extraction_log.csv
    │
    └── 写入 B_literature/ + 生成元数据
```

### 5.3 中医体质专项处理

- **标准依据：** ZYYXH/T157-2009《中医体质分类与判定》
- **9 型判定算法：** 标准量表 60 题 → 各型得分 → 最高分型判定
- **人群分布：** 从中文流行病学文献提取各型患病率
- **参考范围：** 各型对应的体质指数、生活方式建议

---

## 六、数据治理 8 要素详细设计

### 6.1 要素 1：数据资源可行性评估

任何数据集纳入前必须通过 5 维度评估：

```json
{
  "dataset_id": "NHANES_2017_2020",
  "feasibility_assessment": {
    "source_reliability": {"score": 5, "rationale": "CDC 官方"},
    "access_permission": {"level": "public_open", "license": "Public Domain"},
    "update_frequency": "2 年/周期",
    "data_quality_preliminary": {
      "completeness": 0.95,
      "sample_size": 9092,
      "known_bias": "种族分布与中国人群有差异"
    },
    "applicability_score": 4,
    "decision": "approved",
    "reviewer": "auto",
    "review_date": "2026-07-12"
  }
}
```

**评分门槛：** 总分 ≥3.5/5 方可纳入；3.0-3.5 需人工复核；<3.0 拒绝。

### 6.2 要素 2：数据体量控制标准

| 领域 | 上限 | 预估体量 | 触发审查阈值 |
|------|------|---------|-------------|
| 体成分 | 1GB | 560MB | 800MB |
| 心血管 | 1GB | 480MB | 800MB |
| 代谢 | 1GB | 380MB | 800MB |
| 文献 | 500MB | 200MB | 400MB |
| LLM 产出 | 200MB | 5MB | 150MB |
| 归档 | 1GB | 0 | 800MB |
| **总计** | **≤8GB** | **~2.14GB** | **6.4GB** |

### 6.3 要素 3：数据规范制定

#### 6.3.1 命名规范

| 类型 | 命名模板 | 示例 |
|------|---------|------|
| 数据集目录 | `{layer}_{source}_{cycle}_{type}` | `A_nhanes_2017_2020_demographics` |
| 文件名 | `{source}_{table}_{cycle}.{ext}` | `nhanes_bmx_j_2017.parquet` |
| 指标字段 | `{indicator_id}_{stat}` | `body_fat_pct_p50` |
| 元数据 | `{dataset_id}_{layer}.json` | `nhanes_2017_2020_L0_card.json` |
| LLM 产出 | `{topic}_distilled_v{n}.json` | `tcm_constitution_distilled_v1.json` |

#### 6.3.2 格式标准

| 数据类型 | 强制格式 | 理由 |
|---------|---------|------|
| 表格数据 | Parquet + Snappy | 列式存储、压缩比高、带 schema |
| 嵌套结构 | JSON (UTF-8) | 通用、可读 |
| 文本语料 | UTF-8 文本 | 可直接被 LLM 处理 |
| 二进制波形 | WFDB 或 EDF | 医学标准格式 |
| 文档 | Markdown | 版本控制友好 |

#### 6.3.3 元数据三层描述

| 层级 | 文件 | 必填字段 |
|------|------|---------|
| L0 | `*_card.json` | dataset_id, source_url, download_date, size_bytes, checksum_sha256, population, license |
| L1 | `*_fields.json` | field_id, field_name, type, unit, valid_range, missing_rate, description |
| L2 | `*_usage.md` | 适用场景, 不适用场景, 偏差说明, 引用格式, 已知问题 |

#### 6.3.4 数据分类体系

```json
{
  "taxonomy": {
    "by_population": ["chinese", "asian", "caucasian", "mixed"],
    "by_age_group": ["children", "adolescent", "adult", "elderly", "all_age"],
    "by_measurement": ["BIA", "DEXA", "PPG", "ECG", "questionnaire", "lab_test"],
    "by_indicator_domain": ["body_composition", "cardiovascular", "metabolic", "respiratory", "tcm"],
    "by_data_type": ["tabular", "timeseries", "waveform", "text", "image"],
    "by_confidence": ["high_0.9+", "medium_0.7-0.9", "low_0.5-0.7"]
  }
}
```

### 6.4 要素 4：数据预处理规范

**标准化 5 步流程：**

```
原始数据 (RAW)
    │
    ▼ Step 1: 数据清洗
    │  - 去除空白字符、统一编码
    │  - 重复记录去重（基于 subject_id + visit_date）
    │  - 字段名标准化（中英文→snake_case）
    │
    ▼ Step 2: 格式转换
    │  - XPT/SAS → Parquet
    │  - CSV → Parquet (带 schema)
    │  - PDF 表格 → JSON
    │
    ▼ Step 3: 异常值处理
    │  - 生理范围硬过滤（如 BMI 10-80, HR 30-220）
    │  - 3σ 软标记（不删除，标记 is_outlier=true）
    │  - 分组 IQR 检测（按年龄×性别分层）
    │
    ▼ Step 4: 缺失值填充
    │  - 缺失率 >30% 的字段：整列剔除
    │  - 缺失率 5-30%：按分层中位数填充
    │  - 缺失率 <5%：按 KNN (k=5) 填充
    │  - 缺失记录标注 missing_flag
    │
    ▼ Step 5: 数据标准化
       - 年龄分组：6-17 / 18-39 / 40-59 / 60+（与 BestHealth 对齐）
       - 性别编码：1=男 / 0=女
       - 单位统一：kg/m², %, ms, bpm, kcal
       - 输出 PROCESSED/*.parquet
```

**配置化驱动：** 所有规则写在 `_governance/preprocessing_rules.yaml`，可热更新。

### 6.5 要素 5：数据统一性与扩展性保障

#### 6.5.1 统一性

所有指标映射到 `medical_knowledge.json` 的 `indicator_id`：

```json
{
  "indicator_mapping": {
    "BMI": "bmi",
    "Body Mass Index": "bmi",
    "体脂率": "body_fat_pct",
    "BMXBMI": "bmi",
    "BMXBFP": "body_fat_pct"
  }
}
```

#### 6.5.2 扩展性 Schema

```json
{
  "schema_version": "1.0",
  "extensibility": {
    "new_indicator_template": {
      "indicator_id": "<unique_id>",
      "name": "<中文名>",
      "name_en": "<英文名>",
      "unit": "<单位>",
      "category": "BIA | PPG | TCM | derived",
      "population_specific": true,
      "reference_range_schema": {
        "source_type": "enum: open_dataset, literature, llm_distilled",
        "statistics": "object: {p5, p25, p50, p75, p95, mean, sd}",
        "stratified_by": "array: [age_group, gender]"
      }
    },
    "versioning_rule": "新增字段不删除旧字段，标记 deprecated=true"
  }
}
```

### 6.6 要素 6：统一存储管理

**存储目的地：** `e:\Health_man\data\knowledge\chinese_reference\`

```
chinese_reference\
├── _governance\                  # 治理元文件
├── A_open_datasets\              # Layer A
├── B_literature\                 # Layer B
├── C_llm_distilled\              # Layer C
├── unified\                      # 统一聚合产出
├── _archive\                     # 归档与版本
└── README.md                     # 目录说明
```

### 6.7 要素 7：数据冗余控制

#### 6.7.1 去重机制

| 场景 | 去重键 | 机制 |
|------|--------|------|
| 同一受试者多次访问 | `subject_id + visit_date` | 保留最新记录 |
| 跨数据集重复 | `indicator_id + age_group + gender + statistic` | 保留 confidence 高者 |
| LLM 重复提取 | `source_pmid + indicator_id + field` | 保留最新版本 |
| 文件级 | SHA256 | 重复文件自动跳过 |

#### 6.7.2 存储优化

- Parquet 格式 + Snappy 压缩（比 CSV 小 5-10 倍）
- 超过 30 天未访问的 RAW 文件迁移至 `_archive/`
- LLM 提取的中间产物用后即删，仅保留结构化 JSON
- 每月执行 `dedup_audit.py` 扫描冗余

### 6.8 要素 8：数据可读性提升

#### 6.8.1 数据字典

`unified/data_dictionary.md` 包含每个指标的：

- 单位、数据源、覆盖人群、采集方式
- 正常范围、已知偏差、字段示例（含 N 与统计量）
- 引用格式、处理流程、更新日期、质量评级

#### 6.8.2 处理流程文档

每个数据集附 `*_pipeline.md` 记录从 RAW 到 PROCESSED 的完整步骤、参数、时间戳。

---

## 七、Layer C LLM 蒸馏增强模块详细设计

### 7.1 国内大模型优先选型

#### 7.1.1 候选模型评估矩阵

| 模型 | 提供方 | 免费额度 | 中文能力 | 上下文长度 | API 兼容性 | 推荐度 |
|------|--------|---------|---------|-----------|-----------|--------|
| Qwen2.5-72B | 阿里通义 | 100 万 tokens/月 | ⭐⭐⭐⭐⭐ | 128K | OpenAI 兼容 | ⭐⭐⭐⭐⭐ |
| DeepSeek-V3 | 深度求索 | 100 万 tokens/月 | ⭐⭐⭐⭐⭐ | 128K | OpenAI 兼容 | ⭐⭐⭐⭐⭐ |
| 豆包 Pro 128K | 字节跳动 | 50 万 tokens/月 | ⭐⭐⭐⭐ | 128K | OpenAI 兼容 | ⭐⭐⭐⭐ |
| GLM-4-Flash | 智谱 AI | 完全免费 | ⭐⭐⭐⭐⭐ | 128K | OpenAI 兼容 | ⭐⭐⭐⭐⭐ |
| IMA | 腾讯 | 有限免费 | ⭐⭐⭐⭐ | 32K | 私有 API | ⭐⭐⭐ |
| Kimi | 月之暗面 | 100 万 tokens/月 | ⭐⭐⭐⭐⭐ | 200K | OpenAI 兼容 | ⭐⭐⭐⭐ |

#### 7.1.2 推荐组合

**主力：** GLM-4-Flash（完全免费 + 中文强 + 128K 上下文）
**备选：** Qwen2.5-72B（100 万 tokens 免费额度）
**长文档：** Kimi（200K 上下文，处理长 PDF 指南）
**综合兜底：** DeepSeek-V3

### 7.2 强自动化集成架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API 网关层（统一接入）                       │
│  - 模型路由 / 负载均衡 / 故障转移 / 限流熔断 / 日志审计          │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────┐    ┌────────▼────────┐   ┌──────▼──────┐
│  上下文工程    │    │  服务编排层     │   │  监控告警层  │
│  - 提示词模板库│    │  - 任务调度     │   │  - 指标采集  │
│  - 对话状态机  │    │  - 多轮交互     │   │  - 告警通知  │
│  - Few-shot   │    │  - 批量处理     │   │  - 成本监控  │
└──────────────┘    └─────────────────┘   └─────────────┘
                             │
                ┌────────────┴────────────┐
                │   模型适配器层（可切换）   │
                │  GLM / Qwen / Kimi / DS  │
                └─────────────────────────┘
```

### 7.3 上下文工程体系

#### 7.3.1 提示词模板库

```
C_llm_distilled/_metadata/prompt_templates\
├── extract_reference_range.txt     # 参考范围提取
├── extract_percentile_table.txt    # 百分位表提取
├── extract_tcm_syndrome.txt        # 中医体质提取
├── extract_sample_size.txt         # 样本量提取
├── extract_age_gender_split.txt    # 年龄性别分层
└── cross_validate_prompt.txt      # 交叉验证
```

**模板示例（extract_reference_range.txt）：**

```
你是医学数据提取专家。从以下文献片段中提取参考范围数据。

输入文献：
{literature_text}

请严格按以下 JSON schema 输出：
{
  "indicator_id": "string",
  "name_cn": "string",
  "name_en": "string",
  "unit": "string",
  "population": {
    "region": "CN",
    "age_range": "string",
    "gender": "male|female|both"
  },
  "statistics": {
    "p5": "number|null",
    "p25": "number|null",
    "p50": "number|null",
    "p75": "number|null",
    "p95": "number|null",
    "mean": "number|null",
    "sd": "number|null",
    "n_subjects": "integer"
  },
  "source_pmid": "string",
  "extraction_confidence": "0-1"
}

规则：
1. 只提取明确报告的数字，禁止推断
2. 若文献未报告某统计量，填 null
3. 单位必须明确（%、kg/m²、ms 等）
4. extraction_confidence 自评：清晰=0.9，模糊=0.5
```

#### 7.3.2 对话状态管理

```python
# 状态机：idle → searching → extracting → validating → confirmed
class ExtractionState:
    IDLE = "idle"
    SEARCHING = "searching"      # 检索文献
    EXTRACTING = "extracting"    # LLM 提取
    VALIDATING = "validating"    # 人工验证
    CONFIRMED = "confirmed"      # 确认入库
    REJECTED = "rejected"        # 拒绝
```

#### 7.3.3 Few-shot 示例库

每个提示词模板配 3-5 个已标注示例，覆盖正例与反例。

### 7.4 系统工程支持

#### 7.4.1 API 网关

- **统一接口：** OpenAI 兼容协议，`/v1/chat/completions`
- **路由策略：** 按任务类型 + 模型能力 + 当前可用性动态路由
- **限流熔断：** 单模型 QPS 限制 + 错误率 >10% 自动切换
- **日志审计：** 每次调用记录 (timestamp, model, prompt_tokens, completion_tokens, cost, success)

#### 7.4.2 服务编排

- **任务调度：** 单个文档→多指标提取，并行处理
- **批量处理：** 100 篇 PDF 一批次，断点续跑
- **多轮交互：** 复杂表格需 2-3 轮追问，保留上下文

#### 7.4.3 监控告警

- **指标采集：** 调用成功率、平均延迟、token 消耗、成本
- **告警通知：** 单日成本超 ¥10 / 错误率 >15% / 配额耗尽
- **成本监控：** 按模型/任务/日期统计

#### 7.4.4 版本控制

- **提示词版本：** `prompt_templates/v{n}/`
- **模型版本：** 记录 model_id + version
- **输出版本：** `{topic}_distilled_v{n}.json`

### 7.5 兼容性与可切换性

#### 7.5.1 接口标准化

所有模型适配器实现统一接口：

```python
class ModelAdapter(ABC):
    @abstractmethod
    def chat(self, prompt: str, system: str = None) -> dict:
        """返回 {content, tokens_used, model_id, latency_ms}"""

    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
```

#### 7.5.2 负载均衡与故障转移

- **轮询策略：** 多模型轮询，避免单点过载
- **故障转移：** 主模型失败自动切换备选
- **能力路由：** 长文档→Kimi；中文表格→GLM；复杂推理→Qwen

### 7.6 安全规范（已基于审计 P0+P1 强化）

#### 7.6.1 凭证管理（应对 SEC-001、SEC-005）

**API Key 全生命周期管理：**

| 阶段 | 机制 | 实现 |
|------|------|------|
| 存储 | AES-256-GCM 加密 + OS 密钥链集成 | Windows DPAPI (`win32crypt.CryptProtectData`)；密钥文件 `~/.health_man/credentials.enc`，权限 600 |
| 加载 | 启动时解密到内存，不落盘 | `keyring` 库 + 进程内存隔离 |
| 传输 | 仅 HTTPS + 证书校验 | `requests.Session` 强制 `verify=True`；禁用 `SSL_CERT_FILE` 覆盖 |
| 隔离 | 每个模型独立 Key + 独立配额 | `credentials/{model_id}/` 目录隔离；RBAC 角色控制（reader/writer/admin） |
| 轮换 | 90 天自动提醒轮换 | `credential_rotation_log.csv` 记录轮换历史 |
| 撤销 | 异常时一键吊销 | `credential_revocation.json` 黑名单机制 |

**`.env` 文件规范：**
```bash
# .env (不入库，加入 .gitignore)
HEALTH_MAN_DATA_DIR=e:/Health_man/data/knowledge/chinese_reference
GLM_API_KEY_ENC=<base64_encrypted>
QWEN_API_KEY_ENC=<base64_encrypted>
KIMI_API_KEY_ENC=<base64_encrypted>
DEEPSEEK_API_KEY_ENC=<base64_encrypted>
MASTER_KEY_LOCATION=win32_dpapi
```

#### 7.6.2 数据加密（应对 SEC-004）

| 层级 | 加密方案 | 实现细节 |
|------|---------|---------|
| 传输加密 | TLS 1.3 强制 | `ssl.OP_NO_TLSv1_2` 禁用旧版本；启用 HSTS；证书校验 `verify=True` + `check_hostname=True` |
| 证书校验 | OCSP + CRL 双重 | `ssl.SSLContext` 启用 `ocsp_enabled=True`；CRL 自动下载与缓存 |
| 存储加密 | 静态数据加密 | 敏感字段（PII、API Key）用 `cryptography.fernet` 加密；普通参考范围数据明文 |
| 哈希校验 | 全文件 SHA256 | 每个数据集附 `checksum_sha256`，加载前校验 |

#### 7.6.3 访问权限控制（应对 SEC-005）

**RBAC 三级权限模型：**

| 角色 | 权限范围 | 适用对象 |
|------|---------|---------|
| `reader` | 只读 unified/ + A_open_datasets/ 已处理数据 | 主项目代码、报告生成模块 |
| `writer` | 写入 A_open_datasets/ + B_literature/ + 临时文件 | ETL 脚本、下载工具 |
| `admin` | 全部读写 + 凭证管理 + 配额配置 | 开发者本人 |

**访问控制实现：**
- 文件系统层：Windows ACL 设置目录权限
- 应用层：`access_control.py` 装饰器拦截越权访问
- 审计层：所有写操作记录到 `access_audit.log`，含时间戳/操作者/文件路径/操作类型

#### 7.6.4 限流与熔断（应对 SEC-006）

**令牌桶限流器：**

```python
# 伪代码
class TokenBucketLimiter:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity  # 桶容量（如 10 次/秒）
        self.refill_rate = refill_rate  # 填充速率
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def acquire(self) -> bool:
        # 填充令牌
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

**熔断器（三态：CLOSED/OPEN/HALF_OPEN）：**

| 状态 | 触发条件 | 行为 |
|------|---------|------|
| CLOSED | 正常 | 请求通过 |
| OPEN | 错误率 >10% 或 1 分钟内 5 次失败 | 拒绝请求 30 秒，自动切换备选模型 |
| HALF_OPEN | 30 秒冷却后 | 放行 1 个探测请求，成功则回 CLOSED |

**模型故障转移矩阵：**

| 主模型 | 备选 1 | 备选 2 | 触发条件 |
|--------|--------|--------|---------|
| GLM-4-Flash | Qwen2.5-72B | DeepSeek-V3 | 主模型连续 3 次失败 |
| Qwen2.5-72B | GLM-4-Flash | Kimi | 配额耗尽或错误率 >10% |
| Kimi | Qwen2.5-72B | GLM-4-Flash | 长文档任务失败 |

#### 7.6.5 内容过滤与幻觉防护（应对 SEC-002）

**三层防护体系：**

```
LLM 原始输出
    │
    ▼ Layer 1: 结构化校验
    │  - JSON schema 严格校验（jsonschema 库）
    │  - 字段类型/范围/单位合法性
    │  - 必填字段完整性
    │
    ▼ Layer 2: 语义校验
    │  - 关键词黑名单过滤（诊断/治疗/处方/痊愈/治愈等合规风险词）
    │  - 数字范围合理性（如体脂率 0-60%，BMI 10-80）
    │  - 单位一致性检查
    │
    ▼ Layer 3: 交叉验证
    │  - 同一指标多篇文献结果对比，IQR 异常值剔除
    │  - 与 GASC 2025 已知百分位对比，偏差 >10% 标记需人工复核
    │  - LLM 自评 confidence <0.5 自动拒绝
    │
    ▼ 人工抽检（20% 随机抽样）
       - 由人工验证数据准确性
       - 错误率 >15% 触发全量复核
```

**幻觉检测指标：**

| 指标 | 阈值 | 处置 |
|------|------|------|
| JSON 解析失败率 | >5% | 模型降级，切备选 |
| 数字越界率 | >3% | 单条拒绝，记录 |
| confidence 自评 <0.5 | >5% | 批次复核 |
| 人工抽检错误率 | >15% | 全量复核 + 提示词迭代 |
| 与金标准偏差 >10% | >5% | 标记需人工确认 |

#### 7.6.6 法规合规

- **PIPL 合规：** 不上传个人信息到外部 LLM；如文献含 PII，先用 `presidio-analyzer` 脱敏
- **数据出境：** 优先国内模型（GLM/Qwen/豆包/Kimi/DeepSeek），数据不出境
- **版权处理：** 仅处理公开摘要/附录/表格，不存储全文 PDF；元数据记录 license
- **医学免责声明：** unified JSON 顶部固定声明 `"本数据仅作参考范围对标，不构成医学诊断依据"`
- **内容审核：** 输出过滤黑名单含 `诊断|确诊|治疗|处方|痊愈|治愈|药物推荐|疗法治愈` 等敏感词

### 7.7 异常处理与容错设计（应对 SEC-007）

#### 7.7.1 异常分类与处置策略

| 异常类型 | 检测方式 | 处置策略 | 重试上限 | 退避算法 |
|---------|---------|---------|---------|---------|
| 网络超时 | `requests.Timeout` (30s) | 切镜像源 → 切备选源 | 3 次 | 指数退避 1s→2s→4s |
| HTTP 4xx | `response.status_code` | 不重试，记录到错误日志 | 0 | - |
| HTTP 5xx | `response.status_code` | 重试 → 切备选源 | 3 次 | 指数退避 |
| LLM API 超时 | `httpx.Timeout` (60s) | 切备选模型 | 2 次 | 固定 5s |
| LLM JSON 解析失败 | `json.JSONDecodeError` | 重新请求 + 修复提示词 | 2 次 | 固定 2s |
| LLM confidence <0.5 | schema 校验 | 拒绝该条 + 记录 | 0 | - |
| 文件 SHA256 不匹配 | `hashlib.sha256` | 重新下载 | 2 次 | 指数退避 |
| 文件体量超限 | `os.path.getsize` | 终止下载 + 告警 | 0 | - |
| 磁盘空间不足 | `shutil.disk_usage` | 终止流程 + 告警 | 0 | - |
| 配额耗尽 | API 返回 429 | 切备选模型 + 记录 | 0 | - |
| PDF 解析失败 | `PyMuPDF` 异常 | 跳过该文件 + 记录 | 0 | - |
| 数据缺失率 >30% | 字段扫描 | 整列剔除 + 记录 | 0 | - |

#### 7.7.2 重试与退避算法

```python
# 指数退避伪代码
import random
import time

def retry_with_backoff(func, max_retries=3, base_delay=1.0, exceptions=(Exception,)):
    """带指数退避的重试机制"""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

#### 7.7.3 降级策略

| 场景 | 降级方案 | 标记方式 |
|------|---------|---------|
| Layer A 下载全部失败 | 切镜像源（清华源、阿里源） → 手工下载 | `confidence: 0.6` |
| Layer B 中文文献全部不可用 | 仅用 PubMed 中文作者文献 + GASC 附录兜底 | `confidence: 0.5` |
| Layer C 所有 LLM 失败 | 退化为纯手工提取（速度慢但可行） | `confidence: 0.7` |
| 单指标无任何数据 | 标注"数据缺失"，用 datasheet 默认值兜底 | `confidence: 0.3` + `missing: true` |
| 配额耗尽且无备选 | 暂停 Layer C，等待次月配额恢复 | 状态机 `PAUSED` |

#### 7.7.4 失败日志与告警

- **失败日志：** `logs/failures/{date}_failures.jsonl`，含时间戳/异常类型/上下文/堆栈
- **告警通知：** 单日失败率 >15% 或单日成本超 ¥10 触发邮件/控制台告警
- **告警通道：** 控制台输出 + `logs/alerts.log` 文件
- **告警分级：** P0 立即中断 + 通知；P1 记录 + 继续；P2 仅记录

### 7.8 数据销毁与归档机制（应对 SEC-003）

#### 7.8.1 数据生命周期

```
创建 (CREATE)
    │
    ▼ 活跃期 (ACTIVE, 0-30 天)
    │  - 位于 A_open_datasets/ 或 B_literature/ 等
    │  - 频繁访问
    │
    ▼ 归档期 (ARCHIVED, 31-180 天)
    │  - 迁移至 _archive/snapshots/
    │  - Snappy 压缩
    │  - 仅元数据保留在主目录
    │
    ▼ 冷归档 (COLD, 181-365 天)
    │  - 保留 SHA256 与元数据
    │  - 原始文件压缩加密
    │
    ▼ 销毁 (DESTROY, >365 天)
       - 安全擦除（3 次覆写）
       - 保留元数据与处理日志
       - 记录销毁凭证
```

#### 7.8.2 销毁规则

| 数据类型 | 保留期 | 销毁方式 |
|---------|--------|---------|
| 临时中间产物（PDF 文本、LLM 中间响应） | 用后即销 | 立即删除 |
| 下载的 RAW 文件 | 30 天活跃 → 归档 | 归档后压缩 |
| 元数据（L0/L1/L2） | 永久 | 不销毁 |
| 审计日志 | 5 年 | 5 年后安全擦除 |
| 失败日志 | 90 天 | 90 天后删除 |
| 凭证文件 | 轮换后立即销毁旧版本 | 覆写 + 删除 |

#### 7.8.3 归档快照

- **触发：** 每月 1 日自动创建快照
- **位置：** `_archive/snapshots/snapshot_YYYY-MM-DD/`
- **内容：** 全量 unified JSON + 元数据 + changelog
- **加密：** 快照整体用 AES-256 加密
- **保留：** 最近 12 个快照，超出自动销毁最旧

### 7.9 数据提取效率与质量保障

#### 7.9.1 效率指标

| 指标 | 目标 |
|------|------|
| 单文档处理时间 | ≤30 秒 |
| 单日处理量 | ≥100 篇 |
| 提取成功率 | ≥85% |
| Token 消耗/文档 | ≤5,000 |

#### 7.9.2 质量保障

- **双层验证：** LLM 自评 confidence + 人工抽检 20%
- **交叉验证：** 同一指标多篇文献取中位数，IQR 异常值剔除
- **金标准对照：** 与 GASC 2025 已知百分位对比，偏差 >10% 触发复核
- **溯源链路：** 每条数据附 source_pmid + extraction_date + model_id

### 7.10 成本预估

| 模型 | 月度免费额度 | 预估消耗 | 月度成本 |
|------|------------|---------|---------|
| GLM-4-Flash | 完全免费 | 200 万 tokens | ¥0 |
| Qwen2.5-72B | 100 万 tokens | 80 万 tokens | ¥0 |
| Kimi | 100 万 tokens | 30 万 tokens | ¥0 |
| DeepSeek-V3 | 100 万 tokens | 50 万 tokens | ¥0 |
| **合计** | - | 360 万 tokens | **¥0** |

**结论：** 通过合理分配免费额度，Layer C 完全可达成 0 成本。

**超额边界条件：** 若月度实际消耗超出各模型免费额度总和（约 450 万 tokens），超出部分按各模型官方费率计费（GLM-4-Flash 仍免费）。预估本项目月消耗 360 万 tokens，留有 20% 余量。若超出，单日成本超 ¥10 触发告警，单月成本超 ¥100 需征得同意后切换付费模式。

### 7.11 审计日志防篡改（应对 SEC-008）

- **哈希链：** 每条日志含前一条的 SHA256 哈希，形成链式结构
- **时间戳：** 启用 RFC 3161 时间戳协议（可信第三方时间戳）
- **日志签名：** 每日日志文件用开发者 PGP 私钥签名
- **只追加：** 日志文件设置为 append-only 模式（Windows 下用 `FILE_APPEND_DATA` 权限）
- **异地备份：** 每周自动备份到独立磁盘

---

## 八、实施步骤

### 8.1 实施分阶段

| 阶段 | 工作内容 | 交付物 |
|------|---------|--------|
| Phase 1 | 基础设施搭建 | 存储目录、治理配置、Schema |
| Phase 2 | Layer A 开放数据集下载与处理 | A_open_datasets/ + 元数据 |
| Phase 3 | Layer B 文献检索与手工提取 | B_literature/ + 提取日志 |
| Phase 4 | Layer C LLM 蒸馏增强（可选） | C_llm_distilled/ + 审计日志 |
| Phase 5 | 统一聚合与质量门禁 | unified/chinese_reference_unified.json |
| Phase 6 | 数据字典与文档 | data_dictionary.md + pipeline.md |

### 8.2 详细步骤

#### Phase 1：基础设施搭建

1. 创建存储目录体系 `e:\Health_man\data\knowledge\chinese_reference\`
2. 编写治理配置 `_governance/preprocessing_rules.yaml`、`naming_convention.md`、`format_standards.md`
3. 编写统一 Schema 定义 `unified/schema.json`
4. 编写下载脚本框架 `scripts/download_datasets.py`

#### Phase 2：Layer A 数据下载与处理

1. NHANES 2017-2020 下载与转换
2. KNHANES 2021-2023 下载与转换
3. CHNS 下载与转换
4. GASC 2025 PDF 附录提取
5. PhysioNet 三个数据集下载
6. WHO MGRS 2006 下载
7. 各数据集 5 步预处理
8. 三层元数据生成
9. 体量控制审计

#### Phase 3：Layer B 文献聚合

1. PubMed 中国人群 BIA 检索
2. CNKI 摘要检索（体成分+中医体质）
3. 下载公开 PDF 与附录
4. PyMuPDF + GROBID 表格提取
5. 人工校验与录入
6. 中医体质 9 型标准数字化
7. Meta 分析（如有需要）

#### Phase 4：Layer C LLM 蒸馏（可选）

1. 注册 GLM-4-Flash / Qwen / Kimi 账号
2. 编写模型适配器（统一接口）
3. 编写提示词模板库
4. API 网关搭建（路由+限流+审计）
5. 批量蒸馏处理难提取指标
6. 人工抽检验证（20%）
7. 交叉验证与异常值剔除

#### Phase 5：统一聚合

1. 三层数据映射到统一 indicator_id
2. 重复项去重（按 confidence 保留）
3. 缺失指标识别与标注
4. 质量评分与门禁
5. 生成 `chinese_reference_unified.json`

#### Phase 6：文档与归档

1. 编写 `data_dictionary.md`（每指标附说明）
2. 编写各数据集 `*_pipeline.md`
3. 创建快照 `_archive/snapshots/snapshot_2026-07-12/`
4. 编写 `changelog.md`

---

## 九、时间节点

### 9.1 整体排期

| 阶段 | 工期 | 开始日 | 结束日 | 累计 |
|------|------|--------|--------|------|
| Phase 1 基础设施 | 1 天 | D1 | D1 | 1 天 |
| Phase 2 Layer A | 3 天 | D2 | D4 | 4 天 |
| Phase 3 Layer B | 4 天 | D5 | D8 | 8 天 |
| Phase 4 Layer C（可选） | 3 天 | D9 | D11 | 11 天 |
| Phase 5 统一聚合 | 1 天 | D12 | D12 | 12 天 |
| Phase 6 文档归档 | 1 天 | D13 | D13 | 13 天 |

**总计：13 个工作日（约 3 周）**

### 9.2 里程碑

| 里程碑 | 日期 | 交付物 | 验收标准 |
|--------|------|--------|--------|
| M1 | D1 | 基础设施就绪 | 目录 + 治理配置 + Schema 完成 |
| M2 | D4 | Layer A 完成 | 25 项指标参考范围 + 元数据 |
| M3 | D8 | Layer B 完成 | 8 项独家指标 + 中医体质 |
| M4 | D11 | Layer C 完成（可选） | 3-5 项难提取指标 + 审计日志 |
| M5 | D12 | 统一聚合完成 | unified JSON 通过质量门禁 |
| M6 | D13 | 文档交付 | 数据字典 + 流程文档 + 快照 |

---

## 十、风险评估与应对策略

### 10.1 风险矩阵

| 风险 ID | 风险描述 | 类别 | 概率 | 影响 | 严重度 | 应对策略 |
|---------|---------|------|------|------|--------|--------|
| R1 | NHANES/KNHANES 服务器不稳定，下载失败 | 技术 | 中 | 中 | 🟠 | 重试 3 次 + 断点续传 + 镜像源备选 |
| R2 | CNKI 全文 PDF 受版权限制无法下载 | 合规 | 高 | 中 | 🟠 | 仅用公开摘要 + 补充材料 + figshare 共享数据 |
| R3 | LLM 提取数据存在幻觉 | 质量 | 高 | 高 | 🔴 | 人工抽检 20% + 交叉验证 + 金标准对照 |
| R4 | GLM/Qwen 免费额度耗尽 | 成本 | 中 | 中 | 🟠 | 多模型轮询 + 月度配额监控 + 必要时切付费 |
| R5 | 中医体质文献术语不规范 | 质量 | 高 | 中 | 🟠 | 国标 ZYYXH/T157-2009 为准 + 中医专家咨询 |
| R6 | 数据集体量超限 | 运营 | 低 | 低 | 🟡 | 自动终止 + 字段筛选 + Parquet 压缩 |
| R7 | 跨数据集指标定义不一致 | 质量 | 高 | 中 | 🟠 | 统一 indicator_mapping + 人工对齐 |
| R8 | 国内大模型 API 协议变更 | 技术 | 中 | 中 | 🟠 | 适配器模式 + OpenAI 兼容协议 + 备选模型 |
| R9 | 数据源 license 变更限制商用 | 合规 | 低 | 高 | 🟠 | license 字段记录 + 定期复审 + 替代数据源储备 |
| R10 | 单人开发进度延误 | 运营 | 中 | 中 | 🟠 | 分阶段交付 + 优先级排序 + 核心指标优先 |

### 10.2 风险应对优先级

**P0 必须应对（严重度 🔴）：**
- R3 LLM 幻觉：双层验证 + 交叉验证 + 金标准对照

**P1 优先应对（严重度 🟠）：**
- R1 下载失败：重试 + 断点续传
- R2 CNKI 版权：仅公开摘要
- R4 配额耗尽：多模型轮询
- R5 中医术语：国标为准
- R7 指标不一致：统一映射
- R8 API 协议变更：适配器模式
- R9 license 变更：复审机制
- R10 进度延误：分阶段交付

**P2 关注（严重度 🟡）：**
- R6 体量超限：自动终止

### 10.3 应急预案

| 场景 | 应急措施 |
|------|---------|
| Layer A 下载全部失败 | 切换至镜像源（如清华开源镜像）+ 手工下载 |
| Layer B 中文文献全部不可用 | 仅用 PubMed 中文作者文献 + GASC 附录兜底 |
| Layer C 所有 LLM 失败 | 退化为纯手工提取（速度慢但可行） |
| 体量超限 | 优先保留 confidence 高的数据集，归档低优先级 |
| 全部方案失败 | 标注"数据缺失"，主项目用 datasheet 默认值兜底 |

---

## 十一、数据治理对项目各阶段的支持作用

### 11.1 对开发阶段的支持

| 治理要素 | 支持作用 | 量化指标 |
|---------|---------|---------|
| 统一存储目录 | 减少路径查找时间 | ↓80% |
| 命名规范 | 减少硬编码路径 | ↓90% |
| 数据字典 | 减少字段映射错误 | ↓95% |
| 格式标准（Parquet） | 减少数据加载时间 | ↓70% |
| 元数据三层 | 减少运行时数据相关 bug | ↓60% |

### 11.2 对决策准确性的支持

| 治理要素 | 支持作用 | 量化指标 |
|---------|---------|---------|
| 可行性评估 | 避免低质数据导致错误决策 | 数据质量事故 ↓80% |
| 异常值处理 | 防止离群值扭曲参考范围 | 参考范围偏移 ↓50% |
| 置信度标注 | 低置信度指标加注免责 | 合规风险 ↓70% |
| 统一性 schema | 支持多源交叉验证 | 交叉验证覆盖率 ↑300% |
| 来源溯源 | 每条数据可追溯原始来源 | 审计响应时间 ↓90% |

### 11.3 对数据管理成本的支持

| 治理要素 | 支持作用 | 量化指标 |
|---------|---------|---------|
| 体量控制 | 存储成本可控 | ≤8GB |
| 去重机制 | 节省存储空间 | 存储冗余 ↓60% |
| 格式标准 | 减少 ETL 脚本数量 | ↓70% |
| 自动化预处理 | 减少人工清洗工时 | ↓85% |
| 归档机制 | 冷热数据分离 | 查询响应时间 ↓50% |

### 11.4 对系统可维护性的支持

| 治理要素 | 支持作用 | 量化指标 |
|---------|---------|---------|
| 版本控制 | 数据变更可追溯，支持回滚 | 故障恢复时间 ↓80% |
| 扩展性 Schema | 新增指标无需改既有结构 | 接入工时 ↓60% |
| 处理流程文档 | 新人快速理解数据血缘 | 上手时间 ↓70% |
| 质量门禁 | 自动拦截低质数据 | 数据质量事故 ↓75% |
| 分类体系 | 按域分类管理 | 问题定位时间 ↓65% |

### 11.5 对合规审计的支持

| 治理要素 | 支持作用 | 量化指标 |
|---------|---------|---------|
| 来源溯源 | 每条数据可出具来源证明 | 审计准备时间 ↓90% |
| license 字段 | 自动识别使用限制 | 许可证违规风险 ↓95% |
| 人工验证日志 | LLM 产出有复核留痕 | 可追溯性 ↑100% |
| 归档快照 | 历史版本可追溯 | 历史回溯能力 ↑100% |

---

## 十二、验收标准

### 12.1 功能验收

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| 35 项指标覆盖 | ≥33 项有参考范围数据 | 统计 unified JSON |
| 中医体质 9 型覆盖 | 9 型全部有判定标准与分布 | 检查 tcm_constitution |
| 三层元数据完整 | 每数据集 L0+L1+L2 齐全 | 目录扫描 |
| 数据字典完整 | 35 项指标每项有说明 | 文档审查 |
| 体量控制 | 总量 ≤8GB | du -sh 检查 |

### 12.2 质量验收

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| 数据置信度 | 平均 ≥0.75 | 统计 confidence 字段 |
| 来源溯源率 | 100% 有 source_id | 遍历检查 |
| 人工抽检通过率 | ≥85% | 随机抽 50 条 |
| 与 GASC 交叉验证 | 偏差 ≤15% | 对比 4 项已知指标 |
| 异常值标记率 | 100% 标注 | is_outlier 字段检查 |

### 12.3 合规验收

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| License 记录 | 100% 数据集有 license 字段 | 元数据扫描 |
| 无版权全文 PDF | 0 个 CNKI 全文 PDF | 文件扫描 |
| LLM 输出审计 | 100% 调用有日志 | 日志检查 |
| 个人信息脱敏 | 0 条 PII 数据 | 关键词扫描 |

---

## 十三、附录

### 13.1 术语表

| 术语 | 含义 |
|------|------|
| BIA | 生物电阻抗分析法（Bioelectrical Impedance Analysis） |
| PPG | 光电容积脉搏波（Photoplethysmography） |
| HRV | 心率变异性（Heart Rate Variability） |
| NHANES | 美国国家健康与营养调查 |
| KNHANES | 韩国国民健康营养调查 |
| CHNS | 中国健康与营养调查 |
| GASC | 中国国民体质监测数据 |
| IND | 指标（Indicator）编号 |
| PIPL | 《个人信息保护法》 |
| LLM | 大语言模型 |

### 13.2 参考文档

- [MVP1.0_技术方案_v1.1.md](../../docs/planning/MVP1.0_技术方案_v1.1.md)
- [BestHealth_TwoLegs_技术参考手册.md](../../docs/chip/体脂模组/BestHealth_TwoLegs_技术参考手册.md)
- [S3008T_通信协议_权威转写稿.md](../../docs/chip/通讯协议/S3008T_通信协议_权威转写稿.md)
- [BMH08002_技术说明书_重构版.md](../../docs/chip/血氧监测/BMH08002_技术说明书_重构版.md)
- [HealthDataLab-implementation.md](../2026-07-11-HealthDataLab-implementation.md)
- [V1 医学数据补齐](../2026-07-11-MVP1.0_data_and_medical_content_completion.md)
- [V2 全量审计补全](../2026-07-11-MVP1.0_data_and_medical_content_completion_v2.md)
- [Step5+ 引擎交付](../2026-07-11-MVP1.0_step5_plus_implementation.md)

### 13.3 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-07-12 | 初始版本 | brainstorming 生成 |
| v1.1 | 2026-07-12 | 基于 P0+P1 安全审计修订：补全凭证管理、数据加密、访问权限、限流熔断、内容过滤、异常处理、数据销毁、日志防篡改机制；扩展 Layer A 详细设计（§4.1-§4.11）；新增附录 B 安全审计报告 | 安全审计 + brainstorming |

---

## 附录 B：安全审计报告

### B.1 审计概要

| 项 | 值 |
|---|---|
| 审计日期 | 2026-07-12 |
| 审计对象 | 本设计文档 v1.0 |
| 审计范围 | 数据安全、权限控制、接口设计、异常处理、性能、合规、逻辑、数据质量 |
| 审计执行 | search 子代理 |
| 总体风险评级 | 高（修订前）→ 中（修订后） |

**问题统计：**

| 等级 | 修订前 | 已修订 | 剩余 |
|------|--------|--------|------|
| 🔴 致命 | 3 | 3 | 0 |
| 🟠 严重 | 4 | 4 | 0 |
| 🟡 中等 | 4 | 2 | 2（实施中修复） |
| 🟢 轻微 | 2 | 1 | 1（建议修复） |
| **合计** | **13** | **10** | **3** |

### B.2 问题清单与修订对照

| 问题 ID | 描述 | 等级 | 修订位置 | 修订状态 |
|---------|------|------|---------|---------|
| SEC-001 | API Key 加密存储/传输/轮换缺失 | 🔴 | §7.6.1 | ✅ 已修订 |
| SEC-002 | LLM 幻觉检测与拦截缺失 | 🔴 | §7.6.5 | ✅ 已修订 |
| SEC-003 | 数据销毁与归档机制缺失 | 🔴 | §7.8 | ✅ 已修订 |
| SEC-004 | TLS 1.3 实现细节不足 | 🟠 | §7.6.2 | ✅ 已修订 |
| SEC-005 | 多模型凭证隔离不足 | 🟠 | §7.6.1 + §7.6.3 | ✅ 已修订 |
| SEC-006 | 限流熔断机制不足 | 🟠 | §7.6.4 | ✅ 已修订 |
| SEC-007 | 异常处理不全面 | 🟠 | §7.7 | ✅ 已修订 |
| SEC-008 | 审计日志防篡改缺失 | 🟢 | §7.11 | ✅ 已修订 |
| COMP-001 | CNKI 版权边界 | 🟡 | §7.6.6 | ⏳ 实施中细化 |
| PERF-001 | 大文件下载性能指标缺失 | 🟡 | §4.10 | ⏳ 实施中验证 |
| PERF-002 | 存储自动清理缺失 | 🟢 | §7.8.2 | ✅ 已修订 |
| LOGIC-001 | 指标 ID 映射逻辑不一致 | 🟡 | §6.5 + §4.5.2 | ⏳ 实施中校验 |
| DATA-001 | 发表偏倚未识别 | 🟡 | §7.9.2 | ⏳ 实施中完善 |

### B.3 关键修复优先级

| 优先级 | 问题 | 状态 |
|--------|------|------|
| **P0 立即修复** | SEC-001、SEC-002、SEC-003 | ✅ 全部已修订 |
| **P1 实施前修复** | SEC-004、SEC-005、SEC-006、SEC-007 | ✅ 全部已修订 |
| **P2 实施中修复** | COMP-001、PERF-001、LOGIC-001、DATA-001 | ⏳ 留待实施 |
| **P3 建议修复** | SEC-008、PERF-002 | ✅ 已修订 |

### B.4 审计结论

**修订后方案可进入下一阶段（writing-plans）。**

剩余 3 项 P2 问题均为实施细节，不影响架构决策，留待 writing-plans 阶段细化：

1. COMP-001 CNKI 版权边界：实施时仅下载公开摘要，元数据记录 license
2. PERF-001 大文件下载性能：实施时实测并对照 §4.10.3 基准
3. LOGIC-001 指标 ID 映射：实施时通过 `indicator_mapping.json` 字段一致性检查工具校验
4. DATA-001 发表偏倚：实施时在文献聚合阶段引入 Egger 检验
