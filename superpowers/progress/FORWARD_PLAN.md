# 后续工作项目计划书（Forward Plan）

<!-- UPDATE_MARKER: doc_header -->
| 项 | 值 |
|---|---|
| 文档版本 | v1.0 |
| 最后更新 | 2026-07-12 |
| 文档状态 | 活跃维护 |
| 适用范围 | Phase 3 剩余（Task 7-9）+ Phase 4/5/6 全景规划 |
| 关联文档 | [PROJECT_ROADMAP.md](./PROJECT_ROADMAP.md)、[PROJECT_STATUS.md](./PROJECT_STATUS.md)、[Spec v1.1](../specs/2026-07-12-data-acquisition-strategy-design.md) |

---

## 一、文档目的与使用说明

### 1.1 文档定位

本文件是 **Health_man 外部医学数据获取子系统** 的 **后续工作项目单一入口跟踪文档**，统一规划与跟踪：

- Phase 3 Layer B 文献聚合的剩余任务（Task 7-9）
- Phase 4 Layer C LLM 蒸馏增强（已确认启动）
- Phase 5 统一聚合与质量门禁
- Phase 6 数据字典与文档归档

### 1.2 解决的问题

**避免上下文割裂：** 在长周期、多阶段、Subagent-Driven 的工作流中，会话上下文会随压缩而丢失。本文件作为"权威快照"，确保任何新会话或 subagent 打开此文档即可理解：

1. 当前在哪个 Phase、哪个 Task
2. 已经完成了什么（commit、测试数、交付物）
3. 接下来要做什么（顺序、依赖、决策点）
4. 关键约束与已知技术债

### 1.3 使用规则

- **每个 Task 完成后：** 更新 §三当前状态快照 + 对应 Phase 的任务表
- **每个 Phase 完成后：** 更新 §九执行顺序与依赖 + §十决策点
- **每次关键决策：** 追加到 §十决策点与待决事项
- **发现新风险：** 追加到 §十一风险与缓解措施
- **不创建冗余文档：** 本文件是"规划视图"，具体 TDD 步骤在各 Phase 的 plan 文件中

### 1.4 文档层级关系

```
FORWARD_PLAN.md（本文件）— 后续工作全景规划，单一入口
  ├── PROJECT_ROADMAP.md — 6 阶段全景路线图（含已完成阶段）
  ├── PROJECT_STATUS.md — 实时状态总览（含动态更新区）
  ├── Spec v1.1 — 权威设计规范
  └── plans/
      ├── 2026-07-12-data-acquisition-phase3-layer-b.md（进行中 6/9）
      ├── 2026-07-XX-data-acquisition-phase4-layer-c.md（待创建）
      ├── 2026-07-XX-data-acquisition-phase5-unified-aggregation.md（待创建）
      └── 2026-07-XX-data-acquisition-phase6-documentation.md（待创建）
```

---

## 二、当前状态快照

<!-- UPDATE_MARKER: current_snapshot -->
| 项 | 值 |
|---|---|
| 当前阶段 | Phase 3: Layer B 文献聚合 |
| Phase 3 进度 | 6/9 任务完成（66%） |
| 当前任务 | Task 7: ExtractionLogManager（待派发 implementer） |
| 测试通过数 | 110/110 |
| 当前 HEAD | `d533db4` |
| Phase 3 基线 commit | `3acf8db`（Phase 1-2 最终 HEAD，rebase 后） |
| 已完成代码模块 | 18 个（Phase 1-2: 12 + Phase 3: 6） |
| 已完成提交数 | 22 个（Phase 1-2: 16 + Phase 3: 6） |
| Phase 4 决策 | ✅ 已确认启动 |
| 执行方式 | Subagent-Driven Development（SDD） |

### Phase 3 已完成任务（Task 1-6）

| Task | 名称 | Commit | 测试增量 | 状态 |
|---|---|---|---|---|
| 1 | PubMedAdapter + B_literature 目录初始化 | `da48fc7` | +5（57→62） | ✅ |
| 2 | OpenScienceAdapter（figshare/Dryad/Zenodo） | `44a9347` | +5（62→67） | ✅ |
| 3 | PdfTableExtractor（PyMuPDF 表格提取） | `4dd63be` | +5（67→72） | ✅ |
| 4 | GascPdfExtractor（GASC 2025 专用提取） | `581f012` | +7（72→79） | ✅ |
| 5 | TcmConstitutionStandard（9 型标准数字化） | `eaa3a62` | +12（79→91） | ✅ |
| 6 | TcmConstitutionClassifier（60 题量表判定） | `d533db4` | +19（91→110） | ✅ |

### 已登记技术债

| ID | 来源 | 描述 | 严重度 | 处理时机 |
|---|---|---|---|---|
| TD-1 | Task 3 | `except Exception` 过宽（pdf_extractor.py） | Minor | Phase 3 最终审查 |
| TD-2 | Task 5 | Q22/Q23 近似重复（"抓痕"vs"划痕"，brief 级数据问题） | Minor | Phase 3 最终审查 |
| TD-3 | Task 6 | 阈值边界 59 vs 60 测试缺失（`>=` 逻辑正确无代码缺陷） | Minor | Phase 3 最终审查 |

---

## 三、后续工作项目全景图

<!-- UPDATE_MARKER: forward_plan_overview -->
```
┌─────────────────────────────────────────────────────────────────────┐
│                  后续工作项目全景（D5-D13）                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 3 剩余（当前）                                                │
│  ├─ Task 7: ExtractionLogManager ⏳ 待执行（brief 已提取）           │
│  ├─ Task 8: LiteratureMetadataGenerator ⏳ 待执行                   │
│  ├─ Task 9: LayerBPipeline（端到端流水线） ⏳ 待执行                 │
│  ├─ Phase 3 最终全分支审查                                          │
│  └─ finishing-a-development-branch 合并到 main                       │
│         │                                                           │
│         ▼                                                           │
│  Phase 4: Layer C LLM 蒸馏增强（已确认启动）                          │
│  ├─ 编写 Phase 4 plan（基于 Spec §7）                               │
│  ├─ TDD 任务执行（SDD）                                              │
│  │  ├─ ModelAdapter 抽象基类（GLM/Qwen/DeepSeek 统一接口）           │
│  │  ├─ API 网关 + 限流熔断复用                                       │
│  │  ├─ 提示词模板库                                                  │
│  │  ├─ 双层验证（结构化 + 语义）                                     │
│  │  └─ C_llm_distilled/ + 审计日志                                   │
│  └─ Phase 4 最终审查 + 合并                                          │
│         │                                                           │
│         ▼                                                           │
│  Phase 5: 统一聚合与质量门禁                                         │
│  ├─ 编写 Phase 5 plan                                               │
│  ├─ TDD 任务执行（SDD）                                              │
│  │  ├─ 三层数据映射统一 indicator_id                                │
│  │  ├─ 去重 + 质量评分                                               │
│  │  ├─ 生成 chinese_reference_unified.json                          │
│  │  └─ 质量门禁报告（≥33 项指标覆盖）                                │
│  └─ Phase 5 最终审查 + 合并                                         │
│         │                                                           │
│         ▼                                                           │
│  Phase 6: 数据字典与文档归档                                         │
│  ├─ 编写 Phase 6 plan                                               │
│  ├─ 执行                                                            │
│  │  ├─ data_dictionary.md（35 项指标每项说明）                       │
│  │  ├─ 各数据集 *_pipeline.md                                       │
│  │  ├─ _archive/snapshots/snapshot_2026-07-XX/                      │
│  │  └─ changelog.md                                                 │
│  └─ M6 达成：外部数据获取子系统交付完成                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 关键里程碑对应

| 里程碑 | Phase | 预期交付物 | 验收标准 |
|---|---|---|---|
| **M3** | Phase 3 完成 | B_literature/ 完整数据集 + 9 个模块 | 125+ 测试通过；PubMed + PDF + 中医体质全流程 |
| **M4** | Phase 4 完成 | C_llm_distilled/ + 审计日志 | 3-5 项难提取指标；LLM 审计日志完整 |
| **M5** | Phase 5 完成 | chinese_reference_unified.json | 质量门禁通过；≥33 项指标覆盖 |
| **M6** | Phase 6 完成 | data_dictionary.md + pipeline 文档 + 快照 | 35 项指标每项有说明；归档快照完成 |

---

## 四、Phase 3 剩余任务规划（Task 7-9）

<!-- UPDATE_MARKER: phase3_remaining -->
### 4.1 Task 7: ExtractionLogManager（提取日志管理）

**状态：** ⏳ 待执行（brief 已提取到 `.superpowers/sdd/task-7-brief.md`）

**目标：** 实现 CSV 持久化的文献提取日志管理，支持人工校验流程状态追踪。

**文件：**
- 创建：`scripts/data/extraction_log.py`
- 测试：`tests/data/test_extraction_log.py`

**核心接口（来自 plan）：**
- `ExtractionLogManager` 类
- 状态机：`pending` → `extracted` → `verified` / `rejected`
- 方法：`add_entry`, `update_status`, `get_pending`, `get_all`, `save`, `load`
- CSV 存储路径：`B_literature/_logs/literature_extraction_log.csv`

**依赖：** 无（纯 pandas CSV 操作，不涉及网络）

**预期测试数：** 4 个（brief 定义）

**执行步骤：**
1. 派发 implementer 子代理（SDD）
2. 写失败测试 → 验证失败 → 实现 → 验证通过 → commit
3. 生成 review package → 派发 task reviewer
4. 如有 findings → fix → re-review
5. 审查通过 → 更新 progress ledger + 本文件 §二

### 4.2 Task 8: LiteratureMetadataGenerator（Layer B 三层元数据）

**状态：** ⏳ 待执行（待 Task 7 完成后提取 brief）

**目标：** 生成 Layer B 的 L0/L1/L2 三层元数据，复用 Phase 1-2 的 MetadataGenerator 模式。

**文件：**
- 创建：`scripts/data/literature_metadata_generator.py`
- 测试：`tests/data/test_literature_metadata.py`

**核心设计点：**
- 复用 Phase 1-2 的 QualityReport 结构
- L0: 数据集级（dataset_id, source_url, license, region, search_query）
- L1: 记录级（unique_count, row_count, field_summary）
- L2: 字段级（适用场景, 人群代表性, 引用格式, 生成时间）
- 输出路径：`B_literature/_metadata/`

**依赖：** 无强依赖（可独立实现，复用 Phase 1-2 QualityReport 模式）

**预期测试数：** 4 个

### 4.3 Task 9: LayerBPipeline（端到端流水线）

**状态：** ⏳ 待执行（待 Task 7-8 完成后提取 brief）

**目标：** 整合全流程：检索 → 下载 → 提取 → 校验 → 存储 → 审计，执行体量审计。

**文件：**
- 创建：`scripts/data/literature_pipeline.py`
- 测试：`tests/data/test_literature_pipeline.py`

**核心设计点：**
- 整合 Task 1-8 全部模块
- 复用 Phase 1-2 的 `DownloadScheduler`、`QualityChecker`、`AuditLogger`
- `audit_size()` 方法：单域 1GB / 总量 8GB 上限校验
- 空数据集处理：`df.empty` 时跳过 quality check，`quality_report` 保持 `None`
- 端到端流程编排

**依赖：** Task 1-8 全部完成（强依赖）

**预期测试数：** 4 个

### 4.4 Phase 3 收尾步骤

1. **最终全分支审查：**
   - 生成 review package：`scripts/review-package 3acf8db HEAD`
   - 派发 final code reviewer（使用最 capable 模型）
   - 处理 TD-1/TD-2/TD-3 技术债（如审查要求）
2. **finishing-a-development-branch：**
   - 合并 Phase 3 分支到 main
   - 推送到远程 `origin/main`
3. **文档更新：**
   - 更新 PROJECT_ROADMAP/STATUS 标记 Phase 3 ✅ 完成
   - 更新本文件 §二快照
   - 追加 C-012 变更日志

---

## 五、Phase 4: Layer C LLM 蒸馏增强规划

<!-- UPDATE_MARKER: phase4_plan -->
### 5.1 阶段定位

**状态：** ⏳ 已确认启动（待编写 plan）

**目标：** 使用国内大模型蒸馏补齐 Layer A+B 未覆盖的 3-5 项难提取指标，达成 33 项指标全覆盖。

**工期：** 3 天（D9-D11）

**依赖：** Phase 1-3（复用安全工具链、凭证管理、SourceAdapter 架构）

### 5.2 关键设计点（来自 Spec §7）

**模型选型（Spec §7.1.2）：**
- **主力：** GLM-4-Flash（完全免费 + 128K 上下文 + OpenAI 兼容协议）
- **备选：** Qwen-Plus（免费额度）、DeepSeek-Chat（免费额度）
- **轮询策略：** 多模型轮询 + 月度配额监控

**架构设计：**
- `ModelAdapter` 抽象基类（类似 SourceAdapter，支持快速切换模型）
- API 网关：复用 `TokenBucketLimiter` + `CircuitBreaker` + `retry_with_backoff`
- 提示词模板库：结构化提取 + 语义验证双层提示
- `C_llm_distilled/` 存储目录 + 审计日志

**质量保障（Spec §7.5）：**
- **双层验证：** 结构化验证（JSON schema）+ 语义验证（字段合理性）
- **人工抽检：** 20% 抽样交叉验证
- **金标准对照：** 与 DEXA/BIA 已知数据对比
- **confidence 阈值：** `< 0.5` 自动拒绝，`0.5-0.7` 人工复核，`> 0.7` 自动通过

**成本控制（Spec §7.8）：**
- 严格 0 成本：通过合理分配免费额度达成
- 单项成本超 ¥100 需明确标注并征得同意
- 配额耗尽：多模型轮询 + `CircuitBreaker` 故障转移

**安全合规：**
- API Key 全生命周期管理：复用 Phase 1-2 的 `CredentialManager`（AES-256-GCM + Windows DPAPI）
- 审计日志：每次 LLM 调用记录（prompt 摘要 + response + confidence + timestamp）
- 数据脱敏：PII 不发送给 LLM

### 5.3 预期交付物

| 交付物 | 说明 |
|---|---|
| `scripts/llm/model_adapter.py` | LLM 适配器抽象基类 |
| `scripts/llm/glm_adapter.py` | GLM-4-Flash 具体实现 |
| `scripts/llm/prompt_templates/` | 提示词模板库 |
| `scripts/llm/validator.py` | 双层验证器 |
| `scripts/llm/llm_pipeline.py` | Layer C 端到端流水线 |
| `data/knowledge/chinese_reference/C_llm_distilled/` | 蒸馏数据存储 |
| `C_llm_distilled/_metadata/` | 三层元数据 |
| `C_llm_distilled/_logs/llm_audit_log.jsonl` | LLM 审计日志 |

### 5.4 待决事项

- [ ] 编写 Phase 4 plan（Phase 3 完成后启动）
- [ ] 确认 GLM-4-Flash API 凭证获取方式（免费注册 vs 现有账号）
- [ ] 确认 3-5 项难提取指标的具体清单（基于 Phase 3 完成后的指标覆盖差距分析）

---

## 六、Phase 5: 统一聚合与质量门禁规划

<!-- UPDATE_MARKER: phase5_plan -->
### 6.1 阶段定位

**状态：** 🅿️ 待启动（待编写 plan）

**目标：** 将 Layer A + B + C 三层数据映射统一 indicator_id，去重，质量评分，生成 unified JSON。

**工期：** 1 天（D12）

**依赖：** Phase 2-4（聚合三层数据；若 Phase 4 跳过则只依赖 Phase 2-3）

### 6.2 关键设计点（来自 Spec §6.7）

**统一映射：**
- 基于 `_governance/indicator_mapping.json` 将三层数据映射到统一 indicator_id
- 解决跨数据集指标定义不一致（R7 风险）

**去重策略：**
- 同一指标多来源时，按优先级选择：Layer A（金标准）> Layer B（文献）> Layer C（LLM）
- 保留所有来源作为参考，主值取最高优先级

**质量评分：**
- 复用 Phase 1-2 的 `QualityChecker` 三级校验 + A/B/C/D 评级
- unified JSON 必须通过质量门禁（≥33 项指标覆盖，grade ≥ B）

**输出：**
- `unified/chinese_reference_unified.json`（核心交付物）
- `unified/quality_gate_report.json`（质量门禁报告）
- `unified/data_dictionary.md`（字段说明，Phase 6 完善）

### 6.3 预期交付物

| 交付物 | 说明 |
|---|---|
| `scripts/aggregation/unified_aggregator.py` | 统一聚合器 |
| `scripts/aggregation/quality_gate.py` | 质量门禁 |
| `data/knowledge/chinese_reference/unified/chinese_reference_unified.json` | 核心 unified JSON |
| `data/knowledge/chinese_reference/unified/quality_gate_report.json` | 质量门禁报告 |

### 6.4 验收标准

- `chinese_reference_unified.json` 通过质量门禁
- 指标覆盖 ≥ 33 项（Phase 4 启动后预期 33 项全覆盖）
- 质量评级 ≥ B
- 无重复 indicator_id

### 6.5 待决事项

- [ ] 编写 Phase 5 plan（Phase 4 完成后启动）
- [ ] 确认去重优先级策略（当前：A > B > C，待验证）

---

## 七、Phase 6: 数据字典与文档归档规划

<!-- UPDATE_MARKER: phase6_plan -->
### 7.1 阶段定位

**状态：** 🅿️ 待启动（待编写 plan）

**目标：** 编写完整数据字典、处理流程文档、归档快照，完成外部数据获取子系统交付。

**工期：** 1 天（D13）

**依赖：** Phase 5（基于 unified JSON 生成文档）

### 7.2 关键设计点（来自 Spec §6.8）

**数据字典（Spec §6.8.1）：**
- 35 项指标每项附字段说明与处理流程
- 每个字段：名称、类型、单位、范围、来源、处理步骤、质量评级

**处理流程文档：**
- 每个数据集的 `*_pipeline.md`：
  - `A_open_datasets_pipeline.md`
  - `B_literature_pipeline.md`
  - `C_llm_distilled_pipeline.md`
- 记录：数据源 → 下载 → 转换 → 预处理 → 质量校验 → 存储完整流程

**归档快照：**
- `_archive/snapshots/snapshot_2026-07-XX/`
- 包含：全部数据 + 元数据 + 配置 + 代码版本 hash
- 用途：可追溯性 + 未来增量更新基线

**变更日志：**
- `changelog.md`：记录全部 Phase 1-6 的变更历史

### 7.3 预期交付物

| 交付物 | 说明 |
|---|---|
| `data/knowledge/chinese_reference/unified/data_dictionary.md` | 完整数据字典（35 项指标） |
| `docs/pipelines/A_open_datasets_pipeline.md` | Layer A 处理流程 |
| `docs/pipelines/B_literature_pipeline.md` | Layer B 处理流程 |
| `docs/pipelines/C_llm_distilled_pipeline.md` | Layer C 处理流程 |
| `data/knowledge/chinese_reference/_archive/snapshots/snapshot_2026-07-XX/` | 归档快照 |
| `data/knowledge/chinese_reference/changelog.md` | 变更日志 |

### 7.4 验收标准（M6 达成）

- 数据字典完整：35 项指标每项有说明
- 各数据集 pipeline 文档完整
- 归档快照完成
- changelog.md 记录全部变更
- 外部数据获取子系统交付完成

### 7.5 待决事项

- [ ] 编写 Phase 6 plan（Phase 5 完成后启动）
- [ ] 确认归档快照的存储介质（本地 vs 远程备份）

---

## 八、执行顺序与依赖关系

<!-- UPDATE_MARKER: execution_sequence -->
### 8.1 严格依赖链

```
Phase 3 Task 7 → Task 8 → Task 9 → Phase 3 最终审查 → 合并 main
    ↓
Phase 4 plan → Phase 4 执行 → Phase 4 最终审查 → 合并 main
    ↓
Phase 5 plan → Phase 5 执行 → Phase 5 最终审查 → 合并 main
    ↓
Phase 6 plan → Phase 6 执行 → M6 达成
```

### 8.2 可并行项

**Phase 4 plan 编写可与 Phase 3 收尾并行：**
- Phase 3 Task 9 完成后、最终审查期间，可开始编写 Phase 4 plan
- 但 Phase 4 执行必须等待 Phase 3 合并 main 后启动

**Phase 5/6 plan 编写可与 Phase 4 执行并行：**
- Phase 4 执行期间可编写 Phase 5/6 plan
- 但执行必须按序

### 8.3 关键路径

```
关键路径 = Phase 3 Task 7-9 + Phase 3 审查 + Phase 4 + Phase 5 + Phase 6
         = 3 任务 + 1 审查 + 3 天 + 1 天 + 1 天
         ≈ 6-7 个工作日（D8-D13）
```

---

## 九、决策点与待决事项

<!-- UPDATE_MARKER: decisions -->
### 9.1 已决策事项

| 决策 ID | 日期 | 决策内容 | 状态 |
|---|---|---|---|
| D-016 | 2026-07-12 | 启动 Phase 4 Layer C LLM 蒸馏 | ✅ 已采纳，待执行 |
| D-017 | 2026-07-12 | 创建 FORWARD_PLAN.md 统一跟踪后续工作 | ✅ 已执行 |
| SDD | 2026-07-12 | 后续 Phase 5/6 继续使用 SDD 执行方式 | ✅ 已采纳 |

### 9.2 待决事项（需用户输入）

| ID | 待决事项 | 触发时机 | 影响范围 |
|---|---|---|---|
| Q-1 | Phase 4 GLM-4-Flash API 凭证获取方式 | Phase 4 plan 编写时 | Phase 4 能否启动 |
| Q-2 | 3-5 项难提取指标具体清单 | Phase 3 完成后指标覆盖差距分析 | Phase 4 任务范围 |
| Q-3 | Phase 5 去重优先级策略验证 | Phase 5 plan 编写时 | unified JSON 数据准确性 |
| Q-4 | Phase 6 归档快照存储介质 | Phase 6 plan 编写时 | 归档完整性 |
| Q-5 | 是否需要远程备份（GitHub 已有，是否额外） | Phase 6 完成时 | 灾难恢复能力 |

### 9.3 决策规则

- **P0 决策（阻塞执行）：** Q-1、Q-2 必须在 Phase 4 启动前解决
- **P1 决策（影响质量）：** Q-3 必须在 Phase 5 执行前解决
- **P2 决策（影响交付）：** Q-4、Q-5 可在 Phase 6 执行时解决

---

## 十、风险与缓解措施

<!-- UPDATE_MARKER: risks -->
| 风险 ID | 风险描述 | 影响阶段 | 严重度 | 缓解措施 | 状态 |
|---|---|---|---|---|---|
| R-LLM-1 | GLM-4-Flash API 协议变更或下线 | Phase 4 | 🟠 | ModelAdapter 抽象基类支持快速切换；Qwen/DeepSeek 备选 | 🟡 监控 |
| R-LLM-2 | LLM 提取数据存在幻觉 | Phase 4 | 🔴 | 双层验证 + 人工抽检 20% + 金标准对照；confidence < 0.5 拒绝 | 🟡 待实施 |
| R-LLM-3 | 免费额度耗尽 | Phase 4 | 🟠 | 多模型轮询 + 配额监控 + CircuitBreaker 故障转移 | 🟢 已设计 |
| R-AGG-1 | 跨数据集指标定义不一致 | Phase 5 | 🟠 | indicator_mapping.json 统一映射 + Preprocessor 标准化 | 🟢 已实现 |
| R-AGG-2 | unified JSON 质量门禁不通过 | Phase 5 | 🟠 | 逐项排查低质量指标 + 补充数据源 | 🟡 待验证 |
| R-DOC-1 | 数据字典不完整 | Phase 6 | 🟡 | 模板化生成 + 逐项校验 | 🟢 已规划 |
| R-CTX-1 | 上下文割裂导致重复工作 | 全局 | 🟠 | 本文件 FORWARD_PLAN.md 作为单一入口；每次会话开始先读此文件 | 🟢 已实施 |

---

## 十一、文档跟踪与更新规则

<!-- UPDATE_MARKER: tracking_rules -->
### 11.1 更新频率

| 区域 | 更新时机 | 责任人 |
|---|---|---|
| §二当前状态快照 | 每个 Task 完成 | 主会话 |
| §四 Phase 3 剩余任务 | 每个 Task 完成 | 主会话 |
| §五/六/七 Phase 规划 | 对应 Phase plan 编写时 | 主会话 |
| §八执行顺序 | 阶段切换时 | 主会话 |
| §九决策点 | 每次决策时 | 主会话 |
| §十风险 | 发现新风险时 | 主会话 |

### 11.2 与其他文档的关系

- **PROJECT_ROADMAP.md：** 全景路线图（含已完成阶段），本文件是其"后续工作"详细展开
- **PROJECT_STATUS.md：** 实时状态总览，本文件是其"规划视图"补充
- **plans/：** 各 Phase 的 TDD 任务步骤，本文件是"规划层"，plans 是"执行层"
- **progress.md（SDD ledger）：** 任务级审查记录，本文件是"项目级"跟踪

### 11.3 上下文恢复协议

**新会话或上下文压缩后，按以下顺序恢复：**

1. 读取本文件（FORWARD_PLAN.md）— 了解后续工作全貌
2. 读取 PROJECT_STATUS.md §七动态更新区 — 了解最新状态
3. 读取 `.superpowers/sdd/progress.md` — 了解任务级审查记录
4. 读取当前 Task 的 brief 文件（如 `.superpowers/sdd/task-N-brief.md`）
5. 运行 `git log --oneline -10` 确认最新提交链
6. 运行 `python -m pytest tests/ -v --tb=short` 确认测试状态

---

## 十二、变更记录

<!-- UPDATE_MARKER: changelog -->
| 版本 | 日期 | 变更内容 | 作者 |
|---|---|---|---|
| v1.0 | 2026-07-12 | 初始版本：创建后续工作项目计划书，覆盖 Phase 3 剩余（Task 7-9）+ Phase 4/5/6 全景规划；建立单一入口跟踪机制；定义上下文恢复协议 | 项目文档工程师 |
