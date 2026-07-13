"""下载 PubMed 文献摘要

使用 PubMedAdapter 从 NCBI E-utilities 下载中国人群 BIA/体成分相关文献摘要。
支持多种检索查询（骨骼肌、HRV、中医体质），每次修改 SEARCH_QUERY 后重新检索。
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.data.adapters.pubmed_adapter import PubMedAdapter


def download_literature_batch(query_name: str, search_query: str, max_results: int, dest_dir: Path):
    """下载一批 PubMed 文献摘要

    Args:
        query_name: 查询名称（用于日志）
        search_query: PubMed 检索表达式
        max_results: 最大结果数
        dest_dir: 下载目标目录

    Returns:
        下载的文件数量
    """
    # 创建适配器实例
    adapter = PubMedAdapter()

    # 临时修改检索查询和最大结果数
    adapter.SEARCH_QUERY = search_query
    adapter.MAX_RESULTS = max_results

    print(f"\n{'='*60}")
    print(f"检索批次: {query_name}")
    print(f"查询: {search_query[:80]}...")
    print(f"最大结果: {max_results}")
    print(f"目标目录: {dest_dir}")
    print(f"{'='*60}")

    # 检索文献列表
    try:
        files = adapter.list_files()
        print(f"检索到 {len(files)} 篇文献")
    except Exception as e:
        print(f"检索失败: {e}")
        return 0

    if not files:
        print("未检索到文献，跳过下载")
        return 0

    # 打印前 5 篇文献标题
    for i, f in enumerate(files[:5]):
        title = f.get("title", "")[:80]
        pmid = f.get("pmid", "")
        year = f.get("year", "")
        print(f"  {i+1}. PMID={pmid} ({year}) {title}")
    if len(files) > 5:
        print(f"  ... 还有 {len(files) - 5} 篇")

    # 逐篇下载
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded_count = 0
    for i, file_meta in enumerate(files):
        try:
            # 检查文件是否已存在（避免重复下载）
            dest_path = dest_dir / file_meta["filename"]
            if dest_path.exists() and dest_path.stat().st_size > 0:
                print(f"  [{i+1}/{len(files)}] 跳过（已存在）: {file_meta['filename']}")
                downloaded_count += 1
                continue

            # 下载
            adapter.download(file_meta, dest_dir)
            downloaded_count += 1
            print(f"  [{i+1}/{len(files)}] 下载成功: {file_meta['filename']}")

            # NCBI 礼貌延迟（避免过快请求）
            time.sleep(0.5)
        except Exception as e:
            print(f"  [{i+1}/{len(files)}] 下载失败: {e}")

    print(f"批次 {query_name} 完成: {downloaded_count}/{len(files)} 篇下载成功")
    return downloaded_count


def main():
    """主函数：执行多批次 PubMed 文献下载"""
    b_lit = Path("data/knowledge/chinese_reference/B_literature")

    # 定义检索批次
    batches = [
        {
            "name": "BONE_BODY_COMPOSITION",
            "query": '("body composition" OR "BIA" OR "bioelectrical impedance") AND "China"[Affiliation]',
            "max_results": 50,
            "dest_dir": b_lit / "pubmed" / "abstracts",
        },
        {
            "name": "HRV_RMSSD_SDNN",
            "query": '("heart rate variability" OR "HRV" OR "RMSSD" OR "SDNN") AND "China"[Affiliation]',
            "max_results": 50,
            "dest_dir": b_lit / "pubmed" / "abstracts",
        },
        {
            "name": "TCM_CONSTITUTION",
            "query": '("traditional Chinese medicine" OR "constitution" OR "body constitution") AND "China"[Affiliation]',
            "max_results": 50,
            "dest_dir": b_lit / "pubmed" / "abstracts",
        },
    ]

    total_downloaded = 0
    for batch in batches:
        count = download_literature_batch(
            query_name=batch["name"],
            search_query=batch["query"],
            max_results=batch["max_results"],
            dest_dir=batch["dest_dir"],
        )
        total_downloaded += count

    print(f"\n{'='*60}")
    print(f"全部下载完成: 共 {total_downloaded} 篇文献")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
