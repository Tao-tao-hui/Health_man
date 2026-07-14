"""相关性根因分析脚本"""
import json
import re
from pathlib import Path

DATA_DIR = Path("data/scraping")

# 加载所有文章
all_articles = []
for f in sorted(DATA_DIR.rglob("*.json")):
    data = json.loads(f.read_text(encoding="utf-8"))
    if data.get("data", {}).get("header", {}).get("type") == "esummary":
        result = data.get("data", {}).get("result", {})
        for uid in result.get("uids", []):
            art = result.get(uid, {})
            if isinstance(art, dict):
                all_articles.append(art)

keywords_map = {
    "BIA": ["bioelectrical", "impedance", "bia", "body composition"],
    "BCA": ["body composition", "assessment", "fat", "muscle", "bmi"],
    "HMS": ["health", "management", "system", "care", "patient"],
}

print(f"Total articles: {len(all_articles)}")
print(f"{'PMID':<12} {'Score':<8} {'Query':<6} {'Journal':<40} Title")
print("-" * 120)

low_score_count = 0
for art in all_articles:
    title = art.get("title") or ""
    pmid = art.get("uid", "")
    journal = art.get("fulljournalname") or ""

    # 取三个查询的最高分
    max_score = 0
    best_query = ""
    for qname, kws in keywords_map.items():
        title_lower = title.lower()
        matched = sum(1 for kw in kws if kw in title_lower)
        title_score = min(matched / max(len(kws) * 0.5, 1), 1.0) * 0.5

        journal_lower = journal.lower()
        journal_score = 1.0 if any(kw in journal_lower for kw in ["med", "health", "clin", "biol", "nutr", "endocr", "sports"]) else 0.0

        author_score = 1.0 * 0.1

        pubdate = art.get("pubdate", "")
        year_match = re.match(r"(\d{4})", pubdate)
        date_score = 1.0 if year_match and int(year_match.group(1)) >= 2024 else 0.4

        score = title_score + journal_score * 0.2 + author_score + date_score * 0.2
        if score > max_score:
            max_score = score
            best_query = qname

    if max_score < 0.5:
        low_score_count += 1

    title_short = title[:60]
    journal_short = journal[:38]
    print(f"{pmid:<12} {max_score:<8.2f} {best_query:<6} {journal_short:<40} {title_short}")

print(f"\nLow score (<0.5) count: {low_score_count}/{len(all_articles)}")
print(f"\nRoot cause analysis:")

# 分析标题关键词匹配情况
print("\nTitle keyword analysis:")
for qname, kws in keywords_map.items():
    match_counts = []
    for art in all_articles:
        title_lower = (art.get("title") or "").lower()
        matched = sum(1 for kw in kws if kw in title_lower)
        match_counts.append(matched)
    avg_match = sum(match_counts) / len(match_counts) if match_counts else 0
    zero_match = sum(1 for c in match_counts if c == 0)
    print(f"  {qname}: avg_matched={avg_match:.1f}, zero_match={zero_match}/{len(all_articles)}")

# 分析期刊分布
print("\nJournal distribution:")
journal_counter = {}
for art in all_articles:
    j = art.get("fulljournalname") or "unknown"
    journal_counter[j] = journal_counter.get(j, 0) + 1
for j, count in sorted(journal_counter.items(), key=lambda x: -x[1])[:10]:
    print(f"  {j}: {count}")

# 分析日期分布
print("\nDate distribution:")
date_counter = {}
for art in all_articles:
    d = art.get("pubdate") or "unknown"
    year = d[:4] if d[:4].isdigit() else "unknown"
    date_counter[year] = date_counter.get(year, 0) + 1
for y, count in sorted(date_counter.items()):
    print(f"  {y}: {count}")
