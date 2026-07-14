"""PubMed 文献内容分析脚本

对通过质量验证的 29 篇文献执行系统性内容分析：
1. 文献元数据结构化提取（标题/作者/期刊/日期/发表类型）
2. 主题分类与聚类（基于标题关键词）
3. 研究趋势统计（期刊分布/发表类型/时间趋势）
4. 关键词共现分析
5. 生成结构化分析报告

用法：
    python -m scripts.scraping.literature_analysis
"""
import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("literature_analysis")

DATA_DIR = Path("data/scraping")
OUTPUT_DIR = Path("data/scraping/analysis")


def load_all_articles() -> list[dict]:
    """加载所有 esummary 文章（仅扫描 pubmed/data/ 目录，排除分析报告）"""
    articles = []
    scan_dir = DATA_DIR / "pubmed" / "data"
    for f in sorted(scan_dir.glob("*.json")):
        if f.name == "quality_report.json":
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        if data.get("data", {}).get("header", {}).get("type") == "esummary":
            result = data.get("data", {}).get("result", {})
            for uid in result.get("uids", []):
                art = result.get(uid, {})
                if isinstance(art, dict):
                    articles.append(art)
    return articles


def extract_metadata(articles: list[dict]) -> list[dict]:
    """提取结构化元数据"""
    metadata_list = []
    for art in articles:
        # 提取作者姓名列表
        authors = []
        for author in art.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # 提取发表类型
        pub_types = []
        for pt in art.get("pubtype", []):
            pub_types.append(pt)

        # 从 articleids 数组提取 DOI/PII（ISSN/ESSN 是文章直接字段，不在此数组中）
        article_ids = {}
        for aid in art.get("articleids", []):
            id_type = aid.get("idtype", "")
            id_value = aid.get("value", "")
            if id_type and id_value:
                article_ids[id_type] = id_value

        metadata = {
            "pmid": art.get("uid", ""),
            "title": art.get("title", ""),
            "journal": art.get("fulljournalname", ""),
            "journal_abbrev": art.get("source", ""),
            "pubdate": art.get("pubdate", ""),
            "authors": authors,
            "author_count": len(authors),
            "pub_types": pub_types,
            "issn": art.get("issn", ""),
            "essn": art.get("essn", ""),
            "doi": article_ids.get("doi", ""),
            "volume": art.get("volume", ""),
            "issue": art.get("issue", ""),
            "pages": art.get("pages", ""),
            "language": art.get("lang", []),
        }
        metadata_list.append(metadata)
    return metadata_list


def classify_topics(articles: list[dict]) -> dict[str, list[dict]]:
    """基于标题关键词进行主题分类"""
    topic_keywords = {
        "body_composition": [
            "body composition", "fat mass", "lean mass", "adipose",
            "obesity", "bmi", "sarcopenia", "muscle mass", "fat",
        ],
        "bia_impedance": [
            "bioelectrical", "impedance", "bia", "resistance",
            "conductivity", "electrical",
        ],
        "bone_health": [
            "bone", "mineral density", "osteoporosis", "fracture",
        ],
        "nutrition_diet": [
            "nutrition", "diet", "protein", "supplement", "food",
            "calorie", "fasting", "feeding",
        ],
        "health_management": [
            "health", "management", "system", "care", "patient",
            "clinical", "treatment", "intervention",
        ],
        "disease_condition": [
            "disease", "disorder", "syndrome", "cancer", "tumor",
            "diabetes", "hypertension", "infection", "carcinoma",
        ],
        "exercise_rehabilitation": [
            "exercise", "physical activity", "rehabilitation", "training",
            "fitness", "pilates", "yoga",
        ],
        "lab_methods": [
            "assay", "method", "analysis", "measurement", "technique",
            "genetic", "forensic", "microbiome",
        ],
    }

    classified = defaultdict(list)
    for art in articles:
        title = (art.get("title") or "").lower()
        matched_topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in title for kw in keywords):
                matched_topics.append(topic)

        if not matched_topics:
            matched_topics = ["other"]

        for topic in matched_topics:
            classified[topic].append(art)

    return classified


def analyze_journal_distribution(articles: list[dict]) -> dict:
    """分析期刊分布"""
    journal_counter = Counter()
    for art in articles:
        journal = art.get("fulljournalname", "unknown")
        journal_counter[journal] += 1
    return dict(journal_counter.most_common(10))


def analyze_publication_types(articles: list[dict]) -> dict:
    """分析发表类型分布"""
    type_counter = Counter()
    for art in articles:
        for pt in art.get("pubtype", []):
            type_counter[pt] += 1
    return dict(type_counter.most_common(10))


def analyze_author_statistics(articles: list[dict]) -> dict:
    """分析作者统计"""
    all_authors = []
    for art in articles:
        for author in art.get("authors", []):
            name = author.get("name", "")
            if name:
                all_authors.append(name)

    author_counter = Counter(all_authors)
    author_counts = [len(art.get("authors", [])) for art in articles]

    return {
        "total_unique_authors": len(set(all_authors)),
        "total_author_mentions": len(all_authors),
        "avg_authors_per_article": sum(author_counts) / len(author_counts) if author_counts else 0,
        "max_authors": max(author_counts) if author_counts else 0,
        "min_authors": min(author_counts) if author_counts else 0,
        "top_authors": dict(author_counter.most_common(5)),
    }


def extract_title_keywords(articles: list[dict]) -> dict:
    """提取标题关键词频率"""
    # 停用词
    stop_words = {
        "the", "a", "an", "of", "in", "and", "to", "for", "with", "on",
        "by", "from", "as", "at", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "can", "this", "that",
        "these", "those", "i", "we", "they", "it", "its", "their", "our",
        "his", "her", "between", "after", "before", "or", "not", "no",
        "more", "less", "than", "then", "so", "if", "but", "about",
    }

    word_counter = Counter()
    for art in articles:
        title = (art.get("title") or "").lower()
        # 提取词组（2-3个词）
        words = re.findall(r"[a-z]{3,}", title)
        for word in words:
            if word not in stop_words:
                word_counter[word] += 1

        # 提取双词短语
        bigrams = re.findall(r"[a-z]{3,}\s+[a-z]{3,}", title)
        for bigram in bigrams:
            words_in_bigram = bigram.split()
            if all(w not in stop_words for w in words_in_bigram):
                word_counter[f"{bigram}"] += 1

    return dict(word_counter.most_common(20))


def generate_report(articles: list[dict], metadata: list[dict]) -> dict:
    """生成完整分析报告"""
    topics = classify_topics(articles)
    journal_dist = analyze_journal_distribution(articles)
    pub_types = analyze_publication_types(articles)
    author_stats = analyze_author_statistics(articles)
    title_keywords = extract_title_keywords(articles)

    # 年份分布
    year_dist = Counter()
    for art in articles:
        pubdate = art.get("pubdate", "")
        year_match = re.match(r"(\d{4})", pubdate)
        if year_match:
            year_dist[year_match.group(1)] += 1

    report = {
        "summary": {
            "total_articles": len(articles),
            "total_unique_authors": author_stats["total_unique_authors"],
            "total_journals": len(set(art.get("fulljournalname", "") for art in articles)),
            "avg_authors_per_article": round(author_stats["avg_authors_per_article"], 1),
        },
        "topic_classification": {
            topic: len(arts) for topic, arts in sorted(topics.items(), key=lambda x: -len(x[1]))
        },
        "journal_distribution": journal_dist,
        "publication_types": pub_types,
        "year_distribution": dict(sorted(year_dist.items())),
        "author_statistics": author_stats,
        "title_keywords_top20": title_keywords,
        "articles": [
            {
                "pmid": m["pmid"],
                "title": m["title"],
                "journal": m["journal"],
                "pubdate": m["pubdate"],
                "author_count": m["author_count"],
                "pub_types": m["pub_types"],
                "doi": m["doi"],
            }
            for m in metadata
        ],
    }
    return report


def print_summary(report: dict) -> None:
    """打印分析摘要"""
    logger.info("=" * 60)
    logger.info("PubMed 文献内容分析报告")
    logger.info("=" * 60)

    logger.info("\n[1] 数据概览")
    logger.info("  文献总数: %d", report["summary"]["total_articles"])
    logger.info("  独立作者数: %d", report["summary"]["total_unique_authors"])
    logger.info("  期刊数: %d", report["summary"]["total_journals"])
    logger.info("  篇均作者数: %.1f", report["summary"]["avg_authors_per_article"])

    logger.info("\n[2] 主题分类")
    for topic, count in report["topic_classification"].items():
        bar = "#" * count
        logger.info("  %-25s %2d %s", topic, count, bar)

    logger.info("\n[3] 期刊分布 (Top 10)")
    for journal, count in report["journal_distribution"].items():
        logger.info("  %-50s %d", journal[:50], count)

    logger.info("\n[4] 发表类型")
    for pub_type, count in report["publication_types"].items():
        logger.info("  %-40s %d", pub_type[:40], count)

    logger.info("\n[5] 年份分布")
    for year, count in report["year_distribution"].items():
        logger.info("  %s: %d %s", year, count, "#" * count)

    logger.info("\n[6] 作者统计")
    logger.info("  总独立作者: %d", report["author_statistics"]["total_unique_authors"])
    logger.info("  篇均作者: %.1f", report["author_statistics"]["avg_authors_per_article"])
    logger.info("  最多作者: %d", report["author_statistics"]["max_authors"])
    logger.info("  高产作者:")
    for author, count in report["author_statistics"]["top_authors"].items():
        logger.info("    %s: %d 篇", author, count)

    logger.info("\n[7] 高频标题关键词 (Top 20)")
    for kw, count in report["title_keywords_top20"].items():
        logger.info("  %-30s %d %s", kw[:30], count, "#" * count)

    logger.info("\n[8] 文献列表")
    for art in report["articles"]:
        logger.info("  PMID:%s | %s | %s",
                     art["pmid"],
                     art["pubdate"],
                     art["title"][:70])

    logger.info("\n" + "=" * 60)
    logger.info("分析完成")
    logger.info("=" * 60)


def main() -> int:
    """主入口"""
    logger.info("加载文献数据...")
    articles = load_all_articles()
    logger.info("加载完成: %d 篇文献", len(articles))

    if not articles:
        logger.error("未找到文献数据")
        return 1

    logger.info("提取元数据...")
    metadata = extract_metadata(articles)

    logger.info("执行内容分析...")
    report = generate_report(articles, metadata)

    # 打印摘要
    print_summary(report)

    # 导出报告
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "literature_analysis_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("分析报告已导出: %s", report_path)

    # 导出结构化文献列表
    articles_path = OUTPUT_DIR / "articles_catalog.json"
    articles_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("文献目录已导出: %s", articles_path)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
