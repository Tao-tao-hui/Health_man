"""PubMed 医学文献批量抓取脚本

搜索关键词：health management, bioelectrical impedance, body composition
流程：esearch 获取 PMID 列表 → esummary 获取文章详情 → 存储到 data/scraping/
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("batch_fetch")

CONFIG_PATH = Path("config/scrape_sources.yaml")
DEST_DIR = Path("data/scraping")

# 搜索关键词列表
SEARCH_QUERIES = [
    "bioelectrical impedance analysis health",
    "body composition assessment",
    "health management system",
]


async def batch_fetch() -> None:
    """批量抓取 PubMed 文献"""
    manager = AgentManager(
        config_path=CONFIG_PATH,
        dest_dir=DEST_DIR,
    )

    try:
        await manager.initialize()
        logger.info("代理池就绪: %d 个代理", len(manager.agents))

        all_tasks = []

        # 为每个关键词创建 esearch 任务
        for query in SEARCH_QUERIES:
            esearch_url = (
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                f"?db=pubmed&term={query.replace(' ', '+')}&retmax=10&retmode=json"
            )
            task = ScrapeTask(
                task_id=f"esearch_{query.replace(' ', '_')}",
                source_type="api",
                url=esearch_url,
                parse_rules={"format": "json"},
                metadata={"query": query, "endpoint": "esearch"},
            )
            all_tasks.append(task)

        # 批量执行 esearch
        logger.info("开始搜索 %d 个关键词...", len(all_tasks))
        search_results = await manager.submit_batch(all_tasks)

        # 收集所有 PMID
        all_pmids = []
        for result in search_results:
            if not result.success:
                logger.warning("搜索失败: %s", result.error)
                continue

            data = result.data
            if data and "esearchresult" in data:
                id_list = data["esearchresult"].get("idlist", [])
                query = result.task_id.replace("esearch_", "").replace("_", " ")
                logger.info("关键词 '%s' 找到 %d 篇文献", query, len(id_list))
                all_pmids.extend(id_list)

        if not all_pmids:
            logger.error("未找到任何文献，退出")
            return

        # 去重 PMID
        unique_pmids = list(set(all_pmids))
        logger.info("共 %d 篇唯一文献，开始获取摘要...", len(unique_pmids))

        # 为每 10 篇文章创建一个 esummary 任务
        summary_tasks = []
        for i in range(0, len(unique_pmids), 10):
            batch = unique_pmids[i:i + 10]
            pmid_str = ",".join(batch)
            esummary_url = (
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                f"?db=pubmed&id={pmid_str}&retmode=json"
            )
            task = ScrapeTask(
                task_id=f"esummary_{i // 10 + 1}",
                source_type="api",
                url=esummary_url,
                parse_rules={"format": "json"},
                metadata={"endpoint": "esummary", "pmids": batch},
            )
            summary_tasks.append(task)

        # 批量执行 esummary
        logger.info("提交 %d 个摘要获取任务...", len(summary_tasks))
        summary_results = await manager.submit_batch(summary_tasks)

        # 统计结果
        success_count = sum(1 for r in summary_results if r.success)
        fail_count = len(summary_results) - success_count
        logger.info("摘要获取完成: 成功 %d, 失败 %d", success_count, fail_count)

        # 查看存储的文件
        stored_files = list(DEST_DIR.rglob("*.json"))
        logger.info("已存储 %d 个 JSON 文件到 %s", len(stored_files), DEST_DIR)

        # 显示前 3 篇文章标题
        for result in summary_results[:1]:
            if result.success and result.data and "result" in result.data:
                uids = result.data["result"].get("uids", [])
                for uid in uids[:3]:
                    article = result.data["result"].get(uid, {})
                    title = article.get("title", "无标题")
                    authors = [a.get("name", "") for a in article.get("authors", [])[:3]]
                    logger.info("  - [%s] %s (作者: %s)", uid, title, ", ".join(authors))

        # 代理池最终状态
        status = manager.get_pool_status()
        logger.info("代理池最终状态: %s", json.dumps(status, ensure_ascii=False, indent=2))

    finally:
        await manager.shutdown()
        logger.info("系统关闭完成")


if __name__ == "__main__":
    asyncio.run(batch_fetch())
