"""PubMed 文献检索适配器

使用 NCBI E-utilities API 检索中国人群 BIA/体成分相关文献。
- esearch: 检索 PubMed，返回 PMID 列表
- esummary: 获取文献详情（标题、作者、年份）
- efetch: 下载摘要 XML 全文

数据源：PubMed Central
License：PMC Open Access（部分文献全文）；摘要为公共领域
覆盖指标：IND-01~21（BIA 体成分 + PPG 心率相关文献）
"""
import hashlib
from pathlib import Path
from typing import Any

import requests

from scripts.data.source_adapter import SourceAdapter
from scripts.utils.circuit_breaker import CircuitBreaker
from scripts.utils.rate_limiter import TokenBucketLimiter
from scripts.utils.retry import retry_with_backoff


class PubMedAdapter(SourceAdapter):
    """PubMed NCBI E-utilities 文献检索适配器"""

    # NCBI E-utilities 端点
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    # 检索关键词：中国人群 + BIA/体成分
    SEARCH_QUERY = '("body composition" OR "BIA" OR "bioelectrical impedance") AND "China"[Affiliation]'
    MAX_RESULTS = 50  # NCBI 建议单次不超过 200

    # HTTP 请求头（含 User-Agent，符合 NCBI 礼貌访问要求）
    HEADERS = {"User-Agent": "HealthMan/0.1.0"}

    def __init__(self):
        """初始化安全工具链：限流器 + 熔断器"""
        # NCBI E-utilities 限速：3 请求/秒（桶容量 3，填充速率 3/秒）
        self.limiter = TokenBucketLimiter(capacity=3, refill_rate=3.0)
        # 连续失败 5 次熔断，冷却 30 秒
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

    def _acquire(self) -> None:
        """获取令牌并检查熔断状态（网络请求前调用）"""
        if not self.circuit_breaker.can_call():
            raise RuntimeError("PubMed 适配器熔断中，请稍后重试")
        self.limiter.acquire()

    def _safe_get(self, url: str, params: dict) -> requests.Response:
        """安全 GET 请求：限流 + 熔断 + 重试由外层装饰器处理

        统一封装 requests.get 调用，消除重复的 try/except 块（DRY）。
        - 调用 _acquire() 获取令牌并检查熔断状态
        - 请求成功时记录熔断器成功
        - 请求异常时记录熔断器失败并向上抛出，由 @retry_with_backoff 处理重试

        Args:
            url: 请求 URL
            params: 请求参数

        Returns:
            requests.Response 对象
        """
        self._acquire()
        try:
            response = requests.get(url, params=params, headers=self.HEADERS, timeout=30)
            response.raise_for_status()
            self.circuit_breaker.record_success()
            return response
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(requests.RequestException, RuntimeError))
    def list_files(self) -> list[dict[str, Any]]:
        """使用 esearch + esummary 检索 PubMed 文献

        Returns:
            文献元数据列表，每项含 pmid, url, filename, title, authors, year
        """
        # Step 1: esearch 检索 PMID 列表
        esearch_params = {
            "db": "pubmed",
            "term": self.SEARCH_QUERY,
            "retmax": str(self.MAX_RESULTS),
            "retmode": "json",
        }
        esearch_resp = self._safe_get(self.ESEARCH_URL, esearch_params)
        id_list = esearch_resp.json()["esearchresult"]["idlist"]

        if not id_list:
            return []

        # Step 2: esummary 获取文献详情
        esummary_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        esummary_resp = self._safe_get(self.ESUMMARY_URL, esummary_params)
        result_data = esummary_resp.json()["result"]

        files = []
        for pmid in id_list:
            article = result_data.get(pmid, {})
            title = article.get("title", "")
            pubdate = article.get("pubdate", "")
            year = pubdate[:4] if pubdate else ""
            authors = [a.get("name", "") for a in article.get("authors", [])]
            files.append({
                "pmid": pmid,
                "url": self.EFETCH_URL,
                "filename": f"pubmed_{pmid}_{year}.xml",
                "expected_size_bytes": 50_000,  # 估算：摘要 XML 约 50KB
                "title": title,
                "authors": authors,
                "year": year,
            })
        return files

    @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(requests.RequestException, RuntimeError))
    def download(self, file_meta: dict[str, Any], dest_dir: Path) -> Path:
        """使用 efetch 下载单篇文献摘要 XML

        Args:
            file_meta: 含 pmid 和 filename 的文献元数据
            dest_dir: 目标目录

        Returns:
            下载后的本地文件路径
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_meta["filename"]

        efetch_params = {
            "db": "pubmed",
            "id": file_meta["pmid"],
            "rettype": "abstract",
            "retmode": "xml",
        }
        response = self._safe_get(file_meta["url"], efetch_params)
        dest_path.write_bytes(response.content)
        return dest_path

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """校验文件 SHA256"""
        actual = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        return actual == expected_sha256

    def get_metadata_template(self) -> dict[str, Any]:
        """返回 PubMed 文献集的 L0 元数据模板"""
        return {
            "dataset_id": "PubMed_Literature",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/",
            "license": "PMC Open Access（部分）；摘要为公共领域",
            "region": "Global",
            "sample_size": self.MAX_RESULTS,
            "cycle": "2024",
            "update_frequency": "实时（NCBI E-utilities）",
            "population": "全球文献（检索关键词限定中国人群）",
            "known_bias": "文献检索偏倚（发表偏倚、语言偏倚）",
            "search_query": self.SEARCH_QUERY,
            "feasibility_score": 4.20,
        }
