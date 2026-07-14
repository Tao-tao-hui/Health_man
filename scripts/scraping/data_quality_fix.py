"""数据质量修复脚本

修复六维度质量评估发现的问题：
1. 重新抓取空摘要的文献
2. 补充缺失的 pubdate 字段

用法：
    python -m scripts.scraping.data_quality_fix
"""
import asyncio
import json
import logging
import re
from pathlib import Path

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("data_quality_fix")

CONFIG_PATH = Path("config/scrape_sources.yaml")
ABSTRACTS_DIR = Path("data/scraping/pubmed/abstracts")


def load_all_abstracts() -> dict:
    """加载所有摘要"""
    merged_path = ABSTRACTS_DIR / "all_abstracts.json"
    return json.loads(merged_path.read_text(encoding="utf-8"))


def find_problematic_articles(articles: dict) -> tuple:
    """找出有问题的文章"""
    empty_abstract = []
    missing_pubdate = []
    
    for pmid, art in articles.items():
        if not art.get("abstract"):
            empty_abstract.append(pmid)
        if "pubdate" not in art:
            missing_pubdate.append(pmid)
    
    return empty_abstract, missing_pubdate


async def fetch_single_abstract(manager: AgentManager, pmid: str) -> dict:
    """抓取单篇文献摘要"""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml&rettype=abstract"
    
    task = ScrapeTask(
        task_id=f"efetch_fix_{pmid}",
        source_type="api",
        url=url,
        parse_rules={"format": "pubmed_xml"},
        metadata={"endpoint": "efetch", "pmid": pmid},
    )
    
    result = await manager.submit_task(task)
    if not result.success:
        logger.error("抓取失败 %s: %s", pmid, result.error)
        return {}
    
    xml_content = result.data.get("xml", "") if result.data else ""
    return parse_abstract_xml(xml_content)


def parse_abstract_xml(xml_content: str) -> dict:
    """解析 efetch XML"""
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
        
        # 提取日期
        pubdate = ""
        pubdate_elem = pubmed_article.find(".//PubDate")
        if pubdate_elem is not None:
            year_elem = pubdate_elem.find(".//Year")
            month_elem = pubdate_elem.find(".//Month")
            day_elem = pubdate_elem.find(".//Day")
            parts = []
            if year_elem is not None:
                parts.append(year_elem.text or "")
            if month_elem is not None:
                parts.append(month_elem.text or "")
            if day_elem is not None:
                parts.append(day_elem.text or "")
            pubdate = " ".join(parts)
        
        articles[pmid] = {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "keywords": keywords,
            "pubdate": pubdate,
            "abstract_word_count": len(abstract.split()) if abstract else 0,
        }
    
    return articles


async def fetch_esummary_batch(manager: AgentManager, pmids: list) -> dict:
    """批量获取 esummary 数据（包含日期）"""
    pmid_str = ",".join(pmids)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid_str}&retmode=json"
    
    task = ScrapeTask(
        task_id=f"esummary_fix_{pmids[0]}",
        source_type="api",
        url=url,
        parse_rules={"format": "json"},
        metadata={"endpoint": "esummary"},
    )
    
    result = await manager.submit_task(task)
    if not result.success:
        logger.error("esummary 抓取失败: %s", result.error)
        return {}
    
    data = result.data or {}
    return data.get("result", {}).get("uids", [])


async def main() -> None:
    """主入口"""
    logger.info("加载数据...")
    articles = load_all_abstracts()
    logger.info(f"文献总数: {len(articles)}")
    
    empty_abstract, missing_pubdate = find_problematic_articles(articles)
    logger.info(f"空摘要: {len(empty_abstract)} 篇")
    logger.info(f"缺失日期: {len(missing_pubdate)} 篇")
    
    if not empty_abstract and not missing_pubdate:
        logger.info("无需修复")
        return
    
    manager = AgentManager(config_path=CONFIG_PATH, dest_dir=Path("data/scraping"))
    
    try:
        await manager.initialize()
        logger.info("代理池就绪")
        
        # 修复空摘要
        if empty_abstract:
            logger.info(f"\n修复空摘要 ({len(empty_abstract)} 篇)...")
            for pmid in empty_abstract:
                logger.info(f"  重新抓取: {pmid}")
                result = await fetch_single_abstract(manager, pmid)
                if result.get(pmid):
                    articles[pmid] = result[pmid]
                    logger.info(f"    成功: {len(result[pmid].get('abstract', ''))} 字符")
                await asyncio.sleep(0.5)
        
        # 补充日期（从 efetch XML 中提取）
        if missing_pubdate:
            logger.info(f"\n补充日期 ({len(missing_pubdate)} 篇)...")
            BATCH_SIZE = 5
            updated_count = 0
            
            for i in range(0, len(missing_pubdate), BATCH_SIZE):
                batch = missing_pubdate[i:i + BATCH_SIZE]
                logger.info(f"  批次 {i // BATCH_SIZE + 1}: {', '.join(batch)}")
                
                for pmid in batch:
                    result = await fetch_single_abstract(manager, pmid)
                    if result.get(pmid):
                        existing = articles.get(pmid, {})
                        # 保留原有数据，只更新日期
                        articles[pmid] = {**existing, **result[pmid]}
                        updated_count += 1
                
                await asyncio.sleep(0.5)
            
            logger.info(f"  日期补充完成: {updated_count}/{len(missing_pubdate)}")
        
        # 保存修复后的数据
        merged_path = ABSTRACTS_DIR / "all_abstracts.json"
        merged_path.write_text(
            json.dumps(articles, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"\n修复后数据已保存: {merged_path}")
        
        # 保存单篇文件
        for pmid, art in articles.items():
            single_path = ABSTRACTS_DIR / f"pmid_{pmid}.json"
            single_path.write_text(
                json.dumps(art, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        
        # 验证修复结果
        empty_after, missing_after = find_problematic_articles(articles)
        logger.info(f"\n修复结果验证:")
        logger.info(f"  空摘要: {len(empty_after)} 篇 (之前: {len(empty_abstract)})")
        logger.info(f"  缺失日期: {len(missing_after)} 篇 (之前: {len(missing_pubdate)})")
    
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
