# 子代理架构直接数据抓取方案设计

> **日期:** 2026-07-13
> **状态:** 已批准，待实现
> **作者:** 开发工程师

---

## 1. 概述

### 1.1 目标

设计并实现一种基于 asyncio 协程的子代理架构，用于直接抓取医学领域知识数据。系统覆盖三类数据源（公开 API、中文学术数据库、医学网站/指南），具备动态代理管理、负载均衡、健康监控和自动替换能力。

### 1.2 设计约束

| 约束 | 值 | 来源 |
|------|-----|------|
| 并发模型 | asyncio 协程（单进程） | 用户确认 |
| 最大代理数 | 20 | 配置可调 |
| 资源开销目标 | < 100MB 内存 | 用户要求"低成本" |
| 新增依赖 | aiohttp、beautifulsoup4、lxml | 轻量库 |
| 复用组件 | CircuitBreaker、TokenBucketLimiter、AuditLogger、CredentialManager | 现有代码 |
| Python 版本 | >= 3.12 | 项目约定 |
| 合规要求 | 遵守 robots.txt、PIPL 合规、不上传 PII | 项目规范 |

### 1.3 不包含（YAGNI）

- 不实现 JavaScript 渲染（Playwright/Selenium）——后续按需集成
- 不实现分布式多进程——单进程 asyncio 足够
- 不实现 CAPTCHA 自动识别——标记失败后人工处理
- 不实现代理 IP 池——当前单 IP + 限流即可满足需求

---

## 2. 架构

### 2.1 架构图

```
                    ┌─────────────────────────────────┐
                    │         AgentManager            │
                    │  (动态创建/销毁/替换 子代理)      │
                    ├─────────┬───────────┬───────────┤
                    │         │           │           │
               ┌────▼────┐ ┌──▼───┐ ┌────▼────┐ ┌────▼────┐
               │Agent 1  │ │Agent2│ │Agent 3  │ │Agent N  │
               │PubMed   │ │CNKI  │ │医学会   │ │WHO      │
               │API      │ │HTML  │ │HTML     │ │API      │
               └────┬────┘ └──┬───┘ └────┬────┘ └────┬────┘
                    │         │           │           │
         ┌──────────┴─────────┴───────────┴───────────┤
         │                                          │
    ┌────▼─────┐    ┌──────────────┐    ┌───────────▼──────┐
    │LoadBalancer   │HealthMonitor │    │ResultAggregator  │
    │加权轮询   │    │30s 心跳检测  │    │去重 + 质量评分   │
    │跳过熔断者 │    │自动替换      │    │路由到 B_literature│
    └──────────┘    └──────────────┘    └──────────────────┘
```

### 2.2 数据流

```
用户提交任务列表
  │
  ▼
AgentManager.submit_task(task)
  │
  ▼
LoadBalancer.select_agent(task)
  │ ── 过滤熔断代理 (CircuitBreaker.state == OPEN)
  │ ── 加权选择健康代理 (health_score 加权随机)
  ▼
ScrapeAgent.execute(task)
  │ ── 熔断检查 (CircuitBreaker.can_call)
  │ ── 限流获取 (TokenBucketLimiter.acquire)
  │ ── HTTP 抓取 (aiohttp，带超时和重试)
  │ ── 内容解析 (BeautifulSoup4 HTML / json API)
  │ ── 记录健康 (record_success/failure)
  ▼
ResultAggregator.submit(result)
  │ ── URL 去重 (SHA256 + LRU 缓存)
  │ ── 质量评分 (字段完整率 + 数值合理性)
  │ ── 路由存储 (B_literature/{source_name}/)
  │ ── 审计日志 (AuditLogger.log)
  ▼
存储到 B_literature/{source_name}/
```

---

## 3. 组件详细设计

### 3.1 数据结构

```python
@dataclass
class AgentHealth:
    """代理健康状态"""
    health_score: float = 1.0      # 综合健康分 0.0-1.0
    success_rate: float = 1.0      # 最近 20 次成功率
    avg_latency_ms: float = 0.0    # 平均延迟（毫秒）
    error_count: int = 0            # 连续错误次数
    last_active: float = 0.0        # 最后活跃时间戳（time.monotonic）
    state: str = "healthy"           # healthy / degraded / unhealthy

@dataclass
class ScrapeTask:
    """抓取任务"""
    task_id: str                    # UUID
    source_type: str                # "api" | "html"
    url: str                        # 目标 URL
    parse_rules: dict               # 解析规则
    priority: int = 0               # 0=普通, 1=高, 2=紧急
    metadata: dict = field(default_factory=dict)  # 附加参数

@dataclass
class ScrapeResult:
    """抓取结果"""
    task_id: str
    success: bool
    data: dict | None               # 解析后的结构化数据
    raw_content: str = ""            # 原始响应内容
    url: str = ""
    agent_id: str = ""
    timestamp: str = ""             # ISO 8601
    error: str = ""
    latency_ms: float = 0.0
    quality_score: float = 0.0       # ResultAggregator 填充
```

### 3.2 ScrapeAgent

**职责：** 单个子代理，负责对一个数据源执行 HTTP 抓取和内容解析。

**文件：** `scripts/scraping/scrape_agent.py`

```python
class ScrapeAgent:
    """子代理：独立抓取 + 解析 + 容错

    每个代理绑定一个数据源配置，拥有独立的 CircuitBreaker 和
    TokenBucketLimiter，互不影响。
    """

    def __init__(
        self,
        agent_id: str,
        source_config: dict,              # 数据源配置
        circuit_breaker: CircuitBreaker,  # 独立熔断器
        rate_limiter: TokenBucketLimiter,  # 独立限流器
        audit_logger: AuditLogger | None = None,
    ):
        self.agent_id = agent_id
        self.source_config = source_config
        self.circuit_breaker = circuit_breaker
        self.rate_limiter = rate_limiter
        self.audit_logger = audit_logger
        self.health = AgentHealth()
        self._latency_history: deque[float] = deque(maxlen=20)  # 最近20次延迟
        self._success_history: deque[bool] = deque(maxlen=20)   # 最近20次成功/失败
        self._http_session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话（懒加载，复用连接池）"""

    async def fetch(self, url: str, params: dict = None) -> tuple[str, float]:
        """HTTP 请求获取原始内容

        Args:
            url: 目标 URL
            params: 查询参数

        Returns:
            (响应内容, 延迟毫秒)

        Raises:
            CircuitOpenError: 熔断器开启时
            RateLimitError: 限流器拒绝时
            aiohttp.ClientError: 网络错误时
        """

    async def parse(self, content: str, parse_rules: dict) -> dict:
        """解析内容

        根据 source_config["parser"] 类型选择解析器：
        - "json": json.loads(content)
        - "pubmed_xml": XML 解析（ElementTree）
        - "html": BeautifulSoup4 解析
        - "cnki_html": CNKI 专用 HTML 解析
        - "guideline_html": 医学指南 HTML 解析

        Args:
            content: 原始内容
            parse_rules: 解析规则（CSS 选择器 / JSON 路径）

        Returns:
            解析后的结构化字典
        """

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        """执行完整抓取任务

        流程：
        1. 熔断检查 → CircuitBreaker.can_call()
        2. 限流获取 → TokenBucketLimiter.acquire()
        3. HTTP 抓取 → self.fetch(task.url)
        4. 内容解析 → self.parse(content, task.parse_rules)
        5. 健康记录 → self.record_success(latency_ms)
        6. 返回 ScrapeResult

        异常处理：
        - 熔断开启 → 返回失败结果，不计数
        - 限流拒绝 → 短暂等待后重试（最多 3 次）
        - 网络错误 → record_failure + CircuitBreaker.record_failure
        - 解析错误 → record_failure（但不算网络故障）
        """

    def record_success(self, latency_ms: float) -> None:
        """记录成功：更新延迟历史、成功率、重置错误计数、重算健康分"""

    def record_failure(self, error: str) -> None:
        """记录失败：更新错误计数、CircuitBreaker.record_failure、重算健康分"""

    def _recalculate_health(self) -> None:
        """重算健康分

        health_score = 0.4 × success_rate + 0.3 × (1 - normalized_latency) + 0.3 × (1 - error_rate)

        状态阈值：
        - health_score >= 0.7 → healthy
        - 0.3 <= health_score < 0.7 → degraded
        - health_score < 0.3 → unhealthy
        """

    def get_health(self) -> AgentHealth:
        """获取当前健康状态"""

    async def close(self) -> None:
        """关闭 HTTP 会话，释放资源"""
```

### 3.3 AgentManager

**职责：** 代理生命周期管理（创建/销毁/替换）、任务分发入口。

**文件：** `scripts/scraping/agent_manager.py`

```python
class AgentManager:
    """代理池管理器

    管理所有 ScrapeAgent 的生命周期，提供任务提交入口。
    内部持有 LoadBalancer 和 HealthMonitor 实例。
    """

    def __init__(
        self,
        max_agents: int = 20,
        health_check_interval: float = 30.0,
        config_path: Path = None,         # 数据源配置文件
        audit_logger: AuditLogger = None,
        dest_dir: Path = None,             # 结果存储目录
    ):
        self.max_agents = max_agents
        self.agents: dict[str, ScrapeAgent] = {}
        self.load_balancer = LoadBalancer(self.agents)
        self.health_monitor = HealthMonitor(self, health_check_interval)
        self.result_aggregator = ResultAggregator(dest_dir, audit_logger)
        self.audit_logger = audit_logger
        self._agent_counter = 0

    async def initialize(self) -> None:
        """从配置文件加载所有启用的数据源，创建对应代理

        读取 config_path YAML 配置，为每个 enabled=true 的数据源
        创建 ScrapeAgent + 独立 CircuitBreaker + 独立 TokenBucketLimiter
        """

    async def create_agent(self, source_config: dict) -> str:
        """动态创建代理

        1. 检查代理池是否已满（len < max_agents）
        2. 生成 agent_id（格式：{source_name}_{counter}）
        3. 创建 CircuitBreaker 和 TokenBucketLimiter（从配置参数构造）
        4. 创建 ScrapeAgent 实例
        5. 注册到 self.agents 和 LoadBalancer

        Returns:
            agent_id
        """

    async def destroy_agent(self, agent_id: str) -> None:
        """销毁代理：关闭 HTTP 会话、从 LoadBalancer 移除、从字典删除"""

    async def replace_agent(self, agent_id: str) -> str:
        """替换不健康代理

        1. 保存旧代理的 source_config
        2. 销毁旧代理 (destroy_agent)
        3. 用相同配置创建新代理 (create_agent)
        4. 记录审计日志（含旧 agent_id 和新 agent_id）

        Returns:
            新 agent_id
        """

    async def submit_task(self, task: ScrapeTask) -> ScrapeResult:
        """提交任务到代理池

        1. LoadBalancer.select_agent(task) 选择代理
        2. 代理执行 task
        3. ResultAggregator.submit(result) 处理结果
        4. 返回 ScrapeResult

        若无可用代理（全部熔断）→ 返回失败结果
        """

    async def submit_batch(self, tasks: list[ScrapeTask]) -> list[ScrapeResult]:
        """批量提交任务（asyncio.gather 并行执行）"""

    def get_pool_status(self) -> dict:
        """代理池状态概览

        Returns:
            {
                "total_agents": int,
                "healthy": int,
                "degraded": int,
                "unhealthy": int,
                "agents": [
                    {"agent_id": str, "source": str, "health_score": float, "state": str}
                ]
            }
        """

    async def shutdown(self) -> None:
        """关闭所有代理、停止健康监控、关闭 HTTP 会话"""
```

### 3.4 LoadBalancer

**职责：** 加权轮询选择最优代理执行任务。

**文件：** `scripts/scraping/load_balancer.py`

```python
class LoadBalancer:
    """加权轮询负载均衡器

    算法：
    1. 过滤掉 CircuitBreaker.state == OPEN 的代理
    2. 过滤掉 health.state == "unhealthy" 的代理
    3. 计算每个代理权重 = health_score
    4. 加权随机选择（numpy.random.choice 风格）
    5. 若任务有 source_type 要求，只从匹配的代理中选择
    """

    def __init__(self, agents: dict[str, ScrapeAgent]):
        self.agents = agents

    def select_agent(self, task: ScrapeTask) -> ScrapeAgent | None:
        """选择最优代理

        Args:
            task: 抓取任务（含 source_type 用于筛选）

        Returns:
            被选中的 ScrapeAgent，或 None（无可用代理）
        """

    def update_weights(self) -> None:
        """重新计算所有代理权重（基于最新健康分）"""

    def add_agent(self, agent_id: str, agent: ScrapeAgent) -> None:
        """添加新代理到负载均衡器"""

    def remove_agent(self, agent_id: str) -> None:
        """从负载均衡器移除代理"""

    def get_available_count(self) -> int:
        """获取当前可用代理数（非熔断 + 非 unhealthy）"""
```

### 3.5 HealthMonitor

**职责：** 后台协程，周期性检测代理健康，触发自动替换。

**文件：** `scripts/scraping/health_monitor.py`

```python
class HealthMonitor:
    """后台健康监控协程

    每 check_interval 秒执行一次全量检测：
    1. 遍历所有代理，发送心跳请求
    2. 更新健康分和状态
    3. 连续 unhealthy_threshold 次不健康 → 触发 replace_agent
    4. 超过 stale_timeout 无响应 → 立即替换
    """

    def __init__(
        self,
        agent_manager: AgentManager,
        check_interval: float = 30.0,
        unhealthy_threshold: int = 3,
        stale_timeout: float = 300.0,
    ):
        self.agent_manager = agent_manager
        self.check_interval = check_interval
        self.unhealthy_threshold = unhealthy_threshold
        self.stale_timeout = stale_timeout
        self._unhealthy_counts: dict[str, int] = {}  # agent_id → 连续不健康次数
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动后台监控协程"""
        self._running = True
        self._task = asyncio.create_task(self._run_periodic_check())

    async def stop(self) -> None:
        """停止监控"""
        self._running = False
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _run_periodic_check(self) -> None:
        """周期性检测循环"""
        while self._running:
            await self._check_all_agents()
            await asyncio.sleep(self.check_interval)

    async def _check_all_agents(self) -> None:
        """检测所有代理"""
        for agent_id, agent in list(self.agent_manager.agents.items()):
            try:
                health = await self._check_agent(agent)
                self._update_unhealthy_count(agent_id, health)
                await self._maybe_replace(agent_id)
            except Exception as e:
                logger.warning("健康检测异常 %s: %s", agent_id, e)

    async def _check_agent(self, agent: ScrapeAgent) -> AgentHealth:
        """检测单个代理

        1. 检查 last_active 是否超过 stale_timeout
        2. 发送心跳请求（HEAD 请求到 base_url）
        3. 更新健康分
        """

    def _update_unhealthy_count(self, agent_id: str, health: AgentHealth) -> None:
        """更新连续不健康计数"""
        if health.state == "unhealthy":
            self._unhealthy_counts[agent_id] = self._unhealthy_counts.get(agent_id, 0) + 1
        else:
            self._unhealthy_counts[agent_id] = 0

    async def _maybe_replace(self, agent_id: str) -> None:
        """判断是否需要替换代理"""
        count = self._unhealthy_counts.get(agent_id, 0)
        agent = self.agent_manager.agents.get(agent_id)
        if not agent:
            return

        # 条件1：连续不健康次数超阈值
        if count >= self.unhealthy_threshold:
            logger.warning("代理 %s 连续 %d 次不健康，触发替换", agent_id, count)
            new_id = await self.agent_manager.replace_agent(agent_id)
            self._unhealthy_counts.pop(agent_id, None)
            self._unhealthy_counts[new_id] = 0
            return

        # 条件2：超过 stale_timeout 无响应
        import time
        if time.monotonic() - agent.health.last_active > self.stale_timeout:
            logger.warning("代理 %s 超过 %.0fs 无响应，立即替换", agent_id, self.stale_timeout)
            new_id = await self.agent_manager.replace_agent(agent_id)
            self._unhealthy_counts.pop(agent_id, None)
            self._unhealthy_counts[new_id] = 0
```

### 3.6 ResultAggregator

**职责：** 结果去重、质量评分、路由存储。

**文件：** `scripts/scraping/result_aggregator.py`

```python
class ResultAggregator:
    """结果聚合器

    对 ScrapeAgent 返回的结果进行去重、质量评分和路由存储。
    """

    def __init__(
        self,
        dest_dir: Path,
        audit_logger: AuditLogger = None,
        dedup_cache_size: int = 10000,
    ):
        self.dest_dir = dest_dir
        self.audit_logger = audit_logger
        self._dedup_cache: OrderedDict[str, None] = OrderedDict()  # LRU 去重缓存
        self._dedup_cache_size = dedup_cache_size
        self._stats = {
            "total_submitted": 0,
            "total_deduplicated": 0,
            "total_stored": 0,
            "avg_quality": 0.0,
        }

    async def submit(self, result: ScrapeResult) -> Path | None:
        """提交结果

        1. URL 哈希去重（若重复返回 None）
        2. 质量评分
        3. 路由存储
        4. 审计日志
        5. 更新统计

        Returns:
            存储路径，或 None（重复/失败）
        """

    def _url_hash(self, url: str) -> str:
        """URL 规范化 + SHA256 哈希

        规范化：转小写、去 fragment、排序查询参数
        """

    def _is_duplicate(self, url_hash: str) -> bool:
        """检查是否重复（LRU 缓存）"""

    def _score_quality(self, data: dict) -> float:
        """质量评分

        score = field_completeness × 0.6 + value_validity × 0.4

        field_completeness: 必填字段填充率
        value_validity: 数值字段在合理范围内的比例
        """

    def _route_storage(self, result: ScrapeResult) -> Path:
        """路由存储

        按数据源类型路由：
        - API XML → B_literature/{source_name}/abstracts/{filename}.xml
        - HTML → B_literature/{source_name}/pages/{filename}.html
        - JSON → B_literature/{source_name}/data/{filename}.json
        """

    def get_statistics(self) -> dict:
        """获取统计信息"""
```

### 3.7 配置模块

**文件：** `scripts/scraping/config.py`

```python
@dataclass
class SourceConfig:
    """数据源配置"""
    name: str                         # 数据源名称
    source_type: str                  # "api" | "html"
    base_url: str                     # 基础 URL
    rate_limit_capacity: int          # 令牌桶容量
    rate_limit_refill: float          # 令牌桶填充速率
    circuit_failure_threshold: int   # 熔断失败阈值
    circuit_recovery_timeout: float   # 熔断恢复超时
    parser: str                       # 解析器名称
    headers: dict                     # HTTP 头
    enabled: bool = True              # 是否启用

@dataclass
class PoolConfig:
    """代理池配置"""
    max_agents: int = 20
    health_check_interval: float = 30.0
    unhealthy_threshold: int = 3
    stale_timeout: float = 300.0

def load_config(config_path: Path) -> tuple[list[SourceConfig], PoolConfig]:
    """从 YAML 文件加载配置"""
```

**配置文件：** `config/scrape_sources.yaml`

```yaml
sources:
  - name: pubmed
    type: api
    base_url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
    rate_limit:
      capacity: 3
      refill_rate: 3.0
    circuit_breaker:
      failure_threshold: 5
      recovery_timeout: 30.0
    parser: pubmed_xml
    enabled: true

  - name: cnki
    type: html
    base_url: https://kns.cnki.net/
    rate_limit:
      capacity: 1
      refill_rate: 0.5
    circuit_breaker:
      failure_threshold: 3
      recovery_timeout: 60.0
    parser: cnki_html
    headers:
      User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      Accept-Language: "zh-CN,zh;q=0.9"
    enabled: true

  - name: medical_guideline
    type: html
    base_url: https://www.cma.org.cn/
    rate_limit:
      capacity: 2
      refill_rate: 1.0
    circuit_breaker:
      failure_threshold: 3
      recovery_timeout: 45.0
    parser: guideline_html
    enabled: true

pool:
  max_agents: 20
  health_check_interval: 30.0
  unhealthy_threshold: 3
  stale_timeout: 300.0
```

---

## 4. 文件结构

```
scripts/scraping/
├── __init__.py
├── scrape_agent.py       # ScrapeAgent — 单代理抓取+解析
├── agent_manager.py       # AgentManager — 生命周期管理+代理池
├── load_balancer.py       # LoadBalancer — 加权轮询分发
├── health_monitor.py      # HealthMonitor — 心跳检测+自动替换
├── result_aggregator.py   # ResultAggregator — 去重+质量评分+存储
└── config.py              # 配置加载

config/
└── scrape_sources.yaml    # 数据源与代理池配置

tests/scraping/
├── __init__.py
├── conftest.py             # 测试 fixtures
├── test_scrape_agent.py    # ScrapeAgent 测试
├── test_agent_manager.py   # AgentManager 测试
├── test_load_balancer.py   # LoadBalancer 测试
├── test_health_monitor.py  # HealthMonitor 测试
└── test_result_aggregator.py  # ResultAggregator 测试
```

---

## 5. 健康分算法

```
health_score = 0.4 × success_rate + 0.3 × (1 - normalized_latency) + 0.3 × (1 - error_rate)

参数定义：
- success_rate = 最近 20 次成功数 / 20
- normalized_latency = min(avg_latency_ms / 5000, 1.0)  # 5秒归一化
- error_rate = min(consecutive_errors / 10, 1.0)

状态阈值：
- health_score >= 0.7 → healthy（正常权重）
- 0.3 <= health_score < 0.7 → degraded（权重 ×0.5）
- health_score < 0.3 → unhealthy（权重 0，触发替换评估）
```

---

## 6. 反爬应对策略

| 策略 | 实现方式 | 适用场景 |
|------|---------|---------|
| 请求间隔 | TokenBucketLimiter（每数据源独立配置） | 所有数据源 |
| User-Agent | 每个数据源配置独立 headers | HTML 数据源 |
| 请求超时 | aiohttp timeout=30s | 所有数据源 |
| 熔断保护 | CircuitBreaker（3 次失败 → 熔断 30-60s） | 所有数据源 |
| 重试退避 | 指数退避（1s/2s/4s，最多 3 次） | 网络错误 |
| robots.txt | 启动时检查目标站 robots.txt | HTML 数据源 |
| 响应码检测 | 429 → 暂停 60s；403 → 标记禁用 | 所有数据源 |

---

## 7. 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 网络超时 | 重试 3 次（指数退避），失败后 record_failure |
| HTTP 429 | 暂停该代理 60 秒（CircuitBreaker 模拟） |
| HTTP 403 | 标记代理为 unhealthy，触发替换 |
| HTML 解析失败 | 返回 raw_content，quality_score=0 |
| JSON 解析失败 | 返回 raw_content，quality_score=0 |
| 代理池空 | submit_task 返回失败结果，不阻塞 |
| 僵死代理 | HealthMonitor 检测 stale_timeout → 立即替换 |

---

## 8. 测试策略

| 组件 | 测试重点 | mock 策略 |
|------|---------|----------|
| ScrapeAgent | 熔断/限流/解析/健康记录 | mock aiohttp.ClientSession |
| AgentManager | 创建/销毁/替换/任务分发 | mock ScrapeAgent.execute |
| LoadBalancer | 加权选择/熔断过滤/优先级 | 健康分可控的 mock agent |
| HealthMonitor | 心跳检测/替换触发/僵死检测 | mock agent_manager.replace_agent |
| ResultAggregator | 去重/质量评分/路由 | 内存目录，不写磁盘 |

所有测试使用 `pytest-asyncio` 进行异步测试。

---

## 9. 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| aiohttp | >=3.9.0 | 异步 HTTP 客户端 |
| beautifulsoup4 | >=4.12.0 | HTML 解析 |
| lxml | >=5.1.0 | XML/HTML 解析后端 |
| pyyaml | >=6.0 | 配置文件（已安装） |
| pytest-asyncio | >=0.23.0 | 异步测试 |

---

## 10. 使用示例

```python
import asyncio
from pathlib import Path
from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask

async def main():
    # 初始化代理管理器
    manager = AgentManager(
        config_path=Path("config/scrape_sources.yaml"),
        dest_dir=Path("data/knowledge/chinese_reference/B_literature"),
    )
    await manager.initialize()

    # 启动健康监控
    await manager.health_monitor.start()

    # 提交抓取任务
    tasks = [
        ScrapeTask(
            task_id="task-001",
            source_type="api",
            url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=BIA+China&retmax=20",
            parse_rules={"format": "xml", "fields": ["pmid", "title"]},
        ),
        ScrapeTask(
            task_id="task-002",
            source_type="html",
            url="https://www.cma.org.cn/guideline.html",
            parse_rules={"format": "html", "selector": ".guideline-content"},
        ),
    ]

    results = await manager.submit_batch(tasks)
    for r in results:
        print(f"[{r.task_id}] success={r.success}, quality={r.quality_score:.2f}")

    # 查看代理池状态
    status = manager.get_pool_status()
    print(f"代理池: {status['healthy']} healthy, {status['degraded']} degraded")

    # 关闭
    await manager.shutdown()

asyncio.run(main())
```
