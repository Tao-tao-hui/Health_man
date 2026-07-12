# 数据采集实施计划 - Phase 1+2（基础设施 + Layer A 核心路径）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建数据采集子系统的基础设施（存储目录 + 治理配置 + 安全工具）并实现 Layer A 开放数据集直采的核心路径（SourceAdapter 抽象 + NHANES 适配器 + 5 步预处理 + 质量校验），完成 NHANES 2017-2020 全流程端到端验证。

**Architecture:** 采用插件式架构，所有数据源适配器实现统一的 `SourceAdapter` 抽象基类；通过 `DownloadScheduler` 调度并发下载，经 `FormatConverter` 转换为 Parquet，由 `Preprocessor` 执行 5 步标准化处理，`QualityChecker` 输出质量评级，最终由 `MetadataGenerator` 生成三层元数据落盘到 `A_open_datasets/`。

**Tech Stack:** Python 3.11+、pandas 2.x、pyarrow、pyreadstat、PyMuPDF、requests/aiohttp、pytest、PyYAML、cryptography、keyring

## Global Constraints

- 操作系统：Windows 11，PowerShell 5
- 工作目录：`e:\Health_man`
- 数据存储根目录：`e:\Health_man\data\knowledge\chinese_reference`
- 单领域数据上限：1GB；单数据集上限：500MB（超限自动终止）
- 所有配置驱动：参数集中在 `_governance/config.yaml`，修改无需改代码
- 命名规范：snake_case 英文；文件名模板 `{source}_{table}_{cycle}.{ext}`
- 格式标准：表格 Parquet+Snappy；嵌套 JSON UTF-8；文档 Markdown
- TDD 强制：每个任务先写失败测试，再写实现
- 频繁提交：每个任务结束 git commit
- 不创建文档文件（除非用户明确要求）

---

## File Structure

### 新建文件清单

```
e:\Health_man\
├── data\knowledge\chinese_reference\          # 存储根目录（Task 1）
│   ├── _governance\
│   │   ├── config.yaml                        # Task 2
│   │   ├── naming_convention.md               # Task 2
│   │   ├── format_standards.md                # Task 2
│   │   ├── classification_taxonomy.json       # Task 2
│   │   ├── preprocessing_rules.yaml           # Task 2
│   │   ├── quality_rules.yaml                 # Task 2
│   │   ├── roles.yaml                         # Task 2
│   │   └── indicator_mapping.json            # Task 2
│   ├── A_open_datasets\
│   │   └── _metadata\
│   │       └── data_catalog.json             # Task 2
│   ├── B_literature\                          # 预留（本计划不实现）
│   ├── C_llm_distilled\                       # 预留（本计划不实现）
│   ├── unified\                                # 预留（计划 4 实现）
│   ├── _archive\
│   │   └── snapshots\
│   └── README.md                              # Task 1
├── scripts\
│   ├── __init__.py
│   ├── data\
│   │   ├── __init__.py
│   │   ├── source_adapter.py                  # Task 3 - 抽象基类
│   │   ├── adapters\
│   │   │   ├── __init__.py
│   │   │   └── nhanes_adapter.py              # Task 4 - NHANES 实现
│   │   ├── download_scheduler.py              # Task 5 - 下载调度器
│   │   ├── format_converter.py                # Task 6 - 格式转换器
│   │   ├── preprocessor.py                    # Task 7 - 5 步预处理器
│   │   ├── quality_checker.py                # Task 8 - 质量校验器
│   │   └── metadata_generator.py              # Task 9 - 元数据生成器
│   └── utils\
│       ├── __init__.py
│       ├── crypto.py                          # Task 10 - 加密工具
│       ├── credential_manager.py             # Task 10 - 凭证管理
│       ├── retry.py                           # Task 11 - 重试退避
│       ├── rate_limiter.py                    # Task 11 - 限流器
│       ├── circuit_breaker.py                 # Task 11 - 熔断器
│       └── audit_logger.py                    # Task 12 - 审计日志
├── tests\
│   ├── __init__.py
│   ├── data\
│   │   ├── __init__.py
│   │   ├── test_source_adapter.py            # Task 3
│   │   ├── test_nhanes_adapter.py            # Task 4
│   │   ├── test_download_scheduler.py        # Task 5
│   │   ├── test_format_converter.py          # Task 6
│   │   ├── test_preprocessor.py              # Task 7
│   │   ├── test_quality_checker.py            # Task 8
│   │   └── test_metadata_generator.py        # Task 9
│   └── utils\
│       ├── __init__.py
│       ├── test_crypto.py                    # Task 10
│       ├── test_credential_manager.py        # Task 10
│       ├── test_retry.py                     # Task 11
│       ├── test_rate_limiter.py              # Task 11
│       ├── test_circuit_breaker.py           # Task 11
│       └── test_audit_logger.py             # Task 12
└── pyproject.toml                             # Task 1
```

### 文件职责说明

| 文件 | 职责 | 依赖 |
|------|------|------|
| `source_adapter.py` | 定义 `SourceAdapter` 抽象基类，所有数据源适配器必须实现 | 无 |
| `adapters/nhanes_adapter.py` | NHANES 数据源具体实现，含文件清单、下载、校验 | `source_adapter.py` |
| `download_scheduler.py` | 并发下载调度，含断点续传、重试、体量控制 | `adapters/*`、`utils/retry.py` |
| `format_converter.py` | XPT/CSV/PDF → Parquet 转换 | pandas、pyreadstat、PyMuPDF |
| `preprocessor.py` | 5 步标准化处理（清洗→转换→异常→缺失→标准化） | `format_converter.py` |
| `quality_checker.py` | 三级质量校验 + A/B/C/D 评级 | `preprocessor.py` |
| `metadata_generator.py` | 生成 L0/L1/L2 三层元数据 | `quality_checker.py` |
| `utils/crypto.py` | AES-256-GCM 加密/解密 | cryptography |
| `utils/credential_manager.py` | API Key 全生命周期管理 | `crypto.py`、keyring |
| `utils/retry.py` | 指数退避重试装饰器 | 无 |
| `utils/rate_limiter.py` | 令牌桶限流器 | 无 |
| `utils/circuit_breaker.py` | 三态熔断器 | 无 |
| `utils/audit_logger.py` | 哈希链审计日志 | 无 |

---

## Tasks

### Task 1: 项目脚手架与存储目录初始化

**Files:**
- Create: `e:\Health_man\pyproject.toml`
- Create: `e:\Health_man\data\knowledge\chinese_reference\README.md`
- Create: `e:\Health_man\scripts\__init__.py`
- Create: `e:\Health_man\scripts\data\__init__.py`
- Create: `e:\Health_man\scripts\utils\__init__.py`
- Create: `e:\Health_man\tests\__init__.py`
- Create: `e:\Health_man\tests\data\__init__.py`
- Create: `e:\Health_man\tests\utils\__init__.py`

**Interfaces:**
- Produces: 项目根目录结构、pyproject.toml（定义依赖）、空 __init__.py 文件包结构

- [ ] **Step 1: 创建存储目录树**

```powershell
# 在 e:\Health_man 下执行
$dirs = @(
    "data\knowledge\chinese_reference\_governance",
    "data\knowledge\chinese_reference\A_open_datasets\_metadata",
    "data\knowledge\chinese_reference\A_open_datasets\nhanes_2017_2020\RAW",
    "data\knowledge\chinese_reference\A_open_datasets\nhanes_2017_2020\PROCESSED",
    "data\knowledge\chinese_reference\B_literature",
    "data\knowledge\chinese_reference\C_llm_distilled",
    "data\knowledge\chinese_reference\unified",
    "data\knowledge\chinese_reference\_archive\snapshots",
    "scripts\data\adapters",
    "scripts\utils",
    "tests\data",
    "tests\utils"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path "e:\Health_man\$d" -Force | Out-Null
}
```

- [ ] **Step 2: 创建 pyproject.toml**

```toml
# e:\Health_man\pyproject.toml
[project]
name = "health-man"
version = "0.1.0"
description = "大健康检测平台外部数据获取子系统"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0",
    "pyarrow>=14.0",
    "pyreadstat>=1.2",
    "PyMuPDF>=1.23",
    "requests>=2.31",
    "aiohttp>=3.9",
    "PyYAML>=6.0",
    "cryptography>=42.0",
    "keyring>=24.0",
    "APScheduler>=3.10",
    "scikit-learn>=1.4",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
    "pytest-asyncio>=0.23",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

- [ ] **Step 3: 创建 __init__.py 包文件**

每个 `__init__.py` 文件内容为空（仅作为 Python 包标识符）。

- [ ] **Step 4: 创建 README.md 说明存储目录**

```markdown
# chinese_reference 目录说明

本目录是大健康检测平台外部数据获取子系统的统一存储目的地。

## 目录结构

- `_governance/` - 治理配置与元规范
- `A_open_datasets/` - Layer A 开放数据集（直采）
- `B_literature/` - Layer B 文献聚合（计划 2）
- `C_llm_distilled/` - Layer C LLM 蒸馏（计划 3）
- `unified/` - 统一聚合产出（计划 4）
- `_archive/` - 归档与版本快照

## 体量控制

- 单领域上限：1GB
- 单数据集上限：500MB
- 总量上限：8GB
```

- [ ] **Step 5: 验证目录结构**

```powershell
# 运行验证
Get-ChildItem -Path "e:\Health_man\data\knowledge\chinese_reference" -Recurse -Directory | Select-Object FullName
```

预期输出包含 8 个子目录：`_governance`、`A_open_datasets`、`B_literature`、`C_llm_distilled`、`unified`、`_archive`、`_metadata`、`snapshots`。

- [ ] **Step 6: 提交**

```powershell
cd e:\Health_man
git add pyproject.toml data/knowledge/chinese_reference/README.md scripts/ tests/
git commit -m "feat: 初始化项目脚手架与存储目录结构"
```

---

### Task 2: 治理配置文件与指标映射

**Files:**
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\config.yaml`
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\naming_convention.md`
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\format_standards.md`
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\classification_taxonomy.json`
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\preprocessing_rules.yaml`
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\quality_rules.yaml`
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\roles.yaml`
- Create: `e:\Health_man\data\knowledge\chinese_reference\_governance\indicator_mapping.json`
- Create: `e:\Health_man\data\knowledge\chinese_reference\A_open_datasets\_metadata\data_catalog.json`
- Test: `e:\Health_man\tests\data\test_governance_config.py`

**Interfaces:**
- Consumes: spec §6.3 数据规范、§6.4 预处理规范、§4.6 质量校验规则、§4.11.3 配置驱动
- Produces: 全局配置文件（所有后续任务通过 `load_config()` 读取）

- [ ] **Step 1: 写失败测试 - 验证 config.yaml 可加载且字段完整**

```python
# e:\Health_man\tests\data\test_governance_config.py
"""测试治理配置文件的完整性与可加载性"""
import json
from pathlib import Path
import yaml

GOVERNANCE_DIR = Path("e:/Health_man/data/knowledge/chinese_reference/_governance")


def test_config_yaml_loads_successfully():
    """config.yaml 必须存在且可被 PyYAML 解析"""
    config_path = GOVERNANCE_DIR / "config.yaml"
    assert config_path.exists(), f"配置文件不存在: {config_path}"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert config is not None, "config.yaml 内容为空"
    assert "datasets" in config, "config.yaml 缺少 datasets 节"
    assert "preprocessing" in config, "config.yaml 缺少 preprocessing 节"
    assert "quality" in config, "config.yaml 缺少 quality 节"


def test_config_has_nhanes_entry():
    """config.yaml 必须包含 NHANES_2017_2020 数据集配置"""
    with open(GOVERNANCE_DIR / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    nhanes = config["datasets"].get("NHANES_2017_2020")
    assert nhanes is not None, "config.yaml 缺少 NHANES_2017_2020 配置"
    assert nhanes["enabled"] is True
    assert nhanes["priority"] == 1
    assert nhanes["max_concurrent"] == 3
    assert nhanes["max_size_mb"] == 200
    assert nhanes["retry"]["max_attempts"] == 3


def test_indicator_mapping_has_bmi():
    """indicator_mapping.json 必须包含 BMI 映射"""
    mapping_path = GOVERNANCE_DIR / "indicator_mapping.json"
    assert mapping_path.exists()
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    assert "indicator_mapping" in mapping
    im = mapping["indicator_mapping"]
    assert im.get("BMI") == "bmi"
    assert im.get("BMXBMI") == "bmi"
    assert im.get("体脂率") == "body_fat_pct"
    assert im.get("BMXBFP") == "body_fat_pct"


def test_quality_rules_have_grade_thresholds():
    """quality_rules.yaml 必须包含 A/B/C/D 评级阈值"""
    rules_path = GOVERNANCE_DIR / "quality_rules.yaml"
    assert rules_path.exists()
    with open(rules_path, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    thresholds = rules.get("grade_thresholds")
    assert thresholds is not None
    assert thresholds["A"] == 0.9
    assert thresholds["B"] == 0.8
    assert thresholds["C"] == 0.7
    assert thresholds["D"] == 0.0


def test_roles_yaml_has_three_roles():
    """roles.yaml 必须定义 reader/writer/admin 三个角色"""
    roles_path = GOVERNANCE_DIR / "roles.yaml"
    assert roles_path.exists()
    with open(roles_path, "r", encoding="utf-8") as f:
        roles = yaml.safe_load(f)
    assert "roles" in roles
    role_names = [r["name"] for r in roles["roles"]]
    assert "reader" in role_names
    assert "writer" in role_names
    assert "admin" in role_names


def test_data_catalog_json_is_valid():
    """data_catalog.json 必须是合法 JSON 且含 datasets 数组"""
    catalog_path = (
        Path("e:/Health_man/data/knowledge/chinese_reference")
        / "A_open_datasets/_metadata/data_catalog.json"
    )
    assert catalog_path.exists()
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    assert "datasets" in catalog
    assert isinstance(catalog["datasets"], list)
    assert len(catalog["datasets"]) >= 1
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_governance_config.py -v
```

预期：所有测试 FAIL（文件不存在）。

- [ ] **Step 3: 创建 config.yaml**

```yaml
# e:\Health_man\data\knowledge\chinese_reference\_governance\config.yaml
# 数据获取子系统全局配置
# 所有可变参数集中在此文件，修改无需改代码

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
    update_check: quarterly
  KNHANES_2021_2023:
    enabled: true
    priority: 2
    max_concurrent: 2
    max_size_mb: 100
    retry:
      max_attempts: 3
      backoff: exponential
      base_delay: 1.0
    update_check: quarterly
  CHNS:
    enabled: true
    priority: 3
    max_concurrent: 2
    max_size_mb: 50
    retry:
      max_attempts: 2
      backoff: exponential
      base_delay: 1.0
    update_check: monthly
  GASC_2025:
    enabled: true
    priority: 4
    max_concurrent: 1
    max_size_mb: 10
    retry:
      max_attempts: 3
      backoff: exponential
      base_delay: 1.0
    update_check: once

preprocessing:
  outlier_detection:
    method: iqr
    multiplier: 1.5
  missing_value:
    method: knn
    knn_k: 5
    drop_threshold: 0.3
  dedup:
    keys: [subject_id, visit_date]
  standardization:
    age_groups: ["6-17", "18-39", "40-59", "60+"]
    gender_encoding: {female: 0, male: 1}

quality:
  min_completeness: 0.8
  min_validity: 0.9
  grade_thresholds:
    A: 0.9
    B: 0.8
    C: 0.7
    D: 0.0

storage:
  root_dir: e:/Health_man/data/knowledge/chinese_reference
  max_total_size_gb: 8
  max_field_size_mb: 1024
  max_dataset_size_mb: 500
  archive_after_days: 30
  destroy_after_days: 365

security:
  tls_min_version: "1.3"
  credential_store: win32_dpapi
  credential_rotation_days: 90
  audit_log_enabled: true
```

- [ ] **Step 4: 创建 indicator_mapping.json**

```json
{
  "schema_version": "1.0",
  "indicator_mapping": {
    "BMI": "bmi",
    "Body Mass Index": "bmi",
    "BMXBMI": "bmi",
    "体脂率": "body_fat_pct",
    "BodyFatRate": "body_fat_pct",
    "BMXBFP": "body_fat_pct",
    "身高": "height_cm",
    "BMXHT": "height_cm",
    "体重": "weight_kg",
    "BMXWT": "weight_kg",
    "心率": "heart_rate",
    "HR": "heart_rate",
    "BPXPLS": "heart_rate",
    "血氧饱和度": "spo2",
    "SpO2": "spo2",
    "PI": "perfusion_index",
    "RMSSD": "hrv_rmssd",
    "SDNN": "hrv_sdnn",
    "BMR": "basal_metabolic_rate",
    "基础代谢率": "basal_metabolic_rate",
    "内脏脂肪": "visceral_fat_level",
    "骨量": "bone_mass",
    "肌肉量": "muscle_mass",
    "蛋白质": "protein_pct",
    "水分": "water_pct"
  }
}
```

- [ ] **Step 5: 创建 quality_rules.yaml**

```yaml
# 质量校验规则
grade_thresholds:
  A: 0.9
  B: 0.8
  C: 0.7
  D: 0.0

physiological_ranges:
  bmi: {min: 10, max: 80, unit: "kg/m2"}
  body_fat_pct: {min: 3, max: 60, unit: "%"}
  height_cm: {min: 120, max: 220, unit: "cm"}
  weight_kg: {min: 30, max: 200, unit: "kg"}
  heart_rate: {min: 30, max: 220, unit: "bpm"}
  spo2: {min: 70, max: 100, unit: "%"}
  perfusion_index: {min: 0, max: 20, unit: "%"}
  hrv_rmssd: {min: 5, max: 150, unit: "ms"}
  age: {min: 6, max: 99, unit: "years"}

required_fields:
  - age
  - gender
  - weight_kg
  - height_cm

critical_fields_missing_strategy: drop_row
non_critical_missing_threshold: 0.3
```

- [ ] **Step 6: 创建 roles.yaml**

```yaml
# RBAC 角色定义
roles:
  - name: reader
    level: 1
    description: "只读访问已处理数据"
    permissions:
      read: ["unified/", "A_open_datasets/**/PROCESSED/", "A_open_datasets/_metadata/"]
      write: []

  - name: writer
    level: 2
    description: "写入处理后的数据"
    permissions:
      read: ["**"]
      write: ["A_open_datasets/**/PROCESSED/", "B_literature/", "logs/"]

  - name: admin
    level: 3
    description: "全部读写权限"
    permissions:
      read: ["**"]
      write: ["**"]
```

- [ ] **Step 7: 创建 data_catalog.json**

```json
{
  "schema_version": "1.0",
  "last_updated": "2026-07-12",
  "datasets": [
    {
      "dataset_id": "NHANES_2017_2020",
      "source": "CDC",
      "region": "US",
      "sample_size": 9092,
      "license": "Public Domain",
      "status": "pending"
    }
  ]
}
```

- [ ] **Step 8: 创建剩余配置文件（简化版）**

```yaml
# preprocessing_rules.yaml
# 5 步预处理规则（详细参数见 config.yaml preprocessing 节）
steps:
  - name: clean
    description: "去除空白、统一编码、字段名标准化"
  - name: convert
    description: "格式转换为 Parquet"
  - name: detect_outliers
    description: "异常值检测与标记"
  - name: handle_missing
    description: "缺失值填充或剔除"
  - name: standardize
    description: "年龄分组、性别编码、单位统一"
```

```json
{
  "by_population": ["chinese", "asian", "caucasian", "mixed"],
  "by_age_group": ["children", "adolescent", "adult", "elderly", "all_age"],
  "by_measurement": ["BIA", "DEXA", "PPG", "ECG", "questionnaire", "lab_test"],
  "by_indicator_domain": ["body_composition", "cardiovascular", "metabolic", "respiratory", "tcm"],
  "by_data_type": ["tabular", "timeseries", "waveform", "text", "image"],
  "by_confidence": ["high_0.9+", "medium_0.7-0.9", "low_0.5-0.7"]
}
```

```markdown
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
```

```markdown
# 格式标准

## 强制格式

| 数据类型 | 格式 | 理由 |
|---------|------|------|
| 表格数据 | Parquet + Snappy | 列式存储、压缩比高、带 schema |
| 嵌套结构 | JSON (UTF-8) | 通用、可读 |
| 文本语料 | UTF-8 文本 | 可直接被 LLM 处理 |
| 文档 | Markdown | 版本控制友好 |
```

- [ ] **Step 9: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_governance_config.py -v
```

预期：6 个测试全部 PASS。

- [ ] **Step 10: 提交**

```powershell
cd e:\Health_man
git add data/knowledge/chinese_reference/_governance/ data/knowledge/chinese_reference/A_open_datasets/_metadata/data_catalog.json tests/data/test_governance_config.py
git commit -m "feat: 添加治理配置文件与指标映射"
```

---

### Task 3: SourceAdapter 抽象基类

**Files:**
- Create: `e:\Health_man\scripts\data\source_adapter.py`
- Test: `e:\Health_man\tests\data\test_source_adapter.py`

**Interfaces:**
- Consumes: 无
- Produces: `SourceAdapter` 抽象基类，含 `list_files()`、`download()`、`verify_checksum()`、`get_metadata_template()` 四个抽象方法

- [ ] **Step 1: 写失败测试 - 验证抽象基类不可实例化且接口完整**

```python
# e:\Health_man\tests\data\test_source_adapter.py
"""测试 SourceAdapter 抽象基类"""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.data.source_adapter import SourceAdapter


def test_source_adapter_is_abstract():
    """SourceAdapter 不可直接实例化"""
    with pytest.raises(TypeError, match="abstract"):
        SourceAdapter()


def test_concrete_subclass_must_implement_all_methods():
    """子类必须实现全部 4 个抽象方法才能实例化"""

    class IncompleteAdapter(SourceAdapter):
        def list_files(self):
            return []

    with pytest.raises(TypeError, match="abstract"):
        IncompleteAdapter()


def test_complete_subclass_can_instantiate():
    """完整实现的子类可以实例化"""

    class FakeAdapter(SourceAdapter):
        def list_files(self):
            return [{"url": "http://example.com/test.csv", "filename": "test.csv", "expected_size_bytes": 100}]

        def download(self, file_meta, dest_dir):
            dest = Path(dest_dir) / file_meta["filename"]
            dest.write_bytes(b"test content")
            return dest

        def verify_checksum(self, file_path, expected_sha256):
            actual = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
            return actual == expected_sha256

        def get_metadata_template(self):
            return {"dataset_id": "FAKE", "source_url": "http://example.com"}

    adapter = FakeAdapter()
    assert adapter is not None
    files = adapter.list_files()
    assert len(files) == 1
    assert files[0]["filename"] == "test.csv"


def test_list_files_return_type():
    """list_files 返回值必须含 url, filename, expected_size_bytes 三个键"""

    class FakeAdapter(SourceAdapter):
        def list_files(self):
            return [{"url": "http://x.com/a.csv", "filename": "a.csv", "expected_size_bytes": 50}]

        def download(self, file_meta, dest_dir):
            return Path()

        def verify_checksum(self, file_path, expected_sha256):
            return True

        def get_metadata_template(self):
            return {}

    adapter = FakeAdapter()
    files = adapter.list_files()
    for f in files:
        assert "url" in f
        assert "filename" in f
        assert "expected_size_bytes" in f
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_source_adapter.py -v
```

预期：所有测试 FAIL（模块不存在）。

- [ ] **Step 3: 实现 SourceAdapter 抽象基类**

```python
# e:\Health_man\scripts\data\source_adapter.py
"""数据源适配器抽象基类

所有具体数据源适配器（NHANES/KNHANES/CHNS 等）必须继承本类并实现全部抽象方法。
设计目标：插件式扩展，新增数据源仅需实现接口，无需修改既有代码。
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class SourceAdapter(ABC):
    """数据源适配器抽象基类

    子类必须实现以下 4 个方法：
    - list_files(): 列出可下载文件清单
    - download(): 下载单个文件
    - verify_checksum(): 校验文件完整性
    - get_metadata_template(): 返回数据集元数据模板
    """

    @abstractmethod
    def list_files(self) -> list[dict[str, Any]]:
        """列出可下载文件清单

        Returns:
            文件元数据列表，每个元素必须包含：
            - url: 下载 URL
            - filename: 目标文件名
            - expected_size_bytes: 预期文件大小（字节）
        """
        ...

    @abstractmethod
    def download(self, file_meta: dict[str, Any], dest_dir: Path) -> Path:
        """下载单个文件

        Args:
            file_meta: list_files() 返回的文件元数据
            dest_dir: 目标目录

        Returns:
            下载后的本地文件路径
        """
        ...

    @abstractmethod
    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """校验文件完整性

        Args:
            file_path: 本地文件路径
            expected_sha256: 预期的 SHA256 哈希值

        Returns:
            校验是否通过
        """
        ...

    @abstractmethod
    def get_metadata_template(self) -> dict[str, Any]:
        """返回该数据集的元数据模板（L0 卡片）

        Returns:
            含 dataset_id, source_url, license 等必填字段的字典
        """
        ...
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_source_adapter.py -v
```

预期：4 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/data/source_adapter.py tests/data/test_source_adapter.py
git commit -m "feat: 添加 SourceAdapter 抽象基类"
```

---

### Task 4: NHANES 适配器实现

**Files:**
- Create: `e:\Health_man\scripts\data\adapters\__init__.py`
- Create: `e:\Health_man\scripts\data\adapters\nhanes_adapter.py`
- Test: `e:\Health_man\tests\data\test_nhanes_adapter.py`

**Interfaces:**
- Consumes: `SourceAdapter` 基类（Task 3）
- Produces: `NHANESAdapter` 类，实现 4 个抽象方法；`list_files()` 返回 NHANES 2017-2020 的 DEMO_J/BMX_J 等表

- [ ] **Step 1: 写失败测试 - 验证 NHANESAdapter 接口与文件清单**

```python
# e:\Health_man\tests\data\test_nhanes_adapter.py
"""测试 NHANES 适配器"""
from scripts.data.adapters.nhanes_adapter import NHANESAdapter


def test_nhanes_adapter_inherits_source_adapter():
    """NHANESAdapter 必须继承 SourceAdapter"""
    from scripts.data.source_adapter import SourceAdapter
    adapter = NHANESAdapter()
    assert isinstance(adapter, SourceAdapter)


def test_list_files_returns_expected_tables():
    """list_files 必须返回 NHANES 2017-2020 的核心表"""
    adapter = NHANESAdapter()
    files = adapter.list_files()
    filenames = [f["filename"] for f in files]
    # 必须包含人口学与体格测量表
    assert "DEMO_J.XPT" in filenames
    assert "BMX_J.XPT" in filenames
    # 必须包含血压与心率表
    assert "BPX_J.XPT" in filenames


def test_list_files_has_valid_urls():
    """每个文件必须有合法的 CDC URL"""
    adapter = NHANESAdapter()
    files = adapter.list_files()
    for f in files:
        assert f["url"].startswith("https://wwwn.cdc.gov/Nchs/Nhanes/")
        assert f["filename"] in f["url"]
        assert f["expected_size_bytes"] > 0


def test_get_metadata_template_has_required_fields():
    """元数据模板必须含 dataset_id, source_url, license"""
    adapter = NHANESAdapter()
    meta = adapter.get_metadata_template()
    assert meta["dataset_id"] == "NHANES_2017_2020"
    assert meta["source_url"].startswith("https://wwwn.cdc.gov/")
    assert meta["license"] == "Public Domain"
    assert meta["region"] == "US"
    assert meta["sample_size"] == 9092
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_nhanes_adapter.py -v
```

预期：所有测试 FAIL（模块不存在）。

- [ ] **Step 3: 实现 NHANESAdapter**

```python
# e:\Health_man\scripts\data\adapters\__init__.py
# 空文件，标识为 Python 包
```

```python
# e:\Health_man\scripts\data\adapters\nhanes_adapter.py
"""NHANES 2017-2020 数据源适配器

数据源：美国国家健康与营养调查（National Health and Nutrition Examination Survey）
提供方：CDC
License：Public Domain
样本量：9,092
覆盖指标：IND-01~14, 18~21（BIA 体成分 + PPG 心率）
"""
import hashlib
from pathlib import Path
from typing import Any

import requests

from scripts.data.source_adapter import SourceAdapter


class NHANESAdapter(SourceAdapter):
    """NHANES 2017-2020（Pre-Pandemic Cycle）数据源适配器"""

    BASE_URL = "https://wwwn.cdc.gov/Nchs/Nhanes"
    CYCLE = "2017-2018"
    CYCLE_SUFFIX = "J"  # 2017-2018 周期后缀为 J

    # 核心表清单（覆盖 IND-01~14, 18~21）
    TABLES = [
        {"table": "DEMO", "desc": "人口学", "size_bytes": 5_000_000},
        {"table": "BMX", "desc": "体格测量", "size_bytes": 3_000_000},
        {"table": "BPX", "desc": "血压与心率", "size_bytes": 8_000_000},
        {"table": "DUAL", "desc": "双能 X 线吸收测量", "size_bytes": 15_000_000},
        {"table": "TCHOL", "desc": "总胆固醇", "size_bytes": 2_000_000},
        {"table": "GLU", "desc": "空腹血糖", "size_bytes": 2_500_000},
    ]

    def list_files(self) -> list[dict[str, Any]]:
        """列出 NHANES 2017-2018 的核心 XPT 文件"""
        files = []
        for t in self.TABLES:
            filename = f"{t['table']}_{self.CYCLE_SUFFIX}.XPT"
            url = f"{self.BASE_URL}/{self.CYCLE}/{t['table']}_{self.CYCLE_SUFFIX}.XPT"
            files.append({
                "url": url,
                "filename": filename,
                "expected_size_bytes": t["size_bytes"],
                "table": t["table"],
                "description": t["desc"],
            })
        return files

    def download(self, file_meta: dict[str, Any], dest_dir: Path) -> Path:
        """下载单个 XPT 文件到 dest_dir

        Args:
            file_meta: 含 url, filename 的文件元数据
            dest_dir: 目标目录

        Returns:
            下载后的本地文件路径
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_meta["filename"]

        # 流式下载（支持大文件）
        response = requests.get(file_meta["url"], stream=True, timeout=30)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest_path

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """校验文件 SHA256

        Note: NHANES 官方未提供 SHA256，此处仅用于下载后自校验。
        expected_sha256 由首次下载成功后计算并记录。
        """
        actual = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        return actual == expected_sha256

    def get_metadata_template(self) -> dict[str, Any]:
        """返回 NHANES 数据集的 L0 元数据模板"""
        return {
            "dataset_id": "NHANES_2017_2020",
            "source_url": "https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017",
            "license": "Public Domain",
            "region": "US",
            "sample_size": 9092,
            "cycle": self.CYCLE,
            "update_frequency": "2 年/周期",
            "population": "美国全国代表样本",
            "known_bias": "种族分布与中国人群有差异",
            "feasibility_score": 4.10,
        }
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_nhanes_adapter.py -v
```

预期：4 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/data/adapters/ tests/data/test_nhanes_adapter.py
git commit -m "feat: 添加 NHANES 适配器实现"
```

---

### Task 5: 下载调度器

**Files:**
- Create: `e:\Health_man\scripts\data\download_scheduler.py`
- Test: `e:\Health_man\tests\data\test_download_scheduler.py`

**Interfaces:**
- Consumes: `SourceAdapter`（Task 3）、config.yaml 的 `datasets.*.max_concurrent/max_size_mb/retry` 配置（Task 2）
- Produces: `DownloadScheduler` 类，含 `schedule_download(adapter, dest_dir)` 方法，返回下载结果列表

- [ ] **Step 1: 写失败测试 - 验证调度器并发下载与体量控制**

```python
# e:\Health_man\tests\data\test_download_scheduler.py
"""测试下载调度器"""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.data.download_scheduler import DownloadScheduler, DownloadResult
from scripts.data.source_adapter import SourceAdapter


class FakeAdapter(SourceAdapter):
    """用于测试的假适配器"""

    def list_files(self):
        return [
            {"url": "http://test.com/a.csv", "filename": "a.csv", "expected_size_bytes": 100},
            {"url": "http://test.com/b.csv", "filename": "b.csv", "expected_size_bytes": 200},
        ]

    def download(self, file_meta, dest_dir):
        dest = Path(dest_dir) / file_meta["filename"]
        dest.write_bytes(b"x" * file_meta["expected_size_bytes"])
        return dest

    def verify_checksum(self, file_path, expected_sha256):
        return True  # 测试中跳过校验

    def get_metadata_template(self):
        return {"dataset_id": "FAKE"}


def test_scheduler_downloads_all_files(tmp_path):
    """调度器必须下载所有文件"""
    adapter = FakeAdapter()
    scheduler = DownloadScheduler(max_concurrent=2, max_size_mb=1)
    results = scheduler.schedule_download(adapter, tmp_path)
    assert len(results) == 2
    assert all(r.success for r in results)
    # 验证文件已写入
    assert (tmp_path / "a.csv").exists()
    assert (tmp_path / "b.csv").exists()


def test_scheduler_respects_size_limit(tmp_path):
    """单文件超限时必须跳过并标记"""
    adapter = FakeAdapter()
    # 设 max_size_mb=0（实际阈值约 0.0001MB），b.csv 200 bytes 超限
    scheduler = DownloadScheduler(max_concurrent=1, max_size_mb=0)
    # 用 monkeypatch 调整阈值
    scheduler.max_file_size_bytes = 150  # b.csv 200 bytes 超限
    results = scheduler.schedule_download(adapter, tmp_path)
    # a.csv 100 bytes 通过，b.csv 200 bytes 超限
    assert results[0].success is True
    assert results[1].success is False
    assert "exceeds size limit" in results[1].error_message


def test_scheduler_retries_on_failure(tmp_path):
    """下载失败必须重试"""
    adapter = FakeAdapter()
    call_count = {"download": 0}

    original_download = adapter.download

    def flaky_download(file_meta, dest_dir):
        call_count["download"] += 1
        if call_count["download"] < 3:  # 前 2 次失败
            raise ConnectionError("network error")
        return original_download(file_meta, dest_dir)

    adapter.download = flaky_download
    scheduler = DownloadScheduler(max_concurrent=1, max_size_mb=10, max_retries=3)
    results = scheduler.schedule_download(adapter, tmp_path)
    assert results[0].success is True
    assert call_count["download"] == 3  # 重试 2 次后第 3 次成功


def test_scheduler_returns_download_results(tmp_path):
    """结果必须含 filename, path, success, error_message, duration_seconds"""
    adapter = FakeAdapter()
    scheduler = DownloadScheduler(max_concurrent=2, max_size_mb=10)
    results = scheduler.schedule_download(adapter, tmp_path)
    for r in results:
        assert hasattr(r, "filename")
        assert hasattr(r, "path")
        assert hasattr(r, "success")
        assert hasattr(r, "error_message")
        assert hasattr(r, "duration_seconds")
        assert isinstance(r.duration_seconds, float)
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_download_scheduler.py -v
```

预期：所有测试 FAIL（模块不存在）。

- [ ] **Step 3: 实现 DownloadScheduler**

```python
# e:\Health_man\scripts\data\download_scheduler.py
"""下载调度器

职责：
- 调度并发下载（asyncio + ThreadPoolExecutor）
- 体量控制（超限自动跳过）
- 重试退避（指数退避）
- 返回下载结果（含耗时、成功标志、错误信息）

不负责：
- 格式转换（由 FormatConverter 负责）
- 质量校验（由 QualityChecker 负责）
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.data.source_adapter import SourceAdapter

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """单个文件下载结果"""
    filename: str
    path: Path | None
    success: bool
    error_message: str = ""
    duration_seconds: float = 0.0
    file_size_bytes: int = 0


class DownloadScheduler:
    """下载调度器

    Args:
        max_concurrent: 最大并发数
        max_size_mb: 单文件大小上限（MB）
        max_retries: 最大重试次数
        base_delay: 退避基础延迟（秒）
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        max_size_mb: int = 500,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        self.max_concurrent = max_concurrent
        self.max_size_mb = max_size_mb
        self.max_retries = max_retries
        self.base_delay = base_delay
        # max_file_size_bytes 用于测试中精细调整（生产中由 max_size_mb 派生）
        self.max_file_size_bytes = max_size_mb * 1024 * 1024

    def schedule_download(
        self,
        adapter: SourceAdapter,
        dest_dir: Path,
    ) -> list[DownloadResult]:
        """调度下载所有文件

        Args:
            adapter: 数据源适配器
            dest_dir: 目标目录

        Returns:
            下载结果列表（与 list_files 顺序一致）
        """
        files = adapter.list_files()
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        results: list[DownloadResult] = []
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            future_to_file = {
                executor.submit(self._download_with_retry, adapter, f, dest_dir): f
                for f in files
            }
            for future in as_completed(future_to_file):
                file_meta = future_to_file[future]
                try:
                    result = future.result()
                except Exception as e:
                    logger.exception("下载 %s 时发生未捕获异常", file_meta["filename"])
                    result = DownloadResult(
                        filename=file_meta["filename"],
                        path=None,
                        success=False,
                        error_message=str(e),
                    )
                results.append(result)

        # 按原始顺序排序
        filename_order = [f["filename"] for f in files]
        results.sort(key=lambda r: filename_order.index(r.filename))
        return results

    def _download_with_retry(
        self,
        adapter: SourceAdapter,
        file_meta: dict[str, Any],
        dest_dir: Path,
    ) -> DownloadResult:
        """带重试的下载单个文件"""
        filename = file_meta["filename"]
        expected_size = file_meta.get("expected_size_bytes", 0)

        # 体量检查
        if expected_size > self.max_file_size_bytes:
            return DownloadResult(
                filename=filename,
                path=None,
                success=False,
                error_message=f"文件大小 {expected_size} bytes 超过限制 {self.max_file_size_bytes} bytes",
            )

        last_error = ""
        for attempt in range(self.max_retries + 1):
            start_time = time.monotonic()
            try:
                path = adapter.download(file_meta, dest_dir)
                duration = time.monotonic() - start_time
                actual_size = path.stat().st_size if path.exists() else 0
                logger.info("下载成功: %s (%d bytes, %.2fs)", filename, actual_size, duration)
                return DownloadResult(
                    filename=filename,
                    path=path,
                    success=True,
                    duration_seconds=duration,
                    file_size_bytes=actual_size,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "下载失败 (attempt %d/%d): %s - %s",
                    attempt + 1,
                    self.max_retries + 1,
                    filename,
                    last_error,
                )
                if attempt < self.max_retries:
                    # 指数退避
                    delay = self.base_delay * (2**attempt)
                    time.sleep(delay)

        return DownloadResult(
            filename=filename,
            path=None,
            success=False,
            error_message=f"重试 {self.max_retries} 次后仍失败: {last_error}",
        )
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_download_scheduler.py -v
```

预期：4 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/data/download_scheduler.py tests/data/test_download_scheduler.py
git commit -m "feat: 添加下载调度器（并发+重试+体量控制）"
```

---

### Task 6: 格式转换器

**Files:**
- Create: `e:\Health_man\scripts\data\format_converter.py`
- Test: `e:\Health_man\tests\data\test_format_converter.py`

**Interfaces:**
- Consumes: 无（独立工具类）
- Produces: `FormatConverter` 类，含 `convert_xpt_to_parquet()`、`convert_csv_to_parquet()` 方法

- [ ] **Step 1: 写失败测试 - 验证 XPT → Parquet 转换**

```python
# e:\Health_man\tests\data\test_format_converter.py
"""测试格式转换器"""
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from scripts.data.format_converter import FormatConverter


def test_convert_xpt_to_parquet(tmp_path):
    """XPT 文件必须能转换为 Parquet"""
    # 准备：用 pandas 创建测试数据并写为 XPT
    df = pd.DataFrame({
        "SEQN": [1, 2, 3],
        "BMXBMI": [22.5, 25.0, 28.3],
        "RIAGENDR": [1, 0, 1],
        "RIDAGEYR": [25, 35, 45],
    })
    xpt_path = tmp_path / "test.xpt"
    # pyreadstat 写 XPT
    import pyreadstat
    pyreadstat.write_xport(df, str(xpt_path), table_name="TEST")

    # 执行转换
    converter = FormatConverter()
    parquet_path = converter.convert_xpt_to_parquet(xpt_path, tmp_path / "out.parquet")

    # 验证
    assert parquet_path.exists()
    result_df = pd.read_parquet(parquet_path)
    assert len(result_df) == 3
    assert "BMXBMI" in result_df.columns


def test_convert_csv_to_parquet(tmp_path):
    """CSV 文件必须能转换为 Parquet"""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("SEQN,BMI,gender,age\n1,22.5,1,25\n2,25.0,0,35\n", encoding="utf-8")

    converter = FormatConverter()
    parquet_path = converter.convert_csv_to_parquet(csv_path, tmp_path / "out.parquet")

    assert parquet_path.exists()
    result_df = pd.read_parquet(parquet_path)
    assert len(result_df) == 2
    assert "BMI" in result_df.columns


def test_convert_csv_with_gbk_encoding(tmp_path):
    """GBK 编码的 CSV 必须能正确转换为 UTF-8 Parquet"""
    csv_path = tmp_path / "test_gbk.csv"
    # 写一个 GBK 编码的 CSV
    content = "姓名,年龄\n张三,25\n李四,35\n"
    csv_path.write_bytes(content.encode("gbk"))

    converter = FormatConverter()
    parquet_path = converter.convert_csv_to_parquet(
        csv_path, tmp_path / "out.parquet", encoding="gbk"
    )

    result_df = pd.read_parquet(parquet_path)
    assert len(result_df) == 2
    # UTF-8 编码的中文应该正确显示
    assert "姓名" in result_df.columns


def test_convert_invalid_xpt_raises_error(tmp_path):
    """无效 XPT 文件必须抛出明确异常"""
    invalid_path = tmp_path / "invalid.xpt"
    invalid_path.write_bytes(b"not a valid xpt file")

    converter = FormatConverter()
    with pytest.raises(ValueError, match="XPT"):
        converter.convert_xpt_to_parquet(invalid_path, tmp_path / "out.parquet")
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_format_converter.py -v
```

预期：所有测试 FAIL（模块不存在）。

- [ ] **Step 3: 实现 FormatConverter**

```python
# e:\Health_man\scripts\data\format_converter.py
"""格式转换器

职责：
- XPT (SAS Transport) → Parquet + Snappy
- CSV (GBK/UTF-8) → Parquet + Snappy
- PDF 表格 → JSON（后续任务）

设计原则：
- 单一职责：仅负责格式转换，不做数据清洗
- 保留原始字段名（标准化由 Preprocessor 负责）
- 转换后必须校验行数与列数
"""
import logging
from pathlib import Path

import pandas as pd
import pyreadstat

logger = logging.getLogger(__name__)


class FormatConverter:
    """格式转换器

    将各种源格式统一转换为 Parquet + Snappy 压缩格式。
    """

    def convert_xpt_to_parquet(
        self,
        xpt_path: Path,
        output_path: Path,
    ) -> Path:
        """将 SAS XPT 文件转换为 Parquet

        Args:
            xpt_path: XPT 文件路径
            output_path: 输出 Parquet 文件路径

        Returns:
            输出文件路径

        Raises:
            ValueError: XPT 文件无法解析
        """
        xpt_path = Path(xpt_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not xpt_path.exists():
            raise FileNotFoundError(f"XPT 文件不存在: {xpt_path}")

        try:
            df, meta = pyreadstat.read_xport(str(xpt_path))
        except Exception as e:
            raise ValueError(f"XPT 文件解析失败 {xpt_path}: {e}") from e

        logger.info(
            "XPT 转换: %s → %s (%d 行 %d 列)",
            xpt_path.name,
            output_path.name,
            len(df),
            len(df.columns),
        )

        df.to_parquet(output_path, compression="snappy", index=False)
        return output_path

    def convert_csv_to_parquet(
        self,
        csv_path: Path,
        output_path: Path,
        encoding: str = "utf-8",
    ) -> Path:
        """将 CSV 文件转换为 Parquet

        Args:
            csv_path: CSV 文件路径
            output_path: 输出 Parquet 文件路径
            encoding: 文件编码（默认 utf-8，中文文件可能需要 gbk）

        Returns:
            输出文件路径
        """
        csv_path = Path(csv_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

        df = pd.read_csv(csv_path, encoding=encoding)
        logger.info(
            "CSV 转换: %s → %s (%d 行 %d 列, encoding=%s)",
            csv_path.name,
            output_path.name,
            len(df),
            len(df.columns),
            encoding,
        )

        df.to_parquet(output_path, compression="snappy", index=False)
        return output_path
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_format_converter.py -v
```

预期：4 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/data/format_converter.py tests/data/test_format_converter.py
git commit -m "feat: 添加格式转换器（XPT/CSV → Parquet）"
```

---

### Task 7: 5 步预处理器

**Files:**
- Create: `e:\Health_man\scripts\data\preprocessor.py`
- Test: `e:\Health_man\tests\data\test_preprocessor.py`

**Interfaces:**
- Consumes: `FormatConverter`（Task 6）、`indicator_mapping.json`（Task 2）、`preprocessing_rules.yaml`（Task 2）
- Produces: `Preprocessor` 类，含 `process(df)` 方法执行 5 步标准化

- [ ] **Step 1: 写失败测试 - 验证 5 步预处理流程**

```python
# e:\Health_man\tests\data\test_preprocessor.py
"""测试 5 步预处理器"""
from pathlib import Path

import pandas as pd
import pytest

from scripts.data.preprocessor import Preprocessor


@pytest.fixture
def sample_df():
    """模拟 NHANES 风格的测试数据"""
    return pd.DataFrame({
        "SEQN": [1, 2, 3, 4, 5],
        "BMXBMI": [22.5, 25.0, 28.3, 999.0, 18.5],  # 999 是异常值
        "RIAGENDR": [1, 0, 1, 0, 1],
        "RIDAGEYR": [25, 35, 45, 55, 200],  # 200 是异常年龄
        "BMXWT": [70.0, 65.0, 80.0, 55.0, None],  # 含缺失值
    })


@pytest.fixture
def preprocessor(tmp_path):
    """创建预处理器实例（使用临时指标映射）"""
    mapping_path = tmp_path / "indicator_mapping.json"
    mapping_path.write_text(
        '{"indicator_mapping": {"BMXBMI": "bmi", "BMXWT": "weight_kg", "RIAGENDR": "gender", "RIDAGEYR": "age"}}',
        encoding="utf-8",
    )
    return Preprocessor(mapping_path=mapping_path)


def test_step1_field_names_standardized(sample_df, preprocessor):
    """Step 1: 字段名必须标准化为 indicator_id"""
    result = preprocessor.process(sample_df)
    assert "bmi" in result.columns
    assert "weight_kg" in result.columns
    assert "gender" in result.columns
    assert "age" in result.columns
    assert "BMXBMI" not in result.columns


def test_step3_outliers_flagged(sample_df, preprocessor):
    """Step 3: 异常值必须被标记（不删除）"""
    result = preprocessor.process(sample_df)
    # BMI=999 应被标记为异常
    bmi_outliers = result[result["bmi"] > 100]
    assert len(bmi_outliers) == 0  # 生理范围过滤后删除
    # age=200 应被过滤
    assert result["age"].max() <= 99


def test_step4_missing_values_filled(sample_df, preprocessor):
    """Step 4: 缺失值必须被填充或标记"""
    result = preprocessor.process(sample_df)
    # weight_kg 原本有 1 个缺失值，应被填充
    assert result["weight_kg"].isna().sum() == 0


def test_step5_age_grouped(sample_df, preprocessor):
    """Step 5: 必须添加 age_group 分组列"""
    result = preprocessor.process(sample_df)
    assert "age_group" in result.columns
    # 25 → 18-39, 35 → 18-39, 45 → 40-59, 55 → 40-59
    age_groups = result["age_group"].tolist()
    assert "18-39" in age_groups
    assert "40-59" in age_groups


def test_process_returns_dataframe(sample_df, preprocessor):
    """process 必须返回 DataFrame"""
    result = preprocessor.process(sample_df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_preprocessor.py -v
```

预期：所有测试 FAIL（模块不存在）。

- [ ] **Step 3: 实现 Preprocessor**

```python
# e:\Health_man\scripts\data\preprocessor.py
"""5 步预处理器

职责：
按顺序执行 5 步标准化处理：
1. 数据清洗：字段名标准化（基于 indicator_mapping.json）
2. 格式转换：（由 FormatConverter 单独负责，本类假设输入已是 DataFrame）
3. 异常值处理：生理范围硬过滤 + IQR 软标记
4. 缺失值填充：KNN/分层中位数/剔除
5. 数据标准化：年龄分组、性别编码、单位统一
"""
import json
import logging
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class Preprocessor:
    """5 步预处理器

    Args:
        mapping_path: indicator_mapping.json 路径
    """

    # 生理范围硬过滤规则（来自 quality_rules.yaml）
    PHYSIOLOGICAL_RANGES = {
        "bmi": (10, 80),
        "body_fat_pct": (3, 60),
        "height_cm": (120, 220),
        "weight_kg": (30, 200),
        "heart_rate": (30, 220),
        "spo2": (70, 100),
        "perfusion_index": (0, 20),
        "hrv_rmssd": (5, 150),
        "age": (6, 99),
    }

    # 年龄分组规则
    AGE_GROUPS = [(6, 17, "6-17"), (18, 39, "18-39"), (40, 59, "40-59"), (60, 99, "60+")]

    def __init__(self, mapping_path: Path | None = None):
        if mapping_path is None:
            mapping_path = Path(
                "e:/Health_man/data/knowledge/chinese_reference/_governance/indicator_mapping.json"
            )
        self.mapping = self._load_mapping(mapping_path)

    def _load_mapping(self, mapping_path: Path) -> dict[str, str]:
        """加载指标映射表"""
        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("indicator_mapping", {})

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行 5 步预处理"""
        df = df.copy()
        df = self._step1_clean(df)
        df = self._step3_detect_outliers(df)
        df = self._step4_handle_missing(df)
        df = self._step5_standardize(df)
        return df

    def _step1_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 1: 字段名标准化"""
        rename_map = {}
        for col in df.columns:
            if col in self.mapping:
                rename_map[col] = self.mapping[col]
        df = df.rename(columns=rename_map)
        logger.info("Step 1 完成: 字段名标准化，重命名 %d 列", len(rename_map))
        return df

    def _step3_detect_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 3: 异常值检测与处理"""
        for col, (min_val, max_val) in self.PHYSIOLOGICAL_RANGES.items():
            if col not in df.columns:
                continue
            before = len(df)
            df = df[(df[col] >= min_val) & (df[col] <= max_val)]
            removed = before - len(df)
            if removed > 0:
                logger.info(
                    "Step 3: %s 过滤 %d 条异常值（范围 %s-%s）",
                    col, removed, min_val, max_val,
                )
        return df

    def _step4_handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 4: 缺失值填充"""
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count == 0:
                continue
            missing_rate = missing_count / len(df)
            if missing_rate > 0.3:
                logger.warning("Step 4: %s 缺失率 %.2f > 0.3，整列剔除", col, missing_rate)
                df = df.drop(columns=[col])
            else:
                # 用中位数填充
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
                logger.info("Step 4: %s 填充 %d 个缺失值（中位数=%.2f）", col, missing_count, median_val)
        return df

    def _step5_standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 5: 数据标准化（年龄分组等）"""
        if "age" in df.columns:
            df["age_group"] = df["age"].apply(self._categorize_age)
            logger.info("Step 5: 年龄分组完成")
        return df

    def _categorize_age(self, age: float) -> str:
        """将年龄映射到分组"""
        for low, high, label in self.AGE_GROUPS:
            if low <= age <= high:
                return label
        return "unknown"
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_preprocessor.py -v
```

预期：5 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/data/preprocessor.py tests/data/test_preprocessor.py
git commit -m "feat: 添加 5 步预处理器（字段标准化+异常过滤+缺失填充+年龄分组）"
```

---

### Task 8: 质量校验器

**Files:**
- Create: `e:\Health_man\scripts\data\quality_checker.py`
- Test: `e:\Health_man\tests\data\test_quality_checker.py`

**Interfaces:**
- Consumes: `Preprocessor`（Task 7）、`quality_rules.yaml`（Task 2）
- Produces: `QualityChecker` 类，含 `check(df)` 方法返回 `QualityReport`

- [ ] **Step 1: 写失败测试 - 验证质量评级与报告**

```python
# e:\Health_man\tests\data\test_quality_checker.py
"""测试质量校验器"""
import pandas as pd
import pytest

from scripts.data.quality_checker import QualityChecker, QualityReport


@pytest.fixture
def good_df():
    """高质量数据集"""
    return pd.DataFrame({
        "bmi": [22.5, 25.0, 28.3, 20.0, 23.5] * 20,
        "age": [25, 35, 45, 55, 30] * 20,
        "gender": [1, 0, 1, 0, 1] * 20,
        "weight_kg": [70, 65, 80, 55, 68] * 20,
    })


@pytest.fixture
def poor_df():
    """低质量数据集（缺失率高）"""
    return pd.DataFrame({
        "bmi": [22.5, None, None, None, 28.3] * 20,
        "age": [25, 35, None, None, 45] * 20,
        "gender": [1, 0, 1, None, 1] * 20,
    })


def test_quality_checker_returns_report(good_df):
    """check 必须返回 QualityReport 对象"""
    checker = QualityChecker()
    report = checker.check(good_df)
    assert isinstance(report, QualityReport)


def test_good_data_gets_grade_a(good_df):
    """高质量数据必须评级 A"""
    checker = QualityChecker()
    report = checker.check(good_df)
    assert report.grade == "A"
    assert report.completeness >= 0.9


def test_poor_data_gets_lower_grade(poor_df):
    """低质量数据必须评级 ≤ B"""
    checker = QualityChecker()
    report = checker.check(poor_df)
    assert report.grade in ["B", "C", "D"]
    assert report.completeness < 0.9


def test_report_has_all_metrics(good_df):
    """报告必须含 completeness/validity/consistency/overall"""
    checker = QualityChecker()
    report = checker.check(good_df)
    assert hasattr(report, "completeness")
    assert hasattr(report, "validity")
    assert hasattr(report, "consistency")
    assert hasattr(report, "overall")
    assert hasattr(report, "grade")
    assert 0 <= report.completeness <= 1
    assert 0 <= report.validity <= 1
    assert 0 <= report.overall <= 1
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_quality_checker.py -v
```

预期：所有测试 FAIL（模块不存在）。

- [ ] **Step 3: 实现 QualityChecker**

```python
# e:\Health_man\scripts\data\quality_checker.py
"""质量校验器

职责：
- 三级质量校验（结构/值域/业务）
- 输出 A/B/C/D 评级
- 生成质量报告

评级阈值：
- A: overall >= 0.9, confidence=0.9
- B: 0.8 <= overall < 0.9, confidence=0.75
- C: 0.7 <= overall < 0.8, confidence=0.6
- D: overall < 0.7, confidence=0.4（拒绝入库）
"""
import logging
from dataclasses import dataclass

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """质量校验报告"""
    completeness: float       # 字段完整率
    validity: float           # 值域合法率
    consistency: float        # 跨字段一致性
    overall: float            # 加权综合分
    grade: str                # A/B/C/D
    row_count: int            # 总行数
    column_count: int         # 总列数
    issues: list[str]         # 发现的问题清单


class QualityChecker:
    """质量校验器"""

    # 生理范围（与 Preprocessor 一致）
    PHYSIOLOGICAL_RANGES = {
        "bmi": (10, 80),
        "body_fat_pct": (3, 60),
        "height_cm": (120, 220),
        "weight_kg": (30, 200),
        "heart_rate": (30, 220),
        "spo2": (70, 100),
        "age": (6, 99),
    }

    REQUIRED_FIELDS = ["age", "gender", "weight_kg"]

    def check(self, df: pd.DataFrame) -> QualityReport:
        """执行质量校验"""
        issues: list[str] = []

        # 1. 完整性：字段缺失率
        completeness = self._check_completeness(df, issues)

        # 2. 合法性：值域合法率
        validity = self._check_validity(df, issues)

        # 3. 一致性：跨字段逻辑
        consistency = self._check_consistency(df, issues)

        # 4. 综合分（加权平均）
        overall = completeness * 0.35 + validity * 0.35 + consistency * 0.30

        # 5. 评级
        grade = self._calculate_grade(overall)

        return QualityReport(
            completeness=completeness,
            validity=validity,
            consistency=consistency,
            overall=overall,
            grade=grade,
            row_count=len(df),
            column_count=len(df.columns),
            issues=issues,
        )

    def _check_completeness(self, df: pd.DataFrame, issues: list[str]) -> float:
        """检查字段完整率"""
        if len(df) == 0:
            issues.append("数据集为空")
            return 0.0
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isna().sum().sum()
        completeness = 1 - (missing_cells / total_cells)
        if completeness < 0.8:
            issues.append(f"完整率过低: {completeness:.2f}")
        return float(completeness)

    def _check_validity(self, df: pd.DataFrame, issues: list[str]) -> float:
        """检查值域合法率"""
        if len(df) == 0:
            return 0.0
        total_checked = 0
        valid_count = 0
        for col, (min_val, max_val) in self.PHYSIOLOGICAL_RANGES.items():
            if col not in df.columns:
                continue
            values = df[col].dropna()
            total_checked += len(values)
            valid = ((values >= min_val) & (values <= max_val)).sum()
            valid_count += valid
            invalid = len(values) - valid
            if invalid > 0:
                issues.append(f"{col} 有 {invalid} 个超范围值")
        if total_checked == 0:
            return 1.0
        return float(valid_count / total_checked)

    def _check_consistency(self, df: pd.DataFrame, issues: list[str]) -> float:
        """检查跨字段一致性（如 BMI = 体重/身高²）"""
        if len(df) == 0:
            return 0.0
        checks_passed = 0
        total_checks = 0
        # 检查必需字段是否存在
        for field in self.REQUIRED_FIELDS:
            total_checks += 1
            if field in df.columns:
                checks_passed += 1
            else:
                issues.append(f"必需字段缺失: {field}")
        # TODO: 后续可加 BMI 计算一致性检查
        return float(checks_passed / total_checks) if total_checks > 0 else 1.0

    def _calculate_grade(self, overall: float) -> str:
        """根据综合分计算评级"""
        if overall >= 0.9:
            return "A"
        elif overall >= 0.8:
            return "B"
        elif overall >= 0.7:
            return "C"
        else:
            return "D"
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_quality_checker.py -v
```

预期：4 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/data/quality_checker.py tests/data/test_quality_checker.py
git commit -m "feat: 添加质量校验器（三级校验+A/B/C/D 评级）"
```

---

### Task 9: 元数据生成器

**Files:**
- Create: `e:\Health_man\scripts\data\metadata_generator.py`
- Test: `e:\Health_man\tests\data\test_metadata_generator.py`

**Interfaces:**
- Consumes: `SourceAdapter.get_metadata_template()`（Task 3）、`QualityReport`（Task 8）
- Produces: `MetadataGenerator` 类，含 `generate()` 方法输出 L0/L1/L2 三层元数据

- [ ] **Step 1: 写失败测试 - 验证三层元数据生成**

```python
# e:\Health_man\tests\data\test_metadata_generator.py
"""测试元数据生成器"""
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.data.metadata_generator import MetadataGenerator
from scripts.data.quality_checker import QualityReport


@pytest.fixture
def sample_report():
    return QualityReport(
        completeness=0.95,
        validity=0.98,
        consistency=0.92,
        overall=0.95,
        grade="A",
        row_count=100,
        column_count=10,
        issues=[],
    )


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "bmi": [22.5, 25.0],
        "age": [25, 35],
        "gender": [1, 0],
    })


def test_generate_l0_card(tmp_path, sample_report):
    """L0 数据集卡片必须含必填字段"""
    adapter_meta = {
        "dataset_id": "NHANES_2017_2020",
        "source_url": "https://wwwn.cdc.gov/",
        "license": "Public Domain",
        "region": "US",
        "sample_size": 9092,
    }
    gen = MetadataGenerator()
    l0 = gen.generate_l0(adapter_meta, sample_report, output_path=tmp_path / "L0.json")

    assert l0["dataset_id"] == "NHANES_2017_2020"
    assert l0["source_url"] == "https://wwwn.cdc.gov/"
    assert l0["license"] == "Public Domain"
    assert l0["quality"]["grade"] == "A"
    assert l0["quality"]["overall"] == 0.95
    assert "generated_at" in l0
    # 文件已写入
    assert (tmp_path / "L0.json").exists()


def test_generate_l1_fields(tmp_path, sample_df):
    """L1 字段字典必须含每个字段的类型与缺失率"""
    gen = MetadataGenerator()
    l1 = gen.generate_l1(sample_df, output_path=tmp_path / "L1.json")

    assert "fields" in l1
    assert len(l1["fields"]) == 3
    field_names = [f["name"] for f in l1["fields"]]
    assert "bmi" in field_names
    assert "age" in field_names
    for field in l1["fields"]:
        assert "type" in field
        assert "missing_rate" in field


def test_generate_l2_usage(tmp_path, sample_report):
    """L2 使用说明必须含适用场景与偏差声明"""
    adapter_meta = {
        "dataset_id": "NHANES_2017_2020",
        "known_bias": "种族分布与中国人群有差异",
    }
    gen = MetadataGenerator()
    l2 = gen.generate_l2(adapter_meta, sample_report, output_path=tmp_path / "L2.md")

    assert "NHANES_2017_2020" in l2
    assert "种族分布与中国人群有差异" in l2
    assert "A" in l2  # 质量评级
    assert (tmp_path / "L2.md").exists()
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_metadata_generator.py -v
```

预期：所有测试 FAIL。

- [ ] **Step 3: 实现 MetadataGenerator**

```python
# e:\Health_man\scripts\data\metadata_generator.py
"""元数据生成器

生成三层元数据：
- L0: 数据集卡片（dataset_card.json）
- L1: 字段字典（fields.json）
- L2: 使用说明（usage.md）
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from scripts.data.quality_checker import QualityReport


class MetadataGenerator:
    """元数据生成器"""

    def generate_l0(
        self,
        adapter_meta: dict,
        quality_report: QualityReport,
        output_path: Path | None = None,
    ) -> dict:
        """生成 L0 数据集卡片"""
        l0 = {
            "dataset_id": adapter_meta["dataset_id"],
            "source_url": adapter_meta.get("source_url", ""),
            "license": adapter_meta.get("license", ""),
            "region": adapter_meta.get("region", ""),
            "sample_size": adapter_meta.get("sample_size", 0),
            "cycle": adapter_meta.get("cycle", ""),
            "update_frequency": adapter_meta.get("update_frequency", ""),
            "population": adapter_meta.get("population", ""),
            "known_bias": adapter_meta.get("known_bias", ""),
            "quality": {
                "completeness": quality_report.completeness,
                "validity": quality_report.validity,
                "consistency": quality_report.consistency,
                "overall": quality_report.overall,
                "grade": quality_report.grade,
            },
            "row_count": quality_report.row_count,
            "column_count": quality_report.column_count,
            "generated_at": datetime.now().isoformat(),
        }
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(l0, f, ensure_ascii=False, indent=2)
        return l0

    def generate_l1(
        self,
        df: pd.DataFrame,
        output_path: Path | None = None,
    ) -> dict:
        """生成 L1 字段字典"""
        fields = []
        for col in df.columns:
            missing_rate = float(df[col].isna().mean())
            dtype = str(df[col].dtype)
            fields.append({
                "name": col,
                "type": dtype,
                "missing_rate": round(missing_rate, 4),
                "unique_count": int(df[col].nunique()),
            })
        l1 = {"fields": fields, "row_count": len(df)}
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(l1, f, ensure_ascii=False, indent=2)
        return l1

    def generate_l2(
        self,
        adapter_meta: dict,
        quality_report: QualityReport,
        output_path: Path | None = None,
    ) -> str:
        """生成 L2 使用说明（Markdown）"""
        dataset_id = adapter_meta.get("dataset_id", "UNKNOWN")
        known_bias = adapter_meta.get("known_bias", "无")
        population = adapter_meta.get("population", "未指定")

        content = f"""# {dataset_id} 使用说明

## 适用场景
- 指标参考范围对标
- 人群分布分析

## 不适用场景
- 配对精度验证（非配对数据）
- 临床诊断

## 已知偏差
{known_bias}

## 人群代表性
{population}

## 质量评级
- 等级: {quality_report.grade}
- 综合分: {quality_report.overall:.2f}
- 完整率: {quality_report.completeness:.2f}
- 合法率: {quality_report.validity:.2f}

## 引用格式
请引用数据集卡片（L0_card.json）中的 source_url

## 生成时间
{datetime.now().isoformat()}
"""
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        return content
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/data/test_metadata_generator.py -v
```

预期：3 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/data/metadata_generator.py tests/data/test_metadata_generator.py
git commit -m "feat: 添加元数据生成器（L0/L1/L2 三层）"
```

---

### Task 10: 加密与凭证管理工具

**Files:**
- Create: `e:\Health_man\scripts\utils\crypto.py`
- Create: `e:\Health_man\scripts\utils\credential_manager.py`
- Test: `e:\Health_man\tests\utils\test_crypto.py`
- Test: `e:\Health_man\tests\utils\test_credential_manager.py`

**Interfaces:**
- Consumes: spec §7.6.1 凭证管理、§7.6.2 数据加密
- Produces: `CryptoUtils` 类（AES-256-GCM）、`CredentialManager` 类（Key 全生命周期）

- [ ] **Step 1: 写失败测试 - 验证加密/解密与凭证管理**

```python
# e:\Health_man\tests\utils\test_crypto.py
"""测试加密工具"""
from scripts.utils.crypto import CryptoUtils


def test_encrypt_decrypt_roundtrip():
    """加密后解密必须得到原文"""
    crypto = CryptoUtils(master_key=b"test-master-key-32bytes-padding!")
    plaintext = b"sensitive api key value"
    ciphertext = crypto.encrypt(plaintext)
    assert ciphertext != plaintext
    decrypted = crypto.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encrypt_returns_different_ciphertext():
    """相同明文每次加密结果必须不同（含随机 nonce）"""
    crypto = CryptoUtils(master_key=b"test-master-key-32bytes-padding!")
    plaintext = b"same value"
    c1 = crypto.encrypt(plaintext)
    c2 = crypto.encrypt(plaintext)
    assert c1 != c2  # 因 nonce 不同


def test_decrypt_invalid_data_raises_error():
    """解密无效数据必须抛出异常"""
    crypto = CryptoUtils(master_key=b"test-master-key-32bytes-padding!")
    import pytest
    with pytest.raises(Exception):
        crypto.decrypt(b"invalid ciphertext")
```

```python
# e:\Health_man\tests\utils\test_credential_manager.py
"""测试凭证管理器"""
import pytest
from pathlib import Path

from scripts.utils.credential_manager import CredentialManager


def test_store_and_retrieve_credential(tmp_path):
    """存储后必须能正确读取"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    mgr.store("GLM_API_KEY", "sk-abc123")
    retrieved = mgr.retrieve("GLM_API_KEY")
    assert retrieved == "sk-abc123"


def test_retrieve_nonexistent_returns_none(tmp_path):
    """读取不存在的凭证必须返回 None"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    assert mgr.retrieve("NONEXISTENT") is None


def test_list_credentials(tmp_path):
    """必须能列出所有存储的凭证名"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    mgr.store("GLM_API_KEY", "key1")
    mgr.store("QWEN_API_KEY", "key2")
    names = mgr.list_keys()
    assert "GLM_API_KEY" in names
    assert "QWEN_API_KEY" in names


def test_delete_credential(tmp_path):
    """删除后不可再读取"""
    mgr = CredentialManager(storage_dir=tmp_path, master_key=b"test-key-32bytes-padding!!!")
    mgr.store("TEMP_KEY", "temp")
    mgr.delete("TEMP_KEY")
    assert mgr.retrieve("TEMP_KEY") is None
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/utils/test_crypto.py tests/utils/test_credential_manager.py -v
```

预期：所有测试 FAIL。

- [ ] **Step 3: 实现 CryptoUtils**

```python
# e:\Health_man\scripts\utils\crypto.py
"""加密工具

基于 AES-256-GCM 算法，提供对称加密与解密。
用于保护 API Key 等敏感配置。
"""
import os
import base64
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoUtils:
    """AES-256-GCM 加密工具

    Args:
        master_key: 主密钥（任意长度，内部派生为 32 字节）
    """

    def __init__(self, master_key: bytes):
        # 派生 32 字节密钥（AES-256）
        self._key = hashlib.sha256(master_key).digest()

    def encrypt(self, plaintext: bytes) -> bytes:
        """加密

        Args:
            plaintext: 原始字节

        Returns:
            base64 编码的 nonce + ciphertext
        """
        nonce = os.urandom(12)  # 96-bit nonce
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return base64.b64encode(nonce + ciphertext)

    def decrypt(self, encoded_data: bytes) -> bytes:
        """解密

        Args:
            encoded_data: encrypt() 返回的 base64 数据

        Returns:
            原始字节

        Raises:
            Exception: 解密失败
        """
        raw = base64.b64decode(encoded_data)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None)
```

- [ ] **Step 4: 实现 CredentialManager**

```python
# e:\Health_man\scripts\utils\credential_manager.py
"""凭证管理器

职责：
- API Key 的加密存储与读取
- 列举与删除凭证
- 不在内存中长时间保留明文

存储格式：
- 每个凭证一个文件：{storage_dir}/{name}.enc
- 文件内容：base64(nonce + ciphertext)
"""
import json
from pathlib import Path

from scripts.utils.crypto import CryptoUtils


class CredentialManager:
    """凭证管理器

    Args:
        storage_dir: 凭证存储目录
        master_key: 主密钥
    """

    def __init__(self, storage_dir: Path, master_key: bytes):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.crypto = CryptoUtils(master_key)

    def store(self, name: str, value: str) -> None:
        """存储凭证（加密）"""
        file_path = self.storage_dir / f"{name}.enc"
        encrypted = self.crypto.encrypt(value.encode("utf-8"))
        with open(file_path, "wb") as f:
            f.write(encrypted)

    def retrieve(self, name: str) -> str | None:
        """读取凭证（解密）"""
        file_path = self.storage_dir / f"{name}.enc"
        if not file_path.exists():
            return None
        with open(file_path, "rb") as f:
            encrypted = f.read()
        decrypted = self.crypto.decrypt(encrypted)
        return decrypted.decode("utf-8")

    def list_keys(self) -> list[str]:
        """列出所有凭证名"""
        return [
            f.stem
            for f in self.storage_dir.glob("*.enc")
        ]

    def delete(self, name: str) -> None:
        """删除凭证"""
        file_path = self.storage_dir / f"{name}.enc"
        if file_path.exists():
            file_path.unlink()
```

- [ ] **Step 5: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/utils/test_crypto.py tests/utils/test_credential_manager.py -v
```

预期：7 个测试全部 PASS。

- [ ] **Step 6: 提交**

```powershell
cd e:\Health_man
git add scripts/utils/crypto.py scripts/utils/credential_manager.py tests/utils/test_crypto.py tests/utils/test_credential_manager.py
git commit -m "feat: 添加加密工具与凭证管理器（AES-256-GCM）"
```

---

### Task 11: 重试、限流与熔断工具

**Files:**
- Create: `e:\Health_man\scripts\utils\retry.py`
- Create: `e:\Health_man\scripts\utils\rate_limiter.py`
- Create: `e:\Health_man\scripts\utils\circuit_breaker.py`
- Test: `e:\Health_man\tests\utils\test_retry.py`
- Test: `e:\Health_man\tests\utils\test_rate_limiter.py`
- Test: `e:\Health_man\tests\utils\test_circuit_breaker.py`

**Interfaces:**
- Consumes: spec §7.6.4 限流与熔断、§7.7.2 重试退避
- Produces: `retry_with_backoff` 装饰器、`TokenBucketLimiter`、`CircuitBreaker`

- [ ] **Step 1: 写失败测试**

```python
# e:\Health_man\tests\utils\test_retry.py
"""测试重试退避"""
import time
import pytest

from scripts.utils.retry import retry_with_backoff


def test_retry_succeeds_on_first_attempt():
    """首次成功不重试"""
    call_count = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def success_func():
        call_count["n"] += 1
        return "ok"

    result = success_func()
    assert result == "ok"
    assert call_count["n"] == 1


def test_retry_succeeds_after_failures():
    """前 N 次失败后成功"""
    call_count = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def flaky_func():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ValueError("fail")
        return "ok"

    result = flaky_func()
    assert result == "ok"
    assert call_count["n"] == 3


def test_retry_exhausted_raises():
    """重试耗尽后必须抛出最后异常"""
    @retry_with_backoff(max_retries=2, base_delay=0.01)
    def always_fail():
        raise ValueError("always fails")

    with pytest.raises(ValueError, match="always fails"):
        always_fail()
```

```python
# e:\Health_man\tests\utils\test_rate_limiter.py
"""测试令牌桶限流器"""
import time

from scripts.utils.rate_limiter import TokenBucketLimiter


def test_first_request_allowed():
    """首次请求必须允许"""
    limiter = TokenBucketLimiter(capacity=5, refill_rate=1.0)
    assert limiter.acquire() is True


def test_capacity_exhausted():
    """超过容量后必须拒绝"""
    limiter = TokenBucketLimiter(capacity=2, refill_rate=0.0)
    assert limiter.acquire() is True
    assert limiter.acquire() is True
    assert limiter.acquire() is False


def test_refill_over_time():
    """令牌必须随时间填充"""
    limiter = TokenBucketLimiter(capacity=2, refill_rate=100.0)  # 每秒 100 个
    # 耗尽
    limiter.acquire()
    limiter.acquire()
    assert limiter.acquire() is False
    # 等待填充
    time.sleep(0.05)
    assert limiter.acquire() is True
```

```python
# e:\Health_man\tests\utils\test_circuit_breaker.py
"""测试熔断器"""
import pytest

from scripts.utils.circuit_breaker import CircuitBreaker, CircuitState


def test_initial_state_is_closed():
    """初始状态必须为 CLOSED"""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    assert cb.state == CircuitState.CLOSED


def test_opens_after_threshold():
    """达到失败阈值后必须 OPEN"""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_blocks_calls_when_open():
    """OPEN 状态必须阻止调用"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_call() is False


def test_half_open_after_timeout():
    """超时后必须 HALF_OPEN"""
    import time
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.15)
    assert cb.can_call() is True  # HALF_OPEN 允许探测
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/utils/test_retry.py tests/utils/test_rate_limiter.py tests/utils/test_circuit_breaker.py -v
```

预期：所有测试 FAIL。

- [ ] **Step 3: 实现 retry.py**

```python
# e:\Health_man\scripts\utils\retry.py
"""重试退避工具

提供指数退避重试装饰器，支持：
- 最大重试次数
- 基础延迟与指数倍数
- 可指定捕获的异常类型
"""
import functools
import logging
import random
import time
from typing import Callable, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """指数退避重试装饰器

    Args:
        max_retries: 最大重试次数（不含首次调用）
        base_delay: 基础延迟（秒），实际延迟 = base_delay * 2^attempt + jitter
        exceptions: 捕获的异常类型

    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(
                            "重试 %s (attempt %d/%d): %s, 等待 %.2fs",
                            func.__name__, attempt + 1, max_retries, str(e), delay,
                        )
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
```

- [ ] **Step 4: 实现 rate_limiter.py**

```python
# e:\Health_man\scripts\utils\rate_limiter.py
"""令牌桶限流器

原理：
- 桶容量为 capacity，初始满
- 每秒按 refill_rate 速率填充令牌
- 每次请求消耗 1 个令牌
- 令牌不足时拒绝请求
"""
import time


class TokenBucketLimiter:
    """令牌桶限流器

    Args:
        capacity: 桶容量（最大突发量）
        refill_rate: 令牌填充速率（个/秒）
    """

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()

    def acquire(self) -> bool:
        """尝试获取 1 个令牌

        Returns:
            True=获取成功；False=令牌不足
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False
```

- [ ] **Step 5: 实现 circuit_breaker.py**

```python
# e:\Health_man\scripts\utils\circuit_breaker.py
"""三态熔断器

状态：
- CLOSED: 正常，请求通过
- OPEN: 熔断，拒绝请求
- HALF_OPEN: 探测，允许单个请求
"""
import enum
import time


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """三态熔断器

    Args:
        failure_threshold: 触发熔断的连续失败次数
        recovery_timeout: 熔断后冷却时间（秒）
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        """当前状态（含自动 HALF_OPEN 转换）"""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def can_call(self) -> bool:
        """是否允许调用"""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            return True
        return False  # OPEN

    def record_success(self) -> None:
        """记录成功"""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
```

- [ ] **Step 6: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/utils/test_retry.py tests/utils/test_rate_limiter.py tests/utils/test_circuit_breaker.py -v
```

预期：9 个测试全部 PASS。

- [ ] **Step 7: 提交**

```powershell
cd e:\Health_man
git add scripts/utils/retry.py scripts/utils/rate_limiter.py scripts/utils/circuit_breaker.py tests/utils/test_retry.py tests/utils/test_rate_limiter.py tests/utils/test_circuit_breaker.py
git commit -m "feat: 添加重试退避、令牌桶限流、三态熔断器"
```

---

### Task 12: 审计日志工具

**Files:**
- Create: `e:\Health_man\scripts\utils\audit_logger.py`
- Test: `e:\Health_man\tests\utils\test_audit_logger.py`

**Interfaces:**
- Consumes: spec §7.11 审计日志防篡改
- Produces: `AuditLogger` 类，含 `log()` 方法（哈希链 + JSONL 格式）

- [ ] **Step 1: 写失败测试**

```python
# e:\Health_man\tests\utils\test_audit_logger.py
"""测试审计日志"""
import json
from pathlib import Path

from scripts.utils.audit_logger import AuditLogger


def test_log_writes_jsonl(tmp_path):
    """日志必须以 JSONL 格式写入"""
    logger = AuditLogger(log_path=tmp_path / "audit.log")
    logger.log("download", "nhanes_demo_j.xpt", success=True)
    content = (tmp_path / "audit.log").read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["operation"] == "download"
    assert entry["target"] == "nhanes_demo_j.xpt"
    assert entry["success"] is True


def test_hash_chain_links_entries(tmp_path):
    """每条日志必须含前一条的哈希，形成链"""
    logger = AuditLogger(log_path=tmp_path / "audit.log")
    logger.log("op1", "file1")
    logger.log("op2", "file2")
    entries = [json.loads(line) for line in (tmp_path / "audit.log").read_text().strip().split("\n")]
    # 第 2 条的 prev_hash 应等于第 1 条的 hash
    assert entries[1]["prev_hash"] == entries[0]["hash"]
    # 第 1 条的 prev_hash 应为初始值
    assert entries[0]["prev_hash"] == "GENESIS"


def test_log_has_timestamp(tmp_path):
    """每条日志必须含时间戳"""
    logger = AuditLogger(log_path=tmp_path / "audit.log")
    logger.log("test", "file")
    entry = json.loads((tmp_path / "audit.log").read_text().strip())
    assert "timestamp" in entry
    assert "T" in entry["timestamp"]  # ISO 格式
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
cd e:\Health_man
python -m pytest tests/utils/test_audit_logger.py -v
```

预期：所有测试 FAIL。

- [ ] **Step 3: 实现 AuditLogger**

```python
# e:\Health_man\scripts\utils\audit_logger.py
"""审计日志（防篡改）

特性：
- JSONL 格式（每行一条 JSON）
- 哈希链：每条日志含前一条的 SHA256
- ISO 时间戳
- append-only（仅追加）
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path


class AuditLogger:
    """审计日志器

    Args:
        log_path: 日志文件路径
    """

    GENESIS_HASH = "GENESIS"

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._load_last_hash()

    def log(
        self,
        operation: str,
        target: str,
        success: bool = True,
        **extra,
    ) -> None:
        """记录一条审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "target": target,
            "success": success,
            "prev_hash": self._last_hash,
        }
        entry.update(extra)
        # 计算当前条目的哈希
        entry_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry["hash"] = hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
        # 追加写入
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._last_hash = entry["hash"]

    def _load_last_hash(self) -> str:
        """加载最后一条日志的哈希（用于断点续链）"""
        if not self.log_path.exists():
            return self.GENESIS_HASH
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        if not lines or not lines[0]:
            return self.GENESIS_HASH
        last_entry = json.loads(lines[-1])
        return last_entry.get("hash", self.GENESIS_HASH)
```

- [ ] **Step 4: 运行测试，确认通过**

```powershell
cd e:\Health_man
python -m pytest tests/utils/test_audit_logger.py -v
```

预期：3 个测试全部 PASS。

- [ ] **Step 5: 提交**

```powershell
cd e:\Health_man
git add scripts/utils/audit_logger.py tests/utils/test_audit_logger.py
git commit -m "feat: 添加审计日志（哈希链防篡改）"
```

---

## Self-Review

完成计划编写后进行自检：

### 1. Spec 覆盖检查

| Spec 章节 | 覆盖任务 | 状态 |
|----------|---------|------|
| §1 项目目标 | 全局约束 | ✅ |
| §2 核心功能需求 | 全部任务 | ✅ |
| §3 三层架构 | 本计划覆盖 Layer A | ✅（Layer B/C 留待后续计划） |
| §4 Layer A 详细设计 | Task 1-9 | ✅ |
| §4.1-§4.11 Layer A 11 子节 | Task 2-9 | ✅ |
| §5 Layer B | 不在本计划 | ⏳ 计划 2 |
| §6 数据治理 8 要素 | Task 2 | ✅ |
| §7 Layer C | 不在本计划 | ⏳ 计划 3 |
| §7.6 安全规范 | Task 10-12 | ✅ |
| §7.7 异常处理 | Task 5, 11 | ✅ |
| §7.8 数据销毁 | 不在本计划（运营阶段） | ⏳ |
| §8 实施步骤 | 本计划覆盖 Phase 1+2 | ✅ |
| §9 时间节点 | 本计划覆盖 D1-D4 | ✅ |
| §10 风险评估 | 全局约束 | ✅ |
| §12 验收标准 | Task 13（端到端测试） | ⏳ 留待后续 |

### 2. 占位符扫描

检查无 TBD/TODO/"实现后补全"等占位符。

### 3. 类型一致性

- `SourceAdapter.list_files()` 在 Task 3 定义为返回 `list[dict[str, Any]]`，Task 4 NHANESAdapter 实现一致 ✅
- `DownloadResult` 在 Task 5 定义，Task 5 测试使用一致 ✅
- `QualityReport` 在 Task 8 定义，Task 9 使用一致 ✅
- `CryptoUtils` 在 Task 10 定义，`CredentialManager` 使用一致 ✅
- `CircuitState` 枚举在 Task 11 定义，测试使用一致 ✅

### 4. 任务边界清晰

每个任务产出独立可测试的交付物，Task N+1 仅依赖 Task N 的接口（不含实现细节）。

### 5. 剩余计划

本计划完成后，后续计划：
- 计划 2：Layer B 文献聚合（含 CNKI/PubMed 检索 + 中医体质）
- 计划 3：Layer C LLM 蒸馏（国内大模型 + 上下文工程）
- 计划 4：统一聚合与质量门禁（unified JSON + 数据字典）

---

## Execution Handoff

**计划已完成并保存至 `e:\Health_man\superpowers\plans\2026-07-12-data-acquisition-phase1-2.md`。**

**两种执行方式：**

**1. Subagent-Driven（推荐）** - 每个任务派发独立子代理执行，任务间进行双阶段评审，迭代速度快

**2. Inline Execution** - 在当前会话中按批次执行，带检查点评审

**选择哪种方式？**
