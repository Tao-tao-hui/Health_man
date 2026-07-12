# e:\Health_man\scripts\data\quality_checker.py
"""质量校验器

职责：
- 三级质量校验（结构/值域/业务）
- 输出 A/B/C/D 评级
- 生成质量报告

评级阈值：
- A: overall >= 0.9, confidence=0.9
- B: 0.8 <= overall < 0.9, confidence=0.75
- C: 0.7 <= overall < 0.8, confidence=0.6
- D: overall < 0.7, confidence=0.4（拒绝入库）
"""
import logging
from dataclasses import dataclass

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """质量校验报告"""
    completeness: float       # 字段完整率
    validity: float           # 值域合法率
    consistency: float        # 跨字段一致性
    overall: float            # 加权综合分
    grade: str                # A/B/C/D
    row_count: int            # 总行数
    column_count: int         # 总列数
    issues: list[str]         # 发现的问题清单


class QualityChecker:
    """质量校验器"""

    # 生理范围（与 Preprocessor.PHYSIOLOGICAL_RANGES 及 quality_rules.yaml 保持一致）
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

    REQUIRED_FIELDS = ["age", "gender", "weight_kg"]

    def check(self, df: pd.DataFrame) -> QualityReport:
        """执行质量校验"""
        issues: list[str] = []

        # 1. 完整性：字段缺失率
        completeness = self._check_completeness(df, issues)

        # 2. 合法性：值域合法率
        validity = self._check_validity(df, issues)

        # 3. 一致性：跨字段逻辑
        consistency = self._check_consistency(df, issues)

        # 4. 综合分（加权平均）
        overall = completeness * 0.35 + validity * 0.35 + consistency * 0.30

        # 5. 评级
        grade = self._calculate_grade(overall)

        return QualityReport(
            completeness=completeness,
            validity=validity,
            consistency=consistency,
            overall=overall,
            grade=grade,
            row_count=len(df),
            column_count=len(df.columns),
            issues=issues,
        )

    def _check_completeness(self, df: pd.DataFrame, issues: list[str]) -> float:
        """检查字段完整率"""
        if len(df) == 0:
            issues.append("数据集为空")
            return 0.0
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isna().sum().sum()
        completeness = 1 - (missing_cells / total_cells)
        if completeness < 0.8:
            issues.append(f"完整率过低: {completeness:.2f}")
        return float(completeness)

    def _check_validity(self, df: pd.DataFrame, issues: list[str]) -> float:
        """检查值域合法率"""
        if len(df) == 0:
            return 0.0
        total_checked = 0
        valid_count = 0
        for col, (min_val, max_val) in self.PHYSIOLOGICAL_RANGES.items():
            if col not in df.columns:
                continue
            values = df[col].dropna()
            total_checked += len(values)
            valid = ((values >= min_val) & (values <= max_val)).sum()
            valid_count += valid
            invalid = len(values) - valid
            if invalid > 0:
                issues.append(f"{col} 有 {invalid} 个超范围值")
        if total_checked == 0:
            # 无任何生理范围字段可校验时，不应视为"全部合法"，
            # 否则会使 overall 虚高掩盖数据缺失问题。
            issues.append("无生理范围字段可校验，validity 降为 0")
            return 0.0
        return float(valid_count / total_checked)

    def _check_consistency(self, df: pd.DataFrame, issues: list[str]) -> float:
        """检查跨字段一致性（如 BMI = 体重/身高²）"""
        if len(df) == 0:
            return 0.0
        checks_passed = 0
        total_checks = 0
        # 检查必需字段是否存在
        for field in self.REQUIRED_FIELDS:
            total_checks += 1
            if field in df.columns:
                checks_passed += 1
            else:
                issues.append(f"必需字段缺失: {field}")
        # TODO: 后续可加 BMI 计算一致性检查
        return float(checks_passed / total_checks) if total_checks > 0 else 1.0

    def _calculate_grade(self, overall: float) -> str:
        """根据综合分计算评级"""
        if overall >= 0.9:
            return "A"
        elif overall >= 0.8:
            return "B"
        elif overall >= 0.7:
            return "C"
        else:
            return "D"
