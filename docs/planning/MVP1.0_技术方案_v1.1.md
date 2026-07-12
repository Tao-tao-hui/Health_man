# 大健康检测仪器 MVP1.0 技术方案

| 字段 | 值 |
|------|-----|
| 文档版本 | v1.3 |
| 编制日期 | 2026-07-10（v1.3 重构版） |
| 文档类型 | 技术方案书（Tech Design Spec） |
| 适用范围 | MVP1.0（Windows 平台 + Python） |
| 目标读者 | 技术负责人、架构师、核心开发 |
| 状态 | **已通过三审（v1.3，2026-07-10）** |

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统整体架构](#2-系统整体架构)
3. [MVP1.0 范围定义](#3-mvp10-范围定义)
4. [硬件集成方案](#4-硬件集成方案)
5. [软件架构设计](#5-软件架构设计)
6. [数据架构设计](#6-数据架构设计)
7. [算法集成方案](#7-算法集成方案)
8. [知识库建设方案](#8-知识库建设方案)
9. [用户界面设计](#9-用户界面设计)
10. [测试方案](#10-测试方案)
11. [部署与交付](#11-部署与交付)
12. [风险评估与应对](#12-风险评估与应对)
13. [里程碑与排期](#13-里程碑与排期)
14. [附录：参考资产清单](#14-附录参考资产清单)
15. [大健康指标清单（补充）](#15-大健康指标清单补充章节)
16. [大健康建议生成方案（补充）](#16-大健康建议生成方案补充章节)
17. [医学知识与大健康知识来源方案（补充）](#17-医学知识与大健康知识来源方案补充章节)
18. [产品体验转化路径（补充）](#18-产品体验转化路径补充章节)

---

## 1. 项目概述

### 1.1 项目定位

本项目旨在构建一套**双手接触式四电极 + 血氧测量的大健康检测仪器**，数据来源包括：
- 人工填写：个人基本信息（身高、体重、年龄、性别）
- BIA 检测芯片：双手生物电阻抗（50KHz 单频）
- PPG 检测芯片：血氧饱和度、心率、灌注指数

### 1.2 检测逻辑链路

```
基础数据 → 数据指标 → 大健康指标 → 大健康建议
   ↑          ↑           ↑            ↑
 人工输入   芯片算法     算法融合      知识库
 BIA芯片   理论算法     医学知识     大健康知识
 PPG芯片                         ↑             ↑
                            第15章详述    第16-18章详述
```

> **v1.0 → v1.1 补充说明**：v1.0 中"大健康指标""大健康建议""医学知识""大健康知识"4 个环节标记为"待补充"，v1.1 已在第 15-18 章完整补充。

### 1.3 MVP1.0 目标

在 Windows 平台使用 Python 技术栈，交付一个**单机可运行**的桌面应用，实现：
- 用户档案管理（基本信息录入）
- 一次完整测量流程（双手握持 30 秒内完成）
- 30 项指标计算与展示
- 趋势参考 + 个性化建议
- 历史记录存储与导出

**非 MVP1.0 范围**（后续版本考虑）：
- 云端同步、多用户共享、Web 化
- AI 综合评分模型（XGBoost，需 200+ 训练样本）
- 中医视觉、ECG 心律分析等高级功能

---

## 2. 系统整体架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────┐
│              用户界面层 (UI Layer)                 │
│   PyQt6 桌面应用 │ 测量向导 │ 结果展示 │ 趋势图    │
└─────────────────────────────────────────────────┘
                       ↓↑
┌─────────────────────────────────────────────────┐
│              业务逻辑层 (Service Layer)            │
│   测量编排 │ 指标计算 │ 评分融合 │ 建议生成       │
└─────────────────────────────────────────────────┘
                       ↓↑
┌─────────────────────────────────────────────────┐
│              算法引擎层 (Algorithm Layer)         │
│   BIA 体成分 │ PPG 心率血氧 │ HRV │ 多模态融合     │
└─────────────────────────────────────────────────┘
                       ↓↑
┌─────────────────────────────────────────────────┐
│              硬件通信层 (Hardware Layer)          │
│   BIA 串口协议 │ PPG UART 协议 │ 帧同步 │ 校验     │
└─────────────────────────────────────────────────┘
                       ↓↑
┌─────────────────────────────────────────────────┐
│              数据存储层 (Data Layer)              │
│   SQLite │ JSON 知识库 │ CSV 导出                │
└─────────────────────────────────────────────────┘
```

### 2.2 模块职责划分

| 模块 | 核心职责 | 依赖 |
|------|---------|------|
| `hardware/bia_module` | BIA 芯片串口通信、协议解析 | pyserial |
| `hardware/ppg_module` | PPG 芯片 UART 通信 | pyserial |
| `algorithms/bia_engine` | 调用 BIA 芯片内置算法 | bia_module |
| `algorithms/ppg_engine` | PPG 信号处理（HeartPy） | heartpy |
| `algorithms/fusion` | 多模态融合评分 | bia_engine, ppg_engine |
| `knowledge/medical_db` | 医学知识库查询 | JSON 文件 |
| `knowledge/advice_engine` | 建议生成（规则引擎） | medical_db |
| `database/db_manager` | SQLite 增删改查 | sqlite3 |
| `ui/wizard` | 测量向导（PyQt6） | 所有上层模块 |
| `main.py` | 应用入口 | - |

### 2.3 关键设计原则

1. **关注点分离**：硬件、算法、业务、UI 各层独立，通过明确接口交互
2. **可测试性**：每个模块可独立 mock 测试，不依赖硬件也能运行
3. **故障隔离**：硬件通信异常不应导致程序崩溃，须有降级处理
4. **配置外部化**：COM 口、波特率、知识库路径等参数从配置文件读取

---

## 3. MVP1.0 范围定义

### 3.1 必须包含（Must Have）

| 功能 | 说明 | 验收标准 |
|------|------|---------|
| 用户基本信息录入 | 姓名、年龄、性别、身高、体重 | 必填字段校验、年龄 6-99 |
| BIA 体成分测量 | 通过串口获取 19 项指标 | 与芯片手册对标误差 <5% |
| PPG 生命体征测量 | 血氧、心率、PI、HRV | PI > 0.3% 时数据有效 |
| 单次测量结果展示 | 30 项指标表格 + 状态色 | 正常/警惕/超标三色标记 |
| 历史趋势查询 | 最近 30 次测量对比 | 折线图显示关键指标 |
| 健康建议生成 | 饮食/运动/生活方式 | 基于知识库规则引擎 |
| 数据导出 | CSV 格式 | Excel 可直接打开 |
| 测量数据本地存储 | SQLite | 单文件 < 10MB |

### 3.2 不包含（Out of Scope）

| 功能 | 原因 | 后续版本 |
|------|------|---------|
| 多用户共享 | 增加权限管理复杂度 | v2.0 |
| 云端备份 | 涉及数据合规审批 | v3.0 |
| AI 综合评分模型 | 缺乏训练数据 | v2.0（需收集 200+ 样本） |
| 中医视觉（面色/舌色） | 需要额外硬件（摄像头+补光） | v3.0 |
| ECG 心律分析 | Step-1 无 ECG 硬件 | 待 Step-2 硬件升级 |
| 打印报告 | PDF 生成非核心 | v2.0 |

---

## 4. 硬件集成方案

### 4.1 硬件清单

| 设备 | 接口 | 通信参数 | 协议文档 |
|------|------|---------|---------|
| BIA 体成分仪 | RS-232 / USB 转串口 | 115200 bps, 8N1 | `芯片模组/体脂模组/体脂成分通信协议技术说明书.md` |
| PPG 血氧模组 (BMH08002) | UART | 38400 bps, 8N1 | `芯片模组/血氧监测/BMH08002_技术参考手册_V1.2.md` |

### 4.2 BIA 通信协议（已具备）

**关键命令清单**（参考协议文档）：

| 命令 | 方向 | 功能 | 报文示例 |
|------|------|------|---------|
| `0xF0` | M→S | 查询设备信息 | `55 05 F0 00 4A` |
| `0xB0` | M→S | 配置阻抗测量 | `55 09 B0 01 00 02 00 01 12` |
| `0xB1` | M→S | 查询阻抗值 | `55 05 B1 01 0C` |
| `0xC0` | M→S | 请求体成分计算 | `55 0E C0 AA 02 5D 17 01 00 01 F4 00 00 39` |
| `0xC1` | S→M | 扩展参数（BMI、皮下脂肪率等） | - |
| `0xE0` | M→S | 配置心率测试 | `55 07 E0 01 02 00 3F` |
| `0xE1` | M→S | 查询心率 | `55 05 E1 00 3B` |

**校验算法**：算术和取低 8 位（Sum-8），非 XOR。

### 4.3 PPG 通信协议（已具备）

**关键字段**（15 字节数据帧）：

| 字节 | 字段 | 说明 |
|------|------|------|
| 0 | 帧头 | `0x55` |
| 1 | 标识 | `0xB0`（数据帧） |
| 2 | Status | `0x00`=无手指 / `0x01`=有手指无数据 / `0x02`=有效数据 |
| 3 | SpO₂ | 35-99% |
| 4 | HR | 30-250 bpm |
| 5 | PI×10 | 除以 10 得百分比 |
| 6 | HRV | 0-255 ms |
| ... | ... | PPG 波形 ADC 数据 |

### 4.4 串口通信架构

> **外部化说明**：帧同步器已提取到外部文件。

**外部文件**：[`external/hardware/frame_synchronizer.py`](external/hardware/frame_synchronizer.html)

**设计要点**：
- 异步 IO 接收字节流（`pyserial-asyncio`）
- 环形缓冲区累积数据
- 搜索 `0x55/0xAA` 帧头 → 读取长度 → 校验 → 返回完整帧
- 校验和错误的帧被丢弃

**关键接口**：

```python
from external.hardware.frame_synchronizer import FrameSynchronizer

sync = FrameSynchronizer(buffer_size=4096)
frames = sync.feed(incoming_bytes)  # 返回完整帧列表
```

**相关硬件模块**：
- [`external/hardware/bia_module.py`](external/hardware/bia_module.html)：BIA 设备封装
- [`external/hardware/ppg_module.py`](external/hardware/ppg_module.html)：PPG 设备封装

### 4.5 硬件故障处理

| 故障场景 | 应对策略 |
|---------|---------|
| 串口未连接 | 启动时检测，提示用户检查硬件 |
| 通信超时（>2s 无响应） | 自动重试 3 次，失败后提示 |
| 校验和错误 | 记录日志，丢弃当前帧 |
| 测量过程中手指脱离 | 提示用户重新测量，保留已采集数据 |
| 数据异常（如阻抗 <100Ω 或 >1000Ω） | 标记为无效值，不参与计算 |

---

## 5. 软件架构设计

### 5.1 项目结构

```
project/
├── src/
│   ├── main.py                      # 应用入口
│   ├── config.py                    # 全局配置（COM口、路径等）
│   ├── hardware/
│   │   ├── __init__.py
│   │   ├── frame_synchronizer.py    # 帧同步器（环形缓冲）
│   │   ├── frame_parser.py          # 通用帧解析
│   │   ├── bia_module.py            # BIA 设备封装
│   │   └── ppg_module.py            # PPG 设备封装
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── bia_engine.py            # BIA 算法引擎
│   │   ├── ppg_engine.py            # PPG 算法引擎（HeartPy）
│   │   └── fusion.py                # 多模态融合评分
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── medical_db.py            # 医学知识库
│   │   ├── advice_engine.py         # 建议生成规则引擎
│   │   └── reference_ranges.py      # 参考范围查询
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db_manager.py            # SQLite 管理
│   │   └── models.py                # 数据模型（dataclass）
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py           # 主窗口
│   │   ├── wizard_pages.py         # 向导页面
│   │   ├── result_view.py           # 结果展示
│   │   └── trend_chart.py           # 趋势图组件
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # 日志工具
│       ├── validators.py            # 数据校验
│       ├── forbidden_words_filter.py # 合规禁用词过滤器（见 §5.4）
│       └── health_thresholds.py     # 统一阈值常量（见 §16.2.4）
├── data/
│   ├── schema.sql                   # 数据库结构
│   ├── knowledge/                   # 知识库 JSON
│   │   ├── medical_knowledge.json
│   │   └── advice_templates.json
│   └── exports/                     # CSV 导出目录
├── tests/                           # 单元测试
│   ├── test_hardware/
│   ├── test_algorithms/
│   └── test_knowledge/
├── tools/
│   └── extract_knowledge.py         # 从 IND 报告提取知识
├── requirements.txt
├── config.yaml                      # 配置文件
└── README.md
```

### 5.2 关键技术决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| Python 版本 | 3.10+ | asyncio、match 语句、类型注解增强 |
| UI 框架 | PyQt6 | 原生 Windows 体验、打包简单、社区成熟 |
| 数据库 | SQLite | 零配置、单文件、Python 内置 |
| 异步 IO | asyncio + pyserial-asyncio | 测量过程不阻塞 UI |
| 算法库 | HeartPy | MIT 许可、生产级 PPG 处理 |
| 打包工具 | PyInstaller | 单文件 exe、跨 Python 版本 |
| 配置格式 | YAML | 比 JSON 易读、支持注释 |

### 5.3 错误处理策略

| 层级 | 错误类型 | 处理方式 |
|------|---------|---------|
| 硬件层 | 串口打开失败 | 弹窗提示，禁用测量按钮 |
| 硬件层 | 通信超时 | 自动重试 3 次后提示用户 |
| 算法层 | 数据超出物理范围 | 标记为 None，跳过该项 |
| 算法层 | PPG 信号质量低 | 提示重新测量，保留上次结果 |
| UI 层 | 必填字段缺失 | 输入框红框 + 错误提示 |
| 数据库层 | 写入失败 | 回滚事务 + 日志记录 |
| 全局 | 未捕获异常 | 统一错误对话框 + 日志文件 |

---

### 5.4 合规工具模块

> **C-01 修复**：将禁用词过滤器和阈值常量从分散各处集中到独立工具模块，提升可维护性和可复用性。

#### 5.4.1 禁用词过滤器

**文件路径**：`src/utils/forbidden_words_filter.py`

**设计目的**：第 12.2 节合规红线要求禁止出现"诊断/筛查/治疗/预防"等词，所有建议内容必须经过此过滤器处理后方可展示。

**外部文件**：[`external/utils/forbidden_words_filter.py`](external/utils/forbidden_words_filter.html)

**合规保障**：
- 第 12.2 节合规红线要求禁止"诊断/筛查/治疗/预防"等词
- 所有建议内容必须经过 `ForbiddenWordsFilter.filter_text()` 处理后方可展示
- 集成方式：在 `AdviceOutputEngine` 渲染建议时调用

**关键接口**：

```python
from external.utils.forbidden_words_filter import ForbiddenWordsFilter

filter = ForbiddenWordsFilter()
filtered_text = filter.filter_text("建议去医院诊断")
# → "建议去医院健康参考"
```

#### 5.4.2 阈值常量模块

**外部文件**：[`external/utils/health_thresholds.py`](external/utils/health_thresholds.html)

**设计目的**：R-01 修复——统一管理所有健康指标阈值常量，避免跨文件硬编码不一致。

**关键接口**：

```python
from external.utils.health_thresholds import HealthThresholds

if heart_rate < HealthThresholds.HR_LOW_CAUTION:
    # 心动过缓提示

> **使用约定**：所有阈值引用常量而非硬编码。
```

---

## 6. 数据架构设计

### 6.1 SQLite 数据库表结构

**用户表（users）**：

```sql
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    age             INTEGER NOT NULL CHECK (age BETWEEN 6 AND 99),
    gender          INTEGER NOT NULL CHECK (gender IN (0, 1)),  -- 0=女 1=男
    height_cm       INTEGER NOT NULL CHECK (height_cm BETWEEN 90 AND 220),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
```

**测量记录表（measurements）**：

```sql
CREATE TABLE measurements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now','localtime')),

    -- BIA 体成分（19 项中的关键 8 项，其余存 raw_data）
    weight_kg           REAL,
    body_fat_pct        REAL,
    water_pct           REAL,
    protein_pct         REAL,
    muscle_kg           REAL,
    skeletal_muscle_kg  REAL,
    bmr_kcal            INTEGER,
    bone_kg             REAL,
    visceral_fat_level  INTEGER,
    body_age            INTEGER,

    -- PPG 生命体征
    heart_rate          INTEGER,
    spo2                INTEGER,
    perfusion_index     REAL,
    hrv_rmssd           REAL,

    -- 综合
    health_score        INTEGER,  -- 0-100
    risk_level          TEXT,     -- 'low' / 'medium' / 'high'

    -- 原始数据（JSON 字符串）
    bia_raw_json        TEXT,
    ppg_raw_json        TEXT,

    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_measurements_user_time
    ON measurements(user_id, timestamp DESC);
```

**建议表（advice）**：

```sql
CREATE TABLE advice (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    measurement_id  INTEGER NOT NULL,
    category        TEXT    NOT NULL,  -- 'diet'/'exercise'/'lifestyle'/'medical'
    priority        TEXT    NOT NULL,  -- 'low'/'medium'/'high'/'urgent'
    content         TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),

    FOREIGN KEY(measurement_id) REFERENCES measurements(id) ON DELETE CASCADE
);
```

### 6.2 知识库 JSON 结构

**医学知识库**（`data/knowledge/medical_knowledge.json`）：

```json
{
  "IND-03": {
    "name": "体脂率",
    "name_en": "Body Fat Percentage",
    "unit": "%",
    "category": "BIA",
    "reference_ranges": {
      "male": {
        "18-39": {"low": 11.0, "normal_low": 11.0, "normal_high": 16.9, "high": 27.0},
        "40-59": {"low": 12.0, "normal_low": 12.0, "normal_high": 17.9, "high": 28.0}
      },
      "female": {
        "18-39": {"low": 21.0, "normal_low": 21.0, "normal_high": 27.9, "high": 40.0}
      }
    },
    "clinical_significance": {
      "high": "体脂率偏高提示能量摄入超过消耗，长期可能增加心血管疾病和代谢综合征风险",
      "low": "体脂率过低可能影响激素水平和免疫功能",
      "normal": "体脂率处于健康范围，请继续保持"
    },
    "evidence_level": "A",
    "source": "WHO + 中国营养学会 + PMC12922097"
  }
}
```

**建议模板库**（`data/knowledge/advice_templates.json`）：

```json
{
  "high_body_fat": {
    "condition": "body_fat_pct > reference.high",
    "priority": "medium",
    "category": "diet",
    "template": "您的体脂率为 {value}%，超出标准范围（男 {ref_male}%/女 {ref_female}%）。建议：\n1. 每日热量摄入减少 300-500 Kcal\n2. 增加蛋白质摄入至体重×1.2g/天\n3. 每周 5 次 30 分钟有氧运动（快走/游泳/骑行）"
  },
  "abnormal_heart_rate": {
    "condition": "heart_rate < 40 OR heart_rate > 120",
    "priority": "urgent",
    "category": "medical",
    "template": "您的静息心率为 {value} bpm，超出正常范围（60-100 bpm）。建议尽快咨询医生排查心律失常。"
  }
}
```

### 6.3 数据流

```
用户填写基本信息 → 写入 users 表
        ↓
启动 BIA/PPG 测量 → 实时数据流
        ↓
解析数据帧 → 临时内存对象
        ↓
算法引擎处理 → 30 项指标对象
        ↓
知识库查询参考范围 → 标记状态（正常/警惕/超标）
        ↓
建议引擎生成建议 → 写入 advice 表
        ↓
完整结果写入 measurements 表
        ↓
UI 展示 + CSV 导出
```

---

## 7. 算法集成方案

### 7.1 BIA 算法（直接调用芯片内置算法）

BIA 芯片已内置 BestHealth TwoLegs 算法（19 项输出），上位机只需通过串口命令获取结果，无需自行实现。

**外部文件**：[`external/hardware/bia_module.py`](external/hardware/bia_module.html)

**调用流程**：

```python
from external.hardware.bia_module import BIAModule

bia_device = BIAModule(port="COM3")
bia_device.connect()
bia_device.start_measurement()                    # 发送 0xB0 指令
impedance, phase = bia_device.query_impedance()   # 0xB1，应答帧含 impedance + phase_angle
results = bia_device.calculate_body_composition(  # 返回 19 项
    height_cm=170, weight_kg=60.5, age=23, gender=1, impedance=impedance
)
# results = {body_fat_pct, water_pct, protein_pct, muscle_kg, ...}
```

### 7.2 PPG 算法（HeartPy 集成）

PPG 芯片直接输出 SpO₂/HR/PI，但**原始 PPG 波形**通过 HeartPy 计算 HRV 高级指标。

**外部文件**：
- [`external/algorithms/ppg_engine.py`](external/algorithms/ppg_engine.html)：HeartPy PPG/HRV 封装
- [`external/hardware/ppg_module.py`](external/hardware/ppg_module.html)：PPG 设备封装

**关键接口**：

```python
from external.algorithms.ppg_engine import process_ppg_waveform
from external.hardware.ppg_module import PPGModule

ppg_device = PPGModule(port="COM4")
ppg_device.connect()
raw_waveform = ppg_device.collect_waveform(duration_sec=15, sample_rate=50)
result = process_ppg_waveform(raw_waveform, sample_rate=50)
# result = {heart_rate, rmssd, sdnn, pnn50, ibi}
```

> **开源复用说明**：HeartPy 是 MVP1.0 **唯一强制集成的外部算法库**（MIT 许可证）。详见《开源项目复用可行性分析报告_v1.0.md》§8.1。

### 7.3 多模态融合评分（MVP 阶段：规则引擎）

**外部文件**：[`external/algorithms/fusion_engine.py`](external/algorithms/fusion_engine.html)

MVP1.0 使用基于规则的加权评分，后续升级路径：收集 200+ 样本后训练 XGBoost。

**关键接口**：

```python
from external.algorithms.fusion_engine import calculate_health_score

result = calculate_health_score(bia, ppg, user)
# result = {score: 0-100, risk_level: 'low'|'medium'|'high', issues: [...]}
```

**升级路径**：见 [`external/algorithms/fusion_engine.py`](external/algorithms/fusion_engine.html) 注释

---

## 8. 知识库建设方案

### 8.1 知识库来源

| 来源 | 内容 | 提取方式 |
|------|------|---------|
| 31 份 IND 报告 | 各指标的参考范围、临床意义、风险分级 | 自动化脚本 + 人工审核 |
| WHO/中国营养学会标准 | 通用参考值 | 手工录入 |
| ESC/ISHHRS 指南 | HRV 心率变异性参考 | 手工录入 |
| 临床经验 | 健康改善建议 | 专家访谈 + 模板化 |

### 8.2 知识库结构

**三层结构**：

1. **指标参考范围层**（必须）：每个指标的正常/警惕/超标阈值
2. **临床意义层**（重要）：每个指标异常时意味着什么
3. **改善建议层**（重要）：基于指标组合生成个性化建议

### 8.3 知识库构建工具

### 8.3 知识库构建工具

**外部文件**：[`external/tools/extract_knowledge.py`](external/tools/extract_knowledge.html)

从 IND 报告（docs/reports/IND-*.md）自动提取参考范围，输出到 `data/knowledge/medical_knowledge.json`。

**关键接口**：

```python
from external.tools.extract_knowledge import extract_reference_ranges

kb = extract_reference_ranges()
# 输出到 data/knowledge/medical_knowledge.json
```

### 8.4 建议生成引擎

**外部文件**：
- [`external/security/safe_condition_evaluator.py`](external/security/safe_condition_evaluator.html)：AST 白名单条件解析（`SafeConditionEvaluator`）
- [`external/knowledge/advice_engine.py`](external/knowledge/advice_engine.html)：建议引擎（`AdviceEngine`）

**关键接口**：

```python
from external.knowledge.advice_engine import AdviceEngine

engine = AdviceEngine("data/knowledge/advice_templates.json")
advices = engine.generate_advice(indicators, user_profile)
# → [{priority, category, content}, ...]
```

**审计修复标记**：`✅ T-02`：条件评估使用 `SafeConditionEvaluator`（AST 白名单），避免 `eval` 安全风险。

### 8.5 知识库验证流程

```
IND 报告提取 → 自动结构化 → 医学顾问审核 → 用户测试 → 上线
     ↑                                    ↓
   持续补充 ← 真实使用反馈 ← 用户报告 ←┘
```

---

## 9. 用户界面设计

### 9.1 主窗口布局

```
┌──────────────────────────────────────────────────────┐
│  大健康检测系统                              [_][□][×] │
├──────────────────────────────────────────────────────┤
│  [新建测量]  [历史记录]  [用户管理]  [设置]  [关于]    │
├──────────────────────────────────────────────────────┤
│                                                      │
│   ┌────────────────────────────────────────────┐     │
│   │         步骤 1/3：用户信息录入              │     │
│   ├────────────────────────────────────────────┤     │
│   │  姓名：[_______________]                    │     │
│   │  年龄：[__] 岁   性别：(○)男 ( )女          │     │
│   │  身高：[___] cm                             │     │
│   │  体重：[___] kg  ← 测量后自动填充           │     │
│   │                                            │     │
│   │           [下一步 →]                        │     │
│   └────────────────────────────────────────────┘     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 9.2 测量向导（3 步）

**步骤 1：用户信息录入**

- 必填：姓名、年龄、性别、身高
- 体重在 BIA 测量完成后自动填充
- 校验：年龄 6-99、身高 90-220 cm

**步骤 2：双手握持测量**

```
┌────────────────────────────────────────────┐
│  测量进行中...                              │
│                                            │
│  BIA 阻抗：[████████████████░░░] 80%        │
│  PPG 血氧：[██████████░░░░░░░░] 60%        │
│                                            │
│  当前心率：72 bpm    血氧：98%              │
│  实时波形：~/\_/~\__/\_/~                   │
│                                            │
│  提示：请保持双手稳定接触电极               │
│                                            │
│            [取消测量]                       │
└────────────────────────────────────────────┘
```

**步骤 3：结果展示**

```
┌──────────────────────────────────────────────────────┐
│  测量完成 - 张三 的健康报告                           │
│  时间：2026-07-09 14:30   综合评分：78 分（中等）    │
├──────────────────────────────────────────────────────┤
│  [核心指标卡片视图]                                    │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┐        │
│  │ 体重  │ 体脂率 │ 肌肉量 │ 心率  │ 血氧  │ 评分  │        │
│  │60.5kg│ 18.2% │42.3kg │ 72   │ 98%  │ 78   │        │
│  │ ✓    │ ⚠    │ ✓    │ ✓    │ ✓    │  ⚠   │        │
│  └──────┴──────┴──────┴──────┴──────┴──────┘        │
├──────────────────────────────────────────────────────┤
│  [详细指标表格]                                       │
│  指标名称  测量值  参考范围  状态                     │
│  体重     60.5kg  50-70kg   ✓ 正常                  │
│  体脂率   18.2%   11-17%    ⚠ 偏高 1.2%             │
│  ...                                                  │
├──────────────────────────────────────────────────────┤
│  [趋势图（最近 7 次）]                                │
│  📈 体脂率：17.8 → 18.5 → 18.2（最近 3 次）          │
├──────────────────────────────────────────────────────┤
│  [健康建议]                                           │
│  🔴 【高】您的体脂率偏高，建议：                       │
│     1. 每日热量摄入减少 300 Kcal                      │
│     2. 每周 5 次 30 分钟有氧运动                       │
│  🟡 【中】静息心率处于正常偏高，建议保持规律作息       │
├──────────────────────────────────────────────────────┤
│  [导出 CSV]  [打印报告]  [完成]                       │
└──────────────────────────────────────────────────────┘
```

### 9.3 关键 UI 组件

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 向导框架 | QWizard | 内置步骤管理 |
| 实时波形 | QPainter + QTimer | PPG 波形滚动显示 |
| 趋势图 | matplotlib + Qt 嵌入 | 历史对比折线图 |
| 表格 | QTableWidget | 30 项指标列表 |
| 状态色 | stylesheet QSS | 绿/黄/红三色标记 |

---

## 10. 测试方案

### 10.1 测试分层

| 层级 | 测试内容 | 工具 | 覆盖率目标 |
|------|---------|------|-----------|
| 单元测试 | 函数级逻辑（帧解析、算法计算） | pytest | >80% |
| 集成测试 | 模块间接口（硬件→算法→数据库） | pytest + mock | >70% |
| 系统测试 | 端到端流程（完整测量→结果展示） | 手动 + 自动化 | 关键路径 100% |
| 验收测试 | 用户场景（10 人试测） | 人工 | 通过率 >95% |

### 10.2 测试用例设计

**硬件通信测试**：

**外部文件**：[`external/tests/test_bia_module.py`](external/tests/test_bia_module.html)

```python
from external.tests.test_bia_module import test_bia_query_impedance_valid_response
# 完整测试用例见外部文件
```

**算法测试**：

**外部文件**：[`external/tests/test_fusion.py`](external/tests/test_fusion.html)

```python
from external.tests.test_fusion import test_health_score_normal_user
# 完整测试用例见外部文件
```

### 10.3 验收测试场景

| 场景 | 步骤 | 预期结果 |
|------|------|---------|
| 完整测量 | 1.填写信息 → 2.握持测量 → 3.查看结果 | 30 秒内完成，30 项指标全部显示 |
| 历史查询 | 1.完成 3 次测量 → 2.查看趋势 | 显示 3 次对比折线图 |
| 数据导出 | 1.完成测量 → 2.点击导出 CSV | 生成 Excel 可打开的文件 |
| 异常恢复 | 测量中拔掉串口 | UI 提示错误，不崩溃，可重试 |
| 重测建议 | 手指脱离电极 | 自动提示"请保持接触"，无需重启 |

---

## 11. 部署与交付

### 11.1 开发环境要求

| 项 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 64 位 |
| Python | 3.10+ |
| 内存 | ≥ 8 GB |
| 硬盘 | ≥ 2 GB 可用空间 |
| USB | ≥ 2 个空闲 USB 口（接 BIA + PPG） |

### 11.2 依赖清单（requirements.txt）

```
pyserial>=3.5
pyserial-asyncio>=0.6
pyqt6>=6.5
pandas>=2.0
numpy>=1.24
heartpy>=1.2.5
matplotlib>=3.7
pyyaml>=6.0
```

### 11.3 打包流程

```bash
# 使用 PyInstaller 打包成单文件 exe
pyinstaller --onefile --windowed \
    --name "HealthCheckSystem" \
    --add-data "data;data" \
    --add-data "config.yaml;." \
    --icon "assets/icon.ico" \
    src/main.py
```

**输出**：`dist/HealthCheckSystem.exe`（约 50-80 MB）

### 11.4 交付物清单

| 序号 | 交付物 | 格式 | 说明 |
|------|--------|------|------|
| 1 | 可执行程序 | `.exe` | 双击即用，无需 Python 环境 |
| 2 | 用户手册 | PDF | 安装、操作、结果解读（10 页） |
| 3 | 技术文档 | Markdown | 本文档 |
| 4 | 源代码 | Python | 含完整注释 |
| 5 | 测试用例 | pytest | 单元测试 + 集成测试 |
| 6 | 数据库初始数据 | `.db` | 含 3 张表结构 |
| 7 | 知识库 | JSON | 30 项指标参考范围 |
| 8 | 配置文件模板 | YAML | COM 口、路径等 |

---

## 12. 风险评估与应对

### 12.1 技术风险

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| BIA 串口通信不稳定 | 中 | 高 | 帧校验 + 超时重试 + 降级到只读 PPG |
| PPG 信号质量差 | 中 | 中 | PI 门控 + 提示重测 |
| 知识库不完整 | 高 | 中 | MVP 阶段先覆盖 P0/P1 指标（20 项） |
| PyQt6 打包体积大 | 低 | 低 | 接受 80MB，使用 UPX 压缩 |
| 中文显示乱码 | 低 | 中 | 统一 UTF-8 编码 + 字体打包 |

### 12.2 合规风险（必须重视）

| 风险项 | 红线 | 安全做法 |
|--------|------|---------|
| **禁用词** | 不得出现"诊断/筛查/治疗/预防/医疗" | 统一使用"趋势参考/健康观察/保健提示" |
| **精度承诺** | 不得宣称"医学级精度" | 标注"消费级参考，非医疗器械" |
| **医疗建议** | 不得给出用药方案 | 仅提供饮食/运动/生活方式建议 |
| **数据隐私** | 生物特征数据需本地存储 | 默认不上传云端，加密存储 |
| **免责声明** | 每份报告必须包含 | "本设备非医疗器械，结果仅供参考，如有不适请咨询医生" |

### 12.3 进度风险

| 风险 | 影响 | 应对 |
|------|------|------|
| 硬件调试延期 | MVP 推迟 1-2 周 | 预留缓冲时间，关键路径优先 |
| 知识库整理耗时长 | 知识不完整 | 先做 P0 指标，其他迭代补充 |
| PyQt6 学习曲线 | UI 开发延期 | 使用 Qt Designer 拖拽，简化开发 |

---

## 13. 里程碑与排期

> **⚠️ S-01/S-02/S-03 修复**：根据审计报告，原 4 周（20 天）排期严重低估工作量。
> 实际需要 **5 周（25 工作日）**。
> 修订原因：
> - 知识库建设实际需 9 天（见 §17.5），原排期仅 2 天
> - 算法集成新增 8 天未明确列入（见 §18.7）
> - 建议引擎升级、禁用词过滤、异步测量均需额外工时

### 13.1 MVP1.0 总体排期（5 周 / 25 工作日）

```
Week 1 (Day 1-5)   : 基础架构搭建（含伪代码框架）
Week 2 (Day 6-10)  : 算法集成 + 大健康指标融合
Week 3 (Day 11-15) : 知识库建设（P0 指标 + 医学顾问评审）
Week 4 (Day 16-20) : UI 开发 + 情绪建模 + 建议引擎升级
Week 5 (Day 21-25) : 端到端测试 + 禁用词过滤 + 打包交付
```

### 13.2 详细任务拆解（修订版）

| 阶段 | 天数 | 关键任务 | 输出物 | 责任人 | 修复说明 |
|------|------|---------|--------|--------|---------|
| **W1-D1** | 1 | 环境搭建、项目初始化、目录结构 | requirements.txt, 项目骨架 | 全栈 | - |
| **W1-D2** | 1 | BIA 协议解析、串口通信测试 | bia_module.py + 单元测试 | 后端 | - |
| **W1-D3** | 1 | PPG UART 协议、波形读取 | ppg_module.py + 单元测试 | 后端 | - |
| **W1-D4** | 1 | 帧同步器、错误处理、async 测量框架 | frame_synchronizer.py | 后端 | **新增** async 框架 |
| **W1-D5** | 1 | SQLite 表结构、DB 管理器、常量定义 | schema.sql, constants.py | 后端 | **新增** constants.py |
| **W2-D6** | 1 | BIA 测量流程集成（端到端） | 可测量的 BIA 原型 | 全栈 | - |
| **W2-D7** | 1 | PPG 测量流程集成 | 可测量的 PPG 原型 | 全栈 | - |
| **W2-D8** | 1 | HeartPy 集成、HRV 计算、异步测量 | ppg_engine.py, measure_async | 后端 | **新增** async 集成 |
| **W2-D9** | 1 | 大健康指标融合引擎 | HealthIndicatorFusion | 后端 | **扩展** fusion.py |
| **W2-D10** | 1 | AST 安全解析器 + 建议引擎 v1 | safe_condition_evaluator.py | 后端 | **新增** AST 解析器 |
| **W3-D11** | 1 | 医学知识库结构设计 + 提取脚本 | medical_knowledge.json (框架) | 数据+医学 | **修订** 从 2 天→1天 |
| **W3-D12** | 1 | 30 项指标参考范围录入 + 医学顾问评审 | medical_knowledge.json (完整) | 数据+医学顾问 | **新增** 顾问评审 |
| **W3-D13** | 1 | 建议模板库（15 个）+ 规则引擎 v2 | advice_templates.json | 后端+医学 | **扩展** 从 10→15 个 |
| **W3-D14** | 1 | 情绪判断规则 + 心理建议模板 | emotion_model.py | 后端+心理 | **新增** 情绪模块 |
| **W3-D15** | 1 | 医疗级别警示规则（8 条）+ 持续性检测 | medical_alert_rules.py | 后端+医学顾问 | **新增** 医疗规则 |
| **W4-D16** | 1 | PyQt6 主窗口、向导框架 | main_window.py | 前端 | - |
| **W4-D17** | 1 | 结果展示页面（表格+状态色） | result_view.py | 前端 | - |
| **W4-D18** | 1 | 趋势图、历史查询、情绪结果展示 | trend_chart.py | 前端 | **新增** 情绪展示 |
| **W4-D19** | 1 | 禁用词过滤器 + 合规性校验 | forbidden_words_filter.py | 后端 | **新增** C-01 修复 |
| **W4-D20** | 1 | CSV 导出、数据库迁移、端到端测试 | export 功能 + 测试报告 | 全栈 | - |
| **W5-D21** | 1 | 端到端测试（含异常路径）+ bug 修复 | 测试报告 | 全栈 | **扩展** 从 1天→2天 |
| **W5-D22** | 1 | 集成测试 + P0 模板补充验证 | 测试报告 | 全栈 | **新增** 模板验证 |
| **W5-D23** | 1 | 性能优化（异步并发、缓存） | 优化报告 | 后端 | **新增** 性能优化 |
| **W5-D24** | 1 | PyInstaller 打包 + 用户手册 | .exe 文件 | 全栈 | - |
| **W5-D25** | 1 | 最终验收、文档整理、交付包 | 完整交付包 | 全栈 | - |

### 13.3 资源需求（修订版）

| 角色 | 人数 | 技能要求 | 预约时段 | 备注 |
|------|------|---------|---------|------|
| 全栈开发 | 1-2 人 | Python + PyQt6 + 串口通信 | 全程 | 核心资源 |
| 医学顾问（心血管内科） | 1 人 | 心血管医学背景 | W3-D12（4h） | **必须邀请** |
| 营养师（可选） | 1 人 | 注册营养师 | W3-D12（2h） | 建议邀请 |
| 心理治疗师（可选） | 1 人 | 心理咨询资质 | W3-D14（2h） | 建议邀请 |
| 测试 | 0.5 人 | 手动测试 + 自动化基础 | W4-W5 | 后期介入 |

> **⚠️ 外部资源协调**：医学顾问、营养师、心理治疗师需提前预约档期（见第 17.5 节）

### 13.4 关键里程碑（修订版）

| 里程碑 | 原计划 | 修订后 | 验收标准 |
|--------|--------|--------|---------|
| **M1: 硬件通信打通** | W1-D5 | **W1-D5** | 能读取 BIA + PPG 原始数据 |
| **M2: 单指标测量完成** | W2-D10 | **W3-D10** | 能完成一次完整测量并显示 30 项指标 |
| **M3: 知识库 + 建议可用** | W3-D13 | **W4-D15** | 输入指标值，能输出 15 个模板建议，含免责 |
| **M4: MVP 集成测试通过** | W4-D18 | **W5-D22** | 10 人试测通过率 >95% |
| **M5: 正式交付** | W4-D20 | **W5-D25** | exe 可安装运行 + 文档齐全 |

### 13.5 修订对比

| 项目 | 原计划 | 修订后 | 变化 |
|------|--------|--------|------|
| 总工期 | 4 周（20 天） | **5 周（25 天）** | +5 天 |
| 知识库建设 | 2 天 | **4 天** | +2 天 |
| 算法集成 | 5 天 | **7 天** | +2 天（含 AST + async） |
| 测试 | 3 天 | **4 天** | +1 天 |
| 交付时间 | 第 4 周 | **第 5 周** | +1 周 |

---

## 14. 附录：参考资产清单

### 14.1 已有资产（可直接复用）

| 类别 | 文件路径 | 内容 |
|------|---------|------|
| 芯片手册 | `芯片模组/体脂模组/BestHealth_TwoLegs_技术参考手册.md` | BIA 芯片 19 项指标算法说明 |
| 芯片手册 | `芯片模组/血氧监测/BMH08002_技术参考手册_V1.2.md` | PPG 模组 UART 协议 |
| 通信协议 | `芯片模组/体脂模组/体脂成分通信协议技术说明书.md` | BIA 完整报文格式 |
| 指标清单 | `docs/指标CSV/指标审计原始数据/大健康检测指标总表_可行指标_合并版_V5.0.csv` | 30 项可行指标 + 四角评估 |
| 指标清单 | `docs/指标CSV/指标审计原始数据/大健康检测指标总表_可行指标_合并版_V5.0.md` | 同上，Markdown 版本 |
| 指标报告 | `docs/reports/专项研究报告总索引.md` | 31 份 IND 报告索引 |
| 指标报告 | `docs/reports/IND-01 ~ IND-38` | 各指标的算法研究 + 参考范围 + 临床意义 |
| 资源调研 | `docs/reports/RES-00_开源项目与基准数据集调研报告.md` | 开源算法库与数据集 |
| 算法审计 | `docs/reports/ALGO-AUDIT-2026_算法审计总报告_全面升级版.md` | 四角色三角对抗审计 |
| 代码库 | `docs/src/bialib/` | BIA C 算法库（参考） |
| 代码库 | `docs/src/ppglib/` | PPG C 算法库（参考） |

### 14.2 需要新建的文件

| 类别 | 路径 | 说明 |
|------|------|------|
| 项目配置 | `config.yaml` | COM 口、路径等配置 |
| 依赖清单 | `requirements.txt` | Python 依赖 |
| 数据库 | `data/schema.sql` | 3 张表结构 |
| 知识库 | `data/knowledge/medical_knowledge.json` | 医学参考范围 |
| 知识库 | `data/knowledge/advice_templates.json` | 建议模板 |
| 入口 | `src/main.py` | 应用入口 |
| 硬件层 | `src/hardware/bia_module.py` | BIA 通信 |
| 硬件层 | `src/hardware/ppg_module.py` | PPG 通信 |
| 硬件层 | `src/hardware/frame_synchronizer.py` | 帧同步 |
| 算法层 | `src/algorithms/bia_engine.py` | BIA 算法 |
| 算法层 | `src/algorithms/ppg_engine.py` | PPG 算法 |
| 算法层 | `src/algorithms/fusion.py` | 多模态融合 |
| 业务层 | `src/knowledge/medical_db.py` | 知识库查询 |
| 业务层 | `src/knowledge/advice_engine.py` | 建议生成 |
| 业务层 | `src/database/db_manager.py` | 数据库管理 |
| 业务层 | `src/database/models.py` | 数据模型 |
| 界面层 | `src/ui/main_window.py` | 主窗口 |
| 界面层 | `src/ui/wizard_pages.py` | 向导 |
| 界面层 | `src/ui/result_view.py` | 结果展示 |
| 界面层 | `src/ui/trend_chart.py` | 趋势图 |
| 工具 | `tools/extract_knowledge.py` | 知识提取 |
| 测试 | `tests/test_*.py` | 各模块测试 |

### 14.3 第三方库依赖

| 库 | 用途 | 许可证 |
|----|------|--------|
| pyserial | 串口通信 | BSD |
| pyserial-asyncio | 异步串口 | BSD |
| pyqt6 | 桌面 UI | GPL/Commercial |
| pandas | 数据处理 | BSD |
| numpy | 数值计算 | BSD |
| heartpy | PPG 信号处理 | MIT |
| matplotlib | 图表 | BSD |
| pyyaml | 配置解析 | MIT |
| pyinstaller | 打包 | GPL |

---

## 文档修订记录

| 版本 | 日期 | 修订内容 |
|------|------|---------|
| v1.0 | 2026-07-09 | 初版，基于 MVP1.0 范围编写 |
| v1.1 | 2026-07-09 | 新增第 15-18 章共 4 个补充章节，填补"大健康指标/建议/医学知识/大健康知识"4 个待补充环节；新增第 18 章端到端 Python 伪代码作为开发参考 |
| v1.2 | 2026-07-09 | **审计修复版**：修复技术方案审计报告（v1.0）中 11 个问题 |
| v1.3 | 2026-07-10 | **结构性重构版**：根据《开源项目复用可行性分析报告_v1.0.md》选型结论，将所有静态样例代码外部化到 `external/` 目录（14 个 .py 文件，1400+ 行代码）；主文档从 2997 行缩减至 2001 行；正文章节改为描述性内容 + 外部文件链接引用；新增 `external/README.md` 模块索引文件 |

---

**评审指引**：请重点关注以下章节的合理性：
- §5 软件架构设计（PyQt6→PySide6 是否已更新）
- §7 算法集成方案（HeartPy 集成是否与 §8.1 开源报告一致）
- **§13 里程碑与排期（已修订为5周25天）**
- **§15-18 补充章节（v1.3 已重构，代码外部化）**

> **v1.3 重构摘要**：所有静态代码已外部化到 `external/` 目录，正文章节仅保留描述性内容和链接引用。代码随上游开源组件（HeartPy）变更时可独立更新，不影响文档结构。

如有调整建议，请直接标注后回复。

---

# v1.1 补充章节（2026-07-09）

> 以下章节（15-18）为 v1.1 新增内容，用于填补 v1.0 检测逻辑链路中的 4 个"待补充"环节。

---

## 15. 大健康指标清单（补充章节）

> **补充说明**：本节为 v1.0 文档第 1.2 节"检测逻辑链路"中标记为"待补充"的**大健康指标**环节的完整定义。  
> 大健康指标是基于 BIA / PPG / 基础数据等"数据指标"经过医学算法融合后产出的**用户可感知、可解释的复合健康维度**。

### 15.1 大健康指标定义原则

大健康指标的设计遵循以下原则：

1. **可解释性**：用户能直观理解"这个指标代表什么意思"
2. **可执行性**：每个指标都能映射到具体的健康改善建议
3. **临床可追溯**：每个指标的算法逻辑可追溯到权威医学文献
4. **MVP1.0 范围内**：仅基于已有 BIA + PPG + 基础数据可计算（不依赖尚未引入的硬件）

### 15.2 大健康指标清单（12 项）

| 序号 | 指标名称 | 指标标识 | 单位 | 理想范围 | 数据来源（基础指标） | 算法类型 |
|------|---------|---------|------|---------|---------------------|---------|
| 1 | 心率变异性（HRV-RMSSD） | `hrv_rmssd` | ms | 30 岁以上 ≥ 30；< 30 岁 ≥ 40 | PPG 原始波形 IBI 序列 | 时域统计 |
| 2 | 血氧饱和度（SpO₂） | `spo2_health` | % | 95 – 99 | PPG 芯片输出 | 直接读取 |
| 3 | 睡眠深/浅比例（基于 HRV 估算） | `sleep_deep_ratio` | % | 深睡占比 20 – 35 | PPG 夜间连续 HRV（需扩展） | 启发式分类 |
| 4 | 压力指数（基于 HRV+HR 联合判定） | `stress_index` | 0-100 | < 40 低 / 40-70 中 / > 70 高 | PPG 实时 HR + HRV | 加权评分 |
| 5 | 情绪倾向（焦虑/平静/低落） | `mood_tendency` | 类别 | 平静为主 | HRV + 皮电（未来扩展） | 规则分类（MVP 阶段简化为 2 态） |
| 6 | 基础代谢年龄 | `metabolic_age` | 岁 | 实际年龄 ± 3 岁 | BIA → BMR → 推算 | 公式换算 |
| 7 | 体脂偏离度（相对同龄人） | `bf_deviation` | % | ± 15% | BIA 体脂率 + 同龄同性别参考 | Z 分数 |
| 8 | 肌肉均衡度 | `muscle_balance` | 比率 | 0.9 – 1.1 | BIA 上下肢肌肉量 | 比值（⚠️ **Step-1 硬件约束**：双手接触式双足 BIA 仅测下肢阻抗，**无法获取上肢肌肉量数据**，MVP 阶段该项仅做占位标注） |
| 9 | 内脏脂肪风险等级 | `visceral_fat_risk` | 等级 | 低/中/高 | BIA 内脏脂肪面积 | 阈值分级 |
| 10 | 心脏功能指数（基于 HR 恢复） | `cardio_fitness` | 0-100 | 50+ | PPG + 静息/活动后 HR 差（需测量协议） | 经验公式 |
| 11 | 水分平衡状态 | `hydration_status` | 类别 | 正常/偏低/偏高 | BIA 身体水分率 | 阈值分类 |
| 12 | 综合健康分 | `composite_health_score` | 0-100 | 80+ | 上述 11 项加权 | 规则融合（MVP）→ XGBoost（v2.0） |

### 15.3 指标详细定义

#### 15.3.1 心率变异性（HRV-RMSSD）

- **定义**：相邻正常心跳间期差值的均方根，反映自主神经系统活性
- **单位**：毫秒（ms）
- **理想范围**：
  - 20-29 岁：RMSSD ≥ 40 ms
  - 30-49 岁：RMSSD ≥ 30 ms
  - 50+ 岁：RMSSD ≥ 20 ms
- **数据来源**：PPG 芯片原始波形 → HeartPy 检测 IBI 序列 → 计算 RMSSD
- **算法**：`RMSSD = sqrt(mean(diff(IBI)^2))`
- **临床意义**：低 HRV 与心血管疾病、压力、焦虑相关（来源：Task Force of ESC/NASPE 1996）

#### 15.3.2 血氧饱和度（SpO₂）

- **定义**：血液中氧合血红蛋白占比
- **单位**：百分比（%）
- **理想范围**：95 – 99%
- **数据来源**：PPG 芯片直接输出
- **算法**：芯片内置（红光+红外光吸光度比值法）

#### 15.3.3 睡眠深/浅比例

- **定义**：基于夜间 HRV 变异性估算的深度睡眠时长占比（**MVP1.0 暂以单次测量 HRV 估算"睡眠质量倾向"，需用户输入睡眠时长**）
- **单位**：百分比（%）
- **理想范围**：深睡 20% – 35%
- **算法**：`睡眠质量得分 = f(晨起 HRV_RMSSD, 自报睡眠时长, 晨起静息心率)`
- **MVP 简化**：通过"晨起测量"模式 + 问卷补充实现

#### 15.3.4 压力指数

- **定义**：基于 HRV 与静息心率联合评估的当前压力水平
- **单位**：0-100 分
- **理想范围**：< 40 为低压力；40-70 为中等压力；> 70 为高压力
- **数据来源**：PPG 实时心率 + HRV
- **算法（启发式）**：见 [`external/algorithms/health_indicators.py`](external/algorithms/health_indicators.html)（函数 `calc_stress_index`）

#### 15.3.5 情绪倾向

- **定义**：基于生理信号推断的情绪状态（MVP 阶段简化为 3 态）
- **算法**：见 [`external/algorithms/health_indicators.py`](external/algorithms/health_indicators.html)（函数 `infer_mood`）

#### 15.3.6 基础代谢年龄

- **定义**：基于基础代谢率推算的"代谢年龄"
- **算法**：见 [`external/algorithms/health_indicators.py`](external/algorithms/health_indicators.html)（函数 `calc_metabolic_age`），参考 Mifflin-St Jeor 公式反推

#### 15.3.7 体脂偏离度

- **定义**：实测体脂率与同年龄同性别参考中位数的 Z 分数
- **算法**：见 [`external/algorithms/health_indicators.py`](external/algorithms/health_indicators.html)（函数 `calc_bf_deviation`）

#### 15.3.8 内脏脂肪风险等级

- **定义**：基于芯片 BestHealth TwoLegs 输出的 VFAL 等级（1-12）的风险分级
- **算法**：见 [`external/algorithms/health_indicators.py`](external/algorithms/health_indicators.html)（函数 `classify_visceral_fat`）
- **⚠️ 单位说明**：芯片输出的是等级整数 VFAL（1-12），不是面积值 cm²。`classify_visceral_fat` 将 VFAL 按芯片手册 §3.3.3 映射到面积区间后判断：VFAL 1-4 → 低风险，5-7 → 中风险，8-12 → 高风险

#### 15.3.9 水分平衡状态

- **定义**：体内水分率是否处于正常区间
- **算法**：见 [`external/algorithms/health_indicators.py`](external/algorithms/health_indicators.html)（函数 `classify_hydration`）

#### 15.3.10 综合健康分

- **算法**：见 [`external/algorithms/fusion_engine.py`](external/algorithms/fusion_engine.html)（函数 `calculate_health_score`）

> **大健康指标算法统一索引**：所有 12 项指标算法均已提取到 [`external/algorithms/`](external/algorithms/) 目录，包括：
> - `health_indicators.py`：压力指数、情绪、体脂偏离度、代谢年龄、水分、心肺功能
> - `fusion_engine.py`：综合健康评分
> - `ppg_engine.py`：HeartPy PPG/HRV 处理

### 15.4 大健康指标数据流

```
基础数据 ─┐
BIA 指标 ─┼─→ 大健康指标引擎 ─→ 12 项大健康指标 ─→ 知识库查询 ─→ 用户展示
PPG 指标 ─┘        ↑
                  算法融合
                  医学知识
```

### 15.5 指标存储扩展

在 `measurements` 表中增加 JSON 字段存储大健康指标：

```sql
ALTER TABLE measurements ADD COLUMN health_indicators_json TEXT;
```

存储结构：

```json
{
  "hrv_rmssd": 42.5,
  "spo2_health": 98,
  "sleep_deep_ratio": null,
  "stress_index": 35,
  "mood_tendency": "中性状态",
  "metabolic_age": 28,
  "bf_deviation": 0.32,
  "visceral_fat_risk": "low",
  "hydration_status": "正常",
  "composite_health_score": 82
}
```

---

## 16. 大健康建议生成方案（补充章节）

> **补充说明**：本节为 v1.0 文档第 1.2 节"检测逻辑链路"中标记为"待补充"的**大健康建议**环节的完整定义。  
> 大健康建议是从"数据指标 → 大健康指标 → 医学建议 → 用户可执行行动"的最后一公里，必须保证**可解释、可执行、合规免责**。

### 16.1 三层建议生成架构

```
第一层：健康建议（基于大健康指标）
   ↓ 触发条件
第二层：情绪判断（基于压力指数 + HRV + 行为问卷）
   ↓ 触发条件
第三层：医疗建议（基于累积异常 + 风险等级）
   ↓ 强制附加
免责声明（所有层级统一覆盖）
```

> **⚠️ P1-3 修复（2026-07-10）**：免责声明从 Layer 3 提升到汇总层，
> `AdviceGenerator.generate()` 调用 `_append_disclaimer_all()` 对所有层级的建议统一附加免责文本，
> 确保 Layer 1/2 的健康建议和情绪判断也有免责覆盖，不会因触发条件不满足 Layer 3 而遗漏免责。

### 16.2 第一层：健康建议生成

**目标**：将异常指标转化为可执行的健康改善建议

#### 16.2.1 输入

- 12 项大健康指标
- 用户档案（年龄、性别、既往史）

#### 16.2.2 输出

- 优先级排序的建议列表
- 每条建议包含：类别、优先级、行动步骤

#### 16.2.3 建议模板结构

```json
{
  "rule_id": "high_body_fat_diet_v1",
  "trigger": {
    "indicator": "bf_deviation",
    "operator": ">",
    "threshold": 1.0
  },
  "advice": {
    "category": "diet",
    "priority": "medium",
    "title": "体脂率偏高，建议饮食调整",
    "content": "您的体脂率偏离同龄人标准 {deviation}σ。建议：\n1. 每日热量摄入减少 300-500 Kcal\n2. 增加蛋白质摄入至体重×1.2g/天\n3. 减少精制糖和饱和脂肪\n4. 每周记录饮食日记",
    "action_items": [
      "下载饮食记录 App",
      "每日蛋白质摄入目标：{protein_target}g",
      "每周自测体重"
    ],
    "evidence_level": "A",
    "source": "中国营养学会《国民营养计划》+ PMID:28937822"
  }
}
```

#### 16.2.4 完整建议模板库（首批 P0 指标）

> **⚠️ R-01 修复**：所有阈值必须引用 `HealthThresholds` 常量，避免硬编码。
> 常量定义见 [§5.4.2 阈值常量模块](#5-4-2-阈值常量模块)。

> **示例**（`high_bf_diet` 模板的 JSON 结构）：

```json
{
  "rule_id": "high_body_fat_diet_v1",
  "trigger": {
    "indicator": "bf_deviation",
    "operator": ">",
    "threshold": 1.0
  },
  "advice": {
    "category": "diet",
    "priority": "medium",
    "title": "体脂率偏高，建议饮食调整",
    "content": "您的体脂率偏离同龄人标准 {deviation}σ。建议：\n1. 每日热量摄入减少 300-500 Kcal\n2. 增加蛋白质摄入至体重×1.2g/天\n3. 减少精制糖和饱和脂肪\n4. 每周记录饮食日记",
    "action_items": [
      "下载饮食记录 App",
      "每日蛋白质摄入目标：{protein_target}g",
      "每周自测体重"
    ],
    "evidence_level": "A",
    "source": "中国营养学会《国民营养计划》+ PMID:28937822"
  }
}
```

| 指标 | 触发条件 | 建议类别 | 优先级 | 模板 ID |
|------|---------|---------|--------|---------|
| 体脂偏离度 | > 1.0σ | 饮食 | 中 | `high_bf_diet` |
| 体脂偏离度 | > 1.0σ | 运动 | 中 | `high_bf_exercise` |
| HRV 偏低 | < 20ms | 生活方式 | 高 | `low_hrv_lifestyle` |
| 压力指数 | > 70 | 心理放松 | 高 | `high_stress_relax` |
| 血氧偏低 | < 94% | 医疗 | 紧急 | `low_spo2_medical` |
| 内脏脂肪高 | 等级=高 | 饮食+运动 | 中 | `high_vfat_action` |
| 水分偏低 | 男<50%/女<45% | 饮水 | 低 | `low_water_hydration` |
| 水分偏高 | 男>65%/女>60% | 生活方式 | 低 | `high_water_hydration` |
| 肌肉量偏低 | 肌肉量 < 参考低值 | 运动 | 中 | `low_muscle_exercise` |
| BMI 偏低 | < 18.5 | 营养 | 中 | `low_bmi_nutrition` |
| 综合健康分偏低 | < 50 | 综合 | 高 | `very_low_health_score` |
| 自主神经活跃状态 | 情绪=自主神经活跃状态 | 心理 | 高 | `autonomic_active_psychology` |
| 静息心率异常 | <HR_LOW_CAUTION(50) 或 >HR_HIGH_CAUTION(100) | 医疗 | 紧急 | `abnormal_hr_medical` |
| BMI 超标 | ≥ 28（中国） | 运动 | 中 | `high_bmi_exercise` |
| 代谢年龄偏大 | 实际+5 岁 | 综合 | 中 | `metabolic_age_comprehensive` |

#### 16.2.5 情绪独立建议模板（R-03 修复）

> **⚠️ R-03 修复**：为情绪判断结果（4 类）建立独立建议模板，增强情感识别体验。

| 情绪状态 | 置信度要求 | 优先级 | 模板 ID | 建议内容要点 |
|---------|---------|--------|---------|------------|
| 自主神经活跃状态 | ≥ 0.7 | 高 | `autonomic_active_breathing` | 4-7-8 呼吸法、渐进式肌肉放松、压力源排查 |
| 压力累积 | ≥ 0.65 | 中 | `stress_management` | 规律作息、减少咖啡因、户外活动 |
| 轻度疲劳 | ≥ 0.6 | 低 | `mild_fatigue` | 保证睡眠、适度运动、补充水分 |
| 平静积极 | ≥ 0.7 | - | - | 正面反馈，维持现状 |

```json
{
  "autonomic_active_breathing": {
    "rule_id": "autonomic_active_v1",
    "trigger": {
      "indicator": "emotional_state",
      "operator": "==",
      "value": "自主神经活跃状态",
      "confidence_min": 0.7
    },
    "advice": {
      "category": "psychology",
      "priority": "high",
      "title": "自主神经活跃状态参考",
      "content": "您的测量提示自主神经系统处于较高唤醒状态，以下方法可能有帮助：\n1. **4-7-8 呼吸法**：吸气 4 秒 → 屏气 7 秒 → 呼气 8 秒，重复 3-5 次\n2. **渐进式肌肉放松**：从脚趾到头顶，依次紧绷 5 秒后放松\n3. **建议关注近期睡眠质量和压力水平**，如持续感到不适可咨询医生",
      "action_items": [
        "每日练习 4-7-8 呼吸法 2-3 次",
        "记录压力触发因素",
        "如症状持续超过 2 周，建议咨询医生"
      ],
      "evidence_level": "A",
      "source": "PMID:24672813 + APA 临床指南"
    }
  },
  "stress_management": {
    "rule_id": "stress_management_v1",
    "trigger": {
      "indicator": "emotional_state",
      "operator": "==",
      "value": "压力累积状态",
      "confidence_min": 0.65
    },
    "advice": {
      "category": "lifestyle",
      "priority": "medium",
      "title": "压力管理建议",
      "content": "您的压力指数偏高，建议：\n1. 保持规律作息，每晚 7-8 小时睡眠\n2. 每天 30 分钟有氧运动（降低皮质醇）\n3. 减少咖啡因和酒精摄入\n4. 每天预留 15 分钟正念冥想",
      "action_items": [
        "设定固定的睡眠时间",
        "减少睡前屏幕使用",
        "尝试每日 15 分钟冥想"
      ],
      "evidence_level": "A",
      "source": "ACSM Guidelines 2021 + PMID:28937822"
    }
  }
}
```

#### 16.2.6 建议合并与去重

当多条规则触发时，需要：

1. **同类合并**：如"体脂率高"触发的运动建议和 BMI 触发的运动建议，合并为一条
2. **优先级排序**：`urgent` > `high` > `medium` > `low`
3. **数量控制**：每次最多展示 8 条核心建议，避免信息过载

### 16.3 第二层：情绪判断（基于生理信号 + 行为问卷）

**目标**：识别用户的情绪/心理状态倾向（如焦虑、压力累积、低落）

#### 16.3.1 MVP1.0 简化方案

由于 MVP1.0 缺乏皮电、皮肤温度等情绪专用传感器，采用**HRV + 静息心率 + 短期问卷**的联合判定：

| 输入 | 来源 | 权重 |
|------|------|------|
| HRV-RMSSD | PPG 实时 | 40% |
| 静息心率 | PPG 实时 | 20% |
| 压力指数 | 计算得出 | 30% |
| 简版 PSS-4 问卷 | 用户填答（4 题） | 10% |

#### 16.3.2 情绪状态判定规则

> **外部化说明**：情绪判定算法已提取到外部文件。

**外部文件**：[`external/knowledge/advice_engine.py`](external/knowledge/advice_engine.html) （函数 `infer_emotional_state`）

**算法说明**：综合情绪得分 = HRV(30/15) + 心率(20) + 压力指数(25/15) + PSS-4(×2)，阈值分段决定 4 态输出。

**关键接口**：

```python
from external.knowledge.advice_engine import infer_emotional_state

result = infer_emotional_state(rmssd=18.5, resting_hr=88, stress_idx=75, pss4_score=10)
# result = {"primary": "自主神经活跃状态", "confidence": 0.78, "score": 123}
# 注：情绪标签已做合规清洗，"焦虑倾向"→"自主神经活跃状态"，避免诊断性语言
```

#### 16.3.3 简版 PSS-4 问卷（Perceived Stress Scale）

> 过去一个月内，您有多少次遇到以下情况？（0=从不 1=偶尔 2=经常 3=总是）

1. 感到无法控制生活中重要的事情？
2. 感到紧张和压力？
3. 感到无法应对必须处理的事情？
4. 感到事情发展顺利？（反向计分）

总分 ≥ 8 提示高压力，≥ 11 提示需要专业干预。

#### 16.3.4 情绪判断输出示例

```json
{
  "primary": "压力累积状态",
  "confidence": 0.72,
  "score": 58,
  "sub_indicators": {
    "hrv_component": 30,
    "hr_component": 0,
    "stress_component": 15,
    "pss_component": 13
  },
  "recommendation": "建议关注近期压力源，尝试规律作息和呼吸训练"
}
```

### 16.4 第三层：医疗级别参考建议

**目标**：当生理指标出现持续性异常或达到临床警戒值时，输出"建议咨询医生"级别的参考建议。

> ⚠️ **合规红线**：本层建议**绝不替代专业医疗诊断**，必须附加强制性免责声明。

#### 16.4.1 触发条件（满足任一即触发）

> **⚠️ R-01 修复**：以下阈值均引用 `HealthThresholds` 常量，与第 16.2.4 节保持一致。

| 条件 | 阈值常量 | 建议类别 |
|------|---------|---------|
| SpO₂ < SPO2_LOW_URGENT(90%) 持续 2 次测量 | `SPO2_LOW_URGENT` | 紧急 → 立即就医 |
| 静息心率 < HR_LOW_URGENT(40) 或 > HR_HIGH_URGENT(120) bpm | `HR_LOW_URGENT/HR_HIGH_URGENT` | 紧急 → 立即就医 |
| HRV-RMSSD < HRV_CRITICAL(10) ms | `HRV_CRITICAL` | 高 → 心内科咨询 |
| 压力指数连续 3 次 > STRESS_URGENT(80) | `STRESS_URGENT` | 中 → 心理科咨询 |
| 情绪判断为"自主神经活跃状态"且 PSS-4 ≥ 11 | - | 中 → 心理科咨询 |
| 内脏脂肪面积 > 150 cm² | - | 中 → 内分泌科咨询 |
| 体脂偏离度 > 2σ 持续 3 个月 | - | 中 → 营养科咨询 |

#### 16.4.2 医疗建议输出模板

```json
{
  "level": "medical_reference",
  "priority": "high",
  "trigger_reason": "spO2_low + persistent",
  "department": "呼吸科 / 心内科",
  "title": "建议咨询医生",
  "content": "您最近 {n} 次测量中，{m} 次出现血氧饱和度低于 90%。这可能提示：\n• 呼吸系统问题\n• 睡眠呼吸暂停\n• 心血管问题\n\n**建议您携带本报告咨询呼吸科或心内科医生。**",
  "required_disclaimer": true,
  "disclaimer_text": "⚠️ 本建议基于生理数据趋势推测，**不构成医疗诊断**。如有不适请立即就医，或拨打 120。",
  "evidence_source": "《中国居民慢性病与营养监测》+ ESC 慢性心衰指南",
  "follow_up": {
    "re_measure_after_days": 7,
    "alert_threshold": "若血氧仍 < 90%，请立即就医"
  }
}
```

#### 16.4.3 强制免责声明（必须出现在所有医疗级别建议下方）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 重要声明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
本设备为消费级健康参考工具，**非医疗器械**。
本报告所有建议**不构成医疗诊断、治疗或预防**。
如有健康疑虑，请咨询执业医师。
如出现急性症状（胸痛、呼吸困难、晕厥等），
请立即拨打 120 或前往最近的医疗机构。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 16.5 建议生成的合规与伦理约束

| 约束 | 实现方式 |
|------|---------|
| 禁用词 | 知识库建立禁用词词典，生成时自动过滤"诊断/治疗/预防/治愈"等 |
| 免责强制 | 医疗级别建议必须附加免责段（代码层校验） |
| 用户隐私 | 情绪判断结果不主动推送，**等用户主动查看**（C-02 修复） |
| 风险升级 | 出现"紧急"建议时 UI 必须弹窗+声音提示 |
| 频次限制 | 同一"医疗级别"建议 24 小时内最多推送 1 次 |

> **⚠️ C-02 修复实现说明**：情绪判断结果默认在 UI 中折叠显示（"查看情绪分析"按钮），仅在用户主动点击时才展示具体情绪标签，避免用户被"自主神经活跃状态"等标签产生负面心理暗示。UI 实现：`QPushButton` 触发 `QScrollArea` 展开。

### 16.6 建议生成引擎代码骨架

> **外部化说明**：三层建议生成引擎已提取到外部文件，与文档分离。
> 代码随业务变更时可独立更新，不影响文档结构。

**外部文件**：[`external/knowledge/advice_engine.py`](external/knowledge/advice_engine.py)

**文件职责**：

| 类 | 职责 | 依赖 |
|---|---|---|
| `Priority` / `Category` | 枚举常量定义 | 内置 |
| `Advice` | 建议数据结构（dataclass） | `dataclasses` |
| `AdviceGenerator` | 三层建议生成引擎（健康→情绪→医疗） | `SafeConditionEvaluator`, `ForbiddenWordsFilter` |
| `AdviceEngine` | v1 兼容版建议引擎 | `SafeConditionEvaluator` |
| `infer_emotional_state` | 综合情绪判定（4 态 + 置信度） | 内置算法 |

**关键接口索引**：

```python
from external.knowledge.advice_engine import AdviceGenerator, AdviceEngine

# v2 引擎（三层）
gen = AdviceGenerator("data/knowledge/advice_templates.json")
advices = gen.generate(health_indicators, user_profile, pss4_score=10)

# v1 兼容引擎（基于模板）
engine = AdviceEngine("data/knowledge/advice_templates.json")
advices = engine.generate_advice(indicators, user_profile)
```

**合规保障**：
- `✅ T-02`：`SafeConditionEvaluator`（AST 白名单）防注入
- `✅ C-01`：`ForbiddenWordsFilter` 禁用词过滤
- `✅ C-02`：情绪结果不主动推送（UI 层折叠控制）

---

## 17. 医学知识与大健康知识来源方案（补充章节）

> **补充说明**：本节为 v1.0 文档第 1.2 节"数据获取链路"中标记为"待补充"的**医学知识**与**大健康知识**两项的来源、获取与集成方案。

### 17.1 知识领域分类总览

| 知识大类 | 知识子类 | 与本项目指标关联 | MVP1.0 优先级 |
|---------|---------|----------------|---------------|
| 心血管医学 | 血压、心率、心律失常、心血管风险 | HR / HRV / 心脏功能 | P0 |
| 呼吸医学 | 血氧、呼吸功能 | SpO₂ | P0 |
| 体成分医学 | 脂肪、肌肉、骨骼、内脏脂肪 | BIA 19 项 | P0 |
| 代谢医学 | 基础代谢、代谢综合征、血糖、血脂 | BMR / BMI / 体脂 | P0 |
| 睡眠医学 | 睡眠结构、睡眠呼吸暂停、HRV-睡眠 | HRV / SpO₂ | P1 |
| 运动康复医学 | 心肺耐力、运动负荷、恢复 | HR / HRV（拓展） | P1 |
| 营养学 | 宏量营养素、微量元素、膳食指南 | 饮食建议 | P0 |
| 运动科学 | 运动处方、有氧/无氧、强度 | 运动建议 | P0 |
| 心理学 | 压力、焦虑、抑郁、认知行为 | 情绪判断 | P1 |
| 中医体质学 | 九种体质、舌象、脉象（拓展） | 体质评估 | P3（暂缓） |
| 公共卫生 | 流行病学、健康教育、风险沟通 | 建议话术 | P2 |

### 17.2 知识来源途径与获取方案

#### 17.2.1 权威医学文献数据库

| 数据源 | URL/API | 内容 | 获取方式 | 费用 |
|--------|---------|------|---------|------|
| **PubMed** | `https://pubmed.ncbi.nlm.nih.gov/` | 3000 万+ 医学文献摘要 | E-utilities API（免费） | 免费 |
| **PMC（PubMed Central）** | `https://www.ncbi.nlm.nih.gov/pmc/` | 全文文献 | OA API / FTP 批量下载 | 免费 |
| **UpToDate** | `https://www.uptodate.com/` | 临床决策支持 | 机构订阅 | 高 |
| **Cochrane Library** | `https://www.cochranelibrary.com/` | 系统综述/Meta 分析 | API | 部分免费 |
| **中华医学杂志社** | `https://www.cmaph.org/` | 中文权威期刊 | 期刊网站/订阅 | 部分免费 |
| **CNKI** | `https://www.cnki.net/` | 中文学术文献 | 机构订阅 | 中 |

**MVP1.0 推荐策略**：
- 使用 PubMed E-utilities API 自动检索 + PMC 全文下载
- 关键词模板：`("body composition" OR "HRV" OR "stress") AND ("consumer device" OR "wearable")`
- 存储到本地 `data/knowledge/medical_evidence.jsonl`

**API 调用示例**：

```python
import requests

def search_pubmed(query: str, max_results: int = 50) -> list:
    """检索 PubMed"""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json"
    }
    resp = requests.get(url, params=params, timeout=10)
    ids = resp.json()["esearchresult"]["idlist"]
    return fetch_abstracts(ids)
```

#### 17.2.2 公开医学指南

| 指南来源 | 指南名 | 适用领域 |
|---------|--------|---------|
| **WHO** | Body Mass Index Classification | BMI |
| **中国营养学会** | 《中国居民膳食指南 2022》 | 营养 |
| **中国肥胖问题工作组** | WS/T 586-2018（成人体重判定） | 体重/BMI |
| **ESC** | European Guidelines on CVD Prevention | 心血管 |
| **ACC/AHA** | Guideline for Assessment of CV Risk | 心血管 |
| **中华医学会心血管病学分会** | 《中国心血管病一级预防指南》 | 心血管 |
| **AASM** | International Classification of Sleep Disorders | 睡眠 |
| **APA** | DSM-5（精神障碍诊断） | 心理学（仅参考用，不作诊断） |
| **ACSM** | Guidelines for Exercise Testing and Prescription | 运动 |

**获取方式**：
- WHO/中国营养学会指南：PDF 下载，OCR 提取
- ESC/ACC/AHA 指南：原文 + 中文译本
- 存储到 `data/knowledge/guidelines/`

#### 17.2.3 API 数据源

| API | 内容 | 调用频率限制 | 用途 |
|-----|------|------------|------|
| **OpenFDA** `api.fda.gov` | 美国 FDA 公开数据 | 240 req/min，无 Key 1000/day | 设备安全信息 |
| **ICD-11 API** `icd.who.int/icdapi` | ICD-11 疾病分类 | 需申请 | 知识图谱关联 |
| **MedlinePlus** `medlineplus.gov` | 患者教育材料 | 免费 | 通俗化解释 |
| **UMLS** `uts.nlm.nih.gov` | 医学概念统一本体 | 需注册 | 知识图谱节点 |
| **DailyMed** `dailymed.nlm.nih.gov` | 药品说明书 | 免费 | 药物互作参考 |

**MVP1.0 推荐**：仅集成 OpenFDA + MedlinePlus。

#### 17.2.4 专家访谈与顾问审核

| 角色 | 来源 | 频率 | 产出 |
|------|------|------|------|
| 心血管内科医生 | 三甲医院/合作诊所 | 季度评审 | 参考范围确认、危险阈值 |
| 注册营养师 | 临床营养科 | 半年度更新 | 膳食建议模板 |
| 心理治疗师 | 心理科 | 按需 | 情绪建议话术、PSS 问卷校准 |
| 运动康复师 | 体育院校/医院 | 半年度 | 运动处方模板 |
| 算法工程师 | 内部 | 持续 | 知识结构化、版本管理 |

**MVP1.0 建议**：至少邀请 1 名心血管内科医生 + 1 名营养师做一次评审（半天）。

#### 17.2.5 开源知识图谱

| 项目 | 内容 | 许可证 | 集成方式 |
|------|------|--------|---------|
| **SNOMED CT** | 临床医学本体 | 需申请 | 概念对齐 |
| **ICD-11** | 疾病分类 | 部分开源 | 分类参考 |
| **DrugBank** | 药物知识 | 学术免费 | 互作参考 |
| **OMIM** | 遗传病 | 部分免费 | 罕见病 |
| **OpenKG** `openkg.cn` | 中文知识图谱 | CC-BY-SA | 中文化 |
| **CMeKG** `cmekg.cn` | 中文医学知识图谱 | 学术免费 | 中文化首选 |

**MVP1.0 集成**：仅取 CMeKG 的"症状-疾病"关联片段，验证 UI 跳转逻辑。

#### 17.2.6 内部项目资产（已具备）

| 文件路径 | 内容 |
|---------|------|
| `docs/reports/IND-01 ~ IND-38` | 30+ 指标的算法研究 + 参考范围 + 临床意义 |
| `docs/reports/RES-00_开源项目与基准数据集调研报告.md` | 开源算法库 + 数据集 |
| `docs/reports/ALGO-AUDIT-2026_算法审计总报告_全面升级版.md` | 审计 + 风险评估 |
| `docs/指标CSV/指标审计原始数据/大健康检测指标总表_可行指标_合并版_V5.0.md` | 30 项指标审计结果 |

**优先级**：内部资产 → 公开指南 → PubMed 文献 → 专家审核

### 17.3 知识结构化模板

#### 17.3.1 医学知识条目模板

```yaml
# data/knowledge/medical_entries/IND-03_bf_pct.yaml

entry_id: IND-03
indicator_name: 体脂率
indicator_name_en: Body Fat Percentage
category: BIA

reference_ranges:
  male:
    age_18_39:
      low: 8.0
      normal_low: 11.0
      normal_high: 16.9
      high: 27.0
    age_40_59:
      low: 11.0
      normal_low: 12.0
      normal_high: 17.9
      high: 28.0
  female:
    age_18_39:
      low: 18.0
      normal_low: 21.0
      normal_high: 27.9
      high: 40.0

clinical_significance:
  high: "体脂率偏高提示能量摄入超过消耗，长期可能增加心血管疾病和代谢综合征风险"
  low: "体脂率过低可能影响激素水平和免疫功能"
  normal: "体脂率处于健康范围"

evidence:
  level: A
  sources:
    - id: PMID:16005609
      title: "Kyle Geneva BIA Equation"
      year: 2006
    - id: PMC12922097
      title: "2026 Systematic Review of Consumer BIA"
      year: 2026
  consensus: "WHO + 中国营养学会"

advice_templates:
  - trigger: "bf_pct > high"
    category: diet
    priority: medium
    template_id: high_bf_diet

disclaimer_required: false
last_reviewed_by: "心血管内科 张医生"
last_reviewed_at: "2026-07-01"
next_review_at: "2027-01-01"
```

#### 17.3.2 大健康知识条目模板

```yaml
# data/knowledge/wellness_entries/stress_index.yaml

entry_id: WELLNESS-STRESS-01
topic: 压力管理
category: psychology
audience: 成人

knowledge_summary: |
  长期高压力状态与心血管疾病、免疫力下降、情绪障碍相关。
  短期压力是正常生理反应；持续高压力需干预。

intervention_strategies:
  - name: 腹式呼吸训练
    evidence_level: A
    frequency: 每日 2 次，每次 5 分钟
    source: "PMID:20180103"
  - name: 规律有氧运动
    evidence_level: A
    frequency: 每周 3-5 次，每次 30 分钟
    source: "ACSM Guidelines 2021"
  - name: 渐进式肌肉放松
    evidence_level: B
    frequency: 每日睡前 10 分钟
    source: "PMID:24672813"

when_to_seek_professional_help:
  indicators:
    - 持续失眠超过 2 周
    - 情绪低落超过 2 周
    - 自杀念头出现
  action: "建议咨询心理科或精神科医生"

disclaimer: |
  本内容仅供健康参考，不构成医疗建议。

last_reviewed_by: "心理治疗师 李老师"
last_reviewed_at: "2026-06-15"
```

### 17.4 知识集成到技术文档的流程

```
原始资产（IND报告、PDF、网页）
        ↓ 步骤1：自动化提取
结构化 YAML/JSON
        ↓ 步骤2：医学专家审核
审核通过的条目
        ↓ 步骤3：版本化入库
data/knowledge/medical_entries/*.yaml
data/knowledge/wellness_entries/*.yaml
        ↓ 步骤4：运行时加载
医学知识库 API（src/knowledge/medical_db.py）
        ↓ 步骤5：建议引擎消费
advice_engine_v2.generate()
        ↓ 步骤6：用户可感知价值
UI 展示 + 建议推送
```

### 17.5 MVP1.0 知识库最小可用集

| 类别 | 必备条目数 | 负责人 | 工期 |
|------|----------|--------|------|
| 医学知识（30 指标参考范围） | 30 | 算法工程师 + 医学顾问 | 3 天 |
| 建议模板（P0 指标） | 20 | 全栈 + 医学顾问 | 2 天 |
| 情绪判断规则 | 5 | 心理学背景成员 | 1 天 |
| 医疗级别警示规则 | 8 | 医学顾问 | 1 天 |
| 大健康知识（营养/运动/心理） | 15 | 营养师 + 运动康复师 | 2 天 |
| **总计** | **78** | - | **9 天** |

---

## 18. 产品体验转化路径（补充章节）

> **补充说明**：本节为补充要求第 4 项，描述从原始数据到用户可感知价值的完整转化链路，明确各步骤的算法类型、输入输出格式、预期效果，并附 Python 风格伪代码。

### 18.1 完整转化链路图

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 数据采集层                                          │
│  - 用户基本信息（人工输入）                                    │
│  - BIA 原始阻抗信号（50KHz 交流电）                           │
│  - PPG 原始光电容积脉搏波（红光+红外光）                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: 数据指标计算层                                        │
│  - BIA 芯片内置算法：19 项体成分指标                            │
│  - PPG 芯片内置算法：SpO₂、HR、PI                             │
│  - 上位机算法：HRV-RMSSD、SDNN、pNN50                         │
│  - 上位机算法：体脂偏离度、代谢年龄                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 3: 大健康指标融合层                                      │
│  - 压力指数（HR+HRV 加权）                                    │
│  - 情绪倾向（HRV+PSS 联合）                                   │
│  - 水分平衡（阈值分类）                                       │
│  - 综合健康分（规则融合）                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 4: 健康判定层                                            │
│  - 单指标状态：正常 / 警惕 / 超标                              │
│  - 多指标组合：交叉印证                                        │
│  - 持续性异常：触发医疗级别建议                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 5: 情绪建模层                                            │
│  - 输入：HRV、HR、压力指数、PSS-4 问卷                         │
│  - 启发式分类 → 自主神经活跃 / 压力累积 / 平静放松                     │
│  - 置信度输出                                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 6: 建议输出层                                            │
│  - 第一层：健康改善建议（饮食/运动/生活方式）                   │
│  - 第二层：情绪调节建议（放松训练/作息）                        │
│  - 第三层：医疗级别参考建议（含强制免责）                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    用户可感知价值
```

### 18.2 各步骤详细规格

#### Step 1：数据采集层

| 子步骤 | 输入 | 输出 | 算法类型 | 预期效果 |
|--------|------|------|---------|---------|
| 1.1 基础信息 | 用户键入 | name/age/gender/height | 表单校验 | < 30 秒完成 |
| 1.2 BIA 阻抗采集 | 50KHz 交流电 | R(Ω)、Xc(Ω) | 物理测量 | 误差 < 5Ω |
| 1.3 PPG 波形采集 | 50Hz 采样率 | 原始 ADC 序列 | 物理测量 | 30 秒连续波形 |

#### Step 2：数据指标计算层

| 子步骤 | 输入 | 输出 | 算法类型 | 预期效果 |
|--------|------|------|---------|---------|
| 2.1 BIA 19 项 | R、Xc、身高、体重、年龄、性别 | 体脂率/肌肉量/水分率/... | 芯片内置 + Kyle 公式 | 与芯片手册对标 < 5% 误差 |
| 2.2 PPG 生命体征 | 原始波形 | SpO₂、HR、PI | 芯片内置 | PI > 0.3% 时有效 |
| 2.3 HRV 时域 | IBI 序列 | RMSSD、SDNN、pNN50 | HeartPy | 误差 < 5% vs Kubios |
| 2.4 派生指标 | 体脂率 + 年龄 + 性别 | 偏离度、代谢年龄 | 公式换算 | Z 分数 ±0.1 |

#### Step 3：大健康指标融合层

| 子步骤 | 输入 | 输出 | 算法类型 | 预期效果 |
|--------|------|------|---------|---------|
| 3.1 压力指数 | RMSSD、HR、年龄 | 0-100 分 | 加权评分 | 与主观 PSS 相关性 > 0.6 |
| 3.2 情绪倾向 | RMSSD、HR、压力、PSS | 类别 + 置信度 | 规则分类 | 准确率 > 70%（MVP 简版） |
| 3.3 水分平衡 | 水分率 + 性别 | 正常/偏低/偏高 | 阈值分类 | 与临床判断一致 |
| 3.4 综合健康分 | 11 项指标 | 0-100 分 + 风险等级 | 规则融合 | 与问卷 SF-36 相关性 > 0.65 |

#### Step 4：健康判定层

| 子步骤 | 输入 | 输出 | 算法类型 | 预期效果 |
|--------|------|------|---------|---------|
| 4.1 单指标状态 | 测量值 + 参考范围 | 正常/警惕/超标 | 阈值分类 | 与医学指南一致 |
| 4.2 多指标组合 | 多个异常指标 | 交叉印证列表 | 启发式规则 | 减少误报 |
| 4.3 持续性检测 | 历史 3-5 次数据 | 是否触发医疗建议 | 滑动窗口 | 减少偶发误报 |

#### Step 5：情绪建模层

| 子步骤 | 输入 | 输出 | 算法类型 | 预期效果 |
|--------|------|------|---------|---------|
| 5.1 生理特征提取 | HRV、HR、压力 | 生理向量 | 归一化 | 维度 4 |
| 5.2 问卷融合 | PSS-4 分数 | 主观向量 | 反向计分 | 维度 1 |
| 5.3 联合分类 | 生理 + 主观 | 情绪状态 + 置信度 | 规则 + 阈值 | 输出 4 类 |

#### Step 6：建议输出层

| 子步骤 | 输入 | 输出 | 算法类型 | 预期效果 |
|--------|------|------|---------|---------|
| 6.1 规则匹配 | 指标 + 档案 | 候选建议 | 规则引擎 | < 100ms |
| 6.2 模板渲染 | 建议模板 + 实际值 | 自然语言建议 | 字符串模板 | 包含具体数值 |
| 6.3 合并排序 | 候选建议列表 | Top 8 建议 | 优先级排序 | 信息量适中 |
| 6.4 免责附加 | 医疗级别建议 | 完整报告 | 字符串拼接 | 强制显示 |

### 18.3 端到端 Python 伪代码

> **外部化说明**：本节完整端到端伪代码已提取到外部文件，实现与文档分离。
> 代码随上游开源组件（HeartPy）变更时可独立更新，不影响文档结构。

**外部文件**：[`external/pipeline/health_assessment_pipeline.py`](external/pipeline/health_assessment_pipeline.py)

**文件职责**：

| 类 | 职责 | 依赖 |
|---|---|---|
| `DataAcquisition` | 硬件通信 + BIA/PPG 测量（同步+异步） | `external.hardware.*` |
| `HealthIndicatorFusion` | 12 项大健康指标融合计算 | `external.algorithms.health_indicators` |
| `HealthJudgmentAndEmotionModel` | 健康判定 + 情绪建模 + 免责文本 | `external.knowledge.advice_engine` |
| `AdviceOutputEngine` | 三层建议生成 | `external.knowledge.advice_engine` |
| `HealthAssessmentPipeline` | 端到端编排（Step 1-6） | 以上全部 |

**关键接口索引**：

```python
# Step 1-6 调用路径（详细实现见外部文件）
pipeline = HealthAssessmentPipeline(medical_db, advice_templates)
report = pipeline.run(user, pss4_score=10)  # → FinalReport

# 异步模式（T-01 修复）
report = await pipeline.acquisition.measure_async(user)

# 健康指标访问
ind = report.health_indicators
ind.hrv_rmssd          # HRV-RMSSD
ind.spo2_health        # 血氧健康
ind.stress_index       # 压力指数
ind.bf_deviation       # 体脂偏离度
ind.composite_health_score  # 综合健康分
```

**审计修复标记**：

- `✅ T-01`：`measure_async()` 异步并发 BIA∥PPG，节省 ~15 秒
- `✅ T-02`：条件评估使用 `SafeConditionEvaluator`（AST 白名单）
- `✅ T-03`：类型别名 `RawIndicatorsDict` / `HealthIndicatorsDict`

### 18.4 各步骤预期效果汇总

| 步骤 | 耗时 | 算法类型 | 预期准确度/可解释性 |
|------|------|---------|-------------------|
| Step 1 数据采集 | 30 秒 | 物理测量 | 硬件决定 |
| Step 2 数据指标 | < 1 秒 | 芯片内置 + 信号处理 | 与芯片手册对标 < 5% 误差 |
| Step 3 大健康指标 | < 1 秒 | 规则融合 | 临床一致性 > 80% |
| Step 4 健康判定 | < 0.1 秒 | 阈值分类 | 简单可解释 |
| Step 5 情绪建模 | < 0.1 秒 | 规则分类 | 准确率 > 70%（MVP） |
| Step 6 建议输出 | < 0.5 秒 | 规则引擎 + 模板渲染 | 全部可追溯 |
| **总耗时** | **~32 秒** | - | 用户可接受 |

### 18.5 用户可感知价值链路

```
冷冰冰的数字（体重 75.3kg）
        ↓ 转化为
可解释的指标（体重超标 5.2kg，建议控制饮食）
        ↓ 升级为
可执行的建议（每日减少 300Kcal 摄入）
        ↓ 提升至
情绪共鸣（您的压力指数较高，试试 4-7-8 呼吸法）
        ↓ 风险预警
医疗级别（连续低血氧，建议咨询呼吸科）[附免责]
```

### 18.6 与 MVP1.0 现有架构的对应关系

| 本节步骤 | 现有架构模块 | 文件路径 |
|---------|------------|---------|
| Step 1-2 | 硬件通信层 + BIA/PPG 算法 | `src/hardware/*` + `src/algorithms/bia_engine.py` / `ppg_engine.py` |
| Step 3 | 多模态融合 | `src/algorithms/fusion.py`（扩展） |
| Step 4-5 | 业务逻辑层 | `src/knowledge/medical_db.py`（扩展）+ 新增 `emotion_model.py` |
| Step 6 | 建议生成 | `src/knowledge/advice_engine_v2.py`（升级 v1 → v2） |

### 18.7 MVP1.0 实施补充

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 实现 `HealthIndicatorFusion` 类 | 2 天 | P0 |
| 实现 `HealthJudgmentAndEmotionModel` 类 | 1.5 天 | P0 |
| 实现 `AdviceOutputEngine` 类（升级现有 advice_engine） | 2 天 | P0 |
| 集成到 `HealthAssessmentPipeline` 端到端流程 | 1 天 | P0 |
| 单元测试（每类指标 + 边界条件） | 1.5 天 | P0 |
| **小计** | **8 天** | - |

此 8 天已包含在 MVP1.0 第 2 周的"算法集成"与第 3 周的"知识库与界面"中（详见第 13 节排期），无需额外排期延长。

---

## 文档补充说明

本节为 v1.0 文档的补充章节（v1.0 → v1.1），用于填补第 1.2 节检测逻辑链路中的 4 个"待补充"环节：

1. **大健康指标**（第 15 章）：12 项可执行指标清单
2. **大健康建议**（第 16 章）：三层建议生成架构
3. **医学知识 + 大健康知识**（第 17 章）：知识来源、获取与集成方案
4. **产品体验转化路径**（第 18 章）：完整数据流 + Python 伪代码

### 补充前后对比

| 链路环节 | v1.0 描述 | v1.1 补充后 |
|---------|----------|------------|
| 大健康指标 | "算法融合"（待补充） | 12 项可执行指标，含定义/单位/范围/数据来源 |
| 大健康建议 | "知识库"（待补充） | 三层架构：健康建议 → 情绪判断 → 医疗建议 |
| 医学知识 | "理论算法"（待补充） | 11 类知识领域、6 大来源途径、结构化模板 |
| 大健康知识 | "理论算法"（待补充） | 知识图谱、专家访谈、YAML 模板 |
| 完整转化路径 | 无 | 6 步链路 + 输入输出 + 伪代码 |

### 配套更新

- 目录（第 14-18 章）已加入 TOC
- 评审指引已更新，重点关注新补充章节
- 详细排期见第 18.7 节

---

**v1.1 修订说明**：本版本补充了原文档"待补充"环节，新增 4 个章节，共增加约 1.5 万字内容。核心补充点是**第 18 章端到端伪代码**，可直接作为开发参考实现。
