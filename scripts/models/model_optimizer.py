"""模型优化器

实现 5 种优化策略，对比评估其对基线模型的改进效果：
1. 超参数调优（GridSearchCV 网格搜索）
2. 特征选择（SelectKBest 选择最优特征子集）
3. 模型压缩（减少树数量与深度，降低内存占用）
4. 集成学习（VotingClassifier 融合 RF + GradientBoosting + ExtraTrees）
5. 全量优化对比（运行上述全部策略并汇总结果）

每个优化方法返回字典，统一包含以下键：
- optimized_model: 优化后的模型对象
- optimization_params: 优化过程中使用的参数
- expected_improvement: 相对基线的预期提升（基于交叉验证）
"""
from __future__ import annotations

import logging
import time

import numpy as np
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.pipeline import Pipeline

from scripts.models.health_risk_model import HealthRiskModel

logger = logging.getLogger(__name__)


class ModelOptimizer:
    """模型优化器

    围绕基线 HealthRiskModel 实现 5 种优化策略。

    Args:
        baseline_model: 基线 HealthRiskModel 实例（用于对比基准）
    """

    def __init__(self, baseline_model: HealthRiskModel) -> None:
        self.baseline_model = baseline_model
        # 缓存基线交叉验证分数，避免重复计算
        self._baseline_score: float | None = None

    # ------------------------------------------------------------------
    # 策略 1：超参数调优
    # ------------------------------------------------------------------
    def optimize_hyperparameters(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv: int = 5,
    ) -> dict:
        """使用 GridSearchCV 进行超参数调优

        搜索空间：
        - n_estimators: [50, 100, 200]
        - max_depth: [5, 10, 15, None]
        - min_samples_split: [2, 5, 10]
        - min_samples_leaf: [1, 2, 4]

        Args:
            X_train: 训练特征
            y_train: 训练标签
            cv: 交叉验证折数

        Returns:
            包含 optimized_model, optimization_params, expected_improvement 的字典
        """
        start_time = time.time()
        param_grid = {
            "n_estimators": [50, 100, 200],
            "max_depth": [5, 10, 15, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
        }

        grid = GridSearchCV(
            RandomForestClassifier(random_state=self.baseline_model.random_state),
            param_grid,
            cv=cv,
            scoring="f1_weighted",
            n_jobs=-1,
        )
        grid.fit(X_train, y_train)
        best_params = grid.best_params_
        logger.info("超参数调优完成: 最优参数=%s", best_params)

        # 用最优参数构建 HealthRiskModel 并复用已拟合的最佳估计器
        optimized = HealthRiskModel(
            n_estimators=best_params["n_estimators"],
            max_depth=best_params["max_depth"],
            random_state=self.baseline_model.random_state,
        )
        # 直接复用网格搜索已拟合的最佳估计器（已在整个训练集上 refit）
        optimized.model = grid.best_estimator_
        # 同包内部访问私有标记，记录已训练状态
        optimized._is_trained = True

        improvement = self._compute_improvement(
            grid.best_estimator_, X_train, y_train, cv
        )
        elapsed = time.time() - start_time
        logger.info("超参数调优耗时=%.3fs, 预期提升=%.4f", elapsed, improvement)

        return {
            "optimized_model": optimized,
            "optimization_params": {
                "best_params": best_params,
                "cv": cv,
                "best_score": float(grid.best_score_),
            },
            "expected_improvement": improvement,
        }

    # ------------------------------------------------------------------
    # 策略 2：特征选择
    # ------------------------------------------------------------------
    def optimize_features(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        k: int = 8,
    ) -> dict:
        """使用 SelectKBest 进行特征选择

        通过 ANOVA F 检验选择对分类最有区分度的 k 个特征，
        并构建包含特征选择步骤的 Pipeline 模型。

        Args:
            X_train: 训练特征
            y_train: 训练标签
            k: 选择的特征数量

        Returns:
            包含 optimized_model, optimization_params, expected_improvement 的字典
        """
        start_time = time.time()
        # k 不能超过特征总数
        n_features = X_train.shape[1]
        actual_k = min(k, n_features)

        # 构建 Pipeline：先特征选择，再随机森林分类
        pipeline = Pipeline([
            ("select", SelectKBest(score_func=f_classif, k=actual_k)),
            (
                "rf",
                RandomForestClassifier(
                    n_estimators=self.baseline_model.n_estimators,
                    max_depth=self.baseline_model.max_depth,
                    random_state=self.baseline_model.random_state,
                ),
            ),
        ])
        pipeline.fit(X_train, y_train)

        # 提取被选中的特征索引与得分
        selector = pipeline.named_steps["select"]
        selected_mask = selector.get_support()
        selected_indices = [int(i) for i in np.where(selected_mask)[0]]
        feature_scores = selector.scores_.tolist()

        improvement = self._compute_improvement(pipeline, X_train, y_train)
        elapsed = time.time() - start_time
        logger.info(
            "特征选择完成: 选中 %d/%d 个特征, 耗时=%.3fs, 预期提升=%.4f",
            actual_k, n_features, elapsed, improvement,
        )

        return {
            "optimized_model": pipeline,
            "optimization_params": {
                "k": actual_k,
                "selected_feature_indices": selected_indices,
                "feature_scores": feature_scores,
            },
            "expected_improvement": improvement,
        }

    # ------------------------------------------------------------------
    # 策略 3：模型压缩
    # ------------------------------------------------------------------
    def optimize_model_compression(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> dict:
        """通过减少树数量和深度压缩模型

        牺牲少量精度以换取更小的模型体积与更快的推理速度。

        Args:
            X_train: 训练特征
            y_train: 训练标签

        Returns:
            包含 optimized_model, optimization_params, expected_improvement 的字典
        """
        start_time = time.time()
        # 压缩参数：减少树数量、限制深度
        compressed_n_estimators = max(self.baseline_model.n_estimators // 2, 10)
        compressed_max_depth = 5

        compressed = HealthRiskModel(
            n_estimators=compressed_n_estimators,
            max_depth=compressed_max_depth,
            random_state=self.baseline_model.random_state,
        )
        compressed.train(X_train, y_train)

        improvement = self._compute_improvement(
            compressed.model, X_train, y_train
        )
        elapsed = time.time() - start_time
        logger.info(
            "模型压缩完成: 树数=%d, 深度=%d, 耗时=%.3fs, 预期提升=%.4f",
            compressed_n_estimators, compressed_max_depth, elapsed, improvement,
        )

        return {
            "optimized_model": compressed,
            "optimization_params": {
                "original_n_estimators": self.baseline_model.n_estimators,
                "compressed_n_estimators": compressed_n_estimators,
                "original_max_depth": self.baseline_model.max_depth,
                "compressed_max_depth": compressed_max_depth,
            },
            "expected_improvement": improvement,
        }

    # ------------------------------------------------------------------
    # 策略 4：集成学习
    # ------------------------------------------------------------------
    def optimize_ensemble(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> dict:
        """使用 VotingClassifier 集成多个模型

        融合 RandomForest + GradientBoosting + ExtraTrees 三个基学习器。

        Args:
            X_train: 训练特征
            y_train: 训练标签

        Returns:
            包含 optimized_model, optimization_params, expected_improvement 的字典
        """
        start_time = time.time()
        random_state = self.baseline_model.random_state

        ensemble = VotingClassifier(
            estimators=[
                (
                    "rf",
                    RandomForestClassifier(
                        n_estimators=50,
                        max_depth=10,
                        random_state=random_state,
                    ),
                ),
                (
                    "gb",
                    GradientBoostingClassifier(
                        n_estimators=50,
                        max_depth=3,
                        random_state=random_state,
                    ),
                ),
                (
                    "et",
                    ExtraTreesClassifier(
                        n_estimators=50,
                        max_depth=10,
                        random_state=random_state,
                    ),
                ),
            ],
            voting="soft",
        )
        ensemble.fit(X_train, y_train)

        improvement = self._compute_improvement(ensemble, X_train, y_train)
        elapsed = time.time() - start_time
        logger.info(
            "集成学习完成: 融合 RF+GB+ET, 耗时=%.3fs, 预期提升=%.4f",
            elapsed, improvement,
        )

        return {
            "optimized_model": ensemble,
            "optimization_params": {
                "estimators": ["random_forest", "gradient_boosting", "extra_trees"],
                "voting": "soft",
                "n_estimators_per_model": 50,
            },
            "expected_improvement": improvement,
        }

    # ------------------------------------------------------------------
    # 策略 5：全量优化对比
    # ------------------------------------------------------------------
    def run_all_optimizations(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> dict:
        """运行所有优化策略并返回对比结果

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_test: 测试特征
            y_test: 测试标签

        Returns:
            对比结果字典，键为策略名，值包含该策略的优化结果与测试集表现
        """
        start_time = time.time()
        results: dict[str, dict] = {}

        # 依次执行各优化策略
        strategies = [
            ("hyperparameters", lambda: self.optimize_hyperparameters(X_train, y_train, cv=3)),
            ("features", lambda: self.optimize_features(X_train, y_train, k=8)),
            ("compression", lambda: self.optimize_model_compression(X_train, y_train)),
            ("ensemble", lambda: self.optimize_ensemble(X_train, y_train)),
        ]

        for name, strategy_fn in strategies:
            try:
                result = strategy_fn()
            except Exception as exc:  # noqa: BLE001 - 单策略失败不影响整体对比
                logger.error("优化策略 %s 执行失败: %s", name, exc)
                results[name] = {
                    "optimization_params": {},
                    "expected_improvement": 0.0,
                    "test_accuracy": 0.0,
                    "test_f1": 0.0,
                    "error": str(exc),
                }
                continue

            # 在测试集上评估优化后的模型
            test_accuracy, test_f1 = self._evaluate_on_test(
                result["optimized_model"], X_test, y_test
            )
            results[name] = {
                "optimization_params": result["optimization_params"],
                "expected_improvement": result["expected_improvement"],
                "test_accuracy": test_accuracy,
                "test_f1": test_f1,
            }
            logger.info(
                "策略 %s: 测试 accuracy=%.4f, f1=%.4f",
                name, test_accuracy, test_f1,
            )

        # 基线模型在测试集上的表现（作为对比基准）
        if self.baseline_model._is_trained:
            baseline_acc, baseline_f1 = self._evaluate_on_test(
                self.baseline_model, X_test, y_test
            )
        else:
            baseline_acc, baseline_f1 = 0.0, 0.0

        results["baseline"] = {
            "test_accuracy": baseline_acc,
            "test_f1": baseline_f1,
        }
        results["total_time_seconds"] = time.time() - start_time
        logger.info(
            "全量优化对比完成: 基线 accuracy=%.4f, 总耗时=%.3fs",
            baseline_acc, results["total_time_seconds"],
        )
        return results

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _get_baseline_score(
        self, X: np.ndarray, y: np.ndarray, cv: int = 5
    ) -> float:
        """计算并缓存基线模型的交叉验证分数"""
        if self._baseline_score is None:
            scores = cross_val_score(
                self.baseline_model.model, X, y, cv=cv, scoring="f1_weighted",
            )
            self._baseline_score = float(scores.mean())
            logger.info("基线交叉验证 f1=%.4f", self._baseline_score)
        return self._baseline_score

    def _compute_improvement(
        self,
        estimator,
        X: np.ndarray,
        y: np.ndarray,
        cv: int = 5,
    ) -> float:
        """计算优化模型相对基线的预期提升"""
        baseline = self._get_baseline_score(X, y, cv)
        scores = cross_val_score(estimator, X, y, cv=cv, scoring="f1_weighted")
        optimized = float(scores.mean())
        return optimized - baseline

    def _evaluate_on_test(
        self, model, X_test: np.ndarray, y_test: np.ndarray
    ) -> tuple[float, float]:
        """在测试集上评估模型，返回 (accuracy, f1)"""
        # 统一通过 predict 接口预测
        # HealthRiskModel.predict / Pipeline.predict / VotingClassifier.predict 均可用
        if isinstance(model, HealthRiskModel):
            y_pred = model.predict(X_test)
        else:
            y_pred = model.predict(X_test)
        accuracy = float(accuracy_score(y_test, y_pred))
        f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
        return accuracy, f1
