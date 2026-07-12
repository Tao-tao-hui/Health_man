"""NHANES 2017-2020 数据源适配器

数据源：美国国家健康与营养调查（National Health and Nutrition Examination Survey）
提供方：CDC
License：Public Domain
样本量：9,092
覆盖指标：IND-01~14, 18~21（BIA 体成分 + PPG 心率）
"""
import hashlib
from pathlib import Path
from typing import Any

import requests

from scripts.data.source_adapter import SourceAdapter


class NHANESAdapter(SourceAdapter):
    """NHANES 2017-2020（Pre-Pandemic Cycle）数据源适配器"""

    BASE_URL = "https://wwwn.cdc.gov/Nchs/Nhanes"
    CYCLE = "2017-2018"
    CYCLE_SUFFIX = "J"  # 2017-2018 周期后缀为 J

    # 核心表清单（覆盖 IND-01~14, 18~21）
    TABLES = [
        {"table": "DEMO", "desc": "人口学", "size_bytes": 5_000_000},
        {"table": "BMX", "desc": "体格测量", "size_bytes": 3_000_000},
        {"table": "BPX", "desc": "血压与心率", "size_bytes": 8_000_000},
        {"table": "DUAL", "desc": "双能 X 线吸收测量", "size_bytes": 15_000_000},
        {"table": "TCHOL", "desc": "总胆固醇", "size_bytes": 2_000_000},
        {"table": "GLU", "desc": "空腹血糖", "size_bytes": 2_500_000},
    ]

    def list_files(self) -> list[dict[str, Any]]:
        """列出 NHANES 2017-2018 的核心 XPT 文件"""
        files = []
        for t in self.TABLES:
            filename = f"{t['table']}_{self.CYCLE_SUFFIX}.XPT"
            url = f"{self.BASE_URL}/{self.CYCLE}/{t['table']}_{self.CYCLE_SUFFIX}.XPT"
            files.append({
                "url": url,
                "filename": filename,
                "expected_size_bytes": t["size_bytes"],
                "table": t["table"],
                "description": t["desc"],
            })
        return files

    def download(self, file_meta: dict[str, Any], dest_dir: Path) -> Path:
        """下载单个 XPT 文件到 dest_dir

        Args:
            file_meta: 含 url, filename 的文件元数据
            dest_dir: 目标目录

        Returns:
            下载后的本地文件路径
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_meta["filename"]

        # 流式下载（支持大文件）
        response = requests.get(file_meta["url"], stream=True, timeout=30)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest_path

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """校验文件 SHA256

        Note: NHANES 官方未提供 SHA256，此处仅用于下载后自校验。
        expected_sha256 由首次下载成功后计算并记录。
        """
        actual = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        return actual == expected_sha256

    def get_metadata_template(self) -> dict[str, Any]:
        """返回 NHANES 数据集的 L0 元数据模板"""
        return {
            "dataset_id": "NHANES_2017_2020",
            "source_url": "https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017",
            "license": "Public Domain",
            "region": "US",
            "sample_size": 9092,
            "cycle": self.CYCLE,
            "update_frequency": "2 年/周期",
            "population": "美国全国代表样本",
            "known_bias": "种族分布与中国人群有差异",
            "feasibility_score": 4.10,
        }
