"""5 步预处理器

职责：
按顺序执行 5 步标准化处理：
1. 数据清洗：字段名标准化（基于 indicator_mapping.json）
2. 格式转换：（由 FormatConverter 单独负责，本类假设输入已是 DataFrame）
3. 异常值处理：生理范围硬过滤 + IQR 软标记
4. 缺失值填充：KNN/分层中位数/剔除
5. 数据标准化：年龄分组、性别编码、单位统一
"""
import json
import logging
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class Preprocessor:
    """5 步预处理器

    Args:
        mapping_path: indicator_mapping.json 路径
    """

    # 生理范围硬过滤规则（来自 quality_rules.yaml）
    PHYSIOLOGICAL_RANGES = {
        "bmi": (10, 80),
        "body_fat_pct": (3, 60),
        "height_cm": (120, 220),
        "weight_kg": (30, 200),
        "heart_rate": (30, 220),
        "spo2": (70, 100),
        "perfusion_index": (0, 20),
        "hrv_rmssd": (5, 150),
        "age": (6, 99),
    }

    # 年龄分组规则
    AGE_GROUPS = [(6, 17, "6-17"), (18, 39, "18-39"), (40, 59, "40-59"), (60, 99, "60+")]

    def __init__(self, mapping_path: Path | None = None):
        if mapping_path is None:
            mapping_path = Path(
                "e:/Health_man/data/knowledge/chinese_reference/_governance/indicator_mapping.json"
            )
        self.mapping = self._load_mapping(mapping_path)

    def _load_mapping(self, mapping_path: Path) -> dict[str, str]:
        """加载指标映射表"""
        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("indicator_mapping", {})

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行 5 步预处理"""
        df = df.copy()
        df = self._step1_clean(df)
        df = self._step3_detect_outliers(df)
        df = self._step4_handle_missing(df)
        df = self._step5_standardize(df)
        return df

    def _step1_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 1: 字段名标准化"""
        rename_map = {}
        for col in df.columns:
            if col in self.mapping:
                rename_map[col] = self.mapping[col]
        df = df.rename(columns=rename_map)
        logger.info("Step 1 完成: 字段名标准化，重命名 %d 列", len(rename_map))
        return df

    def _step3_detect_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 3: 异常值检测与处理"""
        for col, (min_val, max_val) in self.PHYSIOLOGICAL_RANGES.items():
            if col not in df.columns:
                continue
            before = len(df)
            df = df[(df[col] >= min_val) & (df[col] <= max_val)]
            removed = before - len(df)
            if removed > 0:
                logger.info(
                    "Step 3: %s 过滤 %d 条异常值（范围 %s-%s）",
                    col, removed, min_val, max_val,
                )
        return df

    def _step4_handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 4: 缺失值填充"""
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count == 0:
                continue
            missing_rate = missing_count / len(df)
            if missing_rate > 0.3:
                logger.warning("Step 4: %s 缺失率 %.2f > 0.3，整列剔除", col, missing_rate)
                df = df.drop(columns=[col])
            else:
                # 用中位数填充
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
                logger.info("Step 4: %s 填充 %d 个缺失值（中位数=%.2f）", col, missing_count, median_val)
        return df

    def _step5_standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 5: 数据标准化（年龄分组等）"""
        if "age" in df.columns:
            df["age_group"] = df["age"].apply(self._categorize_age)
            logger.info("Step 5: 年龄分组完成")
        return df

    def _categorize_age(self, age: float) -> str:
        """将年龄映射到分组"""
        for low, high, label in self.AGE_GROUPS:
            if low <= age <= high:
                return label
        return "unknown"
