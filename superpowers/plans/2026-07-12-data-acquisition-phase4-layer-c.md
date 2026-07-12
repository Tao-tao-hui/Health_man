# Phase 4: Layer C LLM 蒸馏增强 — 主从多代理协作蒸馏系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建主从多代理协作蒸馏系统，使用 GLM-4-Flash 等 LLM API 从非结构化医学文献中提取 3-5 项难获取指标，达成 33 项指标全覆盖。

**Architecture:** 主代理（MasterOrchestrator）调度 N 个子代理（ExtractionWorker / ValidationWorker），通过 ModelAdapter 抽象层调用 LLM API，双层验证保障质量，复用 Phase 1-3 安全工具链（CredentialManager / TokenBucketLimiter / CircuitBreaker / AuditLogger），0 成本运行。

**Tech Stack:** Python 3.12+、OpenAI SDK（兼容协议）、jsonschema、pandas、PyMuPDF（PDF 文本提取）、复用 Phase 1-3 全部安全工具链

## Global Constraints

| 约束 | 值 | 来源 |
|------|-----|------|
| 模型主力 | GLM-4-Flash（完全免费，128K 上下文，OpenAI 兼容协议） | Spec §7.1.2 |
| 备选模型 | Qwen2.5-72B → DeepSeek-V3 → Kimi（按优先级故障转移） | Spec §7.1.2 |
| 月度成本上限 | ¥0（通过免费额度分配达成；超额边界：单日 >¥10 告警，单月 >¥100 需同意） | Spec §7.10 |
| confidence 阈值 | <0.5 自动拒绝；0.5-0.7 人工复核；>0.7 自动通过 | Spec §7.6.5 |
| 人工抽检率 | 20% 随机抽样交叉验证 | Spec §7.9.2 |
| 安全合规 | PIPL 合规；不上传 PII；数据不出境（国内模型优先） | Spec §7.6.6 |
| API Key 管理 | 复用 Phase 1-2 CredentialManager（AES-256-GCM + DPAPI） | Spec §7.6.1 |
| 审计日志 | 复用 Phase 1-2 AuditLogger（哈希链防篡改） | Spec §7.11 |
| 存储路径 | `data/knowledge/chinese_reference/C_llm_distilled/` | Spec §7.2 |
| 测试基线 | Phase 3 完成后 122 测试（HEAD `17c0256`） | PROJECT_STATUS v1.2 |
| SDD 执行方式 | Subagent-Driven Development（implementer → reviewer → fix → re-review） | D-016 决策 |

---

## Part A: 高层规划

### A1. Layer C LLM 蒸馏专项规划

#### A1.1 蒸馏目标

本项目中"蒸馏"指**从非结构化医学文献中通过 LLM 提取并凝练结构化参考范围数据**，而非 ML 模型压缩。核心目标如下：

| 目标维度 | 指标 | 验收标准 | 来源 |
|---------|------|---------|------|
| **指标覆盖** | 3-5 项难提取指标 | 33 项指标全覆盖（Layer A+B 覆盖 28-30 项，Layer C 补齐 3-5 项） | Spec §2.2 |
| **数据质量** | 质量评级 | grade ≥ B（完整率 ≥85%，合法率 ≥90%，一致性 ≥80%） | Spec §7.9.2 |
| **提取准确率** | 与金标准对比偏差 | 偏差 ≤10%（与 GASC 2025 已知百分位对比） | Spec §7.6.5 |
| **成本控制** | 月度 API 成本 | ¥0（通过 GLM-4-Flash 完全免费 + 备选模型免费额度分配） | Spec §7.10 |
| **提取效率** | 单文档处理时间 | ≤30 秒 | Spec §7.9.1 |
| **提取成功率** | JSON 解析 + 验证通过率 | ≥85% | Spec §7.9.1 |
| **Token 消耗** | 单文档 token 消耗 | ≤5,000 tokens | Spec §7.9.1 |
| **置信度** | LLM 自评 confidence | >0.7 自动通过；0.5-0.7 人工复核；<0.5 自动拒绝 | Spec §7.6.5 |

#### A1.2 蒸馏方法选择 — 主从多代理协作蒸馏

**方法定位：** 非传统 ML 蒸馏（知识蒸馏/量化/剪枝），而是**多代理协作式知识提取蒸馏**——主代理控制 N 个子代理，从海量非结构化文本中层层提炼核心医学指标数据。

| 方法维度 | 选择 | 理由 |
|---------|------|------|
| **架构模式** | 主从多代理（Master-Worker） | 主代理统一调度，子代理并行提取，进程可控 |
| **提取策略** | 结构化提示词工程 + Few-shot 示例 | Spec §7.3 已定义 6 类提示词模板 |
| **验证策略** | 双层验证（结构化 JSON Schema + 语义合理性） | Spec §7.6.5 三层防护体系 |
| **容错策略** | 多模型轮询 + CircuitBreaker 故障转移 | Spec §7.6.4 |
| **质量控制** | confidence 分数 + 人工抽检 20% + 交叉验证 | Spec §7.9.2 |

**为何不用 ML 蒸馏（知识蒸馏/量化/剪枝）？**

| 维度 | ML 蒸馏 | 多代理协作蒸馏（本项目选择） |
|------|---------|---------------------------|
| 目标 | 压缩大模型为小模型 | 从文献中提取结构化数据 |
| 训练数据 | 需大规模标注数据集 | 文献文本即输入 |
| GPU 需求 | 高（需训练框架） | 无（API 调用） |
| 成本 | GPU 租用 + 训练时间 | ¥0（免费额度） |
| 适用场景 | 模型部署优化 | 知识提取与数据补齐 |
| 与项目契合度 | 低（项目目标为数据获取，非模型部署） | 高（直接补齐缺失指标） |

#### A1.3 数据集准备

**输入数据（待提取的文献/数据）：**

| 数据来源 | 格式 | 内容 | 获取方式 |
|---------|------|------|---------|
| Layer B 已下载文献 | XML/PDF | PubMed 中国人群 BIA 文献 | Phase 3 PubMedAdapter |
| GASC 2025 PDF 附录 | PDF | 全球体成分百分位表 | Phase 3 GascPdfExtractor |
| 中医体质文献 | PDF | 9 型人群分布数据 | Phase 3 PdfTableExtractor |
| 中华医学会指南 | PDF | 临床参考范围 | 人工下载/PyMuPDF 提取 |

**待提取指标清单（Phase 3 完成后确认，预估 3-5 项）：**

| 指标 ID | 指标名称 | 难提取原因 | LLM 蒸馏策略 |
|---------|---------|-----------|-------------|
| IND-10 BONE | 骨骼肌含量 | 历史引用造假需重补 | 从 GASC 2025 PDF 提取百分位表 |
| IND-19 HRV_RMSSD | HRV 均方根差 | PPG 文献 G3 缺失 | 从 PubMed 中文 PPG 文献提取 |
| IND-20 HRV_SDNN | HRV 标准差 | PPG 文献 G3 缺失 | 同上 |
| IND-31 TCM体质 | 中医体质分布 | 9 型人群占比数据分散 | 从国标文献提取人群分布 |
| 派生指标 | 大健康融合派生 | 多为计算指标 | 从多文献交叉提取 |

**训练集/验证集划分：**

| 集合 | 用途 | 数据量 | 划分方式 |
|------|------|-------|---------|
| 提取集 | LLM 实际提取的文献 | 100-200 篇 | Phase 3 已下载的 B_literature/ |
| 验证集（金标准） | 与 LLM 输出对比 | 20-30 条 | 人工标注的已知正确数据（GASC 2025 百分位） |
| 测试集（抽检） | 人工抽检验证 | 20% 随机抽样 | 从 LLM 输出中随机抽取 |

**数据质量要求：**

- 输入文献必须含明确的数字（百分位/均值/标准差），不含则跳过
- 输出必须符合 JSON Schema（Spec §7.3.1 定义）
- 每条输出附 `source_pmid` + `extraction_date` + `model_id` + `extraction_confidence`

#### A1.4 蒸馏流程设计

**预训练模型选择：**

| 优先级 | 模型 | 用途 | 选择理由 |
|--------|------|------|---------|
| 主力 | GLM-4-Flash | 常规提取 | 完全免费、中文强、128K 上下文 |
| 备选 1 | Qwen2.5-72B | 复杂推理 | 100 万 tokens 免费额度 |
| 备选 2 | DeepSeek-V3 | 综合兜底 | 100 万 tokens 免费额度 |
| 长文档 | Kimi | 200K+ PDF | 200K 上下文 |

**蒸馏温度参数设置：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `temperature` | 0.1 | 低温度保证输出稳定性，减少幻觉 |
| `top_p` | 0.8 | 略低于默认值，聚焦高概率 token |
| `max_tokens` | 2000 | 单次响应上限，足够输出结构化 JSON |
| `timeout` | 60s | LLM API 超时阈值（Spec §7.7.1） |
| `retry` | 2 次 | JSON 解析失败重试上限（Spec §7.7.1） |

**训练轮次规划（蒸馏批次）：**

| 轮次 | 任务 | 文献量 | 预期 token 消耗 | 预期耗时 |
|------|------|-------|----------------|---------|
| R1 | BONE 骨骼肌百分位提取 | 20 篇 | 10 万 | 10 分钟 |
| R2 | HRV 指标提取 | 30 篇 | 15 万 | 15 分钟 |
| R3 | 中医体质分布 | 25 篇 | 12 万 | 12 分钟 |
| R4 | 派生指标交叉提取 | 25 篇 | 12 万 | 12 分钟 |
| R5 | 补漏与交叉验证 | 20 篇 | 10 万 | 10 分钟 |
| **合计** | | **120 篇** | **59 万 tokens** | **约 1 小时** |

**蒸馏流程编排：**

```
文献输入 → PDF 文本提取 → 提示词模板渲染 → Master 分发任务
    → ExtractionWorker 调用 LLM API → 原始 JSON 输出
    → ValidationWorker 双层验证 → confidence 评估
    → [confidence ≥0.7] 自动入库
    → [0.5 ≤ confidence <0.7] 人工复核队列
    → [confidence <0.5] 拒绝 + 记录
    → 审计日志记录 → 三层元数据生成
```

#### A1.5 评估指标体系

| 评估维度 | 指标 | 计算方式 | 验收阈值 |
|---------|------|---------|---------|
| **准确率** | 与金标准偏差 | `(LLM值 - 金标准值) / 金标准值` | ≤10% |
| **F1 值** | 结构化提取 F1 | `2 * (precision * recall) / (precision + recall)` | ≥0.85 |
| **完整率** | 必填字段填充率 | `已填充字段数 / 必填字段总数` | ≥85% |
| **合法率** | 数值范围合法率 | `合法值数 / 总值数` | ≥90% |
| **一致性** | 多次提取一致性 | `一致提取次数 / 总提取次数` | ≥80% |
| **困惑度替代** | confidence 自评 | LLM 返回的 extraction_confidence | >0.7 |
| **解析成功率** | JSON 解析通过率 | `成功解析次数 / 总调用次数` | ≥95% |
| **幻觉率** | 越界/编造比率 | `越界值数 / 总值数` | ≤3% |

#### A1.6 风险应对方案

| 风险 ID | 风险描述 | 严重度 | 缓解措施 | 应急方案 |
|---------|---------|--------|---------|---------|
| R-LLM-1 | GLM-4-Flash API 协议变更或下线 | 🟠 中 | ModelAdapter 抽象基类支持快速切换 | 切换 Qwen/DeepSeek |
| R-LLM-2 | LLM 提取数据存在幻觉 | 🔴 高 | 双层验证 + 人工抽检 20% + 金标准对照 | confidence <0.5 自动拒绝；错误率 >15% 全量复核 |
| R-LLM-3 | 免费额度耗尽 | 🟠 中 | 多模型轮询 + 配额监控 + CircuitBreaker | 暂停 Layer C，等待次月配额恢复 |
| R-LLM-4 | API 超时率高 | 🟡 低 | retry_with_backoff + 超时 60s | 切备选模型 |
| R-LLM-5 | JSON 解析失败率高 | 🟡 低 | 修复提示词 + 重试 2 次 | 降级为纯手工提取 |
| R-LLM-6 | PDF 文本提取质量差 | 🟡 低 | PyMuPDF + 表格检测 | 人工录入 |

---

### A2. SKILLS+ 子代理整理方案集成规划

#### A2.1 子代理功能模块划分

**双层子代理架构：**

```
┌─────────────────────────────────────────────────────────────┐
│                  开发层（SDD 工作流）                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Implementer  │  │  Reviewer    │  │    Fixer     │      │
│  │ 子代理       │  │  子代理      │  │    子代理    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────── task brief / report / review package ──┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ 产出
┌─────────────────────────────────────────────────────────────┐
│                  产品层（运行时多代理蒸馏系统）                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              MasterOrchestrator（主代理）              │   │
│  │  任务调度 · 提示词分配 · 质量门控 · 结果聚合            │   │
│  └────────┬──────────────┬──────────────┬───────────────┘   │
│           │              │              │                   │
│    ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼───────┐          │
│    │ Extraction  │ │ Validation │ │  Aggregat- │          │
│    │ Worker      │ │ Worker     │ │  ionWorker │          │
│    │ (提取子代理) │ │ (验证子代理)│ │ (聚合子代理)│          │
│    └─────────────┘ └────────────┘ └────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**产品层子代理职责：**

| 子代理 | 职责 | 输入 | 输出 |
|--------|------|------|------|
| MasterOrchestrator | 任务调度、提示词分配、质量门控 | 指标清单 + 文献路径 | 调度计划 + 最终结果 |
| ExtractionWorker | 调用 LLM API 提取结构化数据 | 文本片段 + 提示词模板 | 原始 JSON + confidence |
| ValidationWorker | 双层验证（Schema + 语义） | 原始 JSON | 验证结果 + 置信度调整 |
| AggregationWorker | 多来源结果聚合与去重 | 验证通过的数据 | 最终结构化数据 |

**开发层子代理职责（SDD）：**

| 子代理 | 职责 | 输入 | 输出 |
|--------|------|------|------|
| Implementer | TDD 任务实施 | task brief | 代码 + commit + report |
| Reviewer | 代码审查 | review package | 审查结论 + findings |
| Fixer | 修复审查问题 | findings | 修复 commit + fix report |

#### A2.2 子代理间通信协议设计

**产品层通信（进程内函数调用）：**

```python
# 任务指令格式（Master → Worker）
@dataclass
class TaskBrief:
    task_id: str                    # 任务唯一标识
    task_type: str                  # "extraction" | "validation" | "aggregation"
    indicator_id: str               # 目标指标 ID
    literature_text: str            # 文献文本片段
    prompt_template: str             # 提示词模板名
    few_shot_examples: list[dict]    # Few-shot 示例
    model_hint: str | None           # 模型偏好（可选）

# 任务结果格式（Worker → Master）
@dataclass
class TaskResult:
    task_id: str
    success: bool
    data: dict | None                # 提取的结构化数据
    confidence: float               # 置信度 0-1
    errors: list[str]               # 错误信息
    model_used: str                  # 实际使用的模型
    tokens_consumed: int             # token 消耗
    latency_ms: int                  # 延迟毫秒
```

**开发层通信（文件系统）：**

| 消息类型 | 格式 | 路径 |
|---------|------|------|
| Task Brief | Markdown | `.superpowers/sdd/task-N-brief.md` |
| Implementer Report | Markdown | `.superpowers/sdd/task-N-report.md` |
| Review Package | diff | `.superpowers/sdd/review-task-N.diff` |
| Progress Ledger | Markdown | `.superpowers/sdd/progress.md` |

#### A2.3 主从架构搭建

**MasterOrchestrator 核心逻辑：**

```python
class MasterOrchestrator:
    """主代理：调度子代理执行蒸馏任务"""

    def __init__(
        self,
        model_adapter: ModelAdapter,
        prompt_library: PromptTemplateLibrary,
        validator: DualLayerValidator,
        audit_logger: AuditLogger,
        max_workers: int = 4,
    ):
        self.model_adapter = model_adapter
        self.prompt_library = prompt_library
        self.validator = validator
        self.audit_logger = audit_logger
        self.max_workers = max_workers

    def dispatch_extraction(
        self, indicator_id: str, literature_texts: list[str]
    ) -> list[TaskResult]:
        """分发提取任务到子代理"""
        results = []
        for text in literature_texts:
            brief = self._build_brief(indicator_id, text)
            worker = ExtractionWorker(
                self.model_adapter, self.prompt_library, self.audit_logger
            )
            result = worker.execute(brief)
            results.append(result)
        return results

    def dispatch_validation(
        self, extraction_results: list[TaskResult]
    ) -> list[TaskResult]:
        """分发验证任务到子代理"""
        validated = []
        for result in extraction_results:
            if not result.success:
                validated.append(result)
                continue
            worker = ValidationWorker(self.validator, self.audit_logger)
            v_result = worker.execute(result)
            validated.append(v_result)
        return validated

    def run(self, tasks: list[dict]) -> LlmPipelineResult:
        """执行完整蒸馏流程"""
        all_results = []
        for task in tasks:
            extracted = self.dispatch_extraction(
                task["indicator_id"], task["literature_texts"]
            )
            validated = self.dispatch_validation(extracted)
            all_results.extend(validated)
        return self._aggregate(all_results)
```

#### A2.4 与现有系统集成接口规范

| 现有模块 | 复用方式 | 集成接口 |
|---------|---------|---------|
| `CredentialManager` | API Key 加密存储/读取 | `retrieve("glm_api_key")` → str |
| `TokenBucketLimiter` | LLM API 调用限流 | `acquire()` → bool |
| `CircuitBreaker` | LLM 故障转移 | `can_call()` / `record_success()` / `record_failure()` |
| `retry_with_backoff` | 网络重试 | `retry_with_backoff(func, max_retries=2)` |
| `AuditLogger` | 审计日志 | `log(operation="llm_call", ...)` |
| `QualityChecker` | 质量校验 | `check(df)` → QualityReport |
| `QualityReport` | 质量报告 | dataclass 复用 |
| `SourceAdapter` | 架构模式参考 | ModelAdapter 镜像 SourceAdapter 设计 |
| `PdfTableExtractor` | PDF 文本提取 | `extract_tables(pdf_path)` → list[dict] |
| `ExtractionLogManager` | 提取日志 | `add_entry()` / `update_status()` |

#### A2.5 数据流转流程设计

```
1. 输入：B_literature/ 中的 PDF/XML 文献
       ↓
2. 文本提取：PdfTableExtractor.extract_tables() → 文本片段
       ↓
3. 任务构建：MasterOrchestrator 根据 indicator_id 选择提示词模板
       ↓
4. 提取执行：ExtractionWorker 调用 ModelAdapter.chat()
   ├─ CredentialManager.retrieve("glm_api_key")
   ├─ TokenBucketLimiter.acquire()
   ├─ CircuitBreaker.can_call()
   ├─ retry_with_backoff(llm_call)
   └─ AuditLogger.log(operation="llm_call")
       ↓
5. 验证执行：ValidationWorker 调用 DualLayerValidator
   ├─ Layer 1: JSON Schema 校验
   └─ Layer 2: 语义校验（范围/单位/关键词黑名单）
       ↓
6. 置信度评估：
   ├─ confidence ≥0.7 → 自动入库
   ├─ 0.5 ≤ confidence <0.7 → 人工复核队列
   └─ confidence <0.5 → 拒绝 + 记录
       ↓
7. 存储：C_llm_distilled/{indicator_id}_distilled.json
       ↓
8. 元数据：L0/L1/L2 三层元数据生成
       ↓
9. 审计：llm_audit_log.jsonl（哈希链防篡改）
```

#### A2.6 错误处理机制

| 错误类型 | 检测方式 | 处置策略 | 重试上限 | 退避 |
|---------|---------|---------|---------|------|
| LLM API 超时 | `httpx.Timeout` (60s) | 切备选模型 | 2 次 | 固定 5s |
| JSON 解析失败 | `json.JSONDecodeError` | 重新请求 + 修复提示词 | 2 次 | 固定 2s |
| confidence <0.5 | schema 校验 | 拒绝该条 + 记录 | 0 | - |
| HTTP 429 配额耗尽 | API 返回 | 切备选模型 + 记录 | 0 | - |
| HTTP 5xx | status_code | 重试 → 切备选 | 3 次 | 指数退避 |
| CircuitBreaker OPEN | 熔断器状态 | 拒绝请求 30s → HALF_OPEN | - | - |
| PDF 解析失败 | PyMuPDF 异常 | 跳过 + 记录 | 0 | - |
| 磁盘空间不足 | shutil.disk_usage | 终止 + 告警 | 0 | - |

#### A2.7 初步测试验证计划

| 测试类型 | 范围 | 验收标准 | 工具 |
|---------|------|---------|------|
| **单元测试** | 每个模块独立测试 | 覆盖率 ≥85% | pytest |
| **集成测试** | Master→Worker→Validator 全链路 | 端到端数据流通 | pytest + FakeModelAdapter |
| **Mock 测试** | LLM API 调用 mock | 不依赖真实 API | unittest.mock |
| **金标准对照** | 与 GASC 2025 已知数据对比 | 偏差 ≤10% | 人工验证 |
| **抽检验证** | 20% 随机抽样 | 错误率 ≤15% | 人工验证 |
| **性能测试** | 单文档处理时间 | ≤30 秒 | time 模块 |
| **成本测试** | token 消耗统计 | ≤5,000 tokens/文档 | API 返回值 |

---

## Part B: TDD 任务分解

### 文件结构

```
scripts/llm/
├── __init__.py
├── model_adapter.py          # Task 1: ModelAdapter 抽象基类
├── glm_adapter.py            # Task 2: GlmAdapter（GLM-4-Flash 实现）
├── prompt_templates.py        # Task 3: 提示词模板库
├── validator.py              # Task 4: 双层验证器
├── master_orchestrator.py    # Task 5: MasterOrchestrator（主代理）
├── workers.py                # Task 6-7: ExtractionWorker + ValidationWorker
├── llm_pipeline.py           # Task 8: LlmPipeline（端到端流水线）
└── llm_metadata_generator.py # Task 9: Layer C 三层元数据

tests/llm/
├── __init__.py
├── test_model_adapter.py      # Task 1 测试
├── test_glm_adapter.py        # Task 2 测试
├── test_prompt_templates.py   # Task 3 测试
├── test_validator.py          # Task 4 测试
├── test_master_orchestrator.py # Task 5 测试
├── test_workers.py            # Task 6-7 测试
├── test_llm_pipeline.py       # Task 8 测试
└── test_llm_metadata.py       # Task 9 测试

data/knowledge/chinese_reference/C_llm_distilled/
├── _metadata/
│   ├── prompt_templates/      # 提示词模板文件
│   │   ├── extract_reference_range.txt
│   │   └── extract_percentile_table.txt
│   ├── L0_card.json           # L0 数据集卡片
│   ├── L1_fields.json         # L1 字段字典
│   └── L2_usage.md            # L2 使用说明
├── _logs/
│   └── llm_audit_log.jsonl    # LLM 审计日志
└── {indicator_id}_distilled.json  # 蒸馏数据
```

---

### Task 1: ModelAdapter 抽象基类

**Files:**
- Create: `e:\Health_man\scripts\llm\__init__.py`
- Create: `e:\Health_man\scripts\llm\model_adapter.py`
- Test: `e:\Health_man\tests\llm\__init__.py`
- Test: `e:\Health_man\tests\llm\test_model_adapter.py`

**Interfaces:**
- Consumes: 无（纯抽象基类，镜像 SourceAdapter 设计模式）
- Produces: `ModelAdapter` 抽象基类；方法签名：
  - `chat(prompt: str, system: str | None = None) -> dict[str, Any]`：调用 LLM，返回 `{content, tokens_used, model_id, latency_ms}`
  - `health_check() -> bool`：健康检查
  - `get_model_info() -> dict[str, Any]`：返回模型信息

- [ ] **Step 1: 写失败测试**

```python
"""ModelAdapter 抽象基类单元测试

验证抽象基类定义和方法签名。
镜像 Phase 1-2 的 SourceAdapter 设计模式。
"""
import pytest
from abc import ABC

from scripts.llm.model_adapter import ModelAdapter


class TestModelAdapter:
    """ModelAdapter 抽象基类测试套件"""

    def test_model_adapter_is_abstract_class(self):
        """测试 ModelAdapter 是抽象基类，无法直接实例化"""
        with pytest.raises(TypeError, match="abstract"):
            ModelAdapter()

    def test_model_adapter_inherits_from_abc(self):
        """测试 ModelAdapter 继承自 ABC"""
        assert issubclass(ModelAdapter, ABC)

    def test_complete_subclass_can_instantiate(self):
        """测试实现全部抽象方法的子类可以实例化"""

        class FakeModelAdapter(ModelAdapter):
            """用于测试的完整实现"""

            def chat(self, prompt: str, system: str | None = None) -> dict:
                return {
                    "content": "模拟响应",
                    "tokens_used": 100,
                    "model_id": "fake-model",
                    "latency_ms": 50,
                }

            def health_check(self) -> bool:
                return True

            def get_model_info(self) -> dict:
                return {"model_id": "fake-model", "provider": "test"}

        adapter = FakeModelAdapter()
        result = adapter.chat("测试提示词")
        assert result["content"] == "模拟响应"
        assert result["tokens_used"] == 100
        assert adapter.health_check() is True
        assert adapter.get_model_info()["model_id"] == "fake-model"

    def test_incomplete_subclass_raises_type_error(self):
        """测试未实现全部抽象方法的子类无法实例化"""

        class IncompleteAdapter(ModelAdapter):
            """缺少 health_check 实现"""
            def chat(self, prompt: str, system: str | None = None) -> dict:
                return {}
            def get_model_info(self) -> dict:
                return {}

        with pytest.raises(TypeError, match="abstract"):
            IncompleteAdapter()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_model_adapter.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 ModelAdapter**

```python
"""LLM 模型适配器抽象基类

所有具体模型适配器（GlmAdapter/QwenAdapter/DeepSeekAdapter 等）必须继承本类
并实现全部抽象方法。
设计目标：插件式扩展，新增模型仅需实现接口，无需修改既有代码。
镜像 Phase 1-2 的 SourceAdapter 设计模式。
"""
from abc import ABC, abstractmethod
from typing import Any


class ModelAdapter(ABC):
    """LLM 模型适配器抽象基类

    子类必须实现以下 3 个方法：
    - chat(): 调用 LLM 进行对话
    - health_check(): 检查模型是否可用
    - get_model_info(): 返回模型元信息
    """

    @abstractmethod
    def chat(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """调用 LLM 进行对话

        Args:
            prompt: 用户提示词
            system: 系统提示词（可选）

        Returns:
            含以下字段的字典：
            - content: str — LLM 响应文本
            - tokens_used: int — 消耗的 token 总数
            - model_id: str — 实际使用的模型 ID
            - latency_ms: int — 响应延迟（毫秒）
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """检查模型是否可用

        Returns:
            模型是否健康可用
        """
        ...

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """返回模型元信息

        Returns:
            含 model_id, provider, max_tokens, context_length 等字段的字典
        """
        ...
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_model_adapter.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（122 + 4 = 126）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/__init__.py scripts/llm/model_adapter.py tests/llm/__init__.py tests/llm/test_model_adapter.py
git commit -m "feat: 添加 ModelAdapter 抽象基类（LLM 模型适配器）"
```

---

### Task 2: GlmAdapter（GLM-4-Flash 实现）

**Files:**
- Create: `e:\Health_man\scripts\llm\glm_adapter.py`
- Test: `e:\Health_man\tests\llm\test_glm_adapter.py`

**Interfaces:**
- Consumes: `ModelAdapter`（Task 1）、`CredentialManager`（Phase 1-2）、`TokenBucketLimiter`（Phase 1-2）、`CircuitBreaker`（Phase 1-2）、`retry_with_backoff`（Phase 1-2）、`AuditLogger`（Phase 1-2）
- Produces: `GlmAdapter` 类；方法签名：
  - `__init__(api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4/", max_tokens: int = 2000, temperature: float = 0.1, timeout: int = 60, rate_limiter: TokenBucketLimiter | None = None, circuit_breaker: CircuitBreaker | None = None, audit_logger: AuditLogger | None = None)`
  - `chat(prompt: str, system: str | None = None) -> dict[str, Any]`
  - `health_check() -> bool`
  - `get_model_info() -> dict[str, Any]`

- [ ] **Step 1: 写失败测试**

```python
"""GlmAdapter 单元测试

验证 GLM-4-Flash 模型适配器实现。
使用 mock 模拟 HTTP 请求，避免真实 API 调用。
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.llm.glm_adapter import GlmAdapter


class TestGlmAdapter:
    """GlmAdapter 测试套件"""

    def test_chat_returns_expected_dict(self):
        """测试 chat 返回包含必要字段的字典"""
        adapter = GlmAdapter(api_key="fake-key")
        mock_response = {
            "choices": [{"message": {"content": '{"indicator_id": "test"}'}}],
            "usage": {"total_tokens": 150},
            "model": "glm-4-flash",
        }
        with patch("scripts.llm.glm_adapter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            result = adapter.chat("提取参考范围")
        assert "content" in result
        assert "tokens_used" in result
        assert "model_id" in result
        assert "latency_ms" in result
        assert result["tokens_used"] == 150
        assert result["model_id"] == "glm-4-flash"

    def test_health_check_returns_true_on_success(self):
        """测试健康检查在模型可用时返回 True"""
        adapter = GlmAdapter(api_key="fake-key")
        with patch("scripts.llm.glm_adapter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            assert adapter.health_check() is True

    def test_health_check_returns_false_on_failure(self):
        """测试健康检查在模型不可用时返回 False"""
        adapter = GlmAdapter(api_key="fake-key")
        with patch("scripts.llm.glm_adapter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=500)
            assert adapter.health_check() is False

    def test_get_model_info_returns_dict(self):
        """测试 get_model_info 返回模型信息"""
        adapter = GlmAdapter(api_key="fake-key")
        info = adapter.get_model_info()
        assert info["model_id"] == "glm-4-flash"
        assert info["provider"] == "zhipu"
        assert "context_length" in info
        assert "max_tokens" in info
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_glm_adapter.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 GlmAdapter**

```python
"""GLM-4-Flash 模型适配器

智谱 AI GLM-4-Flash 实现：完全免费、128K 上下文、OpenAI 兼容协议。
复用 Phase 1-2 的安全工具链：TokenBucketLimiter + CircuitBreaker + retry_with_backoff + AuditLogger。
"""
import logging
import time
from typing import Any

import requests

from scripts.llm.model_adapter import ModelAdapter
from scripts.utils.audit_logger import AuditLogger
from scripts.utils.circuit_breaker import CircuitBreaker
from scripts.utils.rate_limiter import TokenBucketLimiter
from scripts.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# GLM-4-Flash 默认配置
GLM_DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
GLM_MODEL_ID = "glm-4-flash"
GLM_CONTEXT_LENGTH = 128000


class GlmAdapter(ModelAdapter):
    """GLM-4-Flash 模型适配器

    Args:
        api_key: GLM API 密钥
        base_url: API 基础 URL
        max_tokens: 单次响应最大 token 数
        temperature: 采样温度（0.1 保证稳定性）
        timeout: API 超时秒数
        rate_limiter: 令牌桶限流器（可选）
        circuit_breaker: 熔断器（可选）
        audit_logger: 审计日志器（可选）
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = GLM_DEFAULT_BASE_URL,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        timeout: int = 60,
        rate_limiter: TokenBucketLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.audit_logger = audit_logger

    def chat(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """调用 GLM-4-Flash 进行对话

        Returns:
            含 content, tokens_used, model_id, latency_ms 的字典
        """
        # 限流检查
        if self.rate_limiter and not self.rate_limiter.acquire():
            raise RuntimeError("Rate limit exceeded: token bucket empty")

        # 熔断检查
        if self.circuit_breaker and not self.circuit_breaker.can_call():
            raise RuntimeError("Circuit breaker is OPEN: model unavailable")

        start_time = time.monotonic()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        def _do_request() -> dict[str, Any]:
            """实际的 API 请求（供 retry_with_backoff 包装）"""
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": GLM_MODEL_ID,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }
            resp = requests.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()

        # 带重试的 API 调用
        try:
            data = retry_with_backoff(
                _do_request, max_retries=2, base_delay=5.0,
                exceptions=(requests.RequestException,),
            )
        except Exception as e:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            if self.audit_logger:
                self.audit_logger.log(
                    operation="llm_call", target=GLM_MODEL_ID,
                    success=False, error=str(e),
                )
            raise

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # 解析响应
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)

        # 记录成功
        if self.circuit_breaker:
            self.circuit_breaker.record_success()
        if self.audit_logger:
            self.audit_logger.log(
                operation="llm_call", target=GLM_MODEL_ID,
                success=True, tokens_used=tokens_used,
                latency_ms=latency_ms,
            )

        logger.info("GLM 调用成功: %d tokens, %dms", tokens_used, latency_ms)
        return {
            "content": content,
            "tokens_used": tokens_used,
            "model_id": GLM_MODEL_ID,
            "latency_ms": latency_ms,
        }

    def health_check(self) -> bool:
        """检查 GLM-4-Flash 是否可用"""
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": GLM_MODEL_ID,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }
            resp = requests.post(
                url, json=payload, headers=headers, timeout=10
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_model_info(self) -> dict[str, Any]:
        """返回 GLM-4-Flash 模型信息"""
        return {
            "model_id": GLM_MODEL_ID,
            "provider": "zhipu",
            "context_length": GLM_CONTEXT_LENGTH,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_glm_adapter.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（126 + 4 = 130）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/glm_adapter.py tests/llm/test_glm_adapter.py
git commit -m "feat: 添加 GlmAdapter（GLM-4-Flash 实现，含限流/熔断/重试/审计）"
```

---

### Task 3: PromptTemplateLibrary（提示词模板库）

**Files:**
- Create: `e:\Health_man\scripts\llm\prompt_templates.py`
- Create: `e:\Health_man\data\knowledge\chinese_reference\C_llm_distilled\_metadata\prompt_templates\extract_reference_range.txt`
- Test: `e:\Health_man\tests\llm\test_prompt_templates.py`

**Interfaces:**
- Consumes: 无
- Produces: `PromptTemplateLibrary` 类；方法签名：
  - `load(template_name: str) -> str`：加载模板内容
  - `render(template_name: str, **kwargs) -> str`：渲染模板（填充变量）
  - `list_templates() -> list[str]`：列出可用模板名

- [ ] **Step 1: 写失败测试**

```python
"""PromptTemplateLibrary 单元测试

验证提示词模板库的加载、渲染和列举功能。
"""
import pytest
from pathlib import Path

from scripts.llm.prompt_templates import PromptTemplateLibrary


class TestPromptTemplateLibrary:
    """PromptTemplateLibrary 测试套件"""

    def test_load_returns_template_content(self, tmp_path):
        """测试加载模板返回内容"""
        # 创建测试模板文件
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取指标: {indicator_name}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        content = lib.load("extract_reference_range")
        assert "提取指标" in content
        assert "{indicator_name}" in content

    def test_render_fills_variables(self, tmp_path):
        """测试渲染模板填充变量"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取指标: {indicator_name}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        rendered = lib.render(
            "extract_reference_range",
            indicator_name="体脂率",
            literature_text="某文献内容",
        )
        assert "体脂率" in rendered
        assert "某文献内容" in rendered
        assert "{" not in rendered

    def test_list_templates_returns_all(self, tmp_path):
        """测试列举所有模板"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text("a", encoding="utf-8")
        (templates_dir / "extract_percentile_table.txt").write_text("b", encoding="utf-8")
        lib = PromptTemplateLibrary(templates_dir)
        names = lib.list_templates()
        assert "extract_reference_range" in names
        assert "extract_percentile_table" in names
        assert len(names) == 2

    def test_load_nonexistent_raises_error(self, tmp_path):
        """测试加载不存在的模板抛出 FileNotFoundError"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        lib = PromptTemplateLibrary(templates_dir)
        with pytest.raises(FileNotFoundError, match="Template not found"):
            lib.load("nonexistent_template")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_prompt_templates.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 PromptTemplateLibrary + 创建模板文件**

```python
"""提示词模板库

管理 LLM 提取任务的提示词模板。
支持模板加载、变量渲染和模板列举。
模板文件存储在 C_llm_distilled/_metadata/prompt_templates/ 目录。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptTemplateLibrary:
    """提示词模板库

    Args:
        templates_dir: 模板文件目录
    """

    def __init__(self, templates_dir: Path | str):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def load(self, template_name: str) -> str:
        """加载模板内容

        Args:
            template_name: 模板名（不含 .txt 扩展名）

        Returns:
            模板文本内容

        Raises:
            FileNotFoundError: 模板不存在
        """
        file_path = self.templates_dir / f"{template_name}.txt"
        if not file_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_name} (path: {file_path})"
            )
        return file_path.read_text(encoding="utf-8")

    def render(self, template_name: str, **kwargs) -> str:
        """渲染模板（填充变量）

        Args:
            template_name: 模板名
            **kwargs: 模板变量

        Returns:
            渲染后的文本
        """
        template = self.load(template_name)
        return template.format(**kwargs)

    def list_templates(self) -> list[str]:
        """列出所有可用模板名

        Returns:
            模板名列表（不含扩展名）
        """
        return [
            f.stem
            for f in self.templates_dir.glob("*.txt")
            if f.is_file()
        ]
```

创建默认提示词模板文件 `extract_reference_range.txt`：

```text
你是医学数据提取专家。从以下文献片段中提取参考范围数据。

输入文献：
{literature_text}

请严格按以下 JSON schema 输出：
{{
  "indicator_id": "{indicator_id}",
  "name_cn": "string",
  "name_en": "string",
  "unit": "string",
  "population": {{
    "region": "CN",
    "age_range": "string",
    "gender": "male|female|both"
  }},
  "statistics": {{
    "p5": "number|null",
    "p25": "number|null",
    "p50": "number|null",
    "p75": "number|null",
    "p95": "number|null",
    "mean": "number|null",
    "sd": "number|null",
    "n_subjects": "integer"
  }},
  "source_pmid": "string",
  "extraction_confidence": "0-1"
}}

规则：
1. 只提取明确报告的数字，禁止推断
2. 若文献未报告某统计量，填 null
3. 单位必须明确（%、kg/m²、ms 等）
4. extraction_confidence 自评：清晰=0.9，模糊=0.5
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_prompt_templates.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（130 + 4 = 134）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/prompt_templates.py tests/llm/test_prompt_templates.py data/knowledge/chinese_reference/C_llm_distilled/_metadata/prompt_templates/extract_reference_range.txt
git commit -m "feat: 添加 PromptTemplateLibrary（提示词模板库）"
```

---

### Task 4: DualLayerValidator（双层验证器）

**Files:**
- Create: `e:\Health_man\scripts\llm\validator.py`
- Test: `e:\Health_man\tests\llm\test_validator.py`

**Interfaces:**
- Consumes: `jsonschema`（标准库）
- Produces: `DualLayerValidator` 类；方法签名：
  - `validate(data: dict, indicator_id: str) -> ValidationResult`
- Produces: `ValidationResult` dataclass：`is_valid: bool`, `confidence: float`, `errors: list[str]`, `layer_passed: list[str]`

- [ ] **Step 1: 写失败测试**

```python
"""DualLayerValidator 单元测试

验证双层验证器：结构化校验 + 语义校验。
"""
import pytest

from scripts.llm.validator import DualLayerValidator, ValidationResult


class TestDualLayerValidator:
    """DualLayerValidator 测试套件"""

    def test_valid_data_passes_both_layers(self):
        """测试合法数据通过双层验证"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 10.0, "p25": 15.0, "p50": 20.0,
                "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.9,
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is True
        assert result.confidence == 0.9
        assert "structure" in result.layer_passed
        assert "semantic" in result.layer_passed

    def test_missing_required_field_fails_structure(self):
        """测试缺少必填字段未通过结构化校验"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            # 缺少 name_cn, unit, statistics, extraction_confidence
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is False
        assert "structure" not in result.layer_passed
        assert len(result.errors) > 0

    def test_out_of_range_value_fails_semantic(self):
        """测试数值越界未通过语义校验"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 150.0,  # 体脂率 150% 越界
                "p25": 15.0, "p50": 20.0, "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.9,
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is False
        assert "semantic" not in result.layer_passed

    def test_low_confidence_rejected(self):
        """测试 confidence <0.5 被拒绝"""
        validator = DualLayerValidator()
        data = {
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 10.0, "p25": 15.0, "p50": 20.0,
                "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.3,
        }
        result = validator.validate(data, "IND-01")
        assert result.is_valid is False
        assert result.confidence < 0.5
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_validator.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 DualLayerValidator**

```python
"""双层验证器

Layer 1: 结构化校验 — JSON Schema 严格校验，字段类型/范围/必填完整性
Layer 2: 语义校验 — 数值范围合理性、单位一致性、关键词黑名单过滤

基于 Spec §7.6.5 三层防护体系设计。
"""
import jsonschema
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# 结构化校验 Schema（Layer 1）
EXTRACTION_SCHEMA = {
    "type": "object",
    "required": [
        "indicator_id", "name_cn", "unit",
        "statistics", "extraction_confidence",
    ],
    "properties": {
        "indicator_id": {"type": "string"},
        "name_cn": {"type": "string"},
        "name_en": {"type": "string"},
        "unit": {"type": "string"},
        "population": {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "age_range": {"type": "string"},
                "gender": {"type": "string"},
            },
        },
        "statistics": {
            "type": "object",
            "required": ["n_subjects"],
            "properties": {
                "p5": {"type": ["number", "null"]},
                "p25": {"type": ["number", "null"]},
                "p50": {"type": ["number", "null"]},
                "p75": {"type": ["number", "null"]},
                "p95": {"type": ["number", "null"]},
                "mean": {"type": ["number", "null"]},
                "sd": {"type": ["number", "null"]},
                "n_subjects": {"type": "integer"},
            },
        },
        "source_pmid": {"type": "string"},
        "extraction_confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

# 语义校验范围（Layer 2）— 各指标的合理范围
INDICATOR_RANGES = {
    "IND-01": {"name": "体脂率", "unit": "%", "min": 0, "max": 60},
    "IND-02": {"name": "BMI", "unit": "kg/m²", "min": 10, "max": 80},
    "IND-10": {"name": "骨骼肌", "unit": "kg", "min": 10, "max": 100},
    "IND-15": {"name": "SpO₂", "unit": "%", "min": 70, "max": 100},
    "IND-18": {"name": "心率", "unit": "bpm", "min": 30, "max": 220},
    "IND-19": {"name": "HRV_RMSSD", "unit": "ms", "min": 0, "max": 500},
    "IND-20": {"name": "HRV_SDNN", "unit": "ms", "min": 0, "max": 500},
    "default": {"min": 0, "max": 10000},
}

# 关键词黑名单（Spec §7.6.6）
KEYWORD_BLACKLIST = [
    "诊断", "确诊", "治疗", "处方", "痊愈", "治愈",
    "药物推荐", "疗法治愈",
]

# confidence 阈值
CONFIDENCE_REJECT_THRESHOLD = 0.5
CONFIDENCE_REVIEW_THRESHOLD = 0.7


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    confidence: float
    errors: list[str] = field(default_factory=list)
    layer_passed: list[str] = field(default_factory=list)
    action: str = "accept"  # accept | review | reject


class DualLayerValidator:
    """双层验证器"""

    def validate(self, data: dict[str, Any], indicator_id: str) -> ValidationResult:
        """执行双层验证

        Args:
            data: LLM 提取的结构化数据
            indicator_id: 指标 ID（用于语义校验范围查找）

        Returns:
            验证结果
        """
        errors: list[str] = []
        layer_passed: list[str] = []

        # Layer 1: 结构化校验
        try:
            jsonschema.validate(instance=data, schema=EXTRACTION_SCHEMA)
            layer_passed.append("structure")
        except jsonschema.ValidationError as e:
            errors.append(f"Structure error: {e.message}")

        # Layer 2: 语义校验（仅在结构化校验通过后执行）
        if "structure" in layer_passed:
            semantic_errors = self._check_semantic(data, indicator_id)
            if semantic_errors:
                errors.extend(semantic_errors)
            else:
                layer_passed.append("semantic")

        # confidence 评估
        confidence = data.get("extraction_confidence", 0.0)

        # 综合判定
        is_valid = len(layer_passed) == 2 and confidence >= CONFIDENCE_REJECT_THRESHOLD

        # action 判定
        if not is_valid and confidence < CONFIDENCE_REJECT_THRESHOLD:
            action = "reject"
        elif confidence < CONFIDENCE_REVIEW_THRESHOLD:
            action = "review"
        else:
            action = "accept"

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            errors=errors,
            layer_passed=layer_passed,
            action=action,
        )

    def _check_semantic(
        self, data: dict[str, Any], indicator_id: str
    ) -> list[str]:
        """语义校验：数值范围 + 关键词黑名单"""
        errors: list[str] = []

        # 数值范围检查
        stats = data.get("statistics", {})
        range_info = INDICATOR_RANGES.get(
            indicator_id, INDICATOR_RANGES["default"]
        )
        min_val = range_info["min"]
        max_val = range_info["max"]

        for key in ["p5", "p25", "p50", "p75", "p95", "mean"]:
            val = stats.get(key)
            if val is not None and (val < min_val or val > max_val):
                errors.append(
                    f"Semantic error: {key}={val} out of range "
                    f"[{min_val}, {max_val}] for {indicator_id}"
                )

        # 关键词黑名单检查
        name_cn = data.get("name_cn", "")
        for keyword in KEYWORD_BLACKLIST:
            if keyword in name_cn:
                errors.append(f"Semantic error: blacklisted keyword '{keyword}' in name_cn")

        return errors
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_validator.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（134 + 4 = 138）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/validator.py tests/llm/test_validator.py
git commit -m "feat: 添加 DualLayerValidator（双层验证器：结构化+语义）"
```

---

### Task 5: TaskBrief 与 TaskResult 数据结构

**Files:**
- Create: `e:\Health_man\scripts\llm\task_types.py`
- Test: `e:\Health_man\tests\llm\test_task_types.py`

**Interfaces:**
- Consumes: 无
- Produces: `TaskBrief` dataclass、`TaskResult` dataclass — 子代理间通信的数据结构

- [ ] **Step 1: 写失败测试**

```python
"""TaskBrief 与 TaskResult 数据结构测试

验证子代理间通信的数据结构定义。
"""
from scripts.llm.task_types import TaskBrief, TaskResult


class TestTaskTypes:
    """任务数据结构测试套件"""

    def test_task_brief_creation(self):
        """测试 TaskBrief 创建"""
        brief = TaskBrief(
            task_id="task-001",
            task_type="extraction",
            indicator_id="IND-01",
            literature_text="某文献内容",
            prompt_template="extract_reference_range",
            few_shot_examples=[{"input": "a", "output": "b"}],
        )
        assert brief.task_id == "task-001"
        assert brief.task_type == "extraction"
        assert brief.indicator_id == "IND-01"
        assert brief.literature_text == "某文献内容"
        assert brief.prompt_template == "extract_reference_range"
        assert len(brief.few_shot_examples) == 1

    def test_task_result_success(self):
        """测试 TaskResult 成功状态"""
        result = TaskResult(
            task_id="task-001",
            success=True,
            data={"indicator_id": "IND-01"},
            confidence=0.9,
            model_used="glm-4-flash",
            tokens_consumed=150,
            latency_ms=500,
        )
        assert result.success is True
        assert result.data["indicator_id"] == "IND-01"
        assert result.confidence == 0.9
        assert len(result.errors) == 0

    def test_task_result_failure_with_errors(self):
        """测试 TaskResult 失败状态含错误"""
        result = TaskResult(
            task_id="task-002",
            success=False,
            errors=["JSON parse error", "timeout"],
        )
        assert result.success is False
        assert result.data is None
        assert len(result.errors) == 2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_task_types.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 task_types.py**

```python
"""子代理间通信数据结构

定义 TaskBrief（任务指令）和 TaskResult（任务结果），
用于 MasterOrchestrator 与 Worker 之间的通信。
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskBrief:
    """任务指令（Master → Worker）

    Attributes:
        task_id: 任务唯一标识
        task_type: 任务类型（extraction / validation / aggregation）
        indicator_id: 目标指标 ID
        literature_text: 文献文本片段
        prompt_template: 提示词模板名
        few_shot_examples: Few-shot 示例列表
        model_hint: 模型偏好（可选，如 "glm" / "kimi"）
    """
    task_id: str
    task_type: str
    indicator_id: str
    literature_text: str
    prompt_template: str
    few_shot_examples: list[dict[str, Any]] = field(default_factory=list)
    model_hint: str | None = None


@dataclass
class TaskResult:
    """任务结果（Worker → Master）

    Attributes:
        task_id: 任务唯一标识（与 TaskBrief 对应）
        success: 是否成功
        data: 提取的结构化数据（成功时）
        confidence: 置信度 0-1
        errors: 错误信息列表（失败时）
        model_used: 实际使用的模型 ID
        tokens_consumed: token 消耗量
        latency_ms: 延迟毫秒
    """
    task_id: str
    success: bool
    data: dict[str, Any] | None = None
    confidence: float = 0.0
    errors: list[str] = field(default_factory=list)
    model_used: str = ""
    tokens_consumed: int = 0
    latency_ms: int = 0
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_task_types.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（138 + 3 = 141）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/task_types.py tests/llm/test_task_types.py
git commit -m "feat: 添加 TaskBrief 与 TaskResult 通信数据结构"
```

---

### Task 6: ExtractionWorker（提取子代理）

**Files:**
- Create: `e:\Health_man\scripts\llm\workers.py`
- Test: `e:\Health_man\tests\llm\test_workers.py`

**Interfaces:**
- Consumes: `ModelAdapter`（Task 1）、`PromptTemplateLibrary`（Task 3）、`TaskBrief`/`TaskResult`（Task 5）、`AuditLogger`（Phase 1-2）
- Produces: `ExtractionWorker` 类；方法签名：
  - `execute(brief: TaskBrief) -> TaskResult`

- [ ] **Step 1: 写失败测试**

```python
"""ExtractionWorker 单元测试

验证提取子代理的 LLM 调用、JSON 解析和结果返回。
使用 FakeModelAdapter 模拟 LLM 响应。
"""
import json
import pytest
from pathlib import Path

from scripts.llm.workers import ExtractionWorker
from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.task_types import TaskBrief


class FakeModelAdapter(ModelAdapter):
    """用于测试的假模型适配器"""

    def __init__(self, response_content: str):
        self.response_content = response_content

    def chat(self, prompt: str, system: str | None = None) -> dict:
        return {
            "content": self.response_content,
            "tokens_used": 100,
            "model_id": "fake-model",
            "latency_ms": 50,
        }

    def health_check(self) -> bool:
        return True

    def get_model_info(self) -> dict:
        return {"model_id": "fake-model", "provider": "test"}


class TestExtractionWorker:
    """ExtractionWorker 测试套件"""

    def test_execute_returns_success_result(self, tmp_path):
        """测试成功提取返回成功结果"""
        # 准备模板
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)

        # 准备假 LLM 响应
        fake_response = json.dumps({
            "indicator_id": "IND-01",
            "name_cn": "体脂率",
            "unit": "%",
            "statistics": {
                "p5": 10.0, "p25": 15.0, "p50": 20.0,
                "p75": 25.0, "p95": 30.0,
                "mean": 20.5, "sd": 5.0, "n_subjects": 100,
            },
            "extraction_confidence": 0.9,
        })
        adapter = FakeModelAdapter(fake_response)
        worker = ExtractionWorker(adapter, lib)

        brief = TaskBrief(
            task_id="task-001",
            task_type="extraction",
            indicator_id="IND-01",
            literature_text="某文献",
            prompt_template="extract_reference_range",
        )
        result = worker.execute(brief)
        assert result.success is True
        assert result.data["indicator_id"] == "IND-01"
        assert result.confidence == 0.9
        assert result.model_used == "fake-model"

    def test_execute_returns_failure_on_invalid_json(self, tmp_path):
        """测试 LLM 返回非法 JSON 时返回失败结果"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)

        adapter = FakeModelAdapter("这不是合法的 JSON")
        worker = ExtractionWorker(adapter, lib)

        brief = TaskBrief(
            task_id="task-002",
            task_type="extraction",
            indicator_id="IND-01",
            literature_text="某文献",
            prompt_template="extract_reference_range",
        )
        result = worker.execute(brief)
        assert result.success is False
        assert len(result.errors) > 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_workers.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 ExtractionWorker**

```python
"""子代理模块

ExtractionWorker: 提取子代理，调用 LLM API 提取结构化数据
ValidationWorker: 验证子代理，执行双层验证
"""
import json
import logging

from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.task_types import TaskBrief, TaskResult
from scripts.llm.validator import DualLayerValidator, ValidationResult
from scripts.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class ExtractionWorker:
    """提取子代理

    职责：调用 LLM API 提取结构化医学数据
    输入：TaskBrief（含文献文本 + 提示词模板）
    输出：TaskResult（含提取的结构化数据 + confidence）
    """

    def __init__(
        self,
        model_adapter: ModelAdapter,
        prompt_library: PromptTemplateLibrary,
        audit_logger: AuditLogger | None = None,
    ):
        self.model_adapter = model_adapter
        self.prompt_library = prompt_library
        self.audit_logger = audit_logger

    def execute(self, brief: TaskBrief) -> TaskResult:
        """执行提取任务

        Args:
            brief: 任务指令

        Returns:
            任务结果
        """
        try:
            # 渲染提示词模板
            prompt = self.prompt_library.render(
                brief.prompt_template,
                indicator_id=brief.indicator_id,
                literature_text=brief.literature_text,
            )

            # 调用 LLM
            response = self.model_adapter.chat(prompt)
            content = response["content"]

            # 解析 JSON
            data = json.loads(content)
            confidence = data.get("extraction_confidence", 0.0)

            logger.info(
                "提取成功: task=%s, confidence=%.2f, tokens=%d",
                brief.task_id, confidence, response["tokens_used"],
            )

            return TaskResult(
                task_id=brief.task_id,
                success=True,
                data=data,
                confidence=confidence,
                model_used=response["model_id"],
                tokens_consumed=response["tokens_used"],
                latency_ms=response["latency_ms"],
            )

        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_id=brief.task_id,
                success=False,
                errors=[error_msg],
                model_used=getattr(self.model_adapter, "get_model_info", lambda: {})().get("model_id", "unknown"),
            )
        except Exception as e:
            error_msg = f"提取失败: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_id=brief.task_id,
                success=False,
                errors=[error_msg],
            )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_workers.py -v`
Expected: PASS (2/2)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（141 + 2 = 143）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/workers.py tests/llm/test_workers.py
git commit -m "feat: 添加 ExtractionWorker（提取子代理）"
```

---

### Task 7: ValidationWorker（验证子代理）

**Files:**
- Modify: `e:\Health_man\scripts\llm\workers.py`（追加 ValidationWorker 类）
- Test: `e:\Health_man\tests\llm\test_workers.py`（追加测试）

**Interfaces:**
- Consumes: `DualLayerValidator`（Task 4）、`TaskResult`（Task 5）
- Produces: `ValidationWorker` 类；方法签名：
  - `execute(result: TaskResult, indicator_id: str) -> TaskResult`

- [ ] **Step 1: 写失败测试（追加到 test_workers.py）**

```python
class TestValidationWorker:
    """ValidationWorker 测试套件"""

    def test_execute_valid_data_returns_accepted(self):
        """测试合法数据通过验证"""
        from scripts.llm.workers import ValidationWorker
        from scripts.llm.task_types import TaskResult

        validator = DualLayerValidator()
        worker = ValidationWorker(validator)

        result = TaskResult(
            task_id="task-001",
            success=True,
            data={
                "indicator_id": "IND-01",
                "name_cn": "体脂率",
                "unit": "%",
                "statistics": {
                    "p5": 10.0, "p25": 15.0, "p50": 20.0,
                    "p75": 25.0, "p95": 30.0,
                    "mean": 20.5, "sd": 5.0, "n_subjects": 100,
                },
                "extraction_confidence": 0.9,
            },
            confidence=0.9,
        )
        validated = worker.execute(result, "IND-01")
        assert validated.success is True
        assert validated.confidence == 0.9

    def test_execute_invalid_data_returns_rejected(self):
        """测试非法数据被拒绝"""
        from scripts.llm.workers import ValidationWorker
        from scripts.llm.task_types import TaskResult

        validator = DualLayerValidator()
        worker = ValidationWorker(validator)

        result = TaskResult(
            task_id="task-002",
            success=True,
            data={"indicator_id": "IND-01"},  # 缺少必填字段
            confidence=0.3,
        )
        validated = worker.execute(result, "IND-01")
        assert validated.success is False
        assert len(validated.errors) > 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_workers.py::TestValidationWorker -v`
Expected: FAIL with "ImportError" or "AttributeError"

- [ ] **Step 3: 实现 ValidationWorker（追加到 workers.py）**

```python
class ValidationWorker:
    """验证子代理

    职责：对提取结果执行双层验证（结构化 + 语义）
    输入：TaskResult（含提取的数据）
    输出：TaskResult（含验证结果 + 调整后的 confidence）
    """

    def __init__(
        self,
        validator: DualLayerValidator,
        audit_logger: AuditLogger | None = None,
    ):
        self.validator = validator
        self.audit_logger = audit_logger

    def execute(self, result: TaskResult, indicator_id: str) -> TaskResult:
        """执行验证任务

        Args:
            result: 提取子代理返回的结果
            indicator_id: 指标 ID（用于语义校验范围查找）

        Returns:
            验证后的任务结果
        """
        # 如果提取本身就失败，直接返回
        if not result.success or result.data is None:
            return result

        # 执行双层验证
        validation = self.validator.validate(result.data, indicator_id)

        # 记录审计日志
        if self.audit_logger:
            self.audit_logger.log(
                operation="validation",
                target=indicator_id,
                success=validation.is_valid,
                confidence=validation.confidence,
                action=validation.action,
            )

        if validation.is_valid:
            logger.info(
                "验证通过: task=%s, confidence=%.2f, action=%s",
                result.task_id, validation.confidence, validation.action,
            )
            return TaskResult(
                task_id=result.task_id,
                success=True,
                data=result.data,
                confidence=validation.confidence,
                model_used=result.model_used,
                tokens_consumed=result.tokens_consumed,
                latency_ms=result.latency_ms,
            )
        else:
            logger.warning(
                "验证失败: task=%s, errors=%s",
                result.task_id, validation.errors,
            )
            return TaskResult(
                task_id=result.task_id,
                success=False,
                data=result.data,
                confidence=validation.confidence,
                errors=validation.errors,
                model_used=result.model_used,
                tokens_consumed=result.tokens_consumed,
                latency_ms=result.latency_ms,
            )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_workers.py -v`
Expected: PASS (4/4 — 原 2 个 + 新增 2 个)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（143 + 2 = 145）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/workers.py tests/llm/test_workers.py
git commit -m "feat: 添加 ValidationWorker（验证子代理，双层验证）"
```

---

### Task 8: MasterOrchestrator（主代理）

**Files:**
- Create: `e:\Health_man\scripts\llm\master_orchestrator.py`
- Test: `e:\Health_man\tests\llm\test_master_orchestrator.py`

**Interfaces:**
- Consumes: `ModelAdapter`（Task 1）、`PromptTemplateLibrary`（Task 3）、`DualLayerValidator`（Task 4）、`ExtractionWorker`/`ValidationWorker`（Task 6-7）、`AuditLogger`（Phase 1-2）
- Produces: `MasterOrchestrator` 类；方法签名：
  - `dispatch_extraction(indicator_id: str, literature_texts: list[str]) -> list[TaskResult]`
  - `dispatch_validation(extraction_results: list[TaskResult], indicator_id: str) -> list[TaskResult]`
  - `run(tasks: list[dict]) -> dict`：执行完整蒸馏流程

- [ ] **Step 1: 写失败测试**

```python
"""MasterOrchestrator 单元测试

验证主代理的任务调度和结果聚合功能。
使用 FakeModelAdapter 模拟 LLM。
"""
import json
import pytest
from pathlib import Path

from scripts.llm.master_orchestrator import MasterOrchestrator
from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.validator import DualLayerValidator


class FakeModelAdapter(ModelAdapter):
    """用于测试的假模型适配器"""

    def chat(self, prompt: str, system: str | None = None) -> dict:
        return {
            "content": json.dumps({
                "indicator_id": "IND-01",
                "name_cn": "体脂率",
                "unit": "%",
                "statistics": {
                    "p5": 10.0, "p25": 15.0, "p50": 20.0,
                    "p75": 25.0, "p95": 30.0,
                    "mean": 20.5, "sd": 5.0, "n_subjects": 100,
                },
                "extraction_confidence": 0.9,
            }),
            "tokens_used": 100,
            "model_id": "fake-model",
            "latency_ms": 50,
        }

    def health_check(self) -> bool:
        return True

    def get_model_info(self) -> dict:
        return {"model_id": "fake-model"}


class TestMasterOrchestrator:
    """MasterOrchestrator 测试套件"""

    def test_dispatch_extraction_returns_results(self, tmp_path):
        """测试分发提取任务返回结果列表"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        validator = DualLayerValidator()
        adapter = FakeModelAdapter()

        master = MasterOrchestrator(adapter, lib, validator)
        results = master.dispatch_extraction(
            "IND-01", ["文献1内容", "文献2内容"]
        )
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.confidence == 0.9 for r in results)

    def test_dispatch_validation_returns_validated(self, tmp_path):
        """测试分发验证任务返回验证后结果"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        validator = DualLayerValidator()
        adapter = FakeModelAdapter()

        master = MasterOrchestrator(adapter, lib, validator)
        extracted = master.dispatch_extraction("IND-01", ["文献1"])
        validated = master.dispatch_validation(extracted, "IND-01")
        assert len(validated) == 1
        assert validated[0].success is True

    def test_run_full_pipeline(self, tmp_path):
        """测试完整蒸馏流程"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        validator = DualLayerValidator()
        adapter = FakeModelAdapter()

        master = MasterOrchestrator(adapter, lib, validator)
        tasks = [
            {
                "indicator_id": "IND-01",
                "literature_texts": ["文献1", "文献2"],
                "prompt_template": "extract_reference_range",
            }
        ]
        result = master.run(tasks)
        assert result["total_tasks"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_master_orchestrator.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 MasterOrchestrator**

```python
"""主代理（MasterOrchestrator）

职责：调度子代理执行蒸馏任务，聚合结果。
设计模式：Master-Worker，主代理统一调度，子代理并行执行。
"""
import logging
import uuid
from typing import Any

from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.task_types import TaskBrief, TaskResult
from scripts.llm.validator import DualLayerValidator
from scripts.llm.workers import ExtractionWorker, ValidationWorker
from scripts.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """主代理

    Args:
        model_adapter: LLM 模型适配器
        prompt_library: 提示词模板库
        validator: 双层验证器
        audit_logger: 审计日志器（可选）
    """

    def __init__(
        self,
        model_adapter: ModelAdapter,
        prompt_library: PromptTemplateLibrary,
        validator: DualLayerValidator,
        audit_logger: AuditLogger | None = None,
    ):
        self.model_adapter = model_adapter
        self.prompt_library = prompt_library
        self.validator = validator
        self.audit_logger = audit_logger

    def dispatch_extraction(
        self,
        indicator_id: str,
        literature_texts: list[str],
        prompt_template: str = "extract_reference_range",
    ) -> list[TaskResult]:
        """分发提取任务到 ExtractionWorker

        Args:
            indicator_id: 目标指标 ID
            literature_texts: 文献文本列表
            prompt_template: 提示词模板名

        Returns:
            提取结果列表
        """
        worker = ExtractionWorker(
            self.model_adapter, self.prompt_library, self.audit_logger
        )
        results: list[TaskResult] = []
        for text in literature_texts:
            brief = TaskBrief(
                task_id=str(uuid.uuid4()),
                task_type="extraction",
                indicator_id=indicator_id,
                literature_text=text,
                prompt_template=prompt_template,
            )
            result = worker.execute(brief)
            results.append(result)
        return results

    def dispatch_validation(
        self,
        extraction_results: list[TaskResult],
        indicator_id: str,
    ) -> list[TaskResult]:
        """分发验证任务到 ValidationWorker

        Args:
            extraction_results: 提取结果列表
            indicator_id: 指标 ID

        Returns:
            验证后结果列表
        """
        worker = ValidationWorker(self.validator, self.audit_logger)
        validated: list[TaskResult] = []
        for result in extraction_results:
            v_result = worker.execute(result, indicator_id)
            validated.append(v_result)
        return validated

    def run(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """执行完整蒸馏流程

        Args:
            tasks: 任务列表，每个任务含 indicator_id, literature_texts, prompt_template

        Returns:
            含 total_tasks, successful, failed, results 的聚合结果
        """
        all_results: list[TaskResult] = []
        for task in tasks:
            indicator_id = task["indicator_id"]
            texts = task["literature_texts"]
            template = task.get("prompt_template", "extract_reference_range")

            # 阶段 1: 提取
            extracted = self.dispatch_extraction(indicator_id, texts, template)
            # 阶段 2: 验证
            validated = self.dispatch_validation(extracted, indicator_id)
            all_results.extend(validated)

        successful = sum(1 for r in all_results if r.success)
        failed = len(all_results) - successful
        total_tokens = sum(r.tokens_consumed for r in all_results)

        logger.info(
            "蒸馏完成: total=%d, success=%d, failed=%d, tokens=%d",
            len(all_results), successful, failed, total_tokens,
        )

        return {
            "total_tasks": len(all_results),
            "successful": successful,
            "failed": failed,
            "total_tokens_consumed": total_tokens,
            "results": all_results,
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_master_orchestrator.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（145 + 3 = 148）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/master_orchestrator.py tests/llm/test_master_orchestrator.py
git commit -m "feat: 添加 MasterOrchestrator（主代理，任务调度+结果聚合）"
```

---

### Task 9: LlmPipeline（端到端流水线）

**Files:**
- Create: `e:\Health_man\scripts\llm\llm_pipeline.py`
- Test: `e:\Health_man\tests\llm\test_llm_pipeline.py`

**Interfaces:**
- Consumes: `MasterOrchestrator`（Task 8）、`AuditLogger`（Phase 1-2）、`QualityReport`（Phase 1-2）
- Produces: `LlmPipeline` 类 + `LlmPipelineResult` dataclass；方法签名：
  - `run(tasks: list[dict], dest_dir: Path) -> LlmPipelineResult`：执行完整蒸馏流水线
  - `audit_size(dest_dir: Path) -> dict`：体量审计

- [ ] **Step 1: 写失败测试**

```python
"""LlmPipeline 单元测试

验证端到端流水线整合功能。
使用 FakeModelAdapter 模拟 LLM。
"""
import json
import pytest
from pathlib import Path

from scripts.llm.llm_pipeline import LlmPipeline, LlmPipelineResult
from scripts.llm.model_adapter import ModelAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.validator import DualLayerValidator
from scripts.llm.master_orchestrator import MasterOrchestrator


class FakeModelAdapter(ModelAdapter):
    """用于测试的假模型适配器"""

    def chat(self, prompt: str, system: str | None = None) -> dict:
        return {
            "content": json.dumps({
                "indicator_id": "IND-01",
                "name_cn": "体脂率",
                "unit": "%",
                "statistics": {
                    "p5": 10.0, "p25": 15.0, "p50": 20.0,
                    "p75": 25.0, "p95": 30.0,
                    "mean": 20.5, "sd": 5.0, "n_subjects": 100,
                },
                "extraction_confidence": 0.9,
            }),
            "tokens_used": 100,
            "model_id": "fake-model",
            "latency_ms": 50,
        }

    def health_check(self) -> bool:
        return True

    def get_model_info(self) -> dict:
        return {"model_id": "fake-model"}


def _make_pipeline(tmp_path: Path) -> LlmPipeline:
    """使用临时目录构造 pipeline，避免硬编码路径副作用"""
    templates_dir = tmp_path / "prompt_templates"
    templates_dir.mkdir()
    (templates_dir / "extract_reference_range.txt").write_text(
        "提取: {indicator_id}\n文献: {literature_text}", encoding="utf-8"
    )
    lib = PromptTemplateLibrary(templates_dir)
    validator = DualLayerValidator()
    adapter = FakeModelAdapter()
    master = MasterOrchestrator(adapter, lib, validator)
    audit_path = tmp_path / "audit.jsonl"
    return LlmPipeline(master, audit_log_path=audit_path)


class TestLlmPipeline:
    """LlmPipeline 测试套件"""

    def test_run_returns_pipeline_result(self, tmp_path):
        """测试流水线返回结果对象"""
        pipeline = _make_pipeline(tmp_path)
        tasks = [
            {
                "indicator_id": "IND-01",
                "literature_texts": ["文献1"],
                "prompt_template": "extract_reference_range",
            }
        ]
        result = pipeline.run(tasks, tmp_path)
        assert isinstance(result, LlmPipelineResult)
        assert result.success is True
        assert result.total_extracted == 1

    def test_run_creates_output_files(self, tmp_path):
        """测试流水线在目标目录创建输出文件"""
        pipeline = _make_pipeline(tmp_path)
        tasks = [
            {
                "indicator_id": "IND-01",
                "literature_texts": ["文献1"],
                "prompt_template": "extract_reference_range",
            }
        ]
        pipeline.run(tasks, tmp_path)
        # 验证蒸馏数据文件已创建
        output_files = list(tmp_path.glob("*_distilled.json"))
        assert len(output_files) > 0

    def test_audit_size_under_limit(self, tmp_path):
        """测试体量审计在限制内"""
        pipeline = _make_pipeline(tmp_path)
        (tmp_path / "a.json").write_bytes(b'{"data": "test"}')
        audit = pipeline.audit_size(tmp_path)
        assert audit["total_bytes"] > 0
        assert audit["within_limit"] is True

    def test_audit_size_exceeds_limit(self, tmp_path):
        """测试体量审计超限"""
        pipeline = _make_pipeline(tmp_path, max_size_mb=0.0001)
        (tmp_path / "big.json").write_bytes(b"x" * 200)
        audit = pipeline.audit_size(tmp_path)
        assert audit["within_limit"] is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_llm_pipeline.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 LlmPipeline**

```python
"""Layer C 端到端流水线

整合：主代理调度 → 提取子代理 → 验证子代理 → 存储 → 审计 → 元数据
流水线步骤：
1. MasterOrchestrator 调度提取+验证
2. 通过验证的数据写入 C_llm_distilled/
3. 审计日志记录（哈希链防篡改）
4. 体量审计（500MB 上限）
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.llm.master_orchestrator import MasterOrchestrator
from scripts.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass
class LlmPipelineResult:
    """流水线执行结果"""
    success: bool
    total_extracted: int = 0
    total_validated: int = 0
    total_rejected: int = 0
    total_tokens_consumed: int = 0
    errors: list[str] = field(default_factory=list)


class LlmPipeline:
    """Layer C 端到端流水线

    Args:
        master: 主代理
        max_size_mb: 体量上限（MB），默认 500
        audit_log_path: 审计日志路径
    """

    def __init__(
        self,
        master: MasterOrchestrator,
        max_size_mb: int = 500,
        audit_log_path: Path | None = None,
    ):
        self.master = master
        self.max_size_bytes = max_size_mb * 1024 * 1024
        default_audit_path = Path(
            "data/knowledge/chinese_reference/C_llm_distilled/_logs/llm_audit_log.jsonl"
        )
        self.audit_logger = AuditLogger(audit_log_path or default_audit_path)

    def run(
        self,
        tasks: list[dict[str, Any]],
        dest_dir: Path,
    ) -> LlmPipelineResult:
        """执行完整蒸馏流水线

        Args:
            tasks: 任务列表
            dest_dir: 目标存储目录

        Returns:
            流水线执行结果
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # 阶段 1: 主代理调度提取+验证
        try:
            master_result = self.master.run(tasks)
        except Exception as e:
            error_msg = f"主代理调度失败: {e}"
            logger.error(error_msg)
            return LlmPipelineResult(success=False, errors=[error_msg])

        # 阶段 2: 存储通过验证的数据
        results = master_result.get("results", [])
        total_extracted = master_result["total_tasks"]
        total_validated = 0
        total_rejected = 0
        errors: list[str] = []

        for result in results:
            if result.success and result.data:
                # 按 indicator_id 组织存储
                indicator_id = result.data.get("indicator_id", "unknown")
                output_path = dest_dir / f"{indicator_id}_distilled.json"
                try:
                    # 追加模式写入（同一指标可能多文献）
                    existing = []
                    if output_path.exists():
                        existing = json.loads(output_path.read_text(encoding="utf-8"))
                        if not isinstance(existing, list):
                            existing = [existing]
                    existing.append(result.data)
                    output_path.write_text(
                        json.dumps(existing, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    total_validated += 1
                    # 记录审计日志
                    self.audit_logger.log(
                        operation="llm_distill",
                        target=str(output_path),
                        success=True,
                        confidence=result.confidence,
                        model=result.model_used,
                    )
                except Exception as e:
                    errors.append(f"存储失败 {indicator_id}: {e}")
            else:
                total_rejected += 1
                self.audit_logger.log(
                    operation="llm_distill",
                    target=result.task_id,
                    success=False,
                    errors=result.errors,
                )

        # 阶段 3: 体量审计
        audit = self.audit_size(dest_dir)
        if not audit["within_limit"]:
            errors.append(
                f"体量超限: {audit['total_bytes']} > {self.max_size_bytes}"
            )

        success = total_rejected == 0 and audit["within_limit"] and len(errors) == 0
        logger.info(
            "Layer C 流水线完成: extracted=%d, validated=%d, rejected=%d, tokens=%d",
            total_extracted, total_validated, total_rejected,
            master_result["total_tokens_consumed"],
        )

        return LlmPipelineResult(
            success=success,
            total_extracted=total_extracted,
            total_validated=total_validated,
            total_rejected=total_rejected,
            total_tokens_consumed=master_result["total_tokens_consumed"],
            errors=errors,
        )

    def audit_size(self, dest_dir: Path) -> dict[str, Any]:
        """体量审计

        Returns:
            含 total_bytes, total_mb, limit_mb, within_limit 的字典
        """
        dest_dir = Path(dest_dir)
        total_bytes = 0
        if dest_dir.exists():
            for file_path in dest_dir.rglob("*"):
                if file_path.is_file():
                    total_bytes += file_path.stat().st_size

        total_mb = total_bytes / (1024 * 1024)
        limit_mb = self.max_size_bytes / (1024 * 1024)
        within_limit = total_bytes <= self.max_size_bytes

        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_mb, 2),
            "limit_mb": limit_mb,
            "within_limit": within_limit,
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_llm_pipeline.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（148 + 4 = 152）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/llm_pipeline.py tests/llm/test_llm_pipeline.py
git commit -m "feat: 添加 LlmPipeline 端到端流水线（主代理调度→提取→验证→存储→审计）"
```

---

### Task 10: LlmMetadataGenerator（Layer C 三层元数据）

**Files:**
- Create: `e:\Health_man\scripts\llm\llm_metadata_generator.py`
- Test: `e:\Health_man\tests\llm\test_llm_metadata.py`

**Interfaces:**
- Consumes: `QualityReport`（Phase 1-2）、`LlmPipelineResult`（Task 9）
- Produces: `LlmMetadataGenerator` 类；方法签名：
  - `generate_l0(pipeline_result: LlmPipelineResult, output_path: Path | None) -> dict`
  - `generate_l1(data: list[dict], output_path: Path | None) -> dict`
  - `generate_l2(pipeline_result: LlmPipelineResult, output_path: Path | None) -> str`

- [ ] **Step 1: 写失败测试**

```python
"""LlmMetadataGenerator 单元测试

验证 Layer C 三层元数据生成。
"""
import json
from pathlib import Path

from scripts.llm.llm_metadata_generator import LlmMetadataGenerator
from scripts.llm.llm_pipeline import LlmPipelineResult


def make_test_pipeline_result() -> LlmPipelineResult:
    """创建测试用流水线结果"""
    return LlmPipelineResult(
        success=True,
        total_extracted=10,
        total_validated=8,
        total_rejected=2,
        total_tokens_consumed=5000,
    )


class TestLlmMetadataGenerator:
    """LlmMetadataGenerator 测试套件"""

    def test_generate_l0_returns_dict_with_llm_fields(self, tmp_path):
        """测试 L0 包含 LLM 特定字段"""
        gen = LlmMetadataGenerator()
        result = make_test_pipeline_result()
        l0 = gen.generate_l0(result, output_path=tmp_path / "l0.json")
        assert l0["dataset_id"] == "C_llm_distilled"
        assert "extraction_method" in l0
        assert l0["total_extracted"] == 10
        assert l0["total_validated"] == 8
        assert (tmp_path / "l0.json").exists()

    def test_generate_l1_returns_field_dict(self, tmp_path):
        """测试 L1 返回字段字典"""
        gen = LlmMetadataGenerator()
        data = [
            {"indicator_id": "IND-01", "name_cn": "体脂率", "unit": "%"},
            {"indicator_id": "IND-01", "name_cn": "体脂率", "unit": "%"},
        ]
        l1 = gen.generate_l1(data, output_path=tmp_path / "l1.json")
        assert "fields" in l1
        assert l1["row_count"] == 2
        assert (tmp_path / "l1.json").exists()

    def test_generate_l2_returns_markdown(self, tmp_path):
        """测试 L2 返回 Markdown"""
        gen = LlmMetadataGenerator()
        result = make_test_pipeline_result()
        l2 = gen.generate_l2(result, output_path=tmp_path / "l2.md")
        assert isinstance(l2, str)
        assert "C_llm_distilled" in l2
        assert (tmp_path / "l2.md").exists()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/llm/test_llm_metadata.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 LlmMetadataGenerator**

```python
"""Layer C LLM 蒸馏元数据生成器

复用 Phase 1-2 的 MetadataGenerator 模式，
适配 Layer C LLM 蒸馏数据的特殊需求（模型信息、token 消耗、置信度等）。

生成三层元数据：
- L0: 数据集卡片（含模型信息、提取统计）
- L1: 字段字典（含 LLM 提取字段统计）
- L2: 使用说明（含已知局限、适用场景）
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.llm.llm_pipeline import LlmPipelineResult

logger = logging.getLogger(__name__)


class LlmMetadataGenerator:
    """Layer C LLM 蒸馏元数据生成器"""

    def generate_l0(
        self,
        pipeline_result: LlmPipelineResult,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """生成 L0 数据集卡片

        Args:
            pipeline_result: 流水线执行结果
            output_path: 输出文件路径（可选）

        Returns:
            L0 数据集卡片字典
        """
        l0 = {
            "dataset_id": "C_llm_distilled",
            "source_url": "LLM API (GLM-4-Flash / Qwen / DeepSeek)",
            "license": "内部使用，参考各模型服务条款",
            "region": "CN",
            "extraction_method": "LLM 蒸馏（主从多代理协作）",
            "total_extracted": pipeline_result.total_extracted,
            "total_validated": pipeline_result.total_validated,
            "total_rejected": pipeline_result.total_rejected,
            "total_tokens_consumed": pipeline_result.total_tokens_consumed,
            "success": pipeline_result.success,
            "generated_at": datetime.now().isoformat(),
        }
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(l0, f, ensure_ascii=False, indent=2)
            logger.info("L0 元数据已写入: %s", output_path)
        return l0

    def generate_l1(
        self,
        data: list[dict[str, Any]],
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """生成 L1 字段字典

        Args:
            data: 蒸馏数据列表
            output_path: 输出文件路径（可选）

        Returns:
            L1 字段字典
        """
        fields = []
        if data:
            for key in data[0].keys():
                values = [d.get(key) for d in data if d.get(key) is not None]
                fields.append({
                    "name": key,
                    "type": str(type(values[0]).__name__) if values else "null",
                    "non_null_count": len(values),
                    "missing_rate": round(1 - len(values) / len(data), 4),
                })
        l1 = {"fields": fields, "row_count": len(data)}
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(l1, f, ensure_ascii=False, indent=2)
            logger.info("L1 字段字典已写入: %s", output_path)
        return l1

    def generate_l2(
        self,
        pipeline_result: LlmPipelineResult,
        output_path: Path | None = None,
    ) -> str:
        """生成 L2 使用说明（Markdown）

        Args:
            pipeline_result: 流水线执行结果
            output_path: 输出文件路径（可选）

        Returns:
            L2 Markdown 文本
        """
        content = f"""# C_llm_distilled 使用说明

## 数据来源
- LLM API 蒸馏（GLM-4-Flash 主力，Qwen/DeepSeek 备选）
- 主从多代理协作提取

## 适用场景
- 补齐 Layer A+B 未覆盖的难提取指标
- 文献中非结构化数据的结构化提取
- 参考范围对标（非配对精度验证）

## 不适用场景
- 临床诊断
- 精度验证（LLM 提取存在幻觉风险）
- 个体化评估

## 提取统计
- 总提取数: {pipeline_result.total_extracted}
- 验证通过: {pipeline_result.total_validated}
- 被拒绝: {pipeline_result.total_rejected}
- Token 消耗: {pipeline_result.total_tokens_consumed}

## 已知局限
- LLM 提取可能存在幻觉，已通过双层验证+人工抽检控制
- confidence <0.5 的数据已被自动拒绝
- 0.5 ≤ confidence <0.7 的数据需人工复核

## 生成时间
{datetime.now().isoformat()}
"""
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("L2 使用说明已写入: %s", output_path)
        return content
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/llm/test_llm_metadata.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS（152 + 3 = 155）

- [ ] **Step 6: 提交**

```powershell
git add scripts/llm/llm_metadata_generator.py tests/llm/test_llm_metadata.py
git commit -m "feat: 添加 LlmMetadataGenerator（Layer C 三层元数据）"
```

---

## Part C: 时间节点、资源分配与交付成果

### C1. 时间节点

| 日期 | 阶段 | 任务 | 预期产出 | 验收标准 |
|------|------|------|---------|---------|
| D9 上午 | Phase 4 启动 | Task 1-2: ModelAdapter + GlmAdapter | 2 模块 + 8 测试 | 130 测试通过 |
| D9 下午 | Phase 4 基础 | Task 3-4: PromptTemplateLibrary + DualLayerValidator | 2 模块 + 8 测试 | 138 测试通过 |
| D10 上午 | Phase 4 核心 | Task 5-7: TaskTypes + ExtractionWorker + ValidationWorker | 3 模块 + 7 测试 | 145 测试通过 |
| D10 下午 | Phase 4 集成 | Task 8-9: MasterOrchestrator + LlmPipeline | 2 模块 + 7 测试 | 152 测试通过 |
| D11 上午 | Phase 4 收尾 | Task 10: LlmMetadataGenerator | 1 模块 + 3 测试 | 155 测试通过 |
| D11 下午 | Phase 4 审查 | 最终全分支审查 + 合并 main | review package | READY FOR MERGE |

### C2. 资源分配

| 资源 | 分配 | 说明 |
|------|------|------|
| 开发者 | 1 人（主会话 + SDD 子代理） | implementer/reviewer/fixer |
| GPU | 无需 | API 调用，无本地推理 |
| 存储 | ~50MB | C_llm_distilled/ 目录 |
| API 配额 | GLM-4-Flash（免费）+ Qwen（100万 tokens） | 预估消耗 59 万 tokens |
| 成本 | ¥0 | 全程免费额度 |

### C3. 责任分工

| 角色 | 职责 | 分配 |
|------|------|------|
| 主会话 | 计划执行、子代理调度、决策 | 开发者 |
| Implementer 子代理 | TDD 任务实施 | SDD 自动 |
| Reviewer 子代理 | 代码审查 | SDD 自动 |
| Fixer 子代理 | 修复审查问题 | SDD 自动 |
| 人工验证 | 20% 抽检 + 金标准对照 | 开发者 |

### C4. 阶段性交付成果清单

| 交付物 | Task | 说明 | 验收标准 |
|--------|------|------|---------|
| `scripts/llm/model_adapter.py` | T1 | ModelAdapter 抽象基类 | 3 抽象方法 |
| `scripts/llm/glm_adapter.py` | T2 | GLM-4-Flash 适配器 | 含限流/熔断/重试/审计 |
| `scripts/llm/prompt_templates.py` | T3 | 提示词模板库 | load/render/list |
| `scripts/llm/validator.py` | T4 | 双层验证器 | 结构化+语义 |
| `scripts/llm/task_types.py` | T5 | 通信数据结构 | TaskBrief+TaskResult |
| `scripts/llm/workers.py` | T6-7 | 提取+验证子代理 | ExtractionWorker+ValidationWorker |
| `scripts/llm/master_orchestrator.py` | T8 | 主代理 | dispatch+run |
| `scripts/llm/llm_pipeline.py` | T9 | 端到端流水线 | run+audit_size |
| `scripts/llm/llm_metadata_generator.py` | T10 | 三层元数据 | L0/L1/L2 |
| `C_llm_distilled/_metadata/prompt_templates/` | T3 | 提示词模板文件 | extract_reference_range.txt |
| `C_llm_distilled/_logs/llm_audit_log.jsonl` | T9 | 审计日志 | 哈希链防篡改 |
| 测试套件 | T1-T10 | 10 个测试文件 | 33 个新测试（122→155） |

### C5. 里程碑

| 里程碑 | 日期 | 交付物 | 验收标准 |
|--------|------|--------|---------|
| **M4-1** | D9 | 基础模块完成 | ModelAdapter + GlmAdapter + PromptLibrary + Validator |
| **M4-2** | D10 | 核心系统完成 | Workers + MasterOrchestrator + Pipeline |
| **M4-3** | D11 | Phase 4 完成 | 155 测试通过 + 最终审查 READY FOR MERGE |

---

## Self-Review

### 1. Spec 覆盖检查

| Spec 章节 | 覆盖任务 | 状态 |
|-----------|---------|------|
| §7.1 模型选型 | Task 2 (GlmAdapter) | ✅ GLM-4-Flash 主力 |
| §7.2 强自动化集成架构 | Task 8 (MasterOrchestrator) + Task 9 (Pipeline) | ✅ 主从架构 |
| §7.3 上下文工程 | Task 3 (PromptTemplateLibrary) | ✅ 模板库 |
| §7.4 系统工程支持 | Task 2 (限流/熔断/重试/审计) + Task 9 (Pipeline) | ✅ 复用工具链 |
| §7.5 兼容性与可切换性 | Task 1 (ModelAdapter ABC) | ✅ 可切换 |
| §7.6 安全规范 | Task 2 (CredentialManager) + Task 4 (验证器) | ✅ 双层验证+凭证管理 |
| §7.7 异常处理 | Task 2 (retry+breaker) + Task 6 (错误处理) | ✅ 完整 |
| §7.9 质量保障 | Task 4 (DualLayerValidator) + Task 7 (ValidationWorker) | ✅ 双层验证 |
| §7.11 审计日志 | Task 9 (AuditLogger 复用) | ✅ 哈希链 |
| §8.2 Phase 4 步骤 | Task 1-10 全覆盖 | ✅ 全步骤 |

### 2. Placeholder 扫描

- ✅ 无 "TBD"/"TODO"/"implement later"
- ✅ 所有步骤含完整代码
- ✅ 所有测试含实际断言
- ✅ 无 "similar to Task N" 引用

### 3. 类型一致性

| 接口 | 定义位置 | 使用位置 | 一致性 |
|------|---------|---------|--------|
| `ModelAdapter.chat()` | Task 1 | Task 2, 6, 8 | ✅ |
| `ModelAdapter.health_check()` | Task 1 | Task 2 | ✅ |
| `ModelAdapter.get_model_info()` | Task 1 | Task 2, 6 | ✅ |
| `PromptTemplateLibrary.render()` | Task 3 | Task 6 | ✅ |
| `DualLayerValidator.validate()` | Task 4 | Task 7 | ✅ |
| `ValidationResult` dataclass | Task 4 | Task 7 | ✅ |
| `TaskBrief` dataclass | Task 5 | Task 6, 8 | ✅ |
| `TaskResult` dataclass | Task 5 | Task 6, 7, 8, 9 | ✅ |
| `ExtractionWorker.execute()` | Task 6 | Task 8 | ✅ |
| `ValidationWorker.execute()` | Task 7 | Task 8 | ✅ |
| `MasterOrchestrator.run()` | Task 8 | Task 9 | ✅ |
| `LlmPipelineResult` dataclass | Task 9 | Task 10 | ✅ |

---

**计划完成。** 10 个 TDD 任务，预期 33 个新测试（122→155），10 个新模块，3 天工期（D9-D11）。
