"""测试 SourceAdapter 抽象基类"""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.data.source_adapter import SourceAdapter


def test_source_adapter_is_abstract():
    """SourceAdapter 不可直接实例化"""
    with pytest.raises(TypeError, match="abstract"):
        SourceAdapter()


def test_concrete_subclass_must_implement_all_methods():
    """子类必须实现全部 4 个抽象方法才能实例化"""

    class IncompleteAdapter(SourceAdapter):
        def list_files(self):
            return []

    with pytest.raises(TypeError, match="abstract"):
        IncompleteAdapter()


def test_complete_subclass_can_instantiate():
    """完整实现的子类可以实例化"""

    class FakeAdapter(SourceAdapter):
        def list_files(self):
            return [{"url": "http://example.com/test.csv", "filename": "test.csv", "expected_size_bytes": 100}]

        def download(self, file_meta, dest_dir):
            dest = Path(dest_dir) / file_meta["filename"]
            dest.write_bytes(b"test content")
            return dest

        def verify_checksum(self, file_path, expected_sha256):
            actual = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
            return actual == expected_sha256

        def get_metadata_template(self):
            return {"dataset_id": "FAKE", "source_url": "http://example.com"}

    adapter = FakeAdapter()
    assert adapter is not None
    files = adapter.list_files()
    assert len(files) == 1
    assert files[0]["filename"] == "test.csv"


def test_list_files_return_type():
    """list_files 返回值必须含 url, filename, expected_size_bytes 三个键"""

    class FakeAdapter(SourceAdapter):
        def list_files(self):
            return [{"url": "http://x.com/a.csv", "filename": "a.csv", "expected_size_bytes": 50}]

        def download(self, file_meta, dest_dir):
            return Path()

        def verify_checksum(self, file_path, expected_sha256):
            return True

        def get_metadata_template(self):
            return {}

    adapter = FakeAdapter()
    files = adapter.list_files()
    for f in files:
        assert "url" in f
        assert "filename" in f
        assert "expected_size_bytes" in f
