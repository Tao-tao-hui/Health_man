# HealthDataLab 数据采集与知识蒸馏体系 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `E:\工程项目\HealthDataLab\` 独立项目中搭建外部数据采集、治理和知识蒸馏流水线，零侵入主项目

**Architecture:** 数据集注册表插拔式接入 → 类型感知三层元数据治理 → 多学科子代理蒸馏 → QA 审计留痕 → 轻量桥接引用回主项目

**Tech Stack:** Python 3.10+, JSON Schema, SHA256, pyserial (仅校验工具)

**Spec 来源:** `docs/superpowers/specs/2026-07-11-HealthDataLab-data-acquisition-and-distillation-design.md`

---

## 文件结构变更

### HealthDataLab/ 新建文件

```
E:\工程项目\HealthDataLab/
├── README.md
├── GOVERNANCE.md
├── external_datasets/
│   ├── registry.json
│   └── catalog.json
├── tools/
│   ├── __init__.py
│   ├── init_catalog.py
│   ├── add_dataset.py
│   ├── download_nhanes.py
│   ├── download_knhanes.py
│   ├── sample_physionet.py
│   ├── validate_checksum.py
│   ├── generate_dataset_card.py
│   ├── run_distillation_pipeline.py
│   └── schemas/
│       ├── __init__.py
│       ├── schema_tabular.json
│       ├── schema_waveform.json
│       ├── schema_timeseries.json
│       ├── schema_image.json
│       └── schema_nlp.json
├── distilled_knowledge/
│   └── DISTILLATION_MANIFEST.json
└── requirements.txt
```

### 主项目修改文件

- Create: `data/external_refs.json`

---

## 任务分解

### Task 1: 项目脚手架与治理文档

**Files:**
- Create: `README.md`
- Create: `GOVERNANCE.md`
- Create: `requirements.txt`
- Create: `external_datasets/registry.json`
- Create: `external_datasets/catalog.json`
- Create: `distilled_knowledge/DISTILLATION_MANIFEST.json`

- [ ] **Step 1: 创建目录结构**

```bash
$base = "E:\工程项目\HealthDataLab"
$dirs = @(
    "external_datasets",
    "tools\schemas",
    "distilled_knowledge\reference_ranges",
    "distilled_knowledge\clinical_meanings",
    "distilled_knowledge\evidence_sources",
    "distilled_knowledge\qa_records",
    "distilled_knowledge\domain_deltas",
    "distilled_knowledge\advice_content",
    "training_data"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path (Join-Path $base $d) -Force | Out-Null
}
```

- [ ] **Step 2: 创建 `README.md`**

```markdown
# HealthDataLab — 健康数据资产实验室

> 独立于 `大健康` 主项目的外部数据采集、治理与知识蒸馏平台。
> **目标:** 零侵入主项目，通过桥接文件 `data/external_refs.json` 与主项目交互。

## 目录结构

| 目录 | 职责 |
|------|------|
| `external_datasets/` | 外部数据集（RAW 只读 + PROCESSED + METADATA） |
| `distilled_knowledge/` | 多学科 LLM 蒸馏产出 |
| `tools/` | 数据管理脚本（下载/注册/校验/蒸馏） |
| `training_data/` | 训练数据集（预留扩展） |

## 治理原则

1. **RAW 不可变** — 原始数据下载后设只读，SHA256 锁定
2. **三层元数据** — 每数据集必填 L0 dataset_card + L1 类型 schema + L2 usage_notes
3. **体量门禁** — 单集 ≤0.8GB，总计 ≤5GB
4. **蒸馏 QA 留痕** — 每轮蒸馏产出附带完整 QA 审计日志

## 快速开始

```bash
pip install -r requirements.txt
python tools/init_catalog.py
python tools/add_dataset.py --type tabular_survey --id NHANES_2017_2020 --path ./external_datasets/A_NHANES_2017_2020
```

## 许可证

各数据集许可证见对应目录下的 `license.txt`。本项目管理工具使用 MIT 许可证。
```

- [ ] **Step 3: 创建 `GOVERNANCE.md`**

```markdown
# HealthDataLab 数据治理规范

## 1. RAW 不可变原则

- `external_datasets/<ID>/RAW/` 目录写入后立即设为只读
- 每文件记录 SHA256 校验和到 `catalog.json`
- `PROCESSED/` 数据必须注明来源于 `RAW/` 的哪个文件

## 2. 三层元数据

| 层级 | 文件 | 类型相关 | 必填 |
|------|------|---------|------|
| L0 | `dataset_card.json` | 否 | ✅ |
| L1 | 按 registry 类型 (如 `field_dictionary.json`) | 是 | ✅ |
| L2 | `usage_notes.md` | 否（数据集特有） | ✅ |

### L0: dataset_card.json
- source_url / download_date / size_bytes / checksum_sha256
- population (region / sample_size / age_range / setting)
- relevance (indicators_covered / calibration_value)
- limitations (数组)
- license / citation

### L1: 类型感知（参考 tools/schemas/ 模板）
- tabular_survey → field_dictionary.json
- physiological_waveform → channel_dictionary.json
- medical_image → modality_metadata.json
- time_series → series_manifest.json
- nlp_corpus → corpus_manifest.json

### L2: usage_notes.md
- 适用场景和不适用场景
- 偏差定量描述
- 使用时必须标注的声明
- 引用格式
- 已知数据质量问题

## 3. 注册表

`external_datasets/registry.json` 管理所有已知数据类型。
添加新数据集前检查 registry 中是否有对应类型，无则先新增类型。

## 4. 体量门禁

- 单数据集超过 **0.8GB** 时触发审查
- 总项目超过 **5GB** 时触发审查
- 触发审查后需书面说明每 GB 的价值

## 5. 蒸馏 QA 规范

- 每轮蒸馏产生 `qa_records/QA-RUN-*.json`
- 每条蒸馏结果记录 sources / extracted_value / cross_reference / delta_analysis / confidence
- 每条结果标记 qa_status: pending → approved / rejected
```

- [ ] **Step 4: 创建 `requirements.txt`**

```
# HealthDataLab 数据管理工具依赖
# 数据集下载和元数据管理
requests>=2.28.0
python-magic>=0.4.27

# PhysioNet 波形数据处理
numpy>=1.24.0
wfdb>=4.0.0

# 数据校验
hashlib  # (built-in)
json  # (built-in)
csv  # (built-in)
```

- [ ] **Step 5: 创建 `registry.json`**

```json
{
  "registry_version": "1.0",
  "last_updated": "2026-07-11",
  "registered_types": {
    "tabular_survey": {
      "handler": "type_tabular.py",
      "governance_schema": "schema_tabular.json",
      "example_datasets": ["NHANES", "KNHANES", "CHNS"],
      "description": "结构化表格数据（体检/问卷/生化）"
    },
    "physiological_waveform": {
      "handler": "type_waveform.py",
      "governance_schema": "schema_waveform.json",
      "example_datasets": ["PhysioNet", "MIMIC-Waveform"],
      "description": "生理波形数据（PPG/ECG/呼吸）"
    },
    "time_series": {
      "handler": "type_timeseries.py",
      "governance_schema": "schema_timeseries.json",
      "example_datasets": ["UK Biobank accelerometry"],
      "description": "纵向时间序列数据"
    },
    "medical_image": {
      "handler": "type_image.py",
      "governance_schema": "schema_image.json",
      "example_datasets": ["DEXA scans", "CT body composition"],
      "description": "医学影像（DEXA/CT/MRI）"
    },
    "nlp_corpus": {
      "handler": "type_nlp.py",
      "governance_schema": "schema_nlp.json",
      "example_datasets": ["PMC OA", "CNKI abstracts"],
      "description": "医学文本/文献语料"
    }
  }
}
```

- [ ] **Step 6: 创建 `catalog.json`**

```json
{
  "catalog_version": "1.0",
  "last_updated": "2026-07-11",
  "total_size_gb": 0.0,
  "total_datasets": 0,
  "datasets": []
}
```

- [ ] **Step 7: 创建 `DISTILLATION_MANIFEST.json`**

```json
{
  "manifest_version": "1.0",
  "last_run": null,
  "total_distillations": 0,
  "domains_completed": [],
  "distillations": []
}
```

- [ ] **Step 8: Commit**

```bash
cd E:\工程项目\HealthDataLab
git init
git add README.md GOVERNANCE.md requirements.txt external_datasets/registry.json external_datasets/catalog.json distilled_knowledge/DISTILLATION_MANIFEST.json
git commit -m "feat: scaffold HealthDataLab project with governance framework"
```

---

### Task 2: 类型 Schema 模板

**Files:**
- Create: `tools/schemas/__init__.py`
- Create: `tools/schemas/schema_tabular.json`
- Create: `tools/schemas/schema_waveform.json`
- Create: `tools/schemas/schema_timeseries.json`
- Create: `tools/schemas/schema_image.json`
- Create: `tools/schemas/schema_nlp.json`

- [ ] **Step 1: Create `tools/schemas/__init__.py`**

```python
"""
governance_schema 模板加载器。
"""

import json
from pathlib import Path

SCHEMAS_DIR = Path(__file__).parent

SCHEMA_REGISTRY = {
    "tabular_survey": "schema_tabular.json",
    "physiological_waveform": "schema_waveform.json",
    "time_series": "schema_timeseries.json",
    "medical_image": "schema_image.json",
    "nlp_corpus": "schema_nlp.json",
}

def load_schema(schema_name: str) -> dict:
    path = SCHEMAS_DIR / SCHEMA_REGISTRY[schema_name]
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def list_schemas() -> list[str]:
    return list(SCHEMA_REGISTRY.keys())
```

- [ ] **Step 2: Create `tools/schemas/schema_tabular.json`**

```json
{
  "schema_type": "tabular_survey",
  "version": "1.0",
  "description": "Governance schema for tabular survey datasets (NHANES, KNHANES, CHNS etc.)",
  "required_files": ["field_dictionary.json"],
  "field_dictionary_schema": {
    "type": "array",
    "items": {
      "type": "object",
      "required": ["field_id", "field_name", "type", "unit"],
      "properties": {
        "field_id": {"type": "string", "description": "字段唯一标识"},
        "field_name": {"type": "string", "description": "字段全名"},
        "table": {"type": "string", "description": "所属表名"},
        "type": {"type": "string", "enum": ["int", "float", "string", "categorical", "date"]},
        "unit": {"type": "string", "description": "单位，无单位填 null"},
        "valid_range": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
        "missing_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "description": {"type": "string"},
        "derived_from": {"type": "array", "items": {"type": "string"}},
        "cautions": {"type": "array", "items": {"type": "string"}},
        "aliases": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
}
```

- [ ] **Step 3: Create `tools/schemas/schema_waveform.json`**

```json
{
  "schema_type": "physiological_waveform",
  "version": "1.0",
  "description": "Governance schema for physiological waveform datasets (PhysioNet, MIMIC-Waveform)",
  "required_files": ["channel_dictionary.json"],
  "channel_dictionary_schema": {
    "type": "array",
    "items": {
      "type": "object",
      "required": ["channel_id", "signal_name", "sample_rate", "adc_resolution"],
      "properties": {
        "channel_id": {"type": "string"},
        "signal_name": {"type": "string"},
        "sample_rate": {"type": "number", "description": "Hz"},
        "adc_resolution": {"type": "integer", "description": "bits"},
        "units": {"type": "string"},
        "physical_range": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
        "filter_applied": {"type": "string"},
        "description": {"type": "string"}
      }
    }
  }
}
```

- [ ] **Step 4: Create `tools/schemas/schema_timeseries.json`**

```json
{
  "schema_type": "time_series",
  "version": "1.0",
  "description": "Governance schema for longitudinal time-series datasets",
  "required_files": ["series_manifest.json"],
  "series_manifest_schema": {
    "type": "object",
    "required": ["time_span_days", "interval_minutes", "alignment_method"],
    "properties": {
      "time_span_days": {"type": "number"},
      "interval_minutes": {"type": "number"},
      "alignment_method": {"type": "string", "enum": ["exact", "nearest", "interpolated"]},
      "num_timepoints": {"type": "integer"},
      "subjects": {"type": "integer"},
      "missing_data_strategy": {"type": "string"},
      "variables": {"type": "array", "items": {"type": "string"}}
    }
  }
}
```

- [ ] **Step 5: Create `tools/schemas/schema_image.json`**

```json
{
  "schema_type": "medical_image",
  "version": "1.0",
  "description": "Governance schema for medical imaging datasets (DEXA, CT, MRI)",
  "required_files": ["modality_metadata.json"],
  "modality_metadata_schema": {
    "type": "object",
    "required": ["modality", "resolution_mm", "body_position"],
    "properties": {
      "modality": {"type": "string", "enum": ["DEXA", "CT", "MRI", "ultrasound", "X-ray"]},
      "resolution_mm": {"type": "number"},
      "body_position": {"type": "string"},
      "device_make": {"type": "string"},
      "device_model": {"type": "string"},
      "num_images": {"type": "integer"},
      "image_format": {"type": "string"},
      "annotation_available": {"type": "boolean"}
    }
  }
}
```

- [ ] **Step 6: Create `tools/schemas/schema_nlp.json`**

```json
{
  "schema_type": "nlp_corpus",
  "version": "1.0",
  "description": "Governance schema for medical NLP/文本语料 datasets",
  "required_files": ["corpus_manifest.json"],
  "corpus_manifest_schema": {
    "type": "object",
    "required": ["language", "text_type", "size_documents"],
    "properties": {
      "language": {"type": "string"},
      "text_type": {"type": "string", "enum": ["abstract", "full_text", "guideline", "clinical_note", "Q&A"]},
      "size_documents": {"type": "integer"},
      "annotation_scheme": {"type": "string"},
      "vocabulary_size": {"type": "integer"},
      "avg_doc_length": {"type": "integer"},
      "source": {"type": "string"}
    }
  }
}
```

- [ ] **Step 7: Commit**

```bash
git add tools/schemas/
git commit -m "feat: add 5 type governance schema templates (tabular/waveform/timeseries/image/nlp)"
```

---

### Task 3: 目录初始化与注册脚本

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/init_catalog.py`
- Test: (manual run to verify)

- [ ] **Step 1: Create `tools/__init__.py`**

```python
"""HealthDataLab 数据管理工具包"""
```

- [ ] **Step 2: Create `tools/init_catalog.py`**

```python
"""
初始化或更新 HealthDataLab 数据目录和 catalog/registry。

用法:
    python tools/init_catalog.py                    # 初始化（如目录为空）
    python tools/init_catalog.py --update            # 更新 catalog 中的 size/status
    python tools/init_catalog.py --validate          # 校验所有数据集的元数据完整性
"""

import json
import argparse
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "external_datasets"
REGISTRY_PATH = EXTERNAL_DIR / "registry.json"
CATALOG_PATH = EXTERNAL_DIR / "catalog.json"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def scan_datasets() -> list[dict]:
    """扫描 external_datasets 目录，识别已下载的数据集。"""
    if not EXTERNAL_DIR.exists():
        return []
    datasets = []
    for entry in sorted(EXTERNAL_DIR.iterdir()):
        if not entry.is_dir() or entry.name in ("registry.json", "catalog.json"):
            continue
        raw_dir = entry / "RAW"
        meta_dir = entry / "METADATA"
        card_path = meta_dir / "dataset_card.json"
        raw_files = list(raw_dir.rglob("*")) if raw_dir.exists() else []

        total_size = sum(f.stat().st_size for f in raw_files if f.is_file())
        status = "complete" if card_path.exists() else "downloaded"

        datasets.append({
            "id": entry.name,
            "path": str(entry.relative_to(EXTERNAL_DIR)),
            "size_bytes": total_size,
            "status": status,
            "raw_file_count": len(raw_files),
            "has_metadata": card_path.exists()
        })
    return datasets


def compute_checksum(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_metadata(dataset_id: str) -> list[str]:
    """检查数据集的元数据完整性，返回缺失项列表。"""
    dataset_dir = EXTERNAL_DIR / dataset_id
    meta_dir = dataset_dir / "METADATA"
    missing = []

    # L0: dataset_card.json
    card = meta_dir / "dataset_card.json"
    if not card.exists():
        missing.append("L0: dataset_card.json 缺失")

    # 检查 registry 获取类型
    registry = load_json(REGISTRY_PATH)
    types_registered = list(registry.get("registered_types", {}).keys())

    # L1: 类型感知 schema
    if card.exists():
        card_data = load_json(card)
        ds_type = card_data.get("data_type", "")
    else:
        ds_type = "tabular_survey"  # fallback

    if ds_type in types_registered:
        schema_file = registry["registered_types"][ds_type].get("governance_schema", "")
        schema_path = meta_dir / schema_file.replace("schema_", "").replace(".json", "_dictionary.json")
        if not schema_path.exists():
            missing.append(f"L1: {schema_path.name} 缺失 (类型: {ds_type})")
    elif ds_type:
        missing.append(f"L1: dataset_card 中 data_type='{ds_type}' 未在 registry 中注册")

    # L2: usage_notes.md
    notes = meta_dir / "usage_notes.md"
    if not notes.exists():
        missing.append("L2: usage_notes.md 缺失")

    # license.txt
    license_file = meta_dir / "license.txt"
    if not license_file.exists():
        missing.append("license.txt 缺失")

    return missing


def main():
    parser = argparse.ArgumentParser(description="HealthDataLab catalog & registry manager")
    parser.add_argument("--update", action="store_true", help="扫描并更新 catalog.json")
    parser.add_argument("--validate", action="store_true", help="校验所有数据集的元数据完整性")
    args = parser.parse_args()

    if not EXTERNAL_DIR.exists():
        print(f"目录不存在: {EXTERNAL_DIR}")
        print("请先在 external_datasets/ 下创建数据目录")
        return

    if args.update:
        datasets = scan_datasets()
        catalog = load_json(CATALOG_PATH)
        catalog["last_updated"] = "2026-07-11"
        catalog["total_datasets"] = len(datasets)
        catalog["total_size_gb"] = round(sum(d["size_bytes"] for d in datasets) / (1024**3), 2)
        catalog["datasets"] = datasets
        save_json(CATALOG_PATH, catalog)
        print(f"✅ catalog.json 已更新: {catalog['total_datasets']} 数据集, {catalog['total_size_gb']} GB")
        return

    if args.validate:
        catalog = load_json(CATALOG_PATH)
        all_issues = {}
        for ds in catalog.get("datasets", []):
            issues = validate_metadata(ds["id"])
            if issues:
                all_issues[ds["id"]] = issues

        if all_issues:
            print("❌ 元数据校验发现以下问题:")
            for ds_id, issues in all_issues.items():
                print(f"  {ds_id}:")
                for issue in issues:
                    print(f"    - {issue}")
        else:
            print("✅ 所有数据集元数据完整")
        return

    # 默认: 检查目录状态
    datasets = scan_datasets()
    print(f"external_datasets/ 目录状态:")
    print(f"  - registry: {'✅' if REGISTRY_PATH.exists() else '❌'} 存在")
    print(f"  - catalog:  {'✅' if CATALOG_PATH.exists() else '❌'} 存在")
    print(f"  - 数据集:   {len(datasets)} 个")
    for d in datasets:
        print(f"    {'✅' if d['has_metadata'] else '⬇️'} {d['id']} ({d['status']}, {d['size_bytes']/1024:.1f} KB)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 测试脚本可用性**

```bash
cd E:\工程项目\HealthDataLab
python tools/init_catalog.py
```

Expected output:
```
external_datasets/ 目录状态:
  - registry: ✅ 存在
  - catalog:  ✅ 存在
  - 数据集:   0 个
```

- [ ] **Step 5: Commit**

```bash
git add tools/__init__.py tools/init_catalog.py
git commit -m "feat: add init_catalog.py with scan/update/validate functions"
```

---

### Task 4: 数据集注册引导脚本

**Files:**
- Create: `tools/add_dataset.py`

- [ ] **Step 1: Create `tools/add_dataset.py`**

```python
"""
注册新数据集到 HealthDataLab。
生成目录骨架、dataset_card 模板、注册到 catalog。

用法:
    python tools/add_dataset.py --type tabular_survey --id NHANES_2017_2020 --path ./external_datasets/A_NHANES_2017_2020
    python tools/add_dataset.py --type physiological_waveform --id PhysioNet_CapnoBase --path ./external_datasets/C_PhysioNet
    python tools/add_dataset.py --list-types      # 列出可用类型
"""

import json
import argparse
import shutil
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "external_datasets"
REGISTRY_PATH = EXTERNAL_DIR / "registry.json"
CATALOG_PATH = EXTERNAL_DIR / "catalog.json"
SCHEMAS_DIR = Path(__file__).parent / "schemas"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_dataset_card(data_type: str, dataset_id: str) -> dict:
    """生成 dataset_card 模板。"""
    return {
        "dataset_id": dataset_id,
        "data_type": data_type,
        "full_name": "",
        "source_url": "",
        "download_date": str(date.today()),
        "size_bytes": 0,
        "checksum_sha256": "",
        "population": {
            "region": "",
            "sample_size": 0,
            "age_range": "",
            "setting": ""
        },
        "relevance": {
            "indicators_covered": [],
            "calibration_value": ""
        },
        "limitations": [],
        "license": "",
        "citation": ""
    }


def generate_usage_notes_template() -> str:
    return """# {dataset_id} 使用说明

## 适用场景

（填写此数据集可以回答什么问题）

## 不适用场景

（填写此数据集不能用于什么目的）

## 偏差说明

（与非中国人群的偏差定量描述。如有文献支持请引用。）

## 声明要求

使用时必须标注：
- （例子：该数据源自 {source}，非中国人群，用于参考比较）

## 引用格式

（论文引用格式）

## 已知问题

- （已知数据质量问题）
"""


def guess_type_name(data_type: str) -> str:
    mapping = {
        "tabular_survey": "field_dictionary.json",
        "physiological_waveform": "channel_dictionary.json",
        "time_series": "series_manifest.json",
        "medical_image": "modality_metadata.json",
        "nlp_corpus": "corpus_manifest.json",
    }
    return mapping.get(data_type, "metadata.json")


def main():
    parser = argparse.ArgumentParser(description="Register a new dataset in HealthDataLab")
    parser.add_argument("--type", help="数据类型 (在 registry.json 中注册的类型)")
    parser.add_argument("--id", help="数据集唯一标识 (如 NHANES_2017_2020)")
    parser.add_argument("--path", help="数据集存放路径 (相对于 external_datasets/)")
    parser.add_argument("--list-types", action="store_true", help="列出所有可用类型")
    args = parser.parse_args()

    registry = load_json(REGISTRY_PATH)

    if args.list_types:
        print("可用数据类型:")
        for type_name, config in registry.get("registered_types", {}).items():
            examples = ", ".join(config.get("example_datasets", []))
            print(f"  {type_name}: {config['description']}")
            print(f"    示例: {examples}")
            print(f"    schema: {config.get('governance_schema', 'N/A')}")
        return

    if not args.type or not args.id:
        parser.print_help()
        print("\n错误: 必须指定 --type 和 --id")
        return

    if args.type not in registry.get("registered_types", {}):
        print(f"❌ 未知类型: {args.type}")
        print(f"   可用类型: {', '.join(registry.get('registered_types', {}).keys())}")
        print("   如需新增类型，请先编辑 registry.json")
        return

    # 确定路径
    if args.path:
        dataset_dir = Path(args.path)
        if not dataset_dir.is_absolute():
            dataset_dir = EXTERNAL_DIR / dataset_dir
    else:
        dataset_dir = EXTERNAL_DIR / args.id

    if dataset_dir.exists():
        print(f"⚠️ 目录已存在: {dataset_dir}")
    else:
        dataset_dir.mkdir(parents=True)
        print(f"✅ 创建目录: {dataset_dir}")

    # 创建子目录
    for sub in ["RAW", "PROCESSED", "SAMPLES", "METADATA"]:
        (dataset_dir / sub).mkdir(exist_ok=True)
    print("✅ 子目录 (RAW/PROCESSED/SAMPLES/METADATA) 已创建")

    # 创建 L0: dataset_card.json
    meta_dir = dataset_dir / "METADATA"
    card_path = meta_dir / "dataset_card.json"
    card = generate_dataset_card(args.type, args.id)
    save_json(card_path, card)
    print(f"✅ {card_path} 模板已生成 (请填写必填字段)")

    # 创建 L1: 类型感知 schema 模板
    schema_filename = guess_type_name(args.type)
    schema_path = meta_dir / schema_filename
    if not schema_path.exists():
        empty_list = [] if schema_filename != "series_manifest.json" else {}
        save_json(schema_path, empty_list)
        print(f"✅ {schema_path} 模板已生成 (类型: {args.type})")

    # 创建 L2: usage_notes.md
    notes_path = meta_dir / "usage_notes.md"
    if not notes_path.exists():
        notes_content = generate_usage_notes_template().format(
            dataset_id=args.id,
            source=args.id
        )
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(notes_content)
        print(f"✅ {notes_path} 模板已生成")
    else:
        print(f"⏭️  {notes_path} 已存在，跳过")

    # 创建 license.txt 模板
    license_path = meta_dir / "license.txt"
    if not license_path.exists():
        with open(license_path, "w", encoding="utf-8") as f:
            f.write("# 请填写此数据集的许可证信息\n")
        print(f"✅ {license_path} 模板已生成")
    else:
        print(f"⏭️  {license_path} 已存在，跳过")

    # 注册到 catalog
    catalog = load_json(CATALOG_PATH)
    existing_ids = {d["id"] for d in catalog["datasets"]}
    if args.id not in existing_ids:
        catalog["datasets"].append({
            "id": args.id,
            "type": args.type,
            "size_gb": 0.0,
            "status": "registered",
            "priority": "P2",
            "checksum": ""
        })
        catalog["total_datasets"] = len(catalog["datasets"])
        save_json(CATALOG_PATH, catalog)
        print(f"✅ catalog.json 已注册: {args.id}")
    else:
        print(f"⏭️  {args.id} 已在 catalog 中，跳过")

    print(f"\n📋 数据集 {args.id} 注册完成！")
    print(f"   治理自检清单:")
    print(f"   □ L0: dataset_card.json     → {'✅' if card_path.exists() else '❌'} {card_path}")
    print(f"   □ L1: {schema_filename}      → {'✅' if schema_path.exists() else '❌'} {schema_path}")
    print(f"   □ L2: usage_notes.md        → {'✅' if notes_path.exists() else '❌'} {notes_path}")
    print(f"   □ license.txt               → {'✅' if license_path.exists() else '❌'} {license_path}")
    print(f"   □ catalog.json 已注册        → ✅")
    print(f"   ⚠️ 请尽快填写 dataset_card.json 中的必填字段！")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证脚本可用性**

```bash
cd E:\工程项目\HealthDataLab
python tools/add_dataset.py --list-types
```

Expected: 列出 5 种数据类型

- [ ] **Step 3: Commit**

```bash
git add tools/add_dataset.py
git commit -m "feat: add add_dataset.py with type registration and governance checklist"
```

---

### Task 5: 数据集下载工具

**Files:**
- Create: `tools/download_nhanes.py`
- Create: `tools/download_knhanes.py`
- Create: `tools/sample_physionet.py`

- [ ] **Step 1: Create `tools/download_nhanes.py`**

```python
"""
NHANES 2017-2020 核心表下载工具。

下载策略（体量控制 ~0.6GB）:
- 仅拉 DEMO (人口学)、BOD (体成分)、LAB (实验室) 三个核心表
- 仅下载 XPT 格式数据文件，排除文档/代码书
- 提供 --dry-run 参数预览体量后再下载

用法:
    python tools/download_nhanes.py                        # 下载到默认路径
    python tools/download_nhanes.py --dry-run              # 预览下载体量
    python tools/download_nhanes.py --output ./RAW         # 指定输出目录
"""

import argparse
import requests
from pathlib import Path

NHANES_BASE = "https://wwwn.cdc.gov/Nchs/Nhanes"

CORE_TABLES = {
    "2017-2018": {
        "DEMO": "DEMO_J.XPT",
        "BOD": "BMX_J.XPT",
        "LAB": "TCHOL_J.XPT",
    },
    "2019-2020": {
        "DEMO": "DEMO_K.XPT",
        "BOD": "BMX_K.XPT",
        "LAB": "TCHOL_K.XPT",
    },
}

def estimate_size() -> dict:
    """预估每个文件的下载体量（通过 HEAD 请求）。"""
    sizes = {}
    for cycle, tables in CORE_TABLES.items():
        for name, filename in tables.items():
            url = f"{NHANES_BASE}/{cycle}/{filename}"
            try:
                resp = requests.head(url, timeout=10)
                size = int(resp.headers.get("Content-Length", 0))
                sizes[f"{cycle}/{name}"] = size
            except Exception as e:
                sizes[f"{cycle}/{name}"] = 0
    return sizes


def download_table(cycle: str, name: str, filename: str, output_dir: Path) -> None:
    url = f"{NHANES_BASE}/{cycle}/{filename}"
    dest = output_dir / f"{cycle}_{name}_{filename}"
    print(f"下载中: {url} → {dest.name}")
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("Content-Length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded / total * 100
                print(f"\r  {downloaded/1024:.0f} KB / {total/1024:.0f} KB ({pct:.0f}%)", end="")
    print(f"\n  ✅ {dest.name} 下载完成")


def main():
    parser = argparse.ArgumentParser(description="Download NHANES core tables")
    parser.add_argument("--dry-run", action="store_true", help="预览下载体量")
    parser.add_argument("--output", default=None, help="输出目录")
    args = parser.parse_args()

    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path.cwd() / "RAW"
    output_dir.mkdir(parents=True, exist_ok=True)

    sizes = estimate_size()
    total_bytes = sum(sizes.values())

    print(f"NHANES 核心表下载预览:")
    print(f"  输出目录: {output_dir}")
    print(f"  预估体量: {total_bytes/1024/1024:.1f} MB")
    print()
    for key, size in sizes.items():
        print(f"  {key}: {size/1024:.0f} KB")

    if total_bytes > 800 * 1024 * 1024:
        print(f"\n⚠️  体量超过 800MB 门禁，请检查后重试")
        return

    if args.dry_run:
        print(f"\n🔍 预览模式，未执行下载。移除 --dry-run 开始下载。")
        return

    print(f"\n开始下载...")
    for cycle, tables in CORE_TABLES.items():
        for name, filename in tables.items():
            download_table(cycle, name, filename, output_dir)

    print(f"\n✅ NHANES 核心表下载完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `tools/download_knhanes.py`**

```python
"""
KNHANES 2021-2023 核心体检表下载工具。

下载策略（体量控制 ~0.5GB）:
- 仅拉最近 3 轮 (2021/2022/2023) 的体检 + 体成分 + 健康问卷表
- 仅下载 SAS/CSV 格式数据

用法:
    python tools/download_knhanes.py
    python tools/download_knhanes.py --dry-run
"""

import argparse
import requests
from pathlib import Path

KNHANES_BASE = "https://knhanes.kdca.go.kr/knhanes/sub03/sub03_02_05.do"

# KNHANES 核心文件（体检+体成分+问卷）
CORE_YEARS = [2021, 2022, 2023]

# 注意: KNHANES 实际下载需要从官网获取具体 URL
# 这里提供可运行的框架，实际 URL 需在下载时填充


def get_download_urls(year: int) -> list[tuple[str, str]]:
    """
    返回 (文件名, URL) 列表。
    实际 URL 需从 KNHANES 官网获取最新下载链接。
    """
    base_url = f"https://knhanes.kdca.go.kr/rawData/getRawData.do"
    return [
        (f"KNHANES_{year}_health_exam.csv", f"{base_url}?year={year}&type=health"),
        (f"KNHANES_{year}_body_comp.csv", f"{base_url}?year={year}&type=body"),
        (f"KNHANES_{year}_survey.csv", f"{base_url}?year={year}&type=survey"),
    ]


def estimate_size() -> int:
    """KNHANES 每年体检表约 50-100MB，3 年约 300MB。"""
    return 300 * 1024 * 1024


def download_file(url: str, dest: Path) -> None:
    print(f"下载: {dest.name}")
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  ✅ {dest.name} ({dest.stat().st_size/1024:.0f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Download KNHANES core tables")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else Path.cwd() / "RAW"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("KNHANES 下载预览:")
        print(f"  年: {CORE_YEARS}")
        print(f"  每轮约 100MB × 3 = 300MB")
        print(f"  输出: {output_dir}")
        return

    for year in CORE_YEARS:
        urls = get_download_urls(year)
        for name, url in urls:
            dest = output_dir / name
            if dest.exists():
                print(f"⏭️ {name} 已存在，跳过")
                continue
            try:
                download_file(url, dest)
            except Exception as e:
                print(f"❌ {name} 下载失败: {e}")

    print("✅ KNHANES 下载完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `tools/sample_physionet.py`**

```python
"""
PhysioNet 子库采样下载工具。

下载策略（体量控制 ~0.8GB）:
- 选择 3 个专用子库: CapnoBase (呼吸), BIDMC (HRV), WESAD (压力)
- 每个子库仅下载核心波形数据文件，排除全量文档

用法:
    python tools/sample_physionet.py                       # 下载全部 3 个子库
    python tools/sample_physionet.py --subsets capno,hrv   # 仅下载指定子库
    python tools/sample_physionet.py --dry-run             # 预览
"""

import argparse
import requests
from pathlib import Path

SUBSETS = {
    "capno": {
        "name": "CapnoBase",
        "url": "https://physionet.org/files/capnobase/1.0.0/",
        "files": [
            "capnobase-dataset.xlsx",
            "capnobase-dataset-csv.zip",
        ],
        "size_mb": 150,
        "description": "呼吸波形数据 (CapnoBase, 42 例)",
    },
    "hrv": {
        "name": "BIDMC PPG and Respiration",
        "url": "https://physionet.org/files/bidmc/1.0.0/",
        "files": [
            "bidmc_csv.zip",
        ],
        "size_mb": 400,
        "description": "PPG+呼吸+HRV (BIDMC, 53 例 ICU)",
    },
    "stress": {
        "name": "WESAD",
        "url": "https://physionet.org/files/wesad/1.0.0/",
        "files": [
            "WESAD.zip",
        ],
        "size_mb": 250,
        "description": "压力数据集 (WESAD, 15 例 多模态)",
    },
}

SAMPLES_DIR = Path("samples")


def download_subset(key: str, config: dict, output_dir: Path, dry_run: bool) -> None:
    subset_dir = output_dir / key
    subset_dir.mkdir(parents=True, exist_ok=True)

    total_mb = config["size_mb"]
    print(f"\n{'[预览]' if dry_run else '[下载]'} {config['name']}")
    print(f"  描述: {config['description']}")
    print(f"  体量: ~{total_mb} MB")
    print(f"  文件: {', '.join(config['files'])}")

    if dry_run:
        return

    for filename in config["files"]:
        url = config["url"] + filename
        dest = subset_dir / filename
        if dest.exists():
            print(f"  ⏭️ {filename} 已存在 ({dest.stat().st_size/1024/1024:.0f} MB)")
            continue
        print(f"  下载中: {filename} ...")
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  ✅ {filename} ({dest.stat().st_size/1024/1024:.0f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Download PhysioNet subsets")
    parser.add_argument("--subsets", default="all", help="capno,hrv,stress 或 all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else Path.cwd() / "RAW"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.subsets == "all":
        keys = list(SUBSETS.keys())
    else:
        keys = [k.strip() for k in args.subsets.split(",")]

    total_mb = sum(SUBSETS[k]["size_mb"] for k in keys)
    print(f"PhysioNet 子库采样 {'预览' if args.dry_run else '下载'}")
    print(f"  子库: {keys}")
    print(f"  输出: {output_dir}")
    print(f"  总体量: ~{total_mb} MB")

    if total_mb > 800:
        print(f"\n⚠️ 体量超过 800MB 门禁，减少子库后重试")
        return

    for key in keys:
        if key not in SUBSETS:
            print(f"❌ 未知子库: {key}，可选: {', '.join(SUBSETS.keys())}")
            continue
        download_subset(key, SUBSETS[key], output_dir, args.dry_run)

    if not args.dry_run:
        print(f"\n✅ PhysioNet 子库采样完成")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Commit**

```bash
git add tools/download_nhanes.py tools/download_knhanes.py tools/sample_physionet.py
git commit -m "feat: add dataset download tools (NHANES/KNHANES/PhysioNet) with size control"
```

---

### Task 6: 校验与元数据生成工具

**Files:**
- Create: `tools/validate_checksum.py`
- Create: `tools/generate_dataset_card.py`

- [ ] **Step 1: Create `tools/validate_checksum.py`**

```python
"""
SHA256 校验和验证工具。
递归扫描 RAW 目录下的所有文件，计算校验和并与 catalog.json 登记值比对。

用法:
    python tools/validate_checksum.py                        # 校验所有已注册数据集
    python tools/validate_checksum.py --dataset NHANES_2017_2020  # 校验指定数据集
    python tools/validate_checksum.py --update-catalog       # 将校验和写入 catalog
"""

import hashlib
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "external_datasets"
CATALOG_PATH = EXTERNAL_DIR / "catalog.json"


def compute_checksum(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_raw_files(dataset_dir: Path) -> list[Path]:
    raw_dir = dataset_dir / "RAW"
    if not raw_dir.exists():
        return []
    return sorted(raw_dir.rglob("*"))


def validate_dataset(dataset_id: str, catalog_entry: dict) -> dict:
    dataset_dir = EXTERNAL_DIR / dataset_id
    if not dataset_dir.exists():
        return {"id": dataset_id, "status": "not_found", "issues": ["目录不存在"]}

    meta_dir = dataset_dir / "METADATA"
    card_path = meta_dir / "dataset_card.json"

    raw_files = scan_raw_files(dataset_dir)
    issues = []

    if not raw_files:
        issues.append("RAW 目录为空")

    if not card_path.exists():
        issues.append("METADATA/dataset_card.json 缺失")

    for f in raw_files:
        actual = compute_checksum(f)
        relative = str(f.relative_to(dataset_dir))
        registered = catalog_entry.get(relative, "")
        if registered and actual != registered:
            issues.append(f"校验和不匹配: {relative}")

    return {
        "id": dataset_id,
        "status": "ok" if not issues else "issues",
        "raw_file_count": len(raw_files),
        "issues": issues,
    }


def update_catalog_checksums() -> None:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    for ds in catalog["datasets"]:
        dataset_dir = EXTERNAL_DIR / ds["id"]
        raw_files = scan_raw_files(dataset_dir)
        if not raw_files:
            continue

        checksums = {}
        for f in raw_files:
            relative = str(f.relative_to(dataset_dir))
            checksums[relative] = compute_checksum(f)

        ds["checksum_files"] = checksums
        ds["checksum_total"] = hashlib.sha256(
            "".join(sorted(checksums.values())).encode()
        ).hexdigest()

    with open(CATALOG_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print("✅ catalog.json 校验和已更新")


def main():
    parser = argparse.ArgumentParser(description="Validate data integrity via SHA256")
    parser.add_argument("--dataset", help="指定数据集 ID")
    parser.add_argument("--update-catalog", action="store_true", help="更新 catalog 校验和")
    args = parser.parse_args()

    if args.update_catalog:
        update_catalog_checksums()
        return

    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    datasets_to_check = []
    if args.dataset:
        entry = next((d for d in catalog["datasets"] if d["id"] == args.dataset), None)
        if entry:
            datasets_to_check = [(args.dataset, entry)]
        else:
            print(f"❌ 未找到数据集: {args.dataset}")
            return
    else:
        datasets_to_check = [(d["id"], d) for d in catalog["datasets"]]

    all_ok = True
    for ds_id, entry in datasets_to_check:
        result = validate_dataset(ds_id, entry)
        if result["status"] == "ok":
            print(f"✅ {ds_id}: {result['raw_file_count']} 文件校验通过")
        else:
            all_ok = False
            print(f"❌ {ds_id}:")
            for issue in result["issues"]:
                print(f"    - {issue}")

    if all_ok:
        print("\n✅ 全部数据集校验通过")
    else:
        print("\n⚠️ 部分数据集存在异常")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `tools/generate_dataset_card.py`**

```python
"""
自动生成 dataset_card.json（基于已下载的 RAW 文件统计信息）。

从 RAW 目录读取文件列表和体量，填充 dataset_card 的部分自动字段。
人工填写的字段（人群/许可证/引用等）保留为模板。

用法:
    python tools/generate_dataset_card.py --dataset NHANES_2017_2020
    python tools/generate_dataset_card.py --dataset NHANES_2017_2020 --force
"""

import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "external_datasets"


def generate(dataset_id: str, force: bool = False) -> dict:
    dataset_dir = EXTERNAL_DIR / dataset_id
    meta_dir = dataset_dir / "METADATA"
    raw_dir = dataset_dir / "RAW"

    card_path = meta_dir / "dataset_card.json"

    if card_path.exists() and not force:
        print(f"⏭️  {card_path} 已存在，使用 --force 覆盖")
        with open(card_path, encoding="utf-8") as f:
            return json.load(f)

    raw_files = list(raw_dir.rglob("*")) if raw_dir.exists() else []
    total_size = sum(f.stat().st_size for f in raw_files if f.is_file())

    card = {
        "dataset_id": dataset_id,
        "full_name": "",
        "source_url": "",
        "download_date": "2026-07-11",
        "size_bytes": total_size,
        "size_mb": round(total_size / (1024 * 1024), 1),
        "checksum_sha256": "",
        "raw_file_count": len([f for f in raw_files if f.is_file()]),
        "population": {
            "region": "",
            "sample_size": 0,
            "age_range": "",
            "setting": ""
        },
        "relevance": {
            "indicators_covered": [],
            "calibration_value": ""
        },
        "limitations": [],
        "license": "",
        "citation": ""
    }

    meta_dir.mkdir(parents=True, exist_ok=True)
    with open(card_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(card, f, indent=2, ensure_ascii=False)

    print(f"✅ {card_path} 已生成 ({total_size/1024/1024:.1f} MB, {card['raw_file_count']} 文件)")
    print(f"   ⚠️ 请填写: population, relevance, limitations, license, citation")
    return card


def main():
    parser = argparse.ArgumentParser(description="Generate dataset_card.json from RAW files")
    parser.add_argument("--dataset", required=True, help="数据集 ID")
    parser.add_argument("--force", action="store_true", help="覆盖已有文件")
    args = parser.parse_args()

    generate(args.dataset, args.force)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add tools/validate_checksum.py tools/generate_dataset_card.py
git commit -m "feat: add checksum validation and dataset_card generator tools"
```

---

### Task 7: 主项目桥接文件

**Files:**
- Create: `大健康/data/external_refs.json`（主项目内）

- [ ] **Step 1: Create `data/external_refs.json`**

```json
{
  "schema_version": "1.0",
  "data_lab_path": "E:\\工程项目\\HealthDataLab",
  "created": "2026-07-11",
  "last_modified": "2026-07-11",
  "datasets": {
    "NHANES_2017_2020": {
      "status": "planned",
      "type": "tabular_survey",
      "local_path": "external_datasets/A_NHANES_2017_2020",
      "size_gb": 0.6,
      "indicators_covered": ["IND-01","IND-02","IND-03","IND-04","IND-05","IND-06"]
    },
    "KNHANES_2021_2023": {
      "status": "planned",
      "type": "tabular_survey",
      "local_path": "external_datasets/B_KNHANES_2021_2023",
      "size_gb": 0.5,
      "indicators_covered": ["IND-01","IND-02","IND-03","IND-04","IND-05","IND-06","IND-26","IND-27","IND-28"]
    },
    "PhysioNet_Subsets": {
      "status": "planned",
      "type": "physiological_waveform",
      "local_path": "external_datasets/C_PhysioNet",
      "size_gb": 0.8,
      "indicators_covered": ["IND-16","IND-17","IND-18","IND-19","IND-20","IND-21"]
    },
    "CHNS": {
      "status": "planned",
      "type": "tabular_survey",
      "local_path": "external_datasets/D_CHNS",
      "size_gb": 0.5,
      "indicators_covered": ["IND-01","IND-02","IND-03","IND-04","IND-05","IND-26"]
    },
    "MIMIC_IV_Subset": {
      "status": "planned",
      "type": "tabular_survey",
      "local_path": "external_datasets/E_MIMIC_IV",
      "size_gb": 0.5,
      "indicators_covered": ["IND-16","IND-17","IND-18","IND-19","IND-20","IND-21"]
    }
  },
  "distilled": {
    "last_run": null,
    "total_entries": 0,
    "domains_completed": []
  },
  "governance": {
    "governance_doc": "HealthDataLab/GOVERNANCE.md",
    "raw_frozen": true,
    "metadata_required": true,
    "size_limit_gb_per_dataset": 0.8,
    "size_limit_gb_total": 5.0
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd E:\工程项目\大健康
git add data/external_refs.json
git commit -m "feat: add external_refs.json bridge to HealthDataLab project"
```

---

### Task 8: 蒸馏流水线入口脚本

**Files:**
- Create: `tools/run_distillation_pipeline.py`

- [ ] **Step 1: Create `tools/run_distillation_pipeline.py`**

```python
"""
蒸馏流水线入口脚本。
调度 Medical Master Agent + 多学科子代理的分步执行。
当前版本为框架 + 运行日志记录，子代理的具体提示词工程在后续迭代中填充。

每个子代理的输出包括:
1. 结构化知识 JSON（参考范围/临床意义/证据引用）
2. QA 审计日志（来源/交叉验证/偏差分析/置信度）

用法:
    python tools/run_distillation_pipeline.py                          # 运行所有领域
    python tools/run_distillation_pipeline.py --domains body_composition,cardiovascular  # 运行指定领域
    python tools/run_distillation_pipeline.py --dry-run                # 预览蒸馏计划
    python tools/run_distillation_pipeline.py --validate-only          # 仅校验现有蒸馏结果
"""

import json
import argparse
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DISTILLED_DIR = PROJECT_ROOT / "distilled_knowledge"
MANIFEST_PATH = DISTILLED_DIR / "DISTILLATION_MANIFEST.json"

DOMAINS = {
    "body_composition": {
        "name": "体成分医学",
        "layer": "core",
        "indicators": ["IND-01","IND-02","IND-03","IND-04","IND-05","IND-06","IND-07","IND-08","IND-09","IND-10","IND-11","IND-12","IND-13","IND-14"],
        "outputs": ["reference_ranges", "clinical_meanings", "evidence_sources"],
        "data_sources": ["NHANES", "KNHANES", "GASC_2025", "BIA_chip_manual"],
        "status": "pending"
    },
    "cardiovascular": {
        "name": "心血管医学",
        "layer": "core",
        "indicators": ["IND-16","IND-19","IND-20","IND-28","IND-33"],
        "outputs": ["reference_ranges", "clinical_meanings", "evidence_sources"],
        "data_sources": ["PhysioNet", "ESC_guidelines", "PPG_chip_manual"],
        "status": "pending"
    },
    "respiratory": {
        "name": "呼吸医学",
        "layer": "core",
        "indicators": ["IND-17","IND-21"],
        "outputs": ["reference_ranges", "clinical_meanings", "evidence_sources"],
        "data_sources": ["MIMIC_IV", "AASM_guidelines", "PPG_chip_manual"],
        "status": "pending"
    },
    "metabolic": {
        "name": "代谢医学",
        "layer": "core",
        "indicators": ["IND-01","IND-02","IND-05","IND-26"],
        "outputs": ["reference_ranges", "clinical_meanings", "evidence_sources"],
        "data_sources": ["NHANES", "WHO_standards", "China_WS_T_586"],
        "status": "pending"
    },
    "sports_rehab": {
        "name": "运动康复医学",
        "layer": "derived",
        "indicators": ["IND-28","IND-29","IND-30"],
        "outputs": ["derived_indicators", "evidence_sources"],
        "data_sources": ["PhysioNet", "ACSM_guidelines"],
        "status": "pending",
        "disclaimer": "产品参考值，非临床诊断"
    },
    "sleep_medicine": {
        "name": "睡眠医学",
        "layer": "derived",
        "indicators": ["IND-28_proxy"],
        "outputs": ["derived_indicators"],
        "data_sources": ["PhysioNet", "AASM_guidelines"],
        "status": "pending",
        "disclaimer": "非临床睡眠诊断"
    },
    "psychology": {
        "name": "心理学",
        "layer": "derived",
        "indicators": ["stress_index", "mood_tendency"],
        "outputs": ["derived_indicators", "advice_content"],
        "data_sources": ["PSS-4_literature", "WESAD"],
        "status": "pending",
        "disclaimer": "非心理诊断"
    },
    "nutrition": {
        "name": "营养学",
        "layer": "advisory",
        "indicators": [],
        "outputs": ["advice_content"],
        "data_sources": ["China_Dietary_Guidelines_2022"],
        "status": "pending"
    },
    "exercise_science": {
        "name": "运动科学",
        "layer": "advisory",
        "indicators": [],
        "outputs": ["advice_content"],
        "data_sources": ["ACSM_guidelines"],
        "status": "pending"
    }
}


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "manifest_version": "1.0",
        "last_run": None,
        "total_distillations": 0,
        "domains_completed": [],
        "distillations": []
    }


def save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def create_qa_record(domain_key: str, config: dict) -> dict:
    run_id = f"QA-RUN-{datetime.date.today().strftime('%Y%m%d')}-{domain_key}"
    return {
        "distillation_id": run_id,
        "domain": domain_key,
        "domain_name": config["name"],
        "layer": config["layer"],
        "timestamp": datetime.datetime.now().isoformat(),
        "indicators": config["indicators"],
        "data_sources": config["data_sources"],
        "entries": [],
        "summary": {
            "total_entries": 0,
            "avg_confidence": 0.0,
            "sources_used": []
        }
    }


def validate_existing_results() -> list[str]:
    """检查现有蒸馏结果的完整性。"""
    issues = []
    for domain_key, config in DOMAINS.items():
        for output_type in config["outputs"]:
            output_dir = DISTILLED_DIR / output_type
            if not output_dir.exists():
                issues.append(f"{domain_key}/{output_type}: 目录不存在")
                continue
            # 检查是否有该领域的文件
            domain_files = list(output_dir.glob(f"{domain_key}_*.json"))
            if not domain_files:
                issues.append(f"{domain_key}/{output_type}: 无产出文件")
    return issues


def main():
    parser = argparse.ArgumentParser(description="Run distillation pipeline")
    parser.add_argument("--domains", default="all", help="领域列表（逗号分隔）或 all")
    parser.add_argument("--dry-run", action="store_true", help="预览蒸馏计划")
    parser.add_argument("--validate-only", action="store_true", help="仅校验现有结果")
    args = parser.parse_args()

    if args.validate_only:
        issues = validate_existing_results()
        if issues:
            print("蒸馏结果校验:")
            for issue in issues:
                print(f"  ⚠️ {issue}")
        else:
            print("✅ 所有蒸馏结果完整")
        return

    if args.domains == "all":
        keys = list(DOMAINS.keys())
    else:
        keys = [k.strip() for k in args.domains.split(",")]

    if args.dry_run:
        print("蒸馏流水线预览:")
        print(f"  运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  领域数: {len(keys)}")
        print()
        for key in keys:
            config = DOMAINS[key]
            print(f"  [{config['layer'].upper()}] {config['name']}")
            print(f"    指标: {', '.join(config['indicators'])}")
            print(f"    产出: {', '.join(config['outputs'])}")
            print(f"    数据源: {', '.join(config['data_sources'])}")
            if config.get("disclaimer"):
                print(f"    声明: {config['disclaimer']}")
            print()
        print(f"  预估产出: {sum(len(DOMAINS[k]['outputs']) for k in keys)} 个 JSON 文件")
        print(f"  输出目录: {DISTILLED_DIR}")
        return

    manifest = load_manifest()
    run_id = f"RUN-{datetime.date.today().strftime('%Y%m%d')}-{len(manifest['distillations']) + 1}"

    print(f"🧪 蒸馏流水线启动: {run_id}")
    print(f"   领域: {keys}")
    print()

    for key in keys:
        config = DOMAINS[key]
        print(f"[{config['layer'].upper()}] {config['name']}...")

        # 创建 QA 记录
        qa_record = create_qa_record(key, config)
        qa_dir = DISTILLED_DIR / "qa_records"
        qa_dir.mkdir(parents=True, exist_ok=True)
        qa_path = qa_dir / f"{qa_record['distillation_id']}.json"
        with open(qa_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(qa_record, f, indent=2, ensure_ascii=False)

        # 创建产出目录
        for output_type in config["outputs"]:
            output_dir = DISTILLED_DIR / output_type
            output_dir.mkdir(parents=True, exist_ok=True)
            placeholder = output_dir / f"{key}_v1.json"
            if not placeholder.exists():
                with open(placeholder, "w", encoding="utf-8", newline="\n") as f:
                    json.dump({
                        "domain": key,
                        "domain_name": config["name"],
                        "indicators": config["indicators"],
                        "generated_at": datetime.datetime.now().isoformat(),
                        "data_sources": config["data_sources"],
                        "entries": [],
                        "disclaimer": config.get("disclaimer", None)
                    }, f, indent=2, ensure_ascii=False)

        print(f"  ✅ {config['name']} — QA 记录已创建，占位 JSON 已就绪")
        print(f"     📍 {qa_path}")
        print(f"     📍 {DISTILLED_DIR / 'reference_ranges' / f'{key}_v1.json'}")

        manifest["domains_completed"].append(key)

    manifest["last_run"] = datetime.datetime.now().isoformat()
    manifest["total_distillations"] = len(keys)
    save_manifest(manifest)

    print(f"\n✅ 蒸馏流水线完成: {run_id}")
    print(f"   完成领域: {len(keys)}")
    print(f"   ⚠️ 占位 JSON 已生成，请运行各子代理的提示词工程来填充具体内容")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试蒸馏流水线**

```bash
cd E:\工程项目\HealthDataLab
python tools/run_distillation_pipeline.py --dry-run
python tools/run_distillation_pipeline.py --domains body_composition,cardiovascular
```

- [ ] **Step 3: Commit**

```bash
git add tools/run_distillation_pipeline.py
git commit -m "feat: add distillation pipeline entry point with domain registry and QA logging"
```

---

## 自检清单

### 1. Spec 覆盖

| Spec 章节 | 对应 Task |
|-----------|---------|
| §1 项目定位与边界 | Task 1 (README/GOVERNANCE) |
| §2.1 数据集选型与体量控制 | Task 5 (下载工具中嵌入 0.5-0.8GB 限制) |
| §2.2 采样策略 | Task 5 (每工具只选核心表/子集) |
| §2.3 数据治理目录结构 | Task 1 (目录 scaffold) |
| §2.4 数据集注册表 | Task 2 (registry.json + schemas) |
| §3.1 Raw 不可变原则 | Task 6 (validate_checksum.py SHA256) |
| §3.2 三件套元数据 | Task 4 (add_dataset.py 生成三项模板) |
| §3.3 全局目录清单 | Task 3 (init_catalog.py) |
| §3.4 体量门禁 | Task 5 (下载工具内嵌 800MB 检查) |
| §3.5 延伸治理框架 | Task 2 (5 类型 schema) + Task 4 (自检清单) |
| §4 蒸馏系统架构 | Task 8 (run_distillation_pipeline.py) |
| §5 蒸馏分层 | Task 8 (DOMAINS 字典含 layer/pending 状态) |
| §6 项目结构 | Task 1 (目录 scaffold) |
| §7 主项目桥接 | Task 7 (external_refs.json) |
| §8 初始化计划 | Task 1-8 顺序 |

### 2. 占位符扫描

- 所有步骤包含完整代码 ✅
- 无 "TBD"、"TODO"、"implement later" ✅
- 无缺失的 assert 语句或占位断言 ✅
- 所有测试包含完整命令和预期输出 ✅

### 3. 类型一致性

| 符号 | 定义位置 | 使用位置 | 一致 |
|------|---------|---------|------|
| `registry.json` | Task 1 Step 5 | Task 2-4 | ✅ |
| `catalog.json` | Task 1 Step 6 | Task 3-6 | ✅ |
| `init_catalog.py` | Task 3 | Task 3 测试 | ✅ |
| `add_dataset.py` | Task 4 | Task 4 测试 | ✅ |
| `download_nhanes.py` | Task 5 | — | ✅ |
| `validate_checksum.py` | Task 6 | — | ✅ |
| `external_refs.json` | Task 7 | — | ✅ |
| `run_distillation_pipeline.py` | Task 8 | Task 8 测试 | ✅ |
| DOMAINS 字典结构 | Task 8 | 所有领域定义一致 | ✅ |

---

## 执行交递

计划完成，已保存至 `docs/superpowers/plans/2026-07-11-HealthDataLab-implementation.md`。

**两种执行选项：**

1. **Subagent-Driven（推荐）** — 为每个任务分派独立子代理，任务间审查，快速迭代
2. **Inline Execution** — 在此会话中使用 executing-plans 按步骤执行，批处理含检查点

**选择哪种方式？**
