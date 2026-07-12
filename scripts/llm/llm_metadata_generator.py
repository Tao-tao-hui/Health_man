"""Layer C LLM 蒸馏元数据生成器

复用 Phase 1-2 的 MetadataGenerator 模式，
适配 Layer C LLM 蒸馏数据的特殊需求（模型信息、token 消耗、置信度等）。

生成三层元数据：
- L0: 数据集卡片（含模型信息、提取统计）
- L1: 字段字典（含 LLM 提取字段统计）
- L2: 使用说明（含已知局限、适用场景）
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.llm.llm_pipeline import LlmPipelineResult

logger = logging.getLogger(__name__)


class LlmMetadataGenerator:
    """Layer C LLM 蒸馏元数据生成器"""

    def generate_l0(
        self,
        pipeline_result: LlmPipelineResult,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """生成 L0 数据集卡片

        Args:
            pipeline_result: 流水线执行结果
            output_path: 输出文件路径（可选）

        Returns:
            L0 数据集卡片字典
        """
        l0 = {
            "dataset_id": "C_llm_distilled",
            "source_url": "LLM API (GLM-4-Flash / Qwen / DeepSeek)",
            "license": "内部使用，参考各模型服务条款",
            "region": "CN",
            "extraction_method": "LLM 蒸馏（主从多代理协作）",
            "total_extracted": pipeline_result.total_extracted,
            "total_validated": pipeline_result.total_validated,
            "total_rejected": pipeline_result.total_rejected,
            "total_tokens_consumed": pipeline_result.total_tokens_consumed,
            "success": pipeline_result.success,
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
        data: list[dict[str, Any]],
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """生成 L1 字段字典

        Args:
            data: 蒸馏数据列表
            output_path: 输出文件路径（可选）

        Returns:
            L1 字段字典
        """
        fields = []
        if data:
            for key in data[0].keys():
                values = [d.get(key) for d in data if d.get(key) is not None]
                fields.append({
                    "name": key,
                    "type": str(type(values[0]).__name__) if values else "null",
                    "non_null_count": len(values),
                    "missing_rate": round(1 - len(values) / len(data), 4),
                })
        l1 = {"fields": fields, "row_count": len(data)}
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(l1, f, ensure_ascii=False, indent=2)
            logger.info("L1 字段字典已写入: %s", output_path)
        return l1

    def generate_l2(
        self,
        pipeline_result: LlmPipelineResult,
        output_path: Path | None = None,
    ) -> str:
        """生成 L2 使用说明（Markdown）

        Args:
            pipeline_result: 流水线执行结果
            output_path: 输出文件路径（可选）

        Returns:
            L2 Markdown 文本
        """
        content = f"""# C_llm_distilled 使用说明

## 数据来源
- LLM API 蒸馏（GLM-4-Flash 主力，Qwen/DeepSeek 备选）
- 主从多代理协作提取

## 适用场景
- 补齐 Layer A+B 未覆盖的难提取指标
- 文献中非结构化数据的结构化提取
- 参考范围对标（非配对精度验证）

## 不适用场景
- 临床诊断
- 精度验证（LLM 提取存在幻觉风险）
- 个体化评估

## 提取统计
- 总提取数: {pipeline_result.total_extracted}
- 验证通过: {pipeline_result.total_validated}
- 被拒绝: {pipeline_result.total_rejected}
- Token 消耗: {pipeline_result.total_tokens_consumed}

## 已知局限
- LLM 提取可能存在幻觉，已通过双层验证+人工抽检控制
- confidence <0.5 的数据已被自动拒绝
- 0.5 ≤ confidence <0.7 的数据需人工复核

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
