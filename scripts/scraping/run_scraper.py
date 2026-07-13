"""子代理架构抓取系统 — 启动入口

使用方式：
    python -m scripts.scraping.run_scraper                    # 交互模式
    python -m scripts.scraping.run_scraper --smoke-test       # 冒烟测试
    python -m scripts.scraping.run_scraper --url "https://..." # 单 URL 抓取

功能：
1. 从 config/scrape_sources.yaml 加载数据源配置
2. 初始化代理池（自动创建各数据源对应的 ScrapeAgent）
3. 启动 HealthMonitor 后台监控
4. 接收抓取任务并通过 LoadBalancer 分发
"""
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scrape_runner")


# 默认配置文件路径
CONFIG_PATH = Path("config/scrape_sources.yaml")
# 默认输出目录
DEST_DIR = Path("data/scraping")


async def run_smoke_test() -> bool:
    """冒烟测试：验证系统各组件能正常初始化和协作

    Returns:
        True 表示通过，False 表示失败
    """
    logger.info("=" * 60)
    logger.info("子代理架构抓取系统 — 冒烟测试")
    logger.info("=" * 60)

    # 初始化 AgentManager
    manager = AgentManager(
        config_path=CONFIG_PATH,
        dest_dir=DEST_DIR,
    )

    try:
        # 从配置文件加载并创建代理
        await manager.initialize()
        logger.info("代理池初始化完成")

        # 查看代理池状态
        status = manager.get_pool_status()
        logger.info("代理池状态: %s", json.dumps(status, ensure_ascii=False, indent=2))

        # 验证所有代理健康
        if status["total_agents"] == 0:
            logger.error("冒烟测试失败: 代理池为空")
            return False

        if status["healthy"] != status["total_agents"]:
            logger.warning("部分代理不健康: %s", status)

        # 启动健康监控
        await manager.health_monitor.start()
        logger.info("健康监控器已启动")

        # 创建一个测试任务（不实际发起 HTTP 请求，仅验证任务分发流程）
        task = ScrapeTask(
            task_id="smoke_test_001",
            source_type="api",
            url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed&retmode=json",
            parse_rules={"format": "json"},
            metadata={"params": {"db": "pubmed", "retmode": "json"}},
        )

        # 通过 LoadBalancer 选择代理（不执行实际抓取）
        agent = manager.load_balancer.select_agent(task)
        if agent is None:
            logger.error("冒烟测试失败: 无可用代理执行任务")
            return False

        logger.info("冒烟测试通过: 代理 %s 被选中执行任务", agent.agent_id)
        logger.info("代理健康分: %.2f, 状态: %s", agent.health.health_score, agent.health.state)

        return True

    except Exception as e:
        logger.error("冒烟测试异常: %s", e, exc_info=True)
        return False
    finally:
        await manager.shutdown()
        logger.info("系统已关闭，冒烟测试结束")


async def scrape_single_url(url: str, source_type: str = "api") -> dict:
    """抓取单个 URL

    Args:
        url: 目标 URL
        source_type: 数据源类型（api/html）

    Returns:
        抓取结果字典
    """
    manager = AgentManager(
        config_path=CONFIG_PATH,
        dest_dir=DEST_DIR,
    )

    try:
        await manager.initialize()

        task = ScrapeTask(
            task_id=f"single_{asyncio.get_event_loop().time():.0f}",
            source_type=source_type,
            url=url,
            parse_rules={"format": "json" if source_type == "api" else "html"},
        )

        logger.info("提交抓取任务: %s", url)
        result = await manager.submit_task(task)

        if result.success:
            logger.info("抓取成功: agent=%s, latency=%.0fms, quality=%.2f",
                        result.agent_id, result.latency_ms, result.quality_score)
        else:
            logger.warning("抓取失败: %s", result.error)

        return {
            "success": result.success,
            "url": result.url,
            "agent_id": result.agent_id,
            "latency_ms": result.latency_ms,
            "quality_score": result.quality_score,
            "error": result.error,
            "data": result.data,
        }

    finally:
        await manager.shutdown()


async def run_interactive() -> None:
    """交互模式：持续接收用户输入的 URL 进行抓取"""
    manager = AgentManager(
        config_path=CONFIG_PATH,
        dest_dir=DEST_DIR,
    )

    try:
        await manager.initialize()
        await manager.health_monitor.start()

        logger.info("系统已启动，输入 URL 进行抓取（输入 'quit' 退出）")
        logger.info("代理池: %d 个代理", len(manager.agents))

        while True:
            try:
                user_input = input("\nURL> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input or user_input.lower() in ("quit", "exit", "q"):
                break

            # 自动判断 source_type
            source_type = "html" if any(d in user_input for d in [".html", ".htm", "cnki", "cma"]) else "api"

            task = ScrapeTask(
                task_id=f"interactive_{asyncio.get_event_loop().time():.0f}",
                source_type=source_type,
                url=user_input,
                parse_rules={"format": "json" if source_type == "api" else "html"},
            )

            result = await manager.submit_task(task)

            if result.success:
                logger.info("成功: agent=%s, latency=%.0fms, quality=%.2f",
                            result.agent_id, result.latency_ms, result.quality_score)
                if result.data:
                    # 显示前 500 字符
                    data_str = json.dumps(result.data, ensure_ascii=False)
                    logger.info("数据预览: %s", data_str[:500])
            else:
                logger.warning("失败: %s", result.error)

    except KeyboardInterrupt:
        pass
    finally:
        await manager.shutdown()
        logger.info("系统已关闭")


def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(description="子代理架构抓取系统")
    parser.add_argument("--smoke-test", action="store_true", help="运行冒烟测试")
    parser.add_argument("--url", type=str, help="抓取单个 URL")
    parser.add_argument("--source-type", type=str, default="api", help="数据源类型（api/html）")
    args = parser.parse_args()

    if args.smoke_test:
        success = asyncio.run(run_smoke_test())
        sys.exit(0 if success else 1)
    elif args.url:
        result = asyncio.run(scrape_single_url(args.url, args.source_type))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        asyncio.run(run_interactive())


if __name__ == "__main__":
    main()
