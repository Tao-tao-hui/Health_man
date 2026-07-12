"""测试 NHANES 适配器"""
from scripts.data.adapters.nhanes_adapter import NHANESAdapter


def test_nhanes_adapter_inherits_source_adapter():
    """NHANESAdapter 必须继承 SourceAdapter"""
    from scripts.data.source_adapter import SourceAdapter
    adapter = NHANESAdapter()
    assert isinstance(adapter, SourceAdapter)


def test_list_files_returns_expected_tables():
    """list_files 必须返回 NHANES 2017-2020 的核心表"""
    adapter = NHANESAdapter()
    files = adapter.list_files()
    filenames = [f["filename"] for f in files]
    # 必须包含人口学与体格测量表
    assert "DEMO_J.XPT" in filenames
    assert "BMX_J.XPT" in filenames
    # 必须包含血压与心率表
    assert "BPX_J.XPT" in filenames


def test_list_files_has_valid_urls():
    """每个文件必须有合法的 CDC URL"""
    adapter = NHANESAdapter()
    files = adapter.list_files()
    for f in files:
        assert f["url"].startswith("https://wwwn.cdc.gov/Nchs/Nhanes/")
        assert f["filename"] in f["url"]
        assert f["expected_size_bytes"] > 0


def test_get_metadata_template_has_required_fields():
    """元数据模板必须含 dataset_id, source_url, license"""
    adapter = NHANESAdapter()
    meta = adapter.get_metadata_template()
    assert meta["dataset_id"] == "NHANES_2017_2020"
    assert meta["source_url"].startswith("https://wwwn.cdc.gov/")
    assert meta["license"] == "Public Domain"
    assert meta["region"] == "US"
    assert meta["sample_size"] == 9092
