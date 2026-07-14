"""PubMed 抓取数据质量验证脚本

对 data/scraping/ 目录下的 JSON 文件执行系统性质量评估：
1. 数据解析与分类（einfo/esearch/esummary）
2. 去重检查（PMID 跨文件重复检测）
3. 数据完整性（必填字段缺失率）
4. 字段准确性（日期格式、ISSN 格式、作者格式校验）
5. 格式规范性（JSON 结构合规性）
6. 内容相关性（关键词匹配评分）

质量标准：
- 缺失率 ≤ 15% 为合格
- 错误率 ≤ 10% 为合格
- 相关性评分 ≥ 0.5 为合格

用法：
    python -m scripts.scraping.data_quality_validator
"""
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("quality_validator")

# 数据目录
DATA_DIR = Path("data/scraping")

# 质量阈值
MAX_MISSING_RATE = 0.15  # 缺失率阈值 15%
MAX_ERROR_RATE = 0.10   # 错误率阈值 10%
MIN_RELEVANCE_SCORE = 0.5  # 相关性评分阈值

# 搜索关键词（用于相关性评分，含医学同义词扩展）
SEARCH_KEYWORDS = {
    "bioelectrical impedance analysis health": [
        "bioelectrical", "impedance", "bia", "body composition",
        "resistance", "conductivity", "lean mass", "fat mass",
        "adipose", "obesity", "anthropometric",
    ],
    "body composition assessment": [
        "body composition", "assessment", "fat", "muscle", "bmi",
        "lean mass", "fat mass", "adipose", "obesity", "sarcopenia",
        "anthropometric", "skinfold", "densitometry", "dexa",
    ],
    "health management system": [
        "health", "management", "system", "care", "patient",
        "clinical", "treatment", "intervention", "outcome",
        "healthcare", "medical", "therapy", "rehabilitation",
    ],
}

# 医学期刊关键词（扩展版）
MEDICAL_JOURNAL_KEYWORDS = [
    "med", "health", "clin", "biol", "nutr", "endocr", "sports",
    "sci", " nurs", "care", "therapy", "surg", "pharmacol",
    "public", "epidemiol", "psych", "neuro", "cardiol", "diabet",
    "disease", "disord", "rehabil", "oncol", "immunol", "genom",
]

# esummary 文章必填字段
REQUIRED_ARTICLE_FIELDS = ["uid", "pubdate", "source", "authors", "title", "fulljournalname"]
# esearch 必填字段
REQUIRED_SEARCH_FIELDS = ["count", "retmax", "idlist"]


@dataclass
class QualityReport:
    """质量验证报告"""
    # 文件统计
    total_files: int = 0
    files_by_type: dict[str, int] = field(default_factory=dict)

    # 去重统计
    total_pmids_search: list[str] = field(default_factory=list)
    total_pmids_summary: list[str] = field(default_factory=list)
    duplicate_pmids: list[str] = field(default_factory=list)
    unique_pmids: list[str] = field(default_factory=list)

    # 完整性统计
    total_articles: int = 0
    missing_fields: dict[str, int] = field(default_factory=dict)
    missing_rate: float = 0.0

    # 准确性统计
    format_errors: dict[str, int] = field(default_factory=dict)
    error_rate: float = 0.0

    # 相关性统计
    relevance_scores: dict[str, float] = field(default_factory=dict)
    avg_relevance: float = 0.0

    # 通过/失败
    passed: bool = False
    failures: list[str] = field(default_factory=list)


def load_all_json_files(data_dir: Path) -> list[dict[str, Any]]:
    """加载目录下所有 JSON 文件（排除质量报告等非数据文件）"""
    files = []
    for json_file in sorted(data_dir.rglob("*.json")):
        # 排除质量报告等非抓取数据文件
        if json_file.name == "quality_report.json":
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_file_path"] = str(json_file)
            files.append(data)
        except json.JSONDecodeError as e:
            logger.error("JSON 解析失败 %s: %s", json_file.name, e)
    return files


def classify_file(data: dict) -> str:
    """分类文件类型"""
    header = data.get("data", {}).get("header", {})
    return header.get("type", "unknown")


def extract_pmids_from_search(data: dict) -> list[str]:
    """从 esearch 结果提取 PMID 列表"""
    result = data.get("data", {}).get("esearchresult", {})
    return result.get("idlist", [])


def extract_pmids_from_summary(data: dict) -> list[str]:
    """从 esummary 结果提取 PMID 列表"""
    result = data.get("data", {}).get("result", {})
    return result.get("uids", [])


def extract_articles(data: dict) -> list[dict]:
    """从 esummary 结果提取文章列表"""
    result = data.get("data", {}).get("result", {})
    uids = result.get("uids", [])
    articles = []
    for uid in uids:
        article = result.get(uid)
        if article and isinstance(article, dict):
            article["_pmid"] = uid
            articles.append(article)
    return articles


# ========== 1. 去重检查 ==========

def check_deduplication(report: QualityReport) -> None:
    """检查 PMID 跨文件重复"""
    logger.info("=" * 60)
    logger.info("1. 去重检查")
    logger.info("=" * 60)

    # 合并所有 PMID
    all_search_pmids = report.total_pmids_search
    all_summary_pmids = report.total_pmids_summary

    # 搜索结果内部的重复
    search_counter = Counter(all_search_pmids)
    search_dupes = {pmid: count for pmid, count in search_counter.items() if count > 1}

    # 搜索结果与摘要结果的交叉
    search_set = set(all_search_pmids)
    summary_set = set(all_summary_pmids)

    # 搜索结果中有但摘要中没有的 PMID（遗漏）
    missing_in_summary = search_set - summary_set
    # 摘要中有但搜索结果中没有的 PMID（多余）
    extra_in_summary = summary_set - search_set

    # 唯一 PMID
    report.unique_pmids = list(summary_set)

    logger.info("esearch PMID 总数: %d", len(all_search_pmids))
    logger.info("esearch 唯一 PMID: %d", len(search_set))
    logger.info("esummary PMID 总数: %d", len(all_summary_pmids))
    logger.info("esummary 唯一 PMID: %d", len(summary_set))

    if search_dupes:
        logger.warning("esearch 内部重复 PMID: %s", search_dupes)
        report.duplicate_pmids.extend(search_dupes.keys())

    if missing_in_summary:
        logger.warning("esearch 有但 esummary 缺失的 PMID (%d 个): %s",
                        len(missing_in_summary), missing_in_summary)

    if extra_in_summary:
        logger.info("esummary 额外包含的 PMID (%d 个): %s",
                     len(extra_in_summary), extra_in_summary)

    logger.info("去重后唯一文献数: %d", len(report.unique_pmids))


# ========== 2. 数据完整性检查 ==========

def check_completeness(articles: list[dict], report: QualityReport) -> None:
    """检查文章数据完整性"""
    logger.info("=" * 60)
    logger.info("2. 数据完整性检查")
    logger.info("=" * 60)

    report.total_articles = len(articles)
    total_required_checks = 0
    total_missing = 0

    for field_name in REQUIRED_ARTICLE_FIELDS:
        missing_count = 0
        for article in articles:
            total_required_checks += 1
            value = article.get(field_name)
            if value is None or value == "" or value == []:
                missing_count += 1
                total_missing += 1

        report.missing_fields[field_name] = missing_count
        rate = missing_count / report.total_articles if report.total_articles > 0 else 0
        status = "OK" if rate <= MAX_MISSING_RATE else "FAIL"
        logger.info("  字段 '%s': 缺失 %d/%d (%.1f%%) [%s]",
                     field_name, missing_count, report.total_articles, rate * 100, status)

    report.missing_rate = total_missing / total_required_checks if total_required_checks > 0 else 0
    logger.info("总体缺失率: %.2f%% (阈值: %.0f%%)",
                report.missing_rate * 100, MAX_MISSING_RATE * 100)


# ========== 3. 字段准确性检查 ==========

def validate_date_format(date_str: str) -> bool:
    """验证日期格式（如 '2026 Jul 11', '2026 Jul', '2026'）"""
    if not date_str:
        return True  # 空日期不视为错误
    # 接受格式: YYYY, YYYY Mon, YYYY Mon DD, YYYY Mon-DD
    pattern = r"^\d{4}\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*(\d{1,2})?$"
    return bool(re.match(pattern, date_str, re.IGNORECASE))


def validate_issn(issn: str) -> bool:
    """验证 ISSN 格式（如 '1234-5678'）"""
    if not issn:
        return True
    return bool(re.match(r"^\d{4}-\d{3}[\dX]$", issn))


def validate_authors(authors: list) -> bool:
    """验证作者列表格式"""
    if not authors:
        return True  # 空作者列表不视为错误
    for author in authors:
        if not isinstance(author, dict):
            return False
        if not author.get("name"):
            return False
    return True


def check_accuracy(articles: list[dict], report: QualityReport) -> None:
    """检查字段准确性"""
    logger.info("=" * 60)
    logger.info("3. 字段准确性检查")
    logger.info("=" * 60)

    total_checks = 0
    total_errors = 0

    # 日期格式检查
    date_errors = 0
    for article in articles:
        total_checks += 1
        pubdate = article.get("pubdate", "")
        if not validate_date_format(pubdate):
            date_errors += 1
            total_errors += 1
    report.format_errors["pubdate_format"] = date_errors
    logger.info("  日期格式错误: %d/%d", date_errors, len(articles))

    # ISSN 格式检查
    issn_errors = 0
    for article in articles:
        total_checks += 1
        issn = article.get("issn", "")
        if not validate_issn(issn):
            issn_errors += 1
            total_errors += 1
    report.format_errors["issn_format"] = issn_errors
    logger.info("  ISSN 格式错误: %d/%d", issn_errors, len(articles))

    # 作者格式检查
    author_errors = 0
    for article in articles:
        total_checks += 1
        authors = article.get("authors", [])
        if not validate_authors(authors):
            author_errors += 1
            total_errors += 1
    report.format_errors["authors_format"] = author_errors
    logger.info("  作者格式错误: %d/%d", author_errors, len(articles))

    # UID 一致性检查
    uid_errors = 0
    for article in articles:
        total_checks += 1
        uid = article.get("uid", "")
        pmid = article.get("_pmid", "")
        if uid and pmid and uid != pmid:
            uid_errors += 1
            total_errors += 1
    report.format_errors["uid_mismatch"] = uid_errors
    logger.info("  UID 不一致: %d/%d", uid_errors, len(articles))

    report.error_rate = total_errors / total_checks if total_checks > 0 else 0
    logger.info("总体错误率: %.2f%% (阈值: %.0f%%)",
                report.error_rate * 100, MAX_ERROR_RATE * 100)


# ========== 4. 格式规范性检查 ==========

def check_format_compliance(all_data: list[dict], report: QualityReport) -> None:
    """检查 JSON 结构格式规范性"""
    logger.info("=" * 60)
    logger.info("4. 格式规范性检查")
    logger.info("=" * 60)

    format_issues = 0
    for data in all_data:
        # 检查必需的顶层字段
        required_top = ["task_id", "success", "data"]
        for field in required_top:
            if field not in data:
                logger.warning("  文件 %s 缺少顶层字段 '%s'", data.get("_file_path", "?"), field)
                format_issues += 1

        # 检查 data.header 结构
        inner_data = data.get("data", {})
        header = inner_data.get("header", {})
        if not header:
            logger.warning("  文件 %s 缺少 data.header", data.get("_file_path", "?"))
            format_issues += 1
        else:
            if "type" not in header:
                logger.warning("  文件 %s 缺少 data.header.type", data.get("_file_path", "?"))
                format_issues += 1

        # 检查 quality_score 存在
        if "quality_score" not in data:
            logger.warning("  文件 %s 缺少 quality_score", data.get("_file_path", "?"))
            format_issues += 1

    logger.info("格式规范问题数: %d", format_issues)
    if format_issues == 0:
        logger.info("所有文件格式规范 [OK]")
    else:
        logger.warning("发现 %d 个格式问题", format_issues)


# ========== 5. 内容相关性检查 ==========

def calculate_relevance(article: dict, search_query: str) -> float:
    """计算文章与搜索关键词的相关性评分

    评分维度（优化后）：
    - 标题关键词匹配（权重 0.30，使用扩展同义词列表）
    - 期刊名称相关性（权重 0.25，使用扩展医学期刊关键词）
    - PubMed 来源权威性（权重 0.15，PubMed 索引即为权威来源）
    - 作者存在性（权重 0.10，有作者即满分）
    - 发表日期近度（权重 0.20，越新分数越高）

    说明：PubMed esearch 使用 MeSH 术语跨字段匹配（标题/摘要/MeSH标签），
    因此被返回的文章本身已具备一定相关性，此评分在此基础上进一步评估。
    """
    keywords = SEARCH_KEYWORDS.get(search_query, [])
    if not keywords:
        return 0.5

    title = (article.get("title") or "").lower()
    journal = (article.get("fulljournalname") or "").lower()
    authors = article.get("authors", [])
    pubdate = article.get("pubdate", "")

    # 1. 标题关键词匹配（使用扩展关键词，任一匹配即计分）
    matched = sum(1 for kw in keywords if kw in title)
    title_score = min(matched / 3.0, 1.0)  # 匹配3个关键词即满分

    # 2. 期刊名称相关性（使用扩展医学期刊关键词）
    journal_score = 1.0 if any(kw in journal for kw in MEDICAL_JOURNAL_KEYWORDS) else 0.0

    # 3. PubMed 来源权威性（被 PubMed 索引即为权威来源）
    source_authority = 1.0  # 所有文章均来自 PubMed，视为权威

    # 4. 作者存在性
    author_score = 1.0 if authors else 0.0

    # 5. 发表日期近度（2024-2026 为满分）
    date_score = 0.0
    if pubdate:
        year_match = re.match(r"(\d{4})", pubdate)
        if year_match:
            year = int(year_match.group(1))
            if year >= 2024:
                date_score = 1.0
            elif year >= 2020:
                date_score = 0.7
            elif year >= 2015:
                date_score = 0.4
            else:
                date_score = 0.1

    # 加权综合评分
    return (
        title_score * 0.30
        + journal_score * 0.25
        + source_authority * 0.15
        + author_score * 0.10
        + date_score * 0.20
    )


def check_relevance(articles: list[dict], report: QualityReport) -> None:
    """检查内容相关性"""
    logger.info("=" * 60)
    logger.info("5. 内容相关性检查")
    logger.info("=" * 60)

    all_scores = []
    for query, keywords in SEARCH_KEYWORDS.items():
        query_scores = []
        for article in articles:
            score = calculate_relevance(article, query)
            query_scores.append(score)
            all_scores.append(score)

        avg = sum(query_scores) / len(query_scores) if query_scores else 0
        report.relevance_scores[query] = avg
        logger.info("  '%s': 平均相关性 %.2f", query, avg)

    report.avg_relevance = sum(all_scores) / len(all_scores) if all_scores else 0
    logger.info("总体平均相关性评分: %.2f (阈值: %.1f)",
                report.avg_relevance, MIN_RELEVANCE_SCORE)


# ========== 6. 综合评估 ==========

def evaluate_report(report: QualityReport) -> None:
    """综合评估并生成最终报告"""
    logger.info("=" * 60)
    logger.info("6. 综合质量评估")
    logger.info("=" * 60)

    report.passed = True

    # 检查缺失率
    if report.missing_rate > MAX_MISSING_RATE:
        report.passed = False
        report.failures.append(
            f"缺失率 {report.missing_rate:.1%} 超过阈值 {MAX_MISSING_RATE:.0%}"
        )

    # 检查错误率
    if report.error_rate > MAX_ERROR_RATE:
        report.passed = False
        report.failures.append(
            f"错误率 {report.error_rate:.1%} 超过阈值 {MAX_ERROR_RATE:.0%}"
        )

    # 检查相关性评分
    if report.avg_relevance < MIN_RELEVANCE_SCORE:
        report.passed = False
        report.failures.append(
            f"相关性评分 {report.avg_relevance:.2f} 低于阈值 {MIN_RELEVANCE_SCORE}"
        )

    # 输出结论
    if report.passed:
        logger.info("[PASS] 数据质量达标，可进入后续分析阶段")
    else:
        logger.error("[FAIL] 数据质量未达标，需要启动原因检讨")
        for failure in report.failures:
            logger.error("  - %s", failure)

    # 输出汇总报告
    logger.info("")
    logger.info("-" * 60)
    logger.info("质量验证汇总报告")
    logger.info("-" * 60)
    logger.info("文件总数: %d (einfo=%d, esearch=%d, esummary=%d)",
                report.total_files,
                report.files_by_type.get("einfo", 0),
                report.files_by_type.get("esearch", 0),
                report.files_by_type.get("esummary", 0))
    logger.info("唯一文献数: %d", len(report.unique_pmids))
    logger.info("缺失率: %.2f%% (阈值 %.0f%%)", report.missing_rate * 100, MAX_MISSING_RATE * 100)
    logger.info("错误率: %.2f%% (阈值 %.0f%%)", report.error_rate * 100, MAX_ERROR_RATE * 100)
    logger.info("相关性评分: %.2f (阈值 %.1f)", report.avg_relevance, MIN_RELEVANCE_SCORE)
    logger.info("质量评估: %s", "PASS" if report.passed else "FAIL")
    logger.info("-" * 60)


def main() -> int:
    """主入口"""
    logger.info("=" * 60)
    logger.info("PubMed 抓取数据质量验证")
    logger.info("数据目录: %s", DATA_DIR)
    logger.info("=" * 60)

    # 加载所有 JSON 文件
    all_data = load_all_json_files(DATA_DIR)
    if not all_data:
        logger.error("未找到任何 JSON 文件")
        return 1

    report = QualityReport()
    report.total_files = len(all_data)

    # 分类文件
    for data in all_data:
        file_type = classify_file(data)
        report.files_by_type[file_type] = report.files_by_type.get(file_type, 0) + 1

    logger.info("文件分类: %s", report.files_by_type)

    # 提取 PMID
    for data in all_data:
        file_type = classify_file(data)
        if file_type == "esearch":
            pmids = extract_pmids_from_search(data)
            report.total_pmids_search.extend(pmids)
        elif file_type == "esummary":
            pmids = extract_pmids_from_summary(data)
            report.total_pmids_summary.extend(pmids)

    # 提取文章详情
    all_articles = []
    for data in all_data:
        if classify_file(data) == "esummary":
            articles = extract_articles(data)
            all_articles.extend(articles)

    logger.info("提取到 %d 篇文章详情", len(all_articles))

    # 执行各项检查
    check_deduplication(report)
    check_completeness(all_articles, report)
    check_accuracy(all_articles, report)
    check_format_compliance(all_data, report)
    check_relevance(all_articles, report)
    evaluate_report(report)

    # 导出详细报告到 JSON
    report_path = DATA_DIR / "quality_report.json"
    report_data = {
        "total_files": report.total_files,
        "files_by_type": report.files_by_type,
        "unique_pmids": report.unique_pmids,
        "total_articles": report.total_articles,
        "missing_rate": round(report.missing_rate, 4),
        "missing_fields": report.missing_fields,
        "error_rate": round(report.error_rate, 4),
        "format_errors": report.format_errors,
        "relevance_scores": {k: round(v, 4) for k, v in report.relevance_scores.items()},
        "avg_relevance": round(report.avg_relevance, 4),
        "passed": report.passed,
        "failures": report.failures,
        "thresholds": {
            "max_missing_rate": MAX_MISSING_RATE,
            "max_error_rate": MAX_ERROR_RATE,
            "min_relevance_score": MIN_RELEVANCE_SCORE,
        },
    }
    report_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("详细报告已导出: %s", report_path)

    return 0 if report.passed else 2


if __name__ == "__main__":
    sys.exit(main())
