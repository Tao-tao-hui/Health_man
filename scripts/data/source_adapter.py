"""数据源适配器抽象基类

所有具体数据源适配器（NHANES/KNHANES/CHNS 等）必须继承本类并实现全部抽象方法。
设计目标：插件式扩展，新增数据源仅需实现接口，无需修改既有代码。
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class SourceAdapter(ABC):
    """数据源适配器抽象基类

    子类必须实现以下 4 个方法：
    - list_files(): 列出可下载文件清单
    - download(): 下载单个文件
    - verify_checksum(): 校验文件完整性
    - get_metadata_template(): 返回数据集元数据模板
    """

    @abstractmethod
    def list_files(self) -> list[dict[str, Any]]:
        """列出可下载文件清单

        Returns:
            文件元数据列表，每个元素必须包含：
            - url: 下载 URL
            - filename: 目标文件名
            - expected_size_bytes: 预期文件大小（字节）
        """
        ...

    @abstractmethod
    def download(self, file_meta: dict[str, Any], dest_dir: Path) -> Path:
        """下载单个文件

        Args:
            file_meta: list_files() 返回的文件元数据
            dest_dir: 目标目录

        Returns:
            下载后的本地文件路径
        """
        ...

    @abstractmethod
    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """校验文件完整性

        Args:
            file_path: 本地文件路径
            expected_sha256: 预期的 SHA256 哈希值

        Returns:
            校验是否通过
        """
        ...

    @abstractmethod
    def get_metadata_template(self) -> dict[str, Any]:
        """返回该数据集的元数据模板（L0 卡片）

        Returns:
            含 dataset_id, source_url, license 等必填字段的字典
        """
        ...
