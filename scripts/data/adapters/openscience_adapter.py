"""开放科学平台数据集适配器

支持 figshare / Dryad / Zenodo 三个平台的公开数据集检索下载。
当前实现聚焦 figshare API（最常用），Dryad/Zenodo 后续按需扩展。

数据源：figshare (https://api.figshare.com/v2)
License：CC-BY 4.0（默认，具体按数据集标注）
覆盖指标：IND-01~21（辅助验证数据集）
"""
import hashlib
from pathlib import Path
from typing import Any

import requests

from scripts.data.source_adapter import SourceAdapter
from scripts.utils.circuit_breaker import CircuitBreaker
from scripts.utils.rate_limiter import TokenBucketLimiter
from scripts.utils.retry import retry_with_backoff


class OpenScienceAdapter(SourceAdapter):
    """figshare/Dryad/Zenodo 开放数据集适配器"""

    # figshare API 端点
    FIGSHARE_SEARCH_URL = "https://api.figshare.com/v2/articles/search"
    FIGSHARE_ARTICLE_FILES_URL = "https://api.figshare.com/v2/articles/{article_id}/files"

    # 检索关键词：中国人群 + 体成分
    SEARCH_KEYWORDS = "body composition BIA China"
    MAX_RESULTS = 20

    # HTTP 请求头（含 User-Agent，符合开放平台礼貌访问要求）
    HEADERS = {"User-Agent": "HealthMan/0.1.0"}

    def __init__(self):
        """初始化安全工具链：限流器 + 熔断器"""
        # figshare API 限速：约 1 请求/秒（桶容量 2，填充速率 1/秒）
        self.limiter = TokenBucketLimiter(capacity=2, refill_rate=1.0)
        # 连续失败 5 次熔断，冷却 30 秒
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

    def _acquire(self) -> None:
        """获取令牌并检查熔断状态（网络请求前调用）"""
        if not self.circuit_breaker.can_call():
            raise RuntimeError("开放科学平台适配器熔断中，请稍后重试")
        self.limiter.acquire()

    def _safe_request(
        self,
        method: str,
        url: str,
        timeout: int = 30,
        **kwargs,
    ) -> requests.Response:
        """安全 HTTP 请求：限流 + 熔断 + 重试由外层装饰器处理

        统一封装 requests.post / requests.get 调用，消除重复的 try/except 块（DRY）。
        - 调用 _acquire() 获取令牌并检查熔断状态
        - 请求成功时记录熔断器成功
        - 请求异常时记录熔断器失败并向上抛出，由 @retry_with_backoff 处理重试

        Args:
            method: HTTP 方法（"POST" 或 "GET"）
            url: 请求 URL
            timeout: 请求超时时间（秒），默认 30
            **kwargs: 透传给 requests 的额外参数（如 json, params）

        Returns:
            requests.Response 对象
        """
        self._acquire()
        # 根据 method 选择对应的 requests 函数（POST 用于搜索，GET 用于文件列表/下载）
        request_func = getattr(requests, method.lower())
        try:
            kwargs.setdefault("headers", self.HEADERS)
            response = request_func(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            self.circuit_breaker.record_success()
            return response
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(requests.RequestException, RuntimeError))
    def list_files(self) -> list[dict[str, Any]]:
        """检索 figshare 上的中国体成分相关数据集

        流程：
        1. POST /v2/articles/search 搜索文章列表
        2. GET /v2/articles/{id}/files 获取每个文章下的文件清单

        Returns:
            数据集文件列表，每项含 url, filename, expected_size_bytes, dataset_id, title
        """
        search_payload = {
            "search_for": self.SEARCH_KEYWORDS,
            "page_size": self.MAX_RESULTS,
        }
        # Step 1: 搜索文章（figshare 要求 POST）
        search_resp = self._safe_request(
            "POST", self.FIGSHARE_SEARCH_URL, json=search_payload
        )
        articles = search_resp.json()

        # Step 2: 获取每个文章的文件清单
        files = []
        for article in articles:
            article_id = article.get("id", "")
            title = article.get("title", "")
            files_url = self.FIGSHARE_ARTICLE_FILES_URL.format(article_id=article_id)
            files_resp = self._safe_request("GET", files_url)
            article_files = files_resp.json()
            for f in article_files:
                files.append({
                    "url": f.get("download_url", ""),
                    "filename": f"figshare_{article_id}_{f.get('name', 'unknown')}",
                    "expected_size_bytes": f.get("size", 0),
                    "dataset_id": article_id,
                    "title": title,
                })
        return files

    @retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(requests.RequestException, RuntimeError))
    def download(self, file_meta: dict[str, Any], dest_dir: Path) -> Path:
        """下载单个数据集文件

        Args:
            file_meta: 含 url 和 filename 的文件元数据
            dest_dir: 目标目录

        Returns:
            下载后的本地文件路径
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_meta["filename"]

        # 下载数据集文件，超时设为 60 秒（数据集可能较大）
        response = self._safe_request("GET", file_meta["url"], timeout=60)
        dest_path.write_bytes(response.content)
        return dest_path

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """校验文件 SHA256"""
        actual = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        return actual == expected_sha256

    def get_metadata_template(self) -> dict[str, Any]:
        """返回开放科学平台的 L0 元数据模板"""
        return {
            "dataset_id": "OpenScience_Repositories",
            "source_url": "https://figshare.com",
            "license": "CC-BY 4.0（具体按数据集标注）",
            "region": "Global",
            "sample_size": self.MAX_RESULTS,
            "cycle": "2024",
            "update_frequency": "实时（API 检索）",
            "population": "全球开放数据集（检索关键词限定中国人群）",
            "known_bias": "数据集质量参差不齐，需逐集校验",
            "platforms": ["figshare", "dryad", "zenodo"],
            "feasibility_score": 3.80,
        }
