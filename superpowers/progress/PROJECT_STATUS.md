# Health_man 项目状态总览

<!-- UPDATE_MARKER: doc_header -->
| 项 | 值 |
|---|---|
| 文档版本 | v1.2 |
| 最后更新 | 2026-07-12 |
| 文档状态 | 活跃维护 |
| 适用范围 | MVP1.0 外部医学数据获取子系统 |
| 关联文档 | [PROJECT_ROADMAP.md](./PROJECT_ROADMAP.md)、[FORWARD_PLAN.md](./FORWARD_PLAN.md)、[Spec v1.1](../specs/2026-07-12-data-acquisition-strategy-design.md) |

---

## 一、状态摘要卡片

<!-- UPDATE_MARKER: status_summary -->
| 项 | 值 |
|---|---|
| 项目名称 | Health_man 大健康检测平台 - 外部医学数据获取子系统 |
| 当前阶段 | Phase 3: Layer B 文献聚合（✅ 已完成 9/9，READY FOR MERGE） |
| 总体进度 | 60%（Phase 1-3 完成 + Phase 4 待启动） |
| 测试通过数 | 122/122 |
| 提交数 | 26（Phase 1-2: 16 + Phase 3: 10） |
| 代码模块数 | 21（Phase 1-2: 12 + Phase 3: 9） |
| 最后更新时间 | 2026-07-12 |
| 最终 HEAD | `95591d3` |
| 基线 commit | `3acf8db`（Phase 3 起始基线） |

**状态图例：** ✅ 已完成 | ⏳ 进行中/待执行 | 🅿️ 待启动 | ❌ 阻塞

---

## 二、阶段进度详情

<!-- UPDATE_MARKER: phase_progress_table -->
| 阶段 | 状态 | 完成任务/总任务 | 测试通过数 | 提交数 | 负责人 | 开始时间 | 完成时间 |
|---|---|---|---|---|---|---|---|
| Phase 1: 基础设施搭建 | ✅ 已完成 | 5/5（Task 1-2 + 安全工具 Task 10-12） | 25/25 | 8 | 开发者 | 2026-07-12 | 2026-07-12 |
| Phase 2: Layer A 开放数据集直采 | ✅ 已完成 | 7/7（Task 3-9） | 32/32 | 7 | 开发者 | 2026-07-12 | 2026-07-12 |
| Phase 3: Layer B 文献聚合 | ✅ 已完成 | 9/9（Task 1-9 全部完成，READY FOR MERGE） | 65/65（增量） | 10 | 开发者 | 2026-07-12 | 2026-07-12 |
| Phase 4: Layer C LLM 蒸馏增强 | ⏳ 已启动（待 plan） | 0/- | 0/- | 0 | 开发者 | - | - |
| Phase 5: 统一聚合与质量门禁 | 🅿️ 待启动 | 0/- | 0/- | 0 | 开发者 | - | - |
| Phase 6: 数据字典与文档归档 | 🅿️ 待启动 | 0/- | 0/- | 0 | 开发者 | - | - |

**说明：**
- Phase 1-2 合并执行，共 12 个 TDD 任务，57 个测试全部通过
- Phase 3 完成：Task 1-9 全部完成，新增 65 个测试（57→122），10 个提交（含 1 个 Task 1 fix）
- Phase 3 最终全分支审查通过（READY FOR MERGE：0 Critical，0 MUST FIX，2 SHOULD FIX）
- Phase 4 已确认启动，待 Phase 3 推送后编写 plan 并执行

---

## 三、Phase 1-2 完成总结

### 3.1 实施概要

<!-- UPDATE_MARKER: phase12_summary -->
| 指标 | 数值 |
|---|---|
| TDD 任务数 | 12 |
| 单元测试数 | 57 |
| 测试通过率 | 100%（57/57） |
| Git 提交数 | 16（含基线 6df9e60 与最终审查修复 25757c3） |
| 代码模块数 | 12（核心功能模块） |
| 安全审计问题修复 | 10/10（3 Critical + 4 Important + 3 其他） |
| 最终审查 Important 修复 | 6/6（fix commit 25757c3） |

### 3.2 关键交付物清单

#### 3.2.1 代码模块（12 个）

**数据层模块（scripts/data/）：**

| 模块 | 文件 | 职责 | 测试数 |
|---|---|---|---|
| SourceAdapter 抽象基类 | `source_adapter.py` | 定义 4 个抽象方法：list_files、download、verify_checksum、get_metadata_template | 4 |
| NHANES 适配器 | `adapters/nhanes_adapter.py` | NHANES 2017-2020 数据源具体实现 | 4 |
| 下载调度器 | `download_scheduler.py` | 并发下载 + 体量控制 + 指数退避重试 | 4 |
| 格式转换器 | `format_converter.py` | XPT/CSV → Parquet+Snappy 转换 | 4 |
| 5 步预处理器 | `preprocessor.py` | 字段标准化 + 异常过滤 + 缺失填充 + 年龄分组 | 5 |
| 质量校验器 | `quality_checker.py` | 三级校验 + A/B/C/D 评级 | 4 |
| 元数据生成器 | `metadata_generator.py` | L0/L1/L2 三层元数据生成 | 3 |

**工具层模块（scripts/utils/）：**

| 模块 | 文件 | 职责 | 测试数 |
|---|---|---|---|
| 加密工具 | `crypto.py` | AES-256-GCM 对称加密/解密 | 3 |
| 凭证管理器 | `credential_manager.py` | API Key 加密存储与读取 | 4 |
| 重试退避 | `retry.py` | 指数退避重试装饰器 | 3 |
| 限流器 | `rate_limiter.py` | 令牌桶限流器 | 3 |
| 熔断器 | `circuit_breaker.py` | 三态熔断器（CLOSED/OPEN/HALF_OPEN） | 4 |
| 审计日志 | `audit_logger.py` | 哈希链防篡改审计日志 | 3 |

#### 3.2.2 配置文件（8 个）

| 文件 | 路径 | 说明 |
|---|---|---|
| `config.yaml` | `_governance/` | 全局配置（数据集、预处理、质量、存储、安全） |
| `naming_convention.md` | `_governance/` | 命名规范 |
| `format_standards.md` | `_governance/` | 格式标准 |
| `classification_taxonomy.json` | `_governance/` | 数据分类体系 |
| `preprocessing_rules.yaml` | `_governance/` | 5 步预处理规则 |
| `quality_rules.yaml` | `_governance/` | 质量校验规则 + 生理范围 |
| `roles.yaml` | `_governance/` | RBAC 三级权限（reader/writer/admin） |
| `indicator_mapping.json` | `_governance/` | 指标 ID 映射表 |

#### 3.2.3 存储目录结构

```
e:\Health_man\data\knowledge\chinese_reference\
├── _governance\                  # 治理元文件（8 个配置文件）
├── A_open_datasets\
│   └── _metadata\
│       └── data_catalog.json     # 数据集清单
├── B_literature\                 # 预留（Phase 3 实现）
├── C_llm_distilled\               # 预留（Phase 4 实现）
├── unified\                       # 预留（Phase 5 实现）
├── _archive\
│   └── snapshots\
└── README.md
```

### 3.3 质量指标

<!-- UPDATE_MARKER: phase12_quality -->
| 质量维度 | 指标 | 结果 |
|---|---|---|
| 测试覆盖 | 单元测试通过率 | 57/57 = 100% ✅ |
| 安全审计 | Critical 问题 | 0（3 个已全部修复）✅ |
| 安全审计 | Important 问题 | 0（4 个 P1 + 6 个最终审查 = 10 个已全部修复）✅ |
| 安全审计 | 中等问题（P2） | 3 个留待实施中细化（COMP-001、PERF-001、LOGIC-001、DATA-001） |
| 代码规范 | 命名规范遵循 | 100%（snake_case 英文） |
| 架构设计 | 插件式扩展性 | ✅ SourceAdapter 抽象基类支持新数据源零侵入接入 |
| TDD 流程 | 测试先行遵循率 | 100%（12 个任务均先写失败测试） |

### 3.4 最终审查修复清单（fix commit 25757c3）

| Important # | 修复内容 | 影响模块 |
|---|---|---|
| #1 | QualityChecker PHYSIOLOGICAL_RANGES 补 perfusion_index/hrv_rmssd | quality_checker.py |
| #2 | NHANESAdapter.download() 改用 with 上下文管理（资源释放） | nhanes_adapter.py |
| #3 | FormatConverter + Preprocessor docstring 修正 | format_converter.py、preprocessor.py |
| #4 | QualityChecker._check_validity 无生理字段返回 0.0（原 1.0 虚高） | quality_checker.py |
| #5 | 补测 test_load_last_hash_raises_on_missing_hash | test_audit_logger.py |
| #6 | 删除假阳性 test_step4_missing_values_filled | test_preprocessor.py |

### 3.5 提交链

```
6df9e60 (基线) → 0c80765 (T1) → 9dd3226 (T2) → 0d5fc33 (T3) → 0ec8c76 (T4) →
10282cc (T5) → 769c468 (T6) → d08d0c5 (T7原) → b95e1f3 (T7修) → 66ebc12 (T8) →
f7bf779 (T9) → 3dc1cca (T10) → 6612cfe (T11) → f752cc8 (T12原) → e469f6b (T12修) →
25757c3 (最终审查修复)
```

---

## 四、Phase 3 进行中状态

### 4.1 任务清单

<!-- UPDATE_MARKER: phase3_task_table -->
| 任务 | 名称 | 文件 | 测试数 | 状态 | Commit |
|---|---|---|---|---|---|
| Task 1 | PubMedAdapter + B_literature 目录初始化 | `adapters/pubmed_adapter.py` | 5 | ✅ 完成 | `da48fc7` |
| Task 2 | OpenScienceAdapter（figshare/Dryad/Zenodo） | `adapters/openscience_adapter.py` | 5 | ✅ 完成 | `44a9347` |
| Task 3 | PdfTableExtractor（PyMuPDF 表格提取） | `pdf_extractor.py` | 5 | ✅ 完成 | `4dd63be` |
| Task 4 | GascPdfExtractor（GASC 2025 专用提取） | `adapters/gasc_adapter.py` | 7 | ✅ 完成 | `581f012` |
| Task 5 | TcmConstitutionStandard（中医体质 9 型标准数字化） | `tcm_standard_loader.py` + `tcm_constitution.json` | 12 | ✅ 完成 | `eaa3a62` |
| Task 6 | TcmConstitutionClassifier（60 题量表判定算法） | `tcm_classifier.py` | 19 | ✅ 完成 | `d533db4` |
| Task 7 | ExtractionLogManager（提取日志管理） | `extraction_log.py` | 4 | ✅ 完成（含 dtype=str fix） | `fae6a9f` |
| Task 8 | LiteratureMetadataGenerator（Layer B 三层元数据） | `literature_metadata_generator.py` | 4 | ✅ 完成 | `ea576cc` |
| Task 9 | LayerBPipeline（端到端流水线） | `literature_pipeline.py` | 4 | ✅ 完成 | `95591d3` |

**已完成测试增量：** 65 个（57→122）
**最终全分支审查：** READY FOR MERGE（0 Critical，0 MUST FIX，2 SHOULD FIX：TD-12 测试副作用 + TD-13 死分支）
**技术债总数：** 16 项（TD-1 到 TD-16，详见 PROJECT_ROADMAP.md §七）

### 4.2 阻塞项与风险

<!-- UPDATE_MARKER: phase3_blockers -->
| 阻塞项/风险 | 类型 | 影响 | 缓解措施 | 状态 |
|---|---|---|---|---|
| PubMed API 网络访问 | 技术风险 | NCBI E-utilities 可能限流或不可达 | 测试使用 mock；生产环境使用 retry + rate_limiter + circuit_breaker（Task 1 已实现） | 🟢 已规避 |
| figshare API 变更 | 技术风险 | API 接口可能变更 | 适配器模式隔离；OpenAI 兼容协议（Task 2 已实现） | 🟢 已规避 |
| CNKI 全文 PDF 版权 | 合规风险 | 无法自动下载全文 | 仅用公开摘要 + 补充材料；ExtractionLogManager 记录（Task 7 待实现） | 🟢 已规避 |
| PyMuPDF find_tables 兼容性 | 技术风险 | 不同版本 API 差异 | 异常捕获降级；测试使用临时生成 PDF（Task 3 已验证） | 🟢 已规避 |
| 中医体质 60 题标准录入 | 数据风险 | 标准数字化需人工录入 | JSON 标准文件 + TcmStandardLoader 加载校验（Task 5 已完成） | 🟢 已规避 |
| Q22/Q23 题目近似重复 | 数据质量 | brief 级数据问题，影响判定精度 | 已登记为技术债 TD-2，留待最终审查处理 | 🟡 已登记 |
| `except Exception` 过宽 | 代码质量 | pdf_extractor.py 异常捕获过宽 | 已登记为技术债 TD-1，留待最终审查处理 | 🟡 已登记 |
| 阈值边界 59 vs 60 测试缺失 | 测试覆盖 | TcmClassifier `>=` 逻辑正确但缺测试 | 已登记为技术债 TD-3，留待最终审查处理 | 🟡 已登记 |

### 4.3 预期交付物

#### 新增代码模块（9 个）

| 模块 | 依赖（Phase 1-2） |
|---|---|
| `adapters/pubmed_adapter.py` | `source_adapter.py`、`requests` |
| `adapters/openscience_adapter.py` | `source_adapter.py`、`requests` |
| `pdf_extractor.py` | PyMuPDF (fitz) |
| `adapters/gasc_adapter.py` | `pdf_extractor.py` |
| `tcm_standard_loader.py` | 无（读取 JSON） |
| `tcm_classifier.py` | `tcm_standard_loader.py` |
| `extraction_log.py` | pandas |
| `literature_metadata_generator.py` | `quality_checker.py`（复用 QualityReport） |
| `literature_pipeline.py` | 上述全部 + `download_scheduler.py`、`quality_checker.py` |

#### 新增数据目录

```
B_literature\
├── _metadata\                     # 三层元数据
├── _standards\
│   └── tcm_constitution.json     # 中医体质 9 型标准
├── _logs\
│   └── literature_extraction_log.csv
├── pubmed\
│   ├── abstracts\                 # 摘要 XML
│   └── fulltext\                  # 全文 PDF（仅开放获取）
├── openscience\                   # figshare/Dryad/Zenodo
├── gasc_2025\                     # GASC 2025 PDF 附录
├── tcm_constitution\              # 中医体质数据
└── README.md
```

---

## 五、决策日志（Decision Log）

<!-- UPDATE_MARKER: decision_log -->
| 决策 ID | 日期 | 决策内容 | 决策依据 | 决策者 | 状态 |
|---|---|---|---|---|---|
| **D-001** | 2026-07-12 | 采用三层分工架构（Layer A + B + C）而非单一数据源 | Spec §3.1-3.3：A+B 主路径覆盖 97%，C 增强覆盖 100%；成本 0；合规风险可控 | 项目负责人 | ✅ 已采纳 |
| **D-002** | 2026-07-12 | Layer C 国内大模型优先选型：GLM-4-Flash 为主力 | Spec §7.1.2：GLM-4-Flash 完全免费 + 中文强 + 128K 上下文 + OpenAI 兼容 | 项目负责人 | ✅ 已采纳 |
| **D-003** | 2026-07-12 | 严格 0 成本优先，单项超 ¥100 需征得同意 | Spec §1.3 约束条件：个人开发者资源 | 项目负责人 | ✅ 已采纳 |
| **D-004** | 2026-07-12 | 数据存储统一目的地为 `e:\Health_man\data\knowledge\chinese_reference\` | Spec §6.6 要素 6：统一存储管理 | 项目负责人 | ✅ 已采纳 |
| **D-005** | 2026-07-12 | 采用 TDD 强制流程：每个任务先写失败测试，再写实现 | Spec 最佳实践；确保代码质量与可测试性 | 项目负责人 | ✅ 已采纳 |
| **D-006** | 2026-07-12 | 采用插件式架构：SourceAdapter 抽象基类 + 具体适配器 | Spec §4.11 扩展性设计：新增数据源零侵入 | 项目负责人 | ✅ 已采纳 |
| **D-007** | 2026-07-12 | 安全审计 P0+P1 问题必须在实施前修复 | Spec 附录 B：3 Critical + 4 Important 已全部修订 | 项目负责人 | ✅ 已完成 |
| **D-008** | 2026-07-12 | Phase 1-2 合并执行（基础设施 + Layer A 核心路径） | 两者强依赖；合并执行减少上下文切换 | 项目负责人 | ✅ 已执行 |
| **D-009** | 2026-07-12 | 远程仓库选择：使用本地 Git 仓库，暂不推送远程 | 个人开发者；0 成本；本地版本控制已足够 | 项目负责人 | ✅ 已采纳 |
| **D-010** | 2026-07-12 | 执行方式选择：Subagent-Driven Development（推荐） | Phase 1-2 计划 Execution Handoff；任务间双阶段评审 | 项目负责人 | ✅ 已采纳 |
| **D-011** | 2026-07-12 | 建立项目进度跟踪体系（PROJECT_ROADMAP + PROJECT_STATUS） | 需要完整的项目进度跟踪体系；结构化跟踪 6 阶段进展 | 项目文档工程师 | ✅ 已执行 |
| **D-012** | 2026-07-12 | 数据格式标准：Parquet + Snappy 为表格强制格式 | Spec §6.3.2：列式存储、压缩比高、带 schema | 项目负责人 | ✅ 已采纳 |
| **D-013** | 2026-07-12 | RBAC 三级权限模型：reader/writer/admin | Spec §7.6.3：文件系统层 + 应用层 + 审计层三重控制 | 项目负责人 | ✅ 已采纳 |
| **D-014** | 2026-07-12 | API Key 全生命周期管理：AES-256-GCM + Windows DPAPI | Spec §7.6.1：存储加密 + 加载到内存 + 90 天轮换 | 项目负责人 | ✅ 已完成 |
| **D-015** | 2026-07-12 | 审计日志采用哈希链防篡改机制 | Spec §7.11：每条日志含前一条 SHA256，形成链式结构 | 项目负责人 | ✅ 已完成 |
| **D-016** | 2026-07-12 | 启动 Phase 4 Layer C LLM 蒸馏增强 | Layer A+B 覆盖 32 项指标，Phase 4 补齐剩余 3-5 项难提取指标，达成 33 项全覆盖；GLM-4-Flash 完全免费 | 项目负责人 | ⏳ 待执行 |
| **D-017** | 2026-07-12 | 后续工作项目计划书统一跟踪 | 创建 FORWARD_PLAN.md 作为 Phase 3 剩余 + Phase 4/5/6 单一入口，避免上下文割裂 | 项目文档工程师 | ✅ 已执行 |

---

## 六、变更日志（Change Log）

<!-- UPDATE_MARKER: change_log -->
| 变更 ID | 日期 | 变更类型 | 变更内容 | 影响范围 | 变更原因 |
|---|---|---|---|---|---|
| **C-001** | 2026-07-12 | Spec 创建 | 创建《外部数据获取方案设计文档》v1.0 | 全局 | 替代并整合 4 份既有计划的数据获取部分 |
| **C-002** | 2026-07-12 | Spec 修订 | Spec 升级至 v1.1：基于 P0+P1 安全审计修订 | §7.6 安全规范、§7.7 异常处理、§7.8 数据销毁、§7.11 审计日志、§4.1-4.11 Layer A 详细设计、附录 B | 修订前总体风险评级"高"；修订后降至"中"；3 Critical + 4 Important 全部修复 |
| **C-003** | 2026-07-12 | 计划创建 | 创建 Phase 1-2 实施计划（12 个 TDD 任务） | Phase 1 + Phase 2 | Spec v1.1 通过审查，进入 writing-plans 阶段 |
| **C-004** | 2026-07-12 | 计划执行 | Phase 1-2 计划执行完成（12 任务 + 最终审查修复） | Phase 1 + Phase 2 | 57/57 测试通过；0 Critical；10 Important 已修复；16 个提交 |
| **C-005** | 2026-07-12 | 计划创建 | 创建 Phase 3 实施计划（9 个 TDD 任务） | Phase 3 | Phase 1-2 完成后，进入 Layer B 文献聚合阶段 |
| **C-006** | 2026-07-12 | 文档创建 | 建立项目进度跟踪体系：PROJECT_ROADMAP.md + PROJECT_STATUS.md | 全局 | 需要完整的项目进度跟踪体系，结构化跟踪 6 阶段进展 |
| **C-007** | 2026-07-12 | 路径变更 | 既有计划路径从 `E:\工程项目\` 改为 `e:\Health_man\` | 全局 | Spec §1.4 与既有计划的关系：路径统一 |
| **C-008** | 2026-07-12 | 架构整合 | 保留三层元数据架构；保留 8 项 P0 指标校准目标；保留 33 IND 审计结论 | 全局 | Spec §1.4：整合 4 份既有计划 |
| **C-009** | 2026-07-12 | 状态同步 | PROJECT_ROADMAP/STATUS 同步至 Phase 3 Task 1-6 完成状态 | ROADMAP §三/§五/§七；STATUS §一/§二/§四 | 实际进度（6/9 任务，110 测试，HEAD `d533db4`）与文档显示（0/9，57 测试）存在偏差 |
| **C-010** | 2026-07-12 | 文档创建 | 创建 FORWARD_PLAN.md 后续工作项目计划书 | 全局 | 用户要求"注意整体进度和计划需要有文档跟踪，避免上下文割裂"；统一跟踪 Phase 3 剩余 + Phase 4/5/6 |
| **C-011** | 2026-07-12 | Phase 4 状态变更 | Phase 4 从"可选"改为"已确认启动" | ROADMAP §三/§五；STATUS §二 | 用户决策启动 Layer C LLM 蒸馏，达成 33 项指标全覆盖 |

---

## 七、动态更新区

> **⚠️ 本节需在每次提交后更新**

<!-- UPDATE_MARKER: dynamic_update -->
### 7.1 最新提交信息

| 项 | 值 |
|---|---|
| 最新提交 hash | `95591d3` |
| 提交时间 | 2026-07-12 |
| 提交信息 | feat: 添加 LayerBPipeline 端到端流水线（检索→下载→审计→元数据） |
| 提交类型 | feat（Phase 3 Task 9 实现，最终任务） |
| 变更文件数 | 2 个（`scripts/data/literature_pipeline.py`、`tests/data/test_literature_pipeline.py`） |

### 7.2 最新测试结果

| 项 | 值 |
|---|---|
| 测试命令 | `python -m pytest tests/ -v --tb=short` |
| 测试总数 | 122 |
| 通过数 | 122 |
| 失败数 | 0 |
| 错误数 | 0 |
| 通过率 | 100% |
| 测试耗时 | 22.96s |
| 最后运行时间 | 2026-07-12（Phase 3 Task 9 完成时） |

### 7.3 当前进行任务

| 项 | 值 |
|---|---|
| 当前阶段 | Phase 3: Layer B 文献聚合（✅ 已完成） |
| 当前任务 | 无（Phase 3 全部 9 个任务完成，最终审查通过） |
| 进度 | 9/9（100%） |
| 阻塞项 | 无（等待推送到 origin/main） |

### 7.4 下一步计划

1. **立即行动：** 推送 Phase 3 到 `origin/main`（finishing-a-development-branch）
2. **合并后清理：** 修复 TD-12（测试副作用，约 5 行）和 TD-13（死分支，约 5 行）
3. **短期目标：** 编写 Phase 4 plan（Layer C LLM 蒸馏，GLM-4-Flash）
4. **中期目标：** Phase 4 执行 → Phase 5 统一聚合 → Phase 6 文档归档
5. **长期目标：** M6 达成（文档交付 + 归档快照）
6. **验证标准：** Phase 3 推送后，origin/main HEAD = `95591d3`，122 测试通过

### 7.5 关键指标趋势

| 指标 | Phase 1-2 完成时 | Phase 3 Task 1-6 完成 | Phase 3 全部完成（当前） | Phase 5 预期 | Phase 6 预期 |
|---|---|---|---|---|---|
| 测试通过数 | 57 | 110 | 122 | 127+ | 127+ |
| 代码模块数 | 12 | 18 | 21 | 22+ | 22+ |
| 提交数 | 16 | 22 | 26 | 28+ | 30+ |
| 指标覆盖 | 25 项（Layer A） | 32 项（+Layer B 部分） | 32 项（+Layer B） | 33 项（+Layer C） | 33 项 |
| 数据体量 | ~560MB | ~600MB | ~760MB | ~765MB | ~765MB |

---

## 八、参考文档

| 文档 | 路径 | 说明 |
|---|---|---|
| 项目技术路线图 | `superpowers/progress/PROJECT_ROADMAP.md` | 6 阶段全景、依赖关系、里程碑、风险矩阵 |
| 后续工作计划书 | `superpowers/progress/FORWARD_PLAN.md` | Phase 3 剩余 + Phase 4/5/6 统一跟踪入口 |
| Spec 主文档 | `superpowers/specs/2026-07-12-data-acquisition-strategy-design.md` | v1.1，含 P0+P1 安全审计修订 |
| Phase 1-2 计划 | `superpowers/plans/2026-07-12-data-acquisition-phase1-2.md` | 已完成，12 个 TDD 任务 |
| Phase 3 计划 | `superpowers/plans/2026-07-12-data-acquisition-phase3-layer-b.md` | 进行中（6/9 完成），9 个 TDD 任务 |
| Progress Ledger | `.superpowers/sdd/progress.md` | Phase 1-2 + Phase 3 Task 1-6 完成记录（任务级审查） |

---

## 九、维护说明

### 9.1 更新频率

- **状态摘要卡片（§一）：** 每次阶段变更时更新
- **阶段进度详情（§二）：** 每个任务完成时更新
- **Phase 1-2 完成总结（§三）：** 已归档，不再更新
- **Phase 3 进行中状态（§四）：** 每个任务完成时更新
- **决策日志（§五）：** 每次关键决策时追加
- **变更日志（§六）：** 每次 Spec/计划变更时追加
- **动态更新区（§七）：** **每次提交后必须更新**

### 9.2 更新标记

文档中使用以下 HTML 注释标记需要动态更新的区域：

```html
<!-- UPDATE_MARKER: doc_header -->              # 文档头部（版本、时间）
<!-- UPDATE_MARKER: status_summary -->          # 状态摘要卡片
<!-- UPDATE_MARKER: phase_progress_table -->    # 阶段进度详情表格
<!-- UPDATE_MARKER: phase12_summary -->         # Phase 1-2 实施概要
<!-- UPDATE_MARKER: phase12_quality -->        # Phase 1-2 质量指标
<!-- UPDATE_MARKER: phase3_task_table -->       # Phase 3 任务清单
<!-- UPDATE_MARKER: phase3_blockers -->         # Phase 3 阻塞项与风险
<!-- UPDATE_MARKER: decision_log -->           # 决策日志
<!-- UPDATE_MARKER: change_log -->             # 变更日志
<!-- UPDATE_MARKER: dynamic_update -->         # 动态更新区（每次提交后更新）
<!-- UPDATE_MARKER: milestones_table -->       # 里程碑表格（PROJECT_ROADMAP.md）
<!-- UPDATE_MARKER: phase_roadmap_table -->    # 阶段路线图表格（PROJECT_ROADMAP.md）
<!-- UPDATE_MARKER: risk_matrix -->            # 风险矩阵（PROJECT_ROADMAP.md）
<!-- UPDATE_MARKER: current_focus -->          # 当前焦点（PROJECT_ROADMAP.md）
<!-- UPDATE_MARKER: changelog -->              # 变更记录（PROJECT_ROADMAP.md）
```

### 9.3 版本约定

- 主版本号（v1.0 → v2.0）：阶段完成或重大变更
- 次版本号（v1.0 → v1.1）：任务完成或常规更新
- 修订号（v1.0.0 → v1.0.1）：小修正或动态更新

---

## 十、变更记录

<!-- UPDATE_MARKER: doc_changelog -->
| 版本 | 日期 | 变更内容 | 作者 |
|---|---|---|---|
| v1.0 | 2026-07-12 | 初始版本：建立项目状态总览，覆盖状态摘要、阶段进度、Phase 1-2 完成总结、Phase 3 进行中状态、决策日志、变更日志、动态更新区 | 项目文档工程师 |
| v1.1 | 2026-07-12 | 状态同步：Phase 3 Task 1-6 完成状态（6/9，110 测试，HEAD `d533db4`）；追加 D-016/D-017 决策、C-009/C-010/C-011 变更；新增 FORWARD_PLAN.md 关联文档；动态更新区全部刷新至当前状态 | 项目文档工程师 |
| v1.2 | 2026-07-12 | 状态同步：Phase 3 Task 1-9 全部完成（9/9，122 测试，HEAD `95591d3`，READY FOR MERGE）；最终全分支审查通过（0 Critical，0 MUST FIX，2 SHOULD FIX）；Phase 3 任务表补全 Task 7-9 commit 与测试数；动态更新区全部刷新；关键指标趋势更新 | 项目文档工程师 |
