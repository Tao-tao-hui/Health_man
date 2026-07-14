"""六维度数据质量评估脚本

对 108 篇 PubMed 文献摘要数据集执行全面质量评估：
1. 数据完整性（Completeness）：缺失值比例及分布
2. 数据准确性（Accuracy）：数据值是否符合业务规则和预期范围
3. 数据一致性（Consistency）：数据格式不一致问题
4. 数据有效性（Validity）：数据是否符合预定义格式和约束
5. 数据唯一性（Uniqueness）：重复记录检测与处理
6. 数据及时性（Timeliness）：数据时效性评估

严重程度分级：Critical / High / Medium / Low

用法：
    python -m scripts.scraping.six_dimension_quality
"""
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("six_dimension_quality")

DATA_PATH = Path("data/scraping/pubmed/abstracts/all_abstracts.json")
REPORT_DIR = Path("data/scraping/reports")


@dataclass
class Issue:
    """数据质量问题记录"""
    dimension: str
    category: str
    description: str
    severity: str
    affected_pmids: List[str]
    count: int
    suggestion: str = ""


def load_data() -> Dict[str, Dict[str, Any]]:
    """加载所有摘要数据"""
    if not DATA_PATH.exists():
        logger.error("数据文件不存在: %s", DATA_PATH)
        return {}
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


# ========== 1. 完整性检查 ==========

def check_completeness(articles: Dict[str, Dict]) -> List[Issue]:
    """检查数据完整性"""
    issues = []
    total = len(articles)

    # 缺失字段统计
    field_missing = defaultdict(int)
    for pmid, art in articles.items():
        for field in ["pmid", "title", "abstract"]:
            if not art.get(field):
                field_missing[field] += 1

    # 空摘要或过短摘要
    short_abstract_pmids = []
    for pmid, art in articles.items():
        abstract = art.get("abstract", "")
        if len(abstract) < 50:
            short_abstract_pmids.append(pmid)

    # 空关键词
    empty_keywords_pmids = []
    for pmid, art in articles.items():
        keywords = art.get("keywords", [])
        if not keywords:
            empty_keywords_pmids.append(pmid)

    # 缺少 word_count
    missing_wordcount_pmids = []
    for pmid, art in articles.items():
        if "abstract_word_count" not in art:
            missing_wordcount_pmids.append(pmid)

    # 创建问题记录
    if field_missing["pmid"] > 0:
        issues.append(Issue(
            dimension="完整性",
            category="PMID缺失",
            description=f"{field_missing['pmid']} 篇文献缺失 PMID",
            severity="Critical",
            affected_pmids=[],
            count=field_missing["pmid"],
            suggestion="立即补充缺失的 PMID，这是唯一标识符",
        ))

    if field_missing["title"] > 0:
        issues.append(Issue(
            dimension="完整性",
            category="标题缺失",
            description=f"{field_missing['title']} 篇文献缺失标题",
            severity="High",
            affected_pmids=[],
            count=field_missing["title"],
            suggestion="重新抓取缺失标题的文献",
        ))

    if field_missing["abstract"] > 0:
        issues.append(Issue(
            dimension="完整性",
            category="摘要缺失",
            description=f"{field_missing['abstract']} 篇文献缺失摘要正文",
            severity="Critical",
            affected_pmids=[],
            count=field_missing["abstract"],
            suggestion="重新抓取空摘要的文献",
        ))

    if short_abstract_pmids:
        issues.append(Issue(
            dimension="完整性",
            category="摘要过短",
            description=f"{len(short_abstract_pmids)} 篇文献摘要过短（<50字符）",
            severity="Medium",
            affected_pmids=short_abstract_pmids[:10],
            count=len(short_abstract_pmids),
            suggestion="检查这些文献是否为会议摘要或短讯，考虑重新抓取或标记",
        ))

    if empty_keywords_pmids:
        issues.append(Issue(
            dimension="完整性",
            category="关键词缺失",
            description=f"{len(empty_keywords_pmids)} 篇文献缺少关键词",
            severity="Low",
            affected_pmids=empty_keywords_pmids[:10],
            count=len(empty_keywords_pmids),
            suggestion="关键词缺失不影响核心数据，可考虑从标题/摘要提取",
        ))

    if missing_wordcount_pmids:
        issues.append(Issue(
            dimension="完整性",
            category="词数字段缺失",
            description=f"{len(missing_wordcount_pmids)} 篇文献缺少词数字段",
            severity="Low",
            affected_pmids=missing_wordcount_pmids[:10],
            count=len(missing_wordcount_pmids),
            suggestion="重新计算并补充词数字段",
        ))

    return issues


# ========== 2. 准确性检查 ==========

def check_accuracy(articles: Dict[str, Dict]) -> List[Issue]:
    """检查数据准确性"""
    issues = []

    # PMID 格式验证（应为8位数字）
    invalid_pmid_pmids = []
    for pmid, art in articles.items():
        if not re.match(r"^\d{8}$", pmid):
            invalid_pmid_pmids.append(pmid)

    # 词数准确性验证
    wordcount_mismatch_pmids = []
    for pmid, art in articles.items():
        claimed = art.get("abstract_word_count", 0)
        actual = len(art.get("abstract", "").split())
        if abs(claimed - actual) > 5:
            wordcount_mismatch_pmids.append(pmid)

    # 摘要内容验证（应包含结构化段落）
    no_structured_sections = []
    for pmid, art in articles.items():
        abstract = art.get("abstract", "").lower()
        if not any(section in abstract for section in ["objective", "methods", "results", "conclusions"]):
            no_structured_sections.append(pmid)

    # 关键词格式验证
    invalid_keywords_pmids = []
    for pmid, art in articles.items():
        keywords = art.get("keywords", [])
        for kw in keywords:
            if len(kw) > 100 or len(kw) < 2:
                invalid_keywords_pmids.append(pmid)
                break

    if invalid_pmid_pmids:
        issues.append(Issue(
            dimension="准确性",
            category="PMID格式错误",
            description=f"{len(invalid_pmid_pmids)} 篇文献PMID格式不符合8位数字规范",
            severity="Critical",
            affected_pmids=invalid_pmid_pmids[:10],
            count=len(invalid_pmid_pmids),
            suggestion="验证并修正PMID格式",
        ))

    if wordcount_mismatch_pmids:
        issues.append(Issue(
            dimension="准确性",
            category="词数计算错误",
            description=f"{len(wordcount_mismatch_pmids)} 篇文献词数与实际不符（差异>5词）",
            severity="Medium",
            affected_pmids=wordcount_mismatch_pmids[:10],
            count=len(wordcount_mismatch_pmids),
            suggestion="重新计算词数字段",
        ))

    if no_structured_sections:
        issues.append(Issue(
            dimension="准确性",
            category="摘要缺少结构化段落",
            description=f"{len(no_structured_sections)} 篇文献摘要缺少OBJECTIVE/METHODS等结构化标签",
            severity="Low",
            affected_pmids=no_structured_sections[:10],
            count=len(no_structured_sections),
            suggestion="这可能是综述或短讯类文章，不影响数据有效性",
        ))

    if invalid_keywords_pmids:
        issues.append(Issue(
            dimension="准确性",
            category="关键词格式异常",
            description=f"{len(invalid_keywords_pmids)} 篇文献包含异常格式的关键词",
            severity="Low",
            affected_pmids=invalid_keywords_pmids[:10],
            count=len(invalid_keywords_pmids),
            suggestion="清理异常关键词",
        ))

    return issues


# ========== 3. 一致性检查 ==========

def check_consistency(articles: Dict[str, Dict]) -> List[Issue]:
    """检查数据一致性"""
    issues = []

    # JSON 键一致性
    key_sets = []
    for pmid, art in articles.items():
        key_sets.append(set(art.keys()))

    common_keys = set.intersection(*key_sets) if key_sets else set()
    all_keys = set.union(*key_sets) if key_sets else set()

    missing_keys_pmids = []
    for pmid, art in articles.items():
        if set(art.keys()) != common_keys:
            missing_keys_pmids.append(pmid)

    # 关键词大小写一致性
    keyword_case_issues = []
    for pmid, art in articles.items():
        keywords = art.get("keywords", [])
        for kw in keywords:
            if not kw[0].isupper() or not kw[1:].islower():
                keyword_case_issues.append(pmid)
                break

    # 日期格式一致性
    date_format_issues = []
    date_patterns = {
        "YYYY": re.compile(r"^\d{4}$"),
        "YYYY Mon": re.compile(r"^\d{4} [A-Z][a-z]{2,3}$"),
        "YYYY Mon DD": re.compile(r"^\d{4} [A-Z][a-z]{2,3} \d{1,2}$"),
    }
    for pmid, art in articles.items():
        pubdate = art.get("pubdate", "")
        matched = False
        for pattern in date_patterns.values():
            if pattern.match(pubdate):
                matched = True
                break
        if pubdate and not matched:
            date_format_issues.append(pmid)

    if missing_keys_pmids:
        issues.append(Issue(
            dimension="一致性",
            category="JSON键不一致",
            description=f"{len(missing_keys_pmids)} 篇文献JSON结构与其他文献不一致",
            severity="High",
            affected_pmids=missing_keys_pmids[:10],
            count=len(missing_keys_pmids),
            suggestion=f"标准键集合: {common_keys}. 额外键: {all_keys - common_keys}",
        ))

    if keyword_case_issues:
        issues.append(Issue(
            dimension="一致性",
            category="关键词大小写不一致",
            description=f"{len(keyword_case_issues)} 篇文献关键词大小写格式不统一",
            severity="Low",
            affected_pmids=keyword_case_issues[:10],
            count=len(keyword_case_issues),
            suggestion="统一关键词大小写格式",
        ))

    if date_format_issues:
        issues.append(Issue(
            dimension="一致性",
            category="日期格式不一致",
            description=f"{len(date_format_issues)} 篇文献日期格式与标准格式不符",
            severity="Medium",
            affected_pmids=date_format_issues[:10],
            count=len(date_format_issues),
            suggestion="统一日期格式为 YYYY Mon DD",
        ))

    return issues


# ========== 4. 有效性检查 ==========

def check_validity(articles: Dict[str, Dict]) -> List[Issue]:
    """检查数据有效性"""
    issues = []

    # JSON 结构验证
    invalid_json_pmids = []
    for pmid, art in articles.items():
        required_keys = ["pmid", "title", "abstract"]
        for key in required_keys:
            if key not in art:
                invalid_json_pmids.append(pmid)
                break

    # UTF-8 编码验证（检查特殊字符）
    encoding_issues = []
    for pmid, art in articles.items():
        text = json.dumps(art)
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            encoding_issues.append(pmid)

    # 摘要内容有效性（应包含医学术语）
    medical_terms = ["disease", "treatment", "patient", "study", "clinical", "trial",
                     "method", "result", "conclusion", "objective"]
    no_medical_terms = []
    for pmid, art in articles.items():
        abstract = art.get("abstract", "").lower()
        if not any(term in abstract for term in medical_terms):
            no_medical_terms.append(pmid)

    # 长度验证
    too_long_title = []
    for pmid, art in articles.items():
        title = art.get("title", "")
        if len(title) > 500:
            too_long_title.append(pmid)

    if invalid_json_pmids:
        issues.append(Issue(
            dimension="有效性",
            category="JSON结构无效",
            description=f"{len(invalid_json_pmids)} 篇文献缺少必需字段",
            severity="Critical",
            affected_pmids=invalid_json_pmids[:10],
            count=len(invalid_json_pmids),
            suggestion="补充必需字段: pmid, title, abstract",
        ))

    if encoding_issues:
        issues.append(Issue(
            dimension="有效性",
            category="UTF-8编码问题",
            description=f"{len(encoding_issues)} 篇文献包含无法UTF-8编码的字符",
            severity="High",
            affected_pmids=encoding_issues[:10],
            count=len(encoding_issues),
            suggestion="清理特殊字符，确保UTF-8编码",
        ))

    if no_medical_terms:
        issues.append(Issue(
            dimension="有效性",
            category="摘要缺少医学术语",
            description=f"{len(no_medical_terms)} 篇文献摘要未包含常见医学术语",
            severity="Medium",
            affected_pmids=no_medical_terms[:10],
            count=len(no_medical_terms),
            suggestion="检查这些文献是否为非医学内容，考虑过滤",
        ))

    if too_long_title:
        issues.append(Issue(
            dimension="有效性",
            category="标题过长",
            description=f"{len(too_long_title)} 篇文献标题超过500字符",
            severity="Low",
            affected_pmids=too_long_title[:10],
            count=len(too_long_title),
            suggestion="截断过长标题或检查是否包含额外内容",
        ))

    return issues


# ========== 5. 唯一性检查 ==========

def check_uniqueness(articles: Dict[str, Dict]) -> List[Issue]:
    """检查数据唯一性"""
    issues = []

    # PMID 重复检测
    pmid_counter = Counter()
    for pmid in articles.keys():
        pmid_counter[pmid] += 1
    duplicate_pmids = {pmid: count for pmid, count in pmid_counter.items() if count > 1}

    # 标题重复检测
    title_pmid_map = defaultdict(list)
    for pmid, art in articles.items():
        title = art.get("title", "").strip().lower()
        if title:
            title_pmid_map[title].append(pmid)
    duplicate_titles = {title: pmids for title, pmids in title_pmid_map.items() if len(pmids) > 1}

    # 标题相似度检测（近重复）
    similar_titles = []
    titles = list(title_pmid_map.keys())
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            t1, t2 = titles[i], titles[j]
            if len(t1) > 30 and len(t2) > 30:
                # 计算相似度（简单匹配）
                common_words = set(t1.split()) & set(t2.split())
                similarity = len(common_words) / min(len(t1.split()), len(t2.split()))
                if similarity > 0.8 and t1 != t2:
                    similar_titles.append((t1, t2, title_pmid_map[t1], title_pmid_map[t2]))

    if duplicate_pmids:
        issues.append(Issue(
            dimension="唯一性",
            category="PMID重复",
            description=f"发现 {len(duplicate_pmids)} 个重复PMID",
            severity="Critical",
            affected_pmids=list(duplicate_pmids.keys())[:10],
            count=sum(c - 1 for c in duplicate_pmids.values()),
            suggestion="删除重复记录，保留最新版本",
        ))

    if duplicate_titles:
        issues.append(Issue(
            dimension="唯一性",
            category="标题重复",
            description=f"发现 {len(duplicate_titles)} 组标题重复",
            severity="High",
            affected_pmids=[pmids[0] for pmids in duplicate_titles.values()][:10],
            count=len(duplicate_titles),
            suggestion="检查是否为同一文献的不同版本，删除重复",
        ))

    if similar_titles:
        issues.append(Issue(
            dimension="唯一性",
            category="标题近重复",
            description=f"发现 {len(similar_titles)} 组标题相似度超过80%",
            severity="Medium",
            affected_pmids=[pair[2][0] for pair in similar_titles][:10],
            count=len(similar_titles),
            suggestion="人工审查近重复标题，确认是否需要去重",
        ))

    return issues


# ========== 6. 及时性检查 ==========

def check_timeliness(articles: Dict[str, Dict]) -> List[Issue]:
    """检查数据及时性"""
    issues = []

    # 年份分布
    year_counter = Counter()
    old_articles = []
    for pmid, art in articles.items():
        pubdate = art.get("pubdate", "")
        year_match = re.match(r"(\d{4})", pubdate)
        if year_match:
            year = int(year_match.group(1))
            year_counter[year] += 1
            if year < 2024:
                old_articles.append((pmid, year))

    # 最新文献时间
    latest_year = max(year_counter.keys()) if year_counter else 0

    # 中位年份
    all_years = []
    for pmid, art in articles.items():
        pubdate = art.get("pubdate", "")
        year_match = re.match(r"(\d{4})", pubdate)
        if year_match:
            all_years.append(int(year_match.group(1)))
    all_years.sort()
    median_year = all_years[len(all_years) // 2] if all_years else 0

    # 缺失日期
    missing_date_pmids = []
    for pmid, art in articles.items():
        if not art.get("pubdate"):
            missing_date_pmids.append(pmid)

    if old_articles:
        issues.append(Issue(
            dimension="及时性",
            category="陈旧文献",
            description=f"{len(old_articles)} 篇文献发表于2024年之前",
            severity="Medium",
            affected_pmids=[pmid for pmid, year in old_articles][:10],
            count=len(old_articles),
            suggestion=f"考虑过滤2024年前的文献。当前最新年份: {latest_year}, 中位年份: {median_year}",
        ))

    if missing_date_pmids:
        issues.append(Issue(
            dimension="及时性",
            category="日期缺失",
            description=f"{len(missing_date_pmids)} 篇文献缺少发表日期",
            severity="Low",
            affected_pmids=missing_date_pmids[:10],
            count=len(missing_date_pmids),
            suggestion="补充缺失日期或标记为未知",
        ))

    return issues


# ========== 报告生成 ==========

def generate_report(articles: Dict[str, Dict]) -> Dict:
    """生成完整质量评估报告"""
    report = {
        "report_generated_at": datetime.now().isoformat(),
        "data_source": str(DATA_PATH),
        "total_articles": len(articles),
        "dimensions": {},
        "issues": [],
        "severity_summary": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
        "overall_score": 0.0,
        "summary": {},
    }

    # 执行各维度检查
    check_functions = [
        ("完整性", check_completeness),
        ("准确性", check_accuracy),
        ("一致性", check_consistency),
        ("有效性", check_validity),
        ("唯一性", check_uniqueness),
        ("及时性", check_timeliness),
    ]

    all_issues = []
    for dimension_name, check_func in check_functions:
        issues = check_func(articles)
        all_issues.extend(issues)

        # 计算维度得分
        total_possible = 100
        deductions = 0
        for issue in issues:
            if issue.severity == "Critical":
                deductions += 25
            elif issue.severity == "High":
                deductions += 15
            elif issue.severity == "Medium":
                deductions += 5
            elif issue.severity == "Low":
                deductions += 1
        score = max(0, total_possible - deductions)

        report["dimensions"][dimension_name] = {
            "score": score,
            "issues_count": len(issues),
            "issues": [
                {
                    "category": issue.category,
                    "description": issue.description,
                    "severity": issue.severity,
                    "count": issue.count,
                    "suggestion": issue.suggestion,
                }
                for issue in issues
            ],
        }

    # 汇总严重程度
    for issue in all_issues:
        report["severity_summary"][issue.severity] += 1

    # 计算总体得分（各维度平均）
    report["overall_score"] = sum(
        dim["score"] for dim in report["dimensions"].values()
    ) / len(report["dimensions"])

    # 详细问题列表
    report["issues"] = [
        {
            "dimension": issue.dimension,
            "category": issue.category,
            "description": issue.description,
            "severity": issue.severity,
            "count": issue.count,
            "affected_pmids": issue.affected_pmids,
            "suggestion": issue.suggestion,
        }
        for issue in all_issues
    ]

    # 摘要统计
    report["summary"] = {
        "total_articles": len(articles),
        "total_word_count": sum(a.get("abstract_word_count", 0) for a in articles.values()),
        "avg_word_count": sum(a.get("abstract_word_count", 0) for a in articles.values()) / max(len(articles), 1),
        "median_word_count": sorted(a.get("abstract_word_count", 0) for a in articles.values())[len(articles) // 2] if articles else 0,
        "with_keywords": sum(1 for a in articles.values() if a.get("keywords")),
        "without_keywords": sum(1 for a in articles.values() if not a.get("keywords")),
    }

    return report


def print_report(report: Dict) -> None:
    """打印报告"""
    logger.info("=" * 70)
    logger.info("六维度数据质量评估报告")
    logger.info("=" * 70)

    logger.info(f"\n数据来源: {report['data_source']}")
    logger.info(f"文献总数: {report['total_articles']}")
    logger.info(f"总体得分: {report['overall_score']:.1f}/100")

    # 各维度得分
    logger.info("\n【各维度得分】")
    for dim_name, dim_data in report["dimensions"].items():
        status = "✅" if dim_data["score"] >= 90 else "⚠️" if dim_data["score"] >= 70 else "❌"
        logger.info(f"  {status} {dim_name}: {dim_data['score']:.0f}/100 ({dim_data['issues_count']} 个问题)")

    # 严重程度分布
    logger.info("\n【问题严重程度分布】")
    for severity, count in report["severity_summary"].items():
        bar = "#" * count
        logger.info(f"  {severity:10s} {count:2d} {bar}")

    # 详细问题列表
    logger.info("\n【详细问题清单】")
    for i, issue in enumerate(report["issues"], 1):
        severity_icon = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🟢",
        }[issue["severity"]]
        logger.info(f"\n  {i}. {severity_icon} [{issue['dimension']}] {issue['category']}")
        logger.info(f"     描述: {issue['description']}")
        logger.info(f"     严重程度: {issue['severity']}")
        logger.info(f"     影响数: {issue['count']}")
        if issue["affected_pmids"]:
            logger.info(f"     受影响PMID: {', '.join(issue['affected_pmids'])}")
        logger.info(f"     改进建议: {issue['suggestion']}")

    # 摘要统计
    s = report["summary"]
    logger.info("\n【数据摘要统计】")
    logger.info(f"  总词数: {s['total_word_count']:,}")
    logger.info(f"  篇均词数: {s['avg_word_count']:.0f}")
    logger.info(f"  中位词数: {s['median_word_count']}")
    logger.info(f"  有关键词: {s['with_keywords']}/{report['total_articles']}")
    logger.info(f"  无关键词: {s['without_keywords']}/{report['total_articles']}")

    logger.info("\n" + "=" * 70)


def generate_markdown_report(report: Dict) -> str:
    """生成Markdown格式报告"""
    lines = []
    lines.append("# 六维度数据质量评估报告")
    lines.append("")
    lines.append(f"**生成时间**: {report['report_generated_at']}")
    lines.append(f"**数据来源**: {report['data_source']}")
    lines.append(f"**文献总数**: {report['total_articles']}")
    lines.append(f"**总体得分**: **{report['overall_score']:.1f}/100**")
    lines.append("")

    # 各维度得分
    lines.append("## 各维度得分")
    lines.append("")
    lines.append("| 维度 | 得分 | 问题数 | 状态 |")
    lines.append("|------|------|--------|------|")
    for dim_name, dim_data in report["dimensions"].items():
        status = "✅ 优秀" if dim_data["score"] >= 90 else "⚠️ 需改进" if dim_data["score"] >= 70 else "❌ 不合格"
        lines.append(f"| {dim_name} | {dim_data['score']:.0f}/100 | {dim_data['issues_count']} | {status} |")
    lines.append("")

    # 严重程度分布
    lines.append("## 问题严重程度分布")
    lines.append("")
    for severity, count in report["severity_summary"].items():
        lines.append(f"- **{severity}**: {count} 个")
    lines.append("")

    # 详细问题清单
    lines.append("## 详细问题清单")
    lines.append("")
    for i, issue in enumerate(report["issues"], 1):
        severity_color = {
            "Critical": "<span style='color:red'>Critical</span>",
            "High": "<span style='color:orange'>High</span>",
            "Medium": "<span style='color:gold'>Medium</span>",
            "Low": "<span style='color:green'>Low</span>",
        }[issue["severity"]]
        lines.append(f"### {i}. [{issue['dimension']}] {issue['category']}")
        lines.append("")
        lines.append(f"- **描述**: {issue['description']}")
        lines.append(f"- **严重程度**: {severity_color}")
        lines.append(f"- **影响数**: {issue['count']}")
        if issue["affected_pmids"]:
            lines.append(f"- **受影响PMID**: {', '.join(issue['affected_pmids'])}")
        lines.append(f"- **改进建议**: {issue['suggestion']}")
        lines.append("")

    # 改进建议汇总
    lines.append("## 改进建议汇总")
    lines.append("")
    critical_issues = [i for i in report["issues"] if i["severity"] in ["Critical", "High"]]
    if critical_issues:
        lines.append("### 优先处理（Critical/High）")
        lines.append("")
        for issue in critical_issues:
            lines.append(f"- [ ] {issue['suggestion']}")
        lines.append("")

    medium_issues = [i for i in report["issues"] if i["severity"] == "Medium"]
    if medium_issues:
        lines.append("### 常规改进（Medium）")
        lines.append("")
        for issue in medium_issues:
            lines.append(f"- [ ] {issue['suggestion']}")
        lines.append("")

    low_issues = [i for i in report["issues"] if i["severity"] == "Low"]
    if low_issues:
        lines.append("### 优化项（Low）")
        lines.append("")
        for issue in low_issues:
            lines.append(f"- [ ] {issue['suggestion']}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """主入口"""
    logger.info("加载数据...")
    articles = load_data()
    if not articles:
        return 1

    logger.info(f"数据加载完成: {len(articles)} 篇文献")
    logger.info("执行六维度质量评估...")

    report = generate_report(articles)
    print_report(report)

    # 导出报告
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON格式
    json_path = REPORT_DIR / "six_dimension_quality_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown格式
    md_path = REPORT_DIR / "six_dimension_quality_report.md"
    md_content = generate_markdown_report(report)
    md_path.write_text(md_content, encoding="utf-8")

    logger.info(f"\n评估报告已导出:")
    logger.info(f"  - JSON: {json_path}")
    logger.info(f"  - Markdown: {md_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
