"""PubMed 文献摘要抓取脚本

使用 efetch 接口获取 29 篇文献的完整摘要正文。
efetch 返回 XML 格式，包含 <AbstractText> 标签。

用法：
    python -m scripts.scraping.fetch_abstracts
"""
import asyncio
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.scraping.agent_manager import AgentManager
from scripts.scraping.scrape_agent import ScrapeTask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fetch_abstracts")

CONFIG_PATH = Path("config/scrape_sources.yaml")
DEST_DIR = Path("data/scraping")
ABSTRACTS_DIR = DEST_DIR / "pubmed" / "abstracts"


def load_pmids_from_catalog() -> list[str]:
    """从 articles_catalog.json 加载所有 PMID"""
    catalog_path = DEST_DIR / "analysis" / "articles_catalog.json"
    if not catalog_path.exists():
        logger.error("文献目录不存在: %s", catalog_path)
        return []

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    pmids = [art["pmid"] for art in catalog if art.get("pmid")]
    logger.info("从文献目录加载 %d 个 PMID", len(pmids))
    return pmids


def parse_abstract_xml(xml_content: str) -> dict:
    """解析 efetch XML，提取摘要文本和关键词

    XML 结构：
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>123456</PMID>
          <Article>
            <ArticleTitle>...</ArticleTitle>
            <Abstract>
              <AbstractText>...</AbstractText>
              <AbstractText Label="METHODS">...</AbstractText>
            </Abstract>
            <KeywordList>
              <Keyword>...</Keyword>
            </KeywordList>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    articles = {}
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error("XML 解析失败: %s", e)
        return articles

    for pubmed_article in root.findall(".//PubmedArticle"):
        pmid_elem = pubmed_article.find(".//PMID")
        if pmid_elem is None:
            continue
        pmid = pmid_elem.text or ""

        # 提取标题
        title_elem = pubmed_article.find(".//ArticleTitle")
        title = "".join(title_elem.itertext()) if title_elem is not None else ""

        # 提取摘要（可能有多段，带 Label）
        abstract_parts = []
        for abstract_text in pubmed_article.findall(".//AbstractText"):
            label = abstract_text.get("Label", "")
            text = "".join(abstract_text.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)

        abstract = "\n\n".join(abstract_parts) if abstract_parts else ""

        # 提取关键词
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


async def fetch_all_abstracts() -> None:
    """批量抓取所有文献摘要"""
    pmids = load_pmids_from_catalog()
    if not pmids:
        return

    manager = AgentManager(
        config_path=CONFIG_PATH,
        dest_dir=DEST_DIR,
    )

    try:
        await manager.initialize()
        logger.info("代理池就绪: %d 个代理", len(manager.agents))

        # 每批 5 篇（efetch 返回 XML 较大，控制批量大小）
        BATCH_SIZE = 5
        all_abstracts = {}

        for i in range(0, len(pmids), BATCH_SIZE):
            batch = pmids[i:i + BATCH_SIZE]
            pmid_str = ",".join(batch)
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(pmids) + BATCH_SIZE - 1) // BATCH_SIZE

            url = (
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                f"?db=pubmed&id={pmid_str}&retmode=xml&rettype=abstract"
            )

            task = ScrapeTask(
                task_id=f"efetch_batch_{batch_num}",
                source_type="api",
                url=url,
                parse_rules={"format": "pubmed_xml"},
                metadata={"endpoint": "efetch", "pmids": batch},
            )

            logger.info("抓取批次 %d/%d (PMID: %s)...", batch_num, total_batches, pmid_str)
            result = await manager.submit_task(task)

            if not result.success:
                logger.error("批次 %d 抓取失败: %s", batch_num, result.error)
                continue

            # result.data 是 parse() 返回的 {"xml": raw_xml_content}
            xml_content = result.data.get("xml", "") if result.data else ""
            if not xml_content:
                logger.warning("批次 %d 返回空 XML", batch_num)
                continue

            # 解析 XML 提取摘要
            parsed = parse_abstract_xml(xml_content)
            for pmid, article_data in parsed.items():
                all_abstracts[pmid] = article_data

            logger.info("批次 %d 解析成功: %d 篇摘要", batch_num, len(parsed))

        # 保存结果
        ABSTRACTS_DIR.mkdir(parents=True, exist_ok=True)

        # 保存合并文件
        merged_path = ABSTRACTS_DIR / "all_abstracts.json"
        merged_path.write_text(
            json.dumps(all_abstracts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("合并摘要文件: %s (%d 篇)", merged_path, len(all_abstracts))

        # 每篇单独保存
        for pmid, data in all_abstracts.items():
            single_path = ABSTRACTS_DIR / f"pmid_{pmid}.json"
            single_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # 统计
        total_words = sum(d["abstract_word_count"] for d in all_abstracts.values())
        with_abstract = sum(1 for d in all_abstracts.values() if d["abstract"])
        without_abstract = len(all_abstracts) - with_abstract

        logger.info("=" * 60)
        logger.info("摘要抓取完成")
        logger.info("=" * 60)
        logger.info("总计: %d 篇", len(all_abstracts))
        logger.info("有摘要: %d 篇", with_abstract)
        logger.info("无摘要: %d 篇", without_abstract)
        logger.info("总词数: %d", total_words)
        logger.info("平均词数: %.0f", total_words / max(with_abstract, 1))
        logger.info("存储目录: %s", ABSTRACTS_DIR)

        # 显示前 3 篇摘要预览
        logger.info("\n--- 前 3 篇摘要预览 ---")
        for pmid in list(all_abstracts.keys())[:3]:
            data = all_abstracts[pmid]
            preview = data["abstract"][:200] + "..." if len(data["abstract"]) > 200 else data["abstract"]
            logger.info("\nPMID %s | %d 词", pmid, data["abstract_word_count"])
            logger.info("标题: %s", data["title"][:80])
            logger.info("摘要: %s", preview)

    finally:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(fetch_all_abstracts())
