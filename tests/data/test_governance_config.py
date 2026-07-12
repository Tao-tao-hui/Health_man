"""测试治理配置文件的完整性与可加载性"""
import json
from pathlib import Path
import yaml

GOVERNANCE_DIR = Path("e:/Health_man/data/knowledge/chinese_reference/_governance")


def test_config_yaml_loads_successfully():
    """config.yaml 必须存在且可被 PyYAML 解析"""
    config_path = GOVERNANCE_DIR / "config.yaml"
    assert config_path.exists(), f"配置文件不存在: {config_path}"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert config is not None, "config.yaml 内容为空"
    assert "datasets" in config, "config.yaml 缺少 datasets 节"
    assert "preprocessing" in config, "config.yaml 缺少 preprocessing 节"
    assert "quality" in config, "config.yaml 缺少 quality 节"


def test_config_has_nhanes_entry():
    """config.yaml 必须包含 NHANES_2017_2020 数据集配置"""
    with open(GOVERNANCE_DIR / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    nhanes = config["datasets"].get("NHANES_2017_2020")
    assert nhanes is not None, "config.yaml 缺少 NHANES_2017_2020 配置"
    assert nhanes["enabled"] is True
    assert nhanes["priority"] == 1
    assert nhanes["max_concurrent"] == 3
    assert nhanes["max_size_mb"] == 200
    assert nhanes["retry"]["max_attempts"] == 3


def test_indicator_mapping_has_bmi():
    """indicator_mapping.json 必须包含 BMI 映射"""
    mapping_path = GOVERNANCE_DIR / "indicator_mapping.json"
    assert mapping_path.exists()
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    assert "indicator_mapping" in mapping
    im = mapping["indicator_mapping"]
    assert im.get("BMI") == "bmi"
    assert im.get("BMXBMI") == "bmi"
    assert im.get("体脂率") == "body_fat_pct"
    assert im.get("BMXBFP") == "body_fat_pct"


def test_quality_rules_have_grade_thresholds():
    """quality_rules.yaml 必须包含 A/B/C/D 评级阈值"""
    rules_path = GOVERNANCE_DIR / "quality_rules.yaml"
    assert rules_path.exists()
    with open(rules_path, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    thresholds = rules.get("grade_thresholds")
    assert thresholds is not None
    assert thresholds["A"] == 0.9
    assert thresholds["B"] == 0.8
    assert thresholds["C"] == 0.7
    assert thresholds["D"] == 0.0


def test_roles_yaml_has_three_roles():
    """roles.yaml 必须定义 reader/writer/admin 三个角色"""
    roles_path = GOVERNANCE_DIR / "roles.yaml"
    assert roles_path.exists()
    with open(roles_path, "r", encoding="utf-8") as f:
        roles = yaml.safe_load(f)
    assert "roles" in roles
    role_names = [r["name"] for r in roles["roles"]]
    assert "reader" in role_names
    assert "writer" in role_names
    assert "admin" in role_names


def test_data_catalog_json_is_valid():
    """data_catalog.json 必须是合法 JSON 且含 datasets 数组"""
    catalog_path = (
        Path("e:/Health_man/data/knowledge/chinese_reference")
        / "A_open_datasets/_metadata/data_catalog.json"
    )
    assert catalog_path.exists()
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    assert "datasets" in catalog
    assert isinstance(catalog["datasets"], list)
    assert len(catalog["datasets"]) >= 1
