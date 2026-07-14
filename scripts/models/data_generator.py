"""健康风险评分合成数据生成器

基于正态分布生成 BIA/PPG/TCM 三类指标的合成样本，
并根据异常指标数量加权生成 3 分类风险标签。

标签生成规则：
- 计算风险分数 = 异常指标数量（超出正常范围的指标个数）
- 风险分数 < 3：low_risk (0)
- 风险分数 3-6：medium_risk (1)
- 风险分数 > 6：high_risk (2)
"""
from __future__ import annotations

import logging

import numpy as np
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class HealthDataGenerator:
    """健康风险数据合成生成器

    按 BIA/PPG/TCM 三类指标的正态分布生成合成样本，
    并基于异常指标计数生成 3 分类风险标签。
    """

    # 各指标正态分布参数：(均值, 标准差)
    DISTRIBUTION_PARAMS: dict[str, tuple[float, float]] = {
        # BIA 指标
        "body_fat_pct": (22.0, 8.0),
        "water_pct": (55.0, 5.0),
        "muscle_mass_kg": (28.0, 6.0),
        "bmi": (22.0, 4.0),
        "visceral_fat_level": (7.0, 4.0),
        "basal_metabolism": (1500.0, 200.0),
        # PPG 指标
        "heart_rate": (72.0, 12.0),
        "rmssd": (40.0, 20.0),
        "sdnn": (50.0, 20.0),
        "pnn50": (20.0, 15.0),
        # TCM 指标
        "tcm_primary_score": (50.0, 20.0),
        "tcm_balanced_score": (40.0, 15.0),
    }

    # 异常判定阈值：(下界, 上界)；指标超出该范围即视为异常
    ABNORMAL_RANGES: dict[str, tuple[float, float]] = {
        "body_fat_pct": (16.0, 26.0),
        "water_pct": (51.0, 59.0),
        "muscle_mass_kg": (26.0, 1e9),
        "bmi": (19.0, 23.0),
        "visceral_fat_level": (0.0, 8.5),
        "basal_metabolism": (1350.0, 1e9),
        "heart_rate": (62.0, 98.0),
        "rmssd": (25.0, 1e9),
        "sdnn": (35.0, 1e9),
        "pnn50": (12.0, 1e9),
        "tcm_primary_score": (0.0, 55.0),
        "tcm_balanced_score": (32.0, 1e9),
    }

    # 特征顺序，需与 HealthRiskModel.FEATURE_NAMES 保持一致
    FEATURE_ORDER: list[str] = list(DISTRIBUTION_PARAMS.keys())

    # 风险分数分级阈值
    RISK_LOW_THRESHOLD: float = 3.0   # < 3 → low_risk
    RISK_HIGH_THRESHOLD: float = 6.0   # > 6 → high_risk

    def generate_samples(
        self,
        n_samples: int = 1000,
        random_state: int = 42,
    ) -> tuple[np.ndarray, np.ndarray]:
        """生成合成数据样本

        Args:
            n_samples: 样本数量
            random_state: 随机种子

        Returns:
            (X, y) 元组：
            - X: 特征矩阵，形状 (n_samples, 12)
            - y: 标签数组，形状 (n_samples,)，取值为 0/1/2
        """
        rng = np.random.default_rng(random_state)
        n_features = len(self.FEATURE_ORDER)
        X = np.zeros((n_samples, n_features), dtype=np.float64)

        # 按正态分布生成各指标
        for idx, name in enumerate(self.FEATURE_ORDER):
            mean, std = self.DISTRIBUTION_PARAMS[name]
            X[:, idx] = rng.normal(mean, std, size=n_samples)

        # 计算每个样本的异常指标数量作为风险分数
        risk_scores = np.zeros(n_samples, dtype=np.float64)
        for idx, name in enumerate(self.FEATURE_ORDER):
            low, high = self.ABNORMAL_RANGES[name]
            abnormal_mask = (X[:, idx] < low) | (X[:, idx] > high)
            risk_scores += abnormal_mask.astype(np.float64)

        # 添加少量噪声，避免完全线性可分（更贴近真实场景）
        risk_scores += rng.normal(0.0, 0.2, size=n_samples)

        # 根据风险分数划分等级：< 3 → 0, 3-6 → 1, > 6 → 2
        y = np.where(
            risk_scores < self.RISK_LOW_THRESHOLD,
            0,
            np.where(risk_scores <= self.RISK_HIGH_THRESHOLD, 1, 2),
        ).astype(np.int64)

        logger.info(
            "生成 %d 个样本: low_risk=%d, medium_risk=%d, high_risk=%d",
            n_samples, int((y == 0).sum()), int((y == 1).sum()), int((y == 2).sum()),
        )
        return X, y

    def generate_train_test_split(
        self,
        n_samples: int = 1000,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """生成训练集与测试集

        Args:
            n_samples: 总样本数
            test_size: 测试集比例
            random_state: 随机种子

        Returns:
            (X_train, X_test, y_train, y_test) 四元组
        """
        X, y = self.generate_samples(n_samples, random_state)

        # 优先使用分层抽样保持标签分布；若某类样本过少则退化为随机划分
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y,
            )
        except ValueError:
            logger.warning("分层抽样失败，退化为随机划分")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state,
            )

        logger.info(
            "数据集划分完成: 训练集=%d, 测试集=%d",
            len(X_train), len(X_test),
        )
        return X_train, X_test, y_train, y_test
