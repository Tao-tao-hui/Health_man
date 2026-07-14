"""医学内容深度分析脚本

对 29 篇 PubMed 文献摘要进行系统性分析：
1. 判断数据性质：专业知识 + 量化指标 vs 仅专业名词集合
2. 识别医学知识类型（疾病诊断、治疗方案、生理指标、研究方法等）
3. 提取量化指标（数值范围、统计数据、参考值等）
4. 分类专业名词及其所属医学子领域

用法：
    python -m scripts.scraping.medical_content_analysis
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
logger = logging.getLogger("medical_analysis")

DATA_DIR = Path("data/scraping/pubmed/abstracts")

# 医学知识类型定义
MEDICAL_KNOWLEDGE_TYPES = {
    "disease_diagnosis": {
        "description": "疾病诊断标准、诊断方法、鉴别诊断",
        "keywords": [
            "diagnosis", "diagnostic", "diagnose", "screen", "detect", "identify",
            "clinical trial", "symptom", "sign", "manifestation",
            "criteria", "classification", "staging",
        ],
    },
    "treatment_plan": {
        "description": "治疗方案、干预措施、药物治疗、手术治疗",
        "keywords": [
            "treatment", "therapy", "intervention", "management",
            "supplementation", "supplement", "protein", "collagen",
            "exercise", "training", "diet", "nutrition",
            "exercise intervention", "rehabilitation", "pilates", "yoga",
            "electrical stimulation", "neurolysis", "laser",
        ],
    },
    "physiological_index": {
        "description": "生理指标、生化指标、身体测量指标",
        "keywords": [
            "body composition", "muscle mass", "fat mass", "bone mineral density",
            "bmi", "waist circumference", "body weight",
            "blood glucose", "insulin", "hba1c", "homair",
            "lipid", "cholesterol", "triglyceride",
            "inflammatory", "cytokine", "crp", "tnf", "il6",
            "bone turnover", "biomarker", "p1np", "ctxi",
            "intestinal barrier", "zonulin", "dlactate", "mfg-e8",
        ],
    },
    "study_method": {
        "description": "研究方法、实验设计、样本量、统计方法",
        "keywords": [
            "randomized", "controlled trial", "doubleblind",
            "sample", "participant", "enroll", "screen",
            "cohort", "casecontrol", "crosssectional",
            "anova", "t-test", "regression", "correlation",
            "sensitivity", "specificity", "accuracy",
            "bioelectrical impedance", "dualenergy", "dexa",
            "16s rrna", "sequencing", "microbiota",
        ],
    },
    "pathophysiology": {
        "description": "病理生理机制、发病机制、分子机制",
        "keywords": [
            "mechanism", "pathway", "axis", "signaling",
            "microbiota", "gut", "intestinal barrier",
            "inflammation", "immune", "metabolic",
            "homeostasis", "regulation", "modulation",
            "adaptation", "remodeling",
        ],
    },
    "pharmacology": {
        "description": "药物作用、剂量、疗效、安全性",
        "keywords": [
            "dose", "dosage", "mg/day", "supplementation",
            "efficacy", "safety", "adverse", "side effect",
            "pharmacokinetic", "pharmacodynamic",
        ],
    },
}

# 医学子领域分类
MEDICAL_SUBDOMAINS = {
    "cardiology": ["hypertension", "cardiovascular", "heart", "bp", "blood pressure"],
    "endocrinology": ["diabetes", "insulin", "hormone", "thyroid", "endocrin", "adipose"],
    "gastroenterology": ["gut", "microbiota", "intestinal", "digestive", "stool"],
    "orthopedics": ["bone", "muscle", "skeletal", "fracture", "osteoporosis"],
    "neurology": ["brain", "neuro", "spine", "nervous", "cognitive"],
    "oncology": ["cancer", "tumor", "carcinoma", "oncology", "malignant"],
    "sports_medicine": ["exercise", "training", "fitness", "sports", "performance"],
    "nutrition": ["diet", "nutrition", "protein", "calorie", "supplement"],
    "immunology": ["immune", "inflammation", "cytokine", "antibody", "infect"],
    "public_health": ["healthcare", "management", "policy", "outcome", "population"],
}

# 量化指标模式
QUANTITATIVE_PATTERNS = {
    "measurement": re.compile(
        r"(\d+\.?\d*)\s*(kg|g|cm|mm|m|liter|ml|\u00b5g|ng|mmol|mg|pg|"
        r"cm²|g/cm²|%|years?|months?|days?|hours?|minutes?)"
    ),
    "ratio": re.compile(r"(\d+\.?\d*)\s*:\s*(\d+\.?\d*)"),
    "percentage": re.compile(r"(\d+\.?\d*)\s*%"),
    "statistical": re.compile(
        r"p\s*[<=>]\s*0?\.?\d+|confidence interval|ci\s*\(\d+,\s*\d+\)|"
        r"mean\s*±\s*sd|median|range|standard deviation|variance|"
        r"correlation|r\s*[=<>]\s*\d+\.?\d*|odds ratio|or\s*=\s*\d+\.?\d*|"
        r"hazard ratio|hr\s*=\s*\d+\.?\d*"
    ),
    "sample_size": re.compile(r"(n|sample|participant)s?\s*[=:]\s*(\d+)"),
    "score": re.compile(r"(score|index|scale)\s*[=:]\s*(\d+\.?\d*)"),
    "change": re.compile(r"Δ\s*=\s*(\d+\.?\d*)|change\s*of\s*(\d+\.?\d*)"),
}


def load_all_abstracts() -> dict:
    """加载所有摘要数据"""
    merged_path = DATA_DIR / "all_abstracts.json"
    if not merged_path.exists():
        logger.error("摘要文件不存在")
        return {}
    return json.loads(merged_path.read_text(encoding="utf-8"))


def analyze_knowledge_types(abstract: str) -> dict[str, bool]:
    """分析摘要中包含的医学知识类型"""
    result = {}
    abstract_lower = abstract.lower()
    for knowledge_type, config in MEDICAL_KNOWLEDGE_TYPES.items():
        matched = any(kw in abstract_lower for kw in config["keywords"])
        result[knowledge_type] = matched
    return result


def analyze_subdomains(abstract: str) -> dict[str, bool]:
    """分析摘要涉及的医学子领域"""
    result = {}
    abstract_lower = abstract.lower()
    for subdomain, keywords in MEDICAL_SUBDOMAINS.items():
        matched = any(kw in abstract_lower for kw in keywords)
        result[subdomain] = matched
    return result


def extract_quantitative_data(abstract: str) -> dict:
    """提取量化指标"""
    result = {
        "measurements": [],
        "percentages": [],
        "statistics": [],
        "sample_sizes": [],
        "scores": [],
        "changes": [],
        "total_quantitative_items": 0,
    }

    # 测量值
    for match in QUANTITATIVE_PATTERNS["measurement"].finditer(abstract):
        result["measurements"].append(f"{match.group(1)} {match.group(2)}")

    # 百分比
    for match in QUANTITATIVE_PATTERNS["percentage"].finditer(abstract):
        result["percentages"].append(f"{match.group(1)}%")

    # 统计数据
    for match in QUANTITATIVE_PATTERNS["statistical"].finditer(abstract):
        result["statistics"].append(match.group(0))

    # 样本量
    for match in QUANTITATIVE_PATTERNS["sample_size"].finditer(abstract):
        result["sample_sizes"].append(match.group(0))

    # 分数/指数
    for match in QUANTITATIVE_PATTERNS["score"].finditer(abstract):
        result["scores"].append(match.group(0))

    # 变化量
    for match in QUANTITATIVE_PATTERNS["change"].finditer(abstract):
        result["changes"].append(match.group(0))

    # 计算总量化指标数
    result["total_quantitative_items"] = (
        len(result["measurements"])
        + len(result["percentages"])
        + len(result["statistics"])
        + len(result["sample_sizes"])
        + len(result["scores"])
        + len(result["changes"])
    )

    return result


def extract_medical_terms(abstract: str) -> dict:
    """提取医学专业名词"""
    term_patterns = {
        "diseases": re.compile(
            r"\b(type 2 diabetes|t2dm|hypertension|obesity|sarcopenia|osteoporosis|"
            r"cancer|carcinoma|tumor|sleep apnea|osa|brain injury|"
            r"multiple myeloma|thyroid carcinoma|syndrome)\b",
            re.IGNORECASE,
        ),
        "treatments": re.compile(
            r"\b(whey protein|collagen|resistance training|pilates|yoga|"
            r"neuromuscular electrical stimulation|laser therapy|"
            r"lowglycemic diet|antihypertensive)\b",
            re.IGNORECASE,
        ),
        "tests": re.compile(
            r"\b(bioelectrical impedance analysis|bia|dualenergy xray|"
            r"dexa|ct scan|mri|16s rrna sequencing|elisa)\b",
            re.IGNORECASE,
        ),
        "biomarkers": re.compile(
            r"\b(hba1c|insulin|tnf[a-z]|il[-_]?\d+|crp|p1np|ctxi|"
            r"zonulin|mfg[-_]?e8|dlactate)\b",
            re.IGNORECASE,
        ),
        "organs": re.compile(
            r"\b(bone|muscle|gut|brain|spine|kidney|liver|thyroid|"
            r"nasal|oral|cardiovascular)\b",
            re.IGNORECASE,
        ),
    }

    result = {}
    for category, pattern in term_patterns.items():
        matches = [m.group(0) for m in pattern.finditer(abstract)]
        result[category] = list(set(matches))

    return result


def analyze_all_articles(abstracts: dict) -> dict:
    """分析所有文章"""
    analysis = {
        "summary": {
            "total_articles": len(abstracts),
            "total_word_count": sum(a["abstract_word_count"] for a in abstracts.values()),
            "articles_with_quantitative_data": 0,
            "articles_with_knowledge_types": 0,
            "total_quantitative_items": 0,
        },
        "knowledge_type_distribution": defaultdict(int),
        "subdomain_distribution": defaultdict(int),
        "quantitative_summary": {
            "measurements": [],
            "percentages": [],
            "statistics": [],
            "sample_sizes": [],
            "scores": [],
            "changes": [],
        },
        "medical_terms_summary": {
            "diseases": Counter(),
            "treatments": Counter(),
            "tests": Counter(),
            "biomarkers": Counter(),
            "organs": Counter(),
        },
        "article_details": [],
    }

    for pmid, article in abstracts.items():
        abstract = article.get("abstract", "")
        title = article.get("title", "")
        keywords = article.get("keywords", [])

        # 分析知识类型
        knowledge_types = analyze_knowledge_types(abstract)
        has_knowledge = any(knowledge_types.values())

        # 分析子领域
        subdomains = analyze_subdomains(abstract)

        # 提取量化数据
        quantitative = extract_quantitative_data(abstract)
        has_quantitative = quantitative["total_quantitative_items"] > 0

        # 提取医学名词
        medical_terms = extract_medical_terms(abstract)

        # 更新汇总
        for kt, present in knowledge_types.items():
            if present:
                analysis["knowledge_type_distribution"][kt] += 1

        for sd, present in subdomains.items():
            if present:
                analysis["subdomain_distribution"][sd] += 1

        if has_quantitative:
            analysis["summary"]["articles_with_quantitative_data"] += 1
            analysis["summary"]["total_quantitative_items"] += quantitative["total_quantitative_items"]

        if has_knowledge:
            analysis["summary"]["articles_with_knowledge_types"] += 1

        for cat, terms in medical_terms.items():
            for term in terms:
                analysis["medical_terms_summary"][cat][term.lower()] += 1

        # 收集量化数据样本
        analysis["quantitative_summary"]["measurements"].extend(quantitative["measurements"][:3])
        analysis["quantitative_summary"]["percentages"].extend(quantitative["percentages"][:3])
        analysis["quantitative_summary"]["statistics"].extend(quantitative["statistics"][:3])
        analysis["quantitative_summary"]["sample_sizes"].extend(quantitative["sample_sizes"][:3])

        # 记录文章详情
        analysis["article_details"].append({
            "pmid": pmid,
            "title": title,
            "word_count": article.get("abstract_word_count", 0),
            "has_knowledge": has_knowledge,
            "has_quantitative": has_quantitative,
            "knowledge_types": [kt for kt, present in knowledge_types.items() if present],
            "subdomains": [sd for sd, present in subdomains.items() if present],
            "quantitative_items": quantitative["total_quantitative_items"],
            "keywords": keywords[:5],
        })

    return analysis


def print_analysis_report(analysis: dict) -> None:
    """打印分析报告"""
    logger.info("=" * 70)
    logger.info("医学内容深度分析报告")
    logger.info("=" * 70)

    # 摘要统计
    logger.info("\n[1] 数据概览")
    logger.info("-" * 40)
    logger.info(f"  文献总数: {analysis['summary']['total_articles']}")
    logger.info(f"  总词数: {analysis['summary']['total_word_count']:,}")
    logger.info(f"  篇均词数: {analysis['summary']['total_word_count'] // analysis['summary']['total_articles']}")
    logger.info(f"  含量化指标的文章: {analysis['summary']['articles_with_quantitative_data']}/{analysis['summary']['total_articles']}")
    logger.info(f"  含医学知识的文章: {analysis['summary']['articles_with_knowledge_types']}/{analysis['summary']['total_articles']}")
    logger.info(f"  总量化指标数: {analysis['summary']['total_quantitative_items']}")

    # 核心判断
    has_knowledge = analysis["summary"]["articles_with_knowledge_types"] > 0
    has_quantitative = analysis["summary"]["articles_with_quantitative_data"] > 0
    logger.info("\n[2] 数据性质判断")
    logger.info("-" * 40)
    if has_knowledge and has_quantitative:
        logger.info("  ✅ 数据包含: 医学专业知识 + 量化指标")
        logger.info("  判断依据: 存在具体的疾病诊断、治疗方案、生理指标描述")
        logger.info("            存在具体数值、统计数据、参考范围等量化信息")
    elif has_knowledge and not has_quantitative:
        logger.info("  ⚠️ 数据包含: 医学专业知识（无量化指标）")
    elif not has_knowledge and has_quantitative:
        logger.info("  ⚠️ 数据包含: 量化指标（无明显医学知识）")
    else:
        logger.info("  ❌ 数据仅包含: 医学专业名词集合")

    # 医学知识类型分布
    logger.info("\n[3] 医学知识类型分布")
    logger.info("-" * 40)
    for kt, count in sorted(analysis["knowledge_type_distribution"].items(), key=lambda x: -x[1]):
        desc = MEDICAL_KNOWLEDGE_TYPES[kt]["description"]
        bar = "#" * count
        logger.info(f"  {kt:25s} {count:2d} {bar}")
        logger.info(f"      → {desc}")

    # 医学子领域分布
    logger.info("\n[4] 医学子领域分布")
    logger.info("-" * 40)
    for sd, count in sorted(analysis["subdomain_distribution"].items(), key=lambda x: -x[1]):
        bar = "#" * count
        logger.info(f"  {sd:20s} {count:2d} {bar}")

    # 量化指标分析
    logger.info("\n[5] 量化指标分析")
    logger.info("-" * 40)
    qs = analysis["quantitative_summary"]
    logger.info(f"  测量值示例 ({len(qs['measurements'])}):")
    for m in qs["measurements"][:5]:
        logger.info(f"    - {m}")
    logger.info(f"\n  百分比示例 ({len(qs['percentages'])}):")
    for p in qs["percentages"][:5]:
        logger.info(f"    - {p}")
    logger.info(f"\n  统计数据示例 ({len(qs['statistics'])}):")
    for s in qs["statistics"][:5]:
        logger.info(f"    - {s}")
    logger.info(f"\n  样本量示例 ({len(qs['sample_sizes'])}):")
    for ss in qs["sample_sizes"][:5]:
        logger.info(f"    - {ss}")

    # 医学名词分类
    logger.info("\n[6] 医学专业名词分类")
    logger.info("-" * 40)
    mts = analysis["medical_terms_summary"]
    for cat, counter in mts.items():
        terms = [f"{term}({count})" for term, count in counter.most_common(5)]
        logger.info(f"  {cat:15s}: {', '.join(terms) if terms else '无'}")

    # 文章详情（前5篇）
    logger.info("\n[7] 代表性文章分析")
    logger.info("-" * 40)
    for art in analysis["article_details"][:5]:
        logger.info(f"\n  PMID: {art['pmid']}")
        logger.info(f"  标题: {art['title'][:70]}...")
        logger.info(f"  词数: {art['word_count']}")
        logger.info(f"  知识类型: {', '.join(art['knowledge_types'])}")
        logger.info(f"  子领域: {', '.join(art['subdomains'])}")
        logger.info(f"  量化指标数: {art['quantitative_items']}")
        logger.info(f"  关键词: {', '.join(art['keywords'])}")

    logger.info("\n" + "=" * 70)


def main() -> int:
    """主入口"""
    logger.info("加载摘要数据...")
    abstracts = load_all_abstracts()
    if not abstracts:
        logger.error("未找到摘要数据")
        return 1

    logger.info("执行医学内容分析...")
    analysis = analyze_all_articles(abstracts)

    print_analysis_report(analysis)

    # 导出分析报告
    output_dir = Path("data/scraping/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "medical_content_analysis.json"
    report_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"\n分析报告已导出: {report_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
