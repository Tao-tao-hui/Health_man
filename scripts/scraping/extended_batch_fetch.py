"""扩展批量抓取脚本

使用多样化搜索关键词获取更多医学领域数据：
- 心血管疾病风险因素
- 慢性肾病管理
- 代谢综合征生物标志物
- 术后康复方案
- 睡眠呼吸暂停综合征
- 肿瘤预后评估

包含数据治理功能：执行日志、完整性哈希、隐私扫描
"""
import asyncio
import json
import logging
import time
from pathlib import Path

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask
from scripts.scraping.data_governance import governance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("extended_fetch")

CONFIG_PATH = Path("config/scrape_sources.yaml")
DEST_DIR = Path("data/scraping")
ABSTRACTS_DIR = DEST_DIR / "pubmed" / "abstracts"

# 扩展搜索关键词列表
SEARCH_QUERIES = [
    # 原有查询（保留）
    {"query": "bioelectrical impedance analysis health", "max_results": 10},
    {"query": "body composition assessment", "max_results": 10},
    {"query": "health management system", "max_results": 10},
    # 新增查询
    {"query": "cardiovascular disease risk factors", "max_results": 10},
    {"query": "chronic kidney disease management", "max_results": 10},
    {"query": "metabolic syndrome biomarkers", "max_results": 10},
    {"query": "postoperative rehabilitation outcomes", "max_results": 10},
    {"query": "obstructive sleep apnea treatment", "max_results": 10},
    {"query": "cancer prognosis evaluation", "max_results": 10},
    {"query": "telemedicine healthcare delivery", "max_results": 10},
]


def load_existing_pmids() -> set[str]:
    """加载已有的 PMID，避免重复抓取"""
    existing = set()
    if ABSTRACTS_DIR.exists():
        for f in ABSTRACTS_DIR.glob("pmid_*.json"):
            pmid = f.stem.replace("pmid_", "")
            existing.add(pmid)
    logger.info("已存在 %d 个 PMID，将跳过重复", len(existing))
    return existing


async def search_pubmed(manager: AgentManager, query: str, max_results: int) -> list[str]:
    """搜索 PubMed 获取 PMID 列表"""
    url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={query.replace(' ', '+')}&retmax={max_results}&retmode=json"
        )

    task = ScrapeTask(
        task_id=f"esearch_{query[:30]}",
        source_type="api",
        url=url,
        parse_rules={"format": "json"},
        metadata={"endpoint": "esearch", "query": query},
    )

    result = await manager.submit_task(task)
    if not result.success:
        logger.error("搜索失败: %s", result.error)
        return []

    esearch_result = result.data.get("esearchresult", {}) if result.data else {}
    pmids = esearch_result.get("idlist", [])
    logger.info("搜索 '%s' 找到 %d 篇文献", query, len(pmids))

    return pmids


async def fetch_abstracts(manager: AgentManager, pmids: list[str], query: str) -> dict:
    """批量抓取摘要"""
    if not pmids:
        return {}

    BATCH_SIZE = 5
    all_abstracts = {}

    for i in range(0, len(pmids), BATCH_SIZE):
        batch = pmids[i:i + BATCH_SIZE]
        pmid_str = ",".join(batch)
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(pmids) + BATCH_SIZE - 1) // BATCH_SIZE

        start_time = time.monotonic()
        url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pubmed&id={pmid_str}&retmode=xml&rettype=abstract"
        )

        task = ScrapeTask(
            task_id=f"efetch_{query[:20]}_{batch_num}",
            source_type="api",
            url=url,
            parse_rules={"format": "pubmed_xml"},
            metadata={"endpoint": "efetch", "query": query, "pmids": batch},
        )

        result = await manager.submit_task(task)
        duration_ms = (time.monotonic() - start_time) * 1000

        if not result.success:
            logger.error("抓取批次 %d 失败: %s", batch_num, result.error)
            governance.log_fetch("pubmed", "efetch", url, 500, 0, duration_ms, error=str(result.error))
            continue

        # 解析 XML
        xml_content = result.data.get("xml", "") if result.data else ""
        abstracts = parse_abstract_xml(xml_content)

        # 记录日志
        governance.log_fetch("pubmed", "efetch", url, 200, len(abstracts), duration_ms)

        # 隐私扫描
        for pmid, data in abstracts.items():
            governance.scan_privacy(data.get("abstract", ""), f"pmid_{pmid}")

        # 保存摘要
        for pmid, data in abstracts.items():
            single_path = ABSTRACTS_DIR / f"pmid_{pmid}.json"
            content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            single_path.write_bytes(content)
            governance.hash_file(single_path)
            all_abstracts[pmid] = data

        logger.info("批次 %d/%d 成功: %d 篇摘要", batch_num, total_batches, len(abstracts))

    return all_abstracts


def parse_abstract_xml(xml_content: str) -> dict:
    """解析 efetch XML，提取摘要文本"""
    import xml.etree.ElementTree as ET

    articles = {}
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return articles

    for pubmed_article in root.findall(".//PubmedArticle"):
        pmid_elem = pubmed_article.find(".//PMID")
        if pmid_elem is None:
            continue
        pmid = pmid_elem.text or ""

        title_elem = pubmed_article.find(".//ArticleTitle")
        title = "".join(title_elem.itertext()) if title_elem is not None else ""

        abstract_parts = []
        for abstract_text in pubmed_article.findall(".//AbstractText"):
            label = abstract_text.get("Label", "")
            text = "".join(abstract_text.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)

        abstract = "\n\n".join(abstract_parts) if abstract_parts else ""

        keywords = []
        for kw in pubmed_article.findall(".//Keyword"):
            kw_text = kw.text or ""
            if kw_text:
                keywords.append(kw_text)

        articles[pmid] = {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "keywords": keywords,
            "abstract_word_count": len(abstract.split()) if abstract else 0,
        }

    return articles


async def main() -> None:
    """主入口"""
    logger.info("=" * 60)
    logger.info("扩展医学数据批量抓取")
    logger.info("搜索查询数: %d", len(SEARCH_QUERIES))
    logger.info("=" * 60)

    existing_pmids = load_existing_pmids()

    manager = AgentManager(
        config_path=CONFIG_PATH,
        dest_dir=DEST_DIR,
    )

    try:
        await manager.initialize()
        logger.info("代理池就绪")

        all_new_pmids = []
        total_abstracts_fetched = 0

        for idx, search_query in enumerate(SEARCH_QUERIES, 1):
            query = search_query["query"]
            max_results = search_query["max_results"]

            logger.info("\n[%d/%d] 搜索: %s", idx, len(SEARCH_QUERIES), query)

            # 搜索获取 PMID
            pmids = await search_pubmed(manager, query, max_results)

            # 去重
            new_pmids = [p for p in pmids if p not in existing_pmids]
            logger.info("新发现: %d 篇（已跳过 %d 篇重复）", len(new_pmids), len(pmids) - len(new_pmids))

            if not new_pmids:
                continue

            # 抓取摘要
            abstracts = await fetch_abstracts(manager, new_pmids, query)
            total_abstracts_fetched += len(abstracts)
            all_new_pmids.extend(new_pmids)

            # 延迟避免请求过快
            await asyncio.sleep(1)

        # 合并所有摘要到一个文件
        merged_path = ABSTRACTS_DIR / "all_abstracts.json"
        all_abstracts = {}
        for f in sorted(ABSTRACTS_DIR.glob("pmid_*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                all_abstracts[data["pmid"]] = data
            except (json.JSONDecodeError, KeyError):
                continue

        merged_path.write_text(
            json.dumps(all_abstracts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        governance.hash_file(merged_path)

        # 运行合规性检查
        governance.run_compliance_checks(DEST_DIR / "pubmed" / "data")

        # 保存所有报告
        governance.save_logs()
        governance.save_integrity_report()
        governance.save_privacy_report()
        governance.save_summary_report()

        # 统计输出
        logger.info("\n" + "=" * 60)
        logger.info("扩展抓取完成")
        logger.info("=" * 60)
        logger.info("总搜索查询: %d", len(SEARCH_QUERIES))
        logger.info("新增文献: %d 篇", total_abstracts_fetched)
        logger.info("总文献数: %d 篇", len(all_abstracts))
        logger.info("总词数: %d", sum(a["abstract_word_count"] for a in all_abstracts.values()))
        logger.info("执行日志: %s", LOG_DIR)
        logger.info("总结报告: %s", REPORT_DIR / "data_acquisition_summary.md")

    finally:
        await manager.shutdown()


if __name__ == "__main__":
    LOG_DIR = Path("data/scraping/logs")
    REPORT_DIR = Path("data/scraping/reports")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    asyncio.run(main())
