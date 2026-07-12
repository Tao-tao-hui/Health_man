"""OpenScienceAdapter 单元测试

验证 figshare API 检索和下载功能。
网络请求使用 mock（不可重放，unavoidable）。
"""
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

from scripts.data.adapters.openscience_adapter import OpenScienceAdapter


class TestOpenScienceAdapter:
    """OpenScienceAdapter 测试套件"""

    def test_list_files_returns_dataset_list(self):
        """测试 figshare API 检索返回数据集列表"""
        adapter = OpenScienceAdapter()
        # mock figshare 搜索接口（POST 请求返回文章列表）
        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = [
            {
                "id": 12345,
                "title": "Chinese Body Composition Dataset",
                "doi": "10.6084/m9.figshare.12345",
            }
        ]
        # mock 文章文件列表接口（GET 请求返回文件详情，list_files 会二次请求）
        mock_files_response = MagicMock()
        mock_files_response.status_code = 200
        mock_files_response.json.return_value = [
            {"name": "data.csv", "size": 1024, "download_url": "https://ndownloader.figshare.com/files/67890"}
        ]
        # 实现中 list_files 先 POST 搜索文章，再 GET 获取每个文章的文件列表
        with patch("scripts.data.adapters.openscience_adapter.requests.post",
                    return_value=mock_search_response), \
             patch("scripts.data.adapters.openscience_adapter.requests.get",
                    return_value=mock_files_response):
            files = adapter.list_files()
        assert len(files) >= 1
        assert "url" in files[0]
        assert "filename" in files[0]
        assert "expected_size_bytes" in files[0]

    def test_download_fetches_dataset_file(self, tmp_path):
        """测试下载数据集文件"""
        adapter = OpenScienceAdapter()
        file_meta = {
            "url": "https://ndownloader.figshare.com/files/67890",
            "filename": "figshare_12345_data.csv",
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"col1,col2\n1,2\n"
        with patch("scripts.data.adapters.openscience_adapter.requests.get",
                    return_value=mock_response):
            result_path = adapter.download(file_meta, tmp_path)
        assert result_path.exists()
        assert result_path.read_bytes() == mock_response.content

    def test_verify_checksum_correct(self, tmp_path):
        """测试 SHA256 校验通过"""
        test_file = tmp_path / "test.csv"
        content = b"col1,col2\n1,2\n"
        test_file.write_bytes(content)
        expected_sha = hashlib.sha256(content).hexdigest()
        adapter = OpenScienceAdapter()
        assert adapter.verify_checksum(test_file, expected_sha) is True

    def test_get_metadata_template_has_required_fields(self):
        """测试 L0 元数据模板包含必填字段"""
        adapter = OpenScienceAdapter()
        meta = adapter.get_metadata_template()
        assert meta["dataset_id"] == "OpenScience_Repositories"
        assert "source_url" in meta
        assert "license" in meta
        assert "platforms" in meta

    def test_circuit_breaker_records_failure(self, tmp_path):
        """测试网络失败时熔断器记录失败

        验证安全工具链的失败路径：requests.get 抛出异常时，
        _safe_request 应调用 circuit_breaker.record_failure()。
        @retry_with_backoff(max_retries=3) 会重试 3 次（共 4 次尝试），
        因此 _failure_count 最终为 4（< failure_threshold=5，不会熔断）。
        """
        adapter = OpenScienceAdapter()
        file_meta = {
            "url": "https://ndownloader.figshare.com/files/67890",
            "filename": "figshare_12345_data.csv",
        }
        # mock requests.get 抛出异常，触发失败路径
        with patch("scripts.data.adapters.openscience_adapter.requests.get",
                    side_effect=requests.RequestException("Network error")):
            with pytest.raises(requests.RequestException):
                adapter.download(file_meta, tmp_path)
        # 熔断器应记录失败（retry_with_backoff 重试 3 次，_failure_count >= 1）
        assert adapter.circuit_breaker._failure_count >= 1
