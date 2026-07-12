"""Layer B 文献元数据生成器

复用 Phase 1-2 的 MetadataGenerator 模式，
适配 Layer B 文献数据的特殊需求（提取方法、人工校验状态等）。

生成三层元数据：
- L0: 数据集卡片（含提取方法、质量评级）
- L1: 字段字典（含文献特定字段如 pmid, title, authors）
- L2: 使用说明（含已知偏差、适用场景）
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.data.quality_checker import QualityReport

logger = logging.getLogger(__name__)


class LiteratureMetadataGenerator:
    """Layer B 文献元数据生成器"""

    def generate_l0(
        self,
        adapter_meta: dict[str, Any],
        quality_report: QualityReport,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """生成 L0 数据集卡片

        Args:
            adapter_meta: 适配器元数据（含 dataset_id, source_url, license 等）
            quality_report: 质量校验报告
            output_path: 输出文件路径（可选）

        Returns:
            L0 数据集卡片字典
        """
        l0 = {
            "dataset_id": adapter_meta.get("dataset_id", "UNKNOWN"),
            "source_url": adapter_meta.get("source_url", ""),
            "license": adapter_meta.get("license", ""),
            "region": adapter_meta.get("region", ""),
            "sample_size": adapter_meta.get("sample_size", 0),
            "cycle": adapter_meta.get("cycle", ""),
            "update_frequency": adapter_meta.get("update_frequency", ""),
            "population": adapter_meta.get("population", ""),
            "known_bias": adapter_meta.get("known_bias", ""),
            "extraction_method": adapter_meta.get("extraction_method", ""),
            "quality": {
                "completeness": quality_report.completeness,
                "validity": quality_report.validity,
                "consistency": quality_report.consistency,
                "overall": quality_report.overall,
                "grade": quality_report.grade,
            },
            "row_count": quality_report.row_count,
            "column_count": quality_report.column_count,
            "generated_at": datetime.now().isoformat(),
        }
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(l0, f, ensure_ascii=False, indent=2)
            logger.info("L0 元数据已写入: %s", output_path)
        return l0

    def generate_l1(
        self,
        df: pd.DataFrame,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """生成 L1 字段字典

        Args:
            df: 文献数据 DataFrame
            output_path: 输出文件路径（可选）

        Returns:
            L1 字段字典
        """
        fields = []
        for col in df.columns:
            missing_rate = float(df[col].isna().mean())
            dtype = str(df[col].dtype)
            fields.append({
                "name": col,
                "type": dtype,
                "missing_rate": round(missing_rate, 4),
                "unique_count": int(df[col].nunique()),
            })
        l1 = {"fields": fields, "row_count": len(df)}
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(l1, f, ensure_ascii=False, indent=2)
            logger.info("L1 字段字典已写入: %s", output_path)
        return l1

    def generate_l2(
        self,
        adapter_meta: dict[str, Any],
        quality_report: QualityReport,
        output_path: Path | None = None,
    ) -> str:
        """生成 L2 使用说明（Markdown）

        Args:
            adapter_meta: 适配器元数据
            quality_report: 质量校验报告
            output_path: 输出文件路径（可选）

        Returns:
            L2 Markdown 文本
        """
        dataset_id = adapter_meta.get("dataset_id", "UNKNOWN")
        known_bias = adapter_meta.get("known_bias", "无")
        population = adapter_meta.get("population", "未指定")
        extraction_method = adapter_meta.get("extraction_method", "未指定")

        content = f"""# {dataset_id} 使用说明

## 适用场景
- 文献参考范围对标
- 中医体质判定辅助
- 人群分布分析

## 不适用场景
- 精度验证（文献数据非配对采集）
- 临床诊断
- 个体化评估

## 提取方法
{extraction_method}

## 已知偏差
{known_bias}

## 人群代表性
{population}

## 质量评级
- 等级: {quality_report.grade}
- 综合分: {quality_report.overall:.2f}
- 完整率: {quality_report.completeness:.2f}
- 合法率: {quality_report.validity:.2f}

## 引用格式
请引用数据集卡片（L0_card.json）中的 source_url

## 生成时间
{datetime.now().isoformat()}
"""
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("L2 使用说明已写入: %s", output_path)
        return content
