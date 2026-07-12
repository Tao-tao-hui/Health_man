"""PubMedAdapter 单元测试

验证 NCBI E-utilities 检索和摘要下载功能。
网络请求使用 mock（不可重放，unavoidable）。
"""
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scripts.data.adapters.pubmed_adapter import PubMedAdapter


class TestPubMedAdapter:
    """PubMedAdapter 测试套件"""

    def test_list_files_returns_pmid_list(self):
        """测试 esearch 检索返回 PMID 列表"""
        adapter = PubMedAdapter()
        # mock esearch 返回 2 条结果
        mock_esearch_response = MagicMock()
        mock_esearch_response.status_code = 200
        mock_esearch_response.json.return_value = {
            "esearchresult": {
                "idlist": ["34567890", "35678901"],
                "count": "2"
            }
        }
        # mock esummary 返回文献详情
        mock_esummary_response = MagicMock()
        mock_esummary_response.status_code = 200
        mock_esummary_response.json.return_value = {
            "result": {
                "34567890": {
                    "title": "Body composition analysis in Chinese adults",
                    "pubdate": "2023",
                    "authors": [{"name": "Zhang W"}, {"name": "Li X"}]
                },
                "35678901": {
                    "title": "BIA validation study",
                    "pubdate": "2024",
                    "authors": [{"name": "Wang Y"}]
                }
            }
        }
        with patch("scripts.data.adapters.pubmed_adapter.requests.get",
                    side_effect=[mock_esearch_response, mock_esummary_response]):
            files = adapter.list_files()
        assert len(files) == 2
        assert files[0]["pmid"] == "34567890"
        assert "title" in files[0]
        assert "url" in files[0]
        assert "filename" in files[0]
        assert "expected_size_bytes" in files[0]

    def test_download_fetches_abstract_xml(self, tmp_path):
        """测试 efetch 下载摘要 XML"""
        adapter = PubMedAdapter()
        file_meta = {
            "pmid": "34567890",
            "filename": "pubmed_34567890_2023.xml",
            "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<PubmedArticle><PMID>34567890</PMID></PubmedArticle>"
        with patch("scripts.data.adapters.pubmed_adapter.requests.get",
                    return_value=mock_response):
            result_path = adapter.download(file_meta, tmp_path)
        assert result_path.exists()
        assert result_path.suffix == ".xml"
        assert result_path.read_bytes() == mock_response.content

    def test_verify_checksum_correct(self, tmp_path):
        """测试 SHA256 校验通过"""
        test_file = tmp_path / "test.xml"
        content = b"<test>content</test>"
        test_file.write_bytes(content)
        expected_sha = hashlib.sha256(content).hexdigest()
        adapter = PubMedAdapter()
        assert adapter.verify_checksum(test_file, expected_sha) is True

    def test_get_metadata_template_has_required_fields(self):
        """测试 L0 元数据模板包含必填字段"""
        adapter = PubMedAdapter()
        meta = adapter.get_metadata_template()
        assert meta["dataset_id"] == "PubMed_Literature"
        assert "source_url" in meta
        assert "license" in meta
        assert meta["region"] == "Global"
        assert "search_query" in meta
