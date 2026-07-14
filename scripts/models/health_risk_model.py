"""健康风险评分基线模型

基于 scikit-learn 的 RandomForestClassifier 实现 3 分类健康风险评估。

输入特征（共 12 维）：
- BIA 指标（6 维）：体脂率、水分率、肌肉量、体质指数、内脏脂肪等级、基础代谢
- PPG 指标（4 维）：心率、RMSSD、SDNN、pNN50
- TCM 指标（2 维）：体质转化分、平和质得分

输出 3 分类：
- 0: low_risk（低风险）
- 1: medium_risk（中风险）
- 2: high_risk（高风险）
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)


class HealthRiskModel:
    """健康风险评分基线模型

    基于 RandomForestClassifier 的 3 分类健康风险评估模型。

    Args:
        n_estimators: 随机森林中决策树的数量
        max_depth: 每棵树的最大深度，None 表示不限制
        random_state: 随机种子，保证结果可复现
    """

    # 特征顺序定义（共 12 维），extract_features 按此顺序提取
    FEATURE_NAMES: list[str] = [
        # BIA 指标（6 维）
        "body_fat_pct",        # 体脂率
        "water_pct",           # 水分率
        "muscle_mass_kg",      # 肌肉量
        "bmi",                 # 体质指数
        "visceral_fat_level",  # 内脏脂肪等级
        "basal_metabolism",    # 基础代谢
        # PPG 指标（4 维）
        "heart_rate",          # 心率
        "rmssd",               # HRV-均方根连续差
        "sdnn",                # HRV-标准差
        "pnn50",               # HRV-pNN50
        # TCM 指标（2 维）
        "tcm_primary_score",   # 体质转化分
        "tcm_balanced_score",  # 平和质得分
    ]

    # 风险等级标签映射
    RISK_LABELS: dict[int, str] = {
        0: "low_risk",
        1: "medium_risk",
        2: "high_risk",
    }

    # 期望特征数量
    EXPECTED_FEATURE_COUNT: int = 12

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int | None = 10,
        random_state: int = 42,
    ) -> None:
        """初始化随机森林模型

        Args:
            n_estimators: 决策树数量，默认 100
            max_depth: 树最大深度，默认 10；None 表示不限制
            random_state: 随机种子，默认 42
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        # 构建底层随机森林分类器
        self.model: RandomForestClassifier = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
        )
        # 训练状态标记
        self._is_trained: bool = False
        logger.info(
            "HealthRiskModel 初始化完成: n_estimators=%d, max_depth=%s, random_state=%d",
            n_estimators, max_depth, random_state,
        )

    def extract_features(self, raw_data: dict) -> np.ndarray:
        """从原始数据字典提取特征向量

        按 FEATURE_NAMES 顺序提取 12 个特征，返回一维 numpy 数组。

        Args:
            raw_data: 包含 12 个特征字段的字典

        Returns:
            形状为 (12,) 的特征向量

        Raises:
            TypeError: raw_data 不是字典类型
            ValueError: 缺失必需字段或字段数量不符
        """
        # 输入类型校验
        if not isinstance(raw_data, dict):
            raise TypeError(
                f"raw_data 必须为字典类型，实际类型: {type(raw_data).__name__}"
            )

        # 检查缺失的必需字段
        missing_fields = [
            name for name in self.FEATURE_NAMES if name not in raw_data
        ]
        if missing_fields:
            raise ValueError(f"缺失特征字段: {missing_fields}")

        # 检查特征数量是否匹配
        if len(raw_data) < self.EXPECTED_FEATURE_COUNT:
            raise ValueError(
                f"特征数量不足: 期望 {self.EXPECTED_FEATURE_COUNT}，实际 {len(raw_data)}"
            )

        # 按固定顺序提取特征并转换为浮点数组
        features = np.array(
            [float(raw_data[name]) for name in self.FEATURE_NAMES],
            dtype=np.float64,
        )
        return features

    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """训练模型

        Args:
            X_train: 训练特征矩阵，形状 (n_samples, 12)
            y_train: 训练标签数组，形状 (n_samples,)

        Raises:
            ValueError: 训练数据为空或特征维度不符
        """
        # 输入校验：数据非空
        if X_train is None or len(X_train) == 0:
            raise ValueError("训练数据不能为空")
        # 特征维度校验
        if X_train.ndim != 2 or X_train.shape[1] != self.EXPECTED_FEATURE_COUNT:
            raise ValueError(
                f"特征维度不符: 期望 (n_samples, {self.EXPECTED_FEATURE_COUNT})，"
                f"实际 {X_train.shape}"
            )

        start_time = time.time()
        self.model.fit(X_train, y_train)
        self._is_trained = True
        elapsed = time.time() - start_time
        logger.info(
            "模型训练完成: 样本数=%d, 耗时=%.3fs",
            len(X_train), elapsed,
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测风险等级

        Args:
            X: 特征矩阵，形状 (n_samples, 12)

        Returns:
            预测标签数组，形状 (n_samples,)

        Raises:
            RuntimeError: 模型尚未训练
            ValueError: 特征维度不符
        """
        if not self._is_trained:
            raise RuntimeError("模型尚未训练，请先调用 train 方法")
        # 特征维度校验
        if X.shape[-1] != self.EXPECTED_FEATURE_COUNT:
            raise ValueError(
                f"特征维度不符: 期望 {self.EXPECTED_FEATURE_COUNT}，实际 {X.shape[-1]}"
            )
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测各风险等级的概率

        Args:
            X: 特征矩阵，形状 (n_samples, 12)

        Returns:
            概率矩阵，形状 (n_samples, 3)，列顺序对应 0/1/2 三个等级

        Raises:
            RuntimeError: 模型尚未训练
            ValueError: 特征维度不符
        """
        if not self._is_trained:
            raise RuntimeError("模型尚未训练，请先调用 train 方法")
        if X.shape[-1] != self.EXPECTED_FEATURE_COUNT:
            raise ValueError(
                f"特征维度不符: 期望 {self.EXPECTED_FEATURE_COUNT}，实际 {X.shape[-1]}"
            )
        return self.model.predict_proba(X)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        """评估模型性能

        计算 accuracy、precision、recall、f1 以及推理时间和内存占用。

        Args:
            X_test: 测试特征矩阵
            y_test: 测试标签数组

        Returns:
            包含 accuracy, precision, recall, f1, inference_time_ms, memory_mb 的字典

        Raises:
            RuntimeError: 模型尚未训练
        """
        if not self._is_trained:
            raise RuntimeError("模型尚未训练，请先调用 train 方法")

        # 测量单样本平均推理时间
        start_time = time.time()
        y_pred = self.model.predict(X_test)
        inference_time_ms = (time.time() - start_time) / max(len(X_test), 1) * 1000

        # 估算模型内存占用（基于决策树节点数）
        memory_mb = self._estimate_memory_mb()

        metrics: dict = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(
                precision_score(y_test, y_pred, average="weighted", zero_division=0)
            ),
            "recall": float(
                recall_score(y_test, y_pred, average="weighted", zero_division=0)
            ),
            "f1": float(
                f1_score(y_test, y_pred, average="weighted", zero_division=0)
            ),
            "inference_time_ms": float(inference_time_ms),
            "memory_mb": float(memory_mb),
        }
        logger.info(
            "模型评估完成: accuracy=%.4f, precision=%.4f, recall=%.4f, f1=%.4f, "
            "推理=%.4fms/sample, 内存=%.2fMB",
            metrics["accuracy"], metrics["precision"], metrics["recall"],
            metrics["f1"], metrics["inference_time_ms"], metrics["memory_mb"],
        )
        return metrics

    def _estimate_memory_mb(self) -> float:
        """粗略估算模型内存占用（MB）

        基于所有决策树的节点总数估算，每节点约 100 字节。
        """
        # 汇总所有决策树的节点数
        total_nodes = sum(
            tree.tree_.node_count for tree in self.model.estimators_
        )
        # 每个节点约占用 100 字节（粗略估算）
        memory_bytes = total_nodes * 100
        return memory_bytes / (1024 * 1024)

    def save(self, path: str | Path) -> None:
        """保存模型到文件（使用 joblib 序列化）

        Args:
            path: 保存路径，建议使用 .joblib 扩展名
        """
        path = Path(path)
        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "random_state": self.random_state,
                "is_trained": self._is_trained,
            },
            path,
        )
        logger.info("模型已保存至: %s", path)

    def load(self, path: str | Path) -> None:
        """从文件加载模型

        Args:
            path: 模型文件路径

        Raises:
            FileNotFoundError: 模型文件不存在
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"模型文件不存在: {path}")
        data = joblib.load(path)
        self.model = data["model"]
        self.n_estimators = data["n_estimators"]
        self.max_depth = data["max_depth"]
        self.random_state = data["random_state"]
        self._is_trained = data["is_trained"]
        logger.info("模型已从 %s 加载", path)
