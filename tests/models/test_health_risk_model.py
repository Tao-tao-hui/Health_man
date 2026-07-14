"""健康风险评分模型系统测试套件

覆盖：
- HealthRiskModel：初始化、特征提取、训练预测、评估、保存加载
- HealthDataGenerator：数据生成、训练测试集划分
- ModelOptimizer：超参数调优、特征选择、模型压缩、集成学习、全量优化
"""
from __future__ import annotations

import numpy as np
import pytest

from scripts.models.data_generator import HealthDataGenerator
from scripts.models.health_risk_model import HealthRiskModel
from scripts.models.model_optimizer import ModelOptimizer


# ----------------------------------------------------------------------
# 共享测试夹具
# ----------------------------------------------------------------------
@pytest.fixture
def generator() -> HealthDataGenerator:
    """合成数据生成器"""
    return HealthDataGenerator()


@pytest.fixture
def small_dataset(generator: HealthDataGenerator):
    """小规模数据集（用于快速测试训练/预测流程）"""
    return generator.generate_train_test_split(
        n_samples=300, test_size=0.25, random_state=42
    )


@pytest.fixture
def trained_model(small_dataset) -> HealthRiskModel:
    """已训练的基线模型"""
    X_train, _, y_train, _ = small_dataset
    model = HealthRiskModel(n_estimators=30, max_depth=8, random_state=42)
    model.train(X_train, y_train)
    return model


@pytest.fixture
def sample_raw_data() -> dict:
    """单样本原始数据字典"""
    return {
        "body_fat_pct": 22.0,
        "water_pct": 55.0,
        "muscle_mass_kg": 28.0,
        "bmi": 22.0,
        "visceral_fat_level": 7.0,
        "basal_metabolism": 1500.0,
        "heart_rate": 72.0,
        "rmssd": 40.0,
        "sdnn": 50.0,
        "pnn50": 20.0,
        "tcm_primary_score": 50.0,
        "tcm_balanced_score": 40.0,
    }


# ======================================================================
# TestHealthRiskModel
# ======================================================================
class TestHealthRiskModel:
    """基线健康风险模型测试"""

    def test_model_initialization(self):
        """测试模型初始化：参数正确设置"""
        model = HealthRiskModel(n_estimators=50, max_depth=5, random_state=7)
        assert model.n_estimators == 50
        assert model.max_depth == 5
        assert model.random_state == 7
        # 未训练前标记为 False
        assert model._is_trained is False
        # 底层分类器已构建
        assert model.model is not None
        # 特征顺序与数量正确
        assert len(HealthRiskModel.FEATURE_NAMES) == 12

    def test_feature_extraction_normal(self, sample_raw_data: dict):
        """测试特征提取：正常输入应返回 12 维向量"""
        model = HealthRiskModel()
        features = model.extract_features(sample_raw_data)
        assert isinstance(features, np.ndarray)
        assert features.shape == (12,)
        # 第一个特征应为体脂率
        assert features[0] == pytest.approx(22.0)

    def test_feature_extraction_missing_field(self, sample_raw_data: dict):
        """测试特征提取：缺失字段应抛出 ValueError"""
        model = HealthRiskModel()
        del sample_raw_data["heart_rate"]
        with pytest.raises(ValueError, match="缺失特征字段"):
            model.extract_features(sample_raw_data)

    def test_feature_extraction_wrong_type(self):
        """测试特征提取：非字典输入应抛出 TypeError"""
        model = HealthRiskModel()
        with pytest.raises(TypeError, match="必须为字典"):
            model.extract_features([1, 2, 3])  # type: ignore[arg-type]

    def test_feature_extraction_insufficient_fields(self):
        """测试特征提取：字段数量不足应抛出 ValueError"""
        model = HealthRiskModel()
        # 仅提供 5 个字段
        partial_data = {
            "body_fat_pct": 22.0,
            "water_pct": 55.0,
            "muscle_mass_kg": 28.0,
            "bmi": 22.0,
            "visceral_fat_level": 7.0,
        }
        with pytest.raises(ValueError):
            model.extract_features(partial_data)

    def test_train_predict(self, small_dataset):
        """测试训练与预测流程"""
        X_train, X_test, y_train, _ = small_dataset
        model = HealthRiskModel(n_estimators=30, max_depth=8, random_state=42)
        # 训练前不能预测
        with pytest.raises(RuntimeError):
            model.predict(X_test)

        model.train(X_train, y_train)
        assert model._is_trained is True

        # 预测标签合法
        y_pred = model.predict(X_test)
        assert y_pred.shape == (len(X_test),)
        assert set(np.unique(y_pred)).issubset({0, 1, 2})

        # 预测概率合法
        y_proba = model.predict_proba(X_test)
        assert y_proba.shape == (len(X_test), 3)
        # 每行概率和接近 1
        np.testing.assert_allclose(y_proba.sum(axis=1), 1.0, atol=1e-6)

    def test_train_invalid_dimensions(self):
        """测试训练：特征维度不符应抛出 ValueError"""
        model = HealthRiskModel()
        X_bad = np.random.rand(50, 5)  # 仅 5 维
        y = np.random.randint(0, 3, size=50)
        with pytest.raises(ValueError, match="特征维度不符"):
            model.train(X_bad, y)

    def test_train_empty_data(self):
        """测试训练：空数据应抛出 ValueError"""
        model = HealthRiskModel()
        with pytest.raises(ValueError, match="不能为空"):
            model.train(np.array([]).reshape(0, 12), np.array([]))

    def test_evaluate(self, trained_model: HealthRiskModel, small_dataset):
        """测试评估方法返回正确指标"""
        _, X_test, _, y_test = small_dataset
        metrics = trained_model.evaluate(X_test, y_test)

        # 必需指标键齐全
        required_keys = {
            "accuracy", "precision", "recall", "f1",
            "inference_time_ms", "memory_mb",
        }
        assert required_keys.issubset(metrics.keys())

        # 指标取值合理
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["precision"] <= 1.0
        assert 0.0 <= metrics["recall"] <= 1.0
        assert 0.0 <= metrics["f1"] <= 1.0
        assert metrics["inference_time_ms"] >= 0.0
        assert metrics["memory_mb"] > 0.0

    def test_save_load(self, trained_model: HealthRiskModel, small_dataset, tmp_path):
        """测试模型保存与加载"""
        _, X_test, _, _ = small_dataset

        # 保存模型
        model_path = tmp_path / "health_risk_model.joblib"
        trained_model.save(model_path)
        assert model_path.exists()

        # 加载到新模型实例
        loaded_model = HealthRiskModel()
        loaded_model.load(model_path)
        assert loaded_model._is_trained is True

        # 加载后预测结果应与原模型一致
        original_pred = trained_model.predict(X_test)
        loaded_pred = loaded_model.predict(X_test)
        np.testing.assert_array_equal(original_pred, loaded_pred)

    def test_load_nonexistent(self, tmp_path):
        """测试加载不存在的文件应抛出 FileNotFoundError"""
        model = HealthRiskModel()
        with pytest.raises(FileNotFoundError):
            model.load(tmp_path / "nonexistent.joblib")


# ======================================================================
# TestHealthDataGenerator
# ======================================================================
class TestHealthDataGenerator:
    """合成数据生成器测试"""

    def test_generate_samples(self, generator: HealthDataGenerator):
        """测试数据生成：数量、维度、标签分布"""
        X, y = generator.generate_samples(n_samples=500, random_state=42)

        # 数量与维度
        assert X.shape == (500, 12)
        assert y.shape == (500,)

        # 标签取值合法
        unique_labels = set(np.unique(y).tolist())
        assert unique_labels.issubset({0, 1, 2})

        # 三个风险等级都应出现（合成数据覆盖各等级）
        assert len(unique_labels) >= 2, "至少应出现两个风险等级"

        # 无 NaN 值
        assert not np.isnan(X).any()
        assert not np.isnan(y).any()

    def test_generate_samples_reproducible(self, generator: HealthDataGenerator):
        """测试相同随机种子生成相同数据"""
        X1, y1 = generator.generate_samples(n_samples=100, random_state=42)
        X2, y2 = generator.generate_samples(n_samples=100, random_state=42)
        np.testing.assert_array_equal(X1, X2)
        np.testing.assert_array_equal(y1, y2)

    def test_train_test_split(self, generator: HealthDataGenerator):
        """测试训练测试集划分"""
        X_train, X_test, y_train, y_test = generator.generate_train_test_split(
            n_samples=400, test_size=0.25, random_state=42
        )

        # 划分比例正确
        assert len(X_train) == 300
        assert len(X_test) == 100
        assert len(y_train) == 300
        assert len(y_test) == 100

        # 特征维度正确
        assert X_train.shape[1] == 12
        assert X_test.shape[1] == 12

        # 训练集与测试集无样本重叠（同一随机种子下抽样不重叠）
        train_rows = {tuple(row) for row in X_train}
        test_rows = {tuple(row) for row in X_test}
        assert len(train_rows & test_rows) == 0


# ======================================================================
# TestModelOptimizer
# ======================================================================
class TestModelOptimizer:
    """模型优化器测试"""

    @pytest.fixture
    def optimizer_and_data(self):
        """构建优化器与训练/测试数据"""
        gen = HealthDataGenerator()
        X_train, X_test, y_train, y_test = gen.generate_train_test_split(
            n_samples=300, test_size=0.25, random_state=42
        )
        baseline = HealthRiskModel(n_estimators=30, max_depth=8, random_state=42)
        baseline.train(X_train, y_train)
        optimizer = ModelOptimizer(baseline)
        return optimizer, X_train, y_train, X_test, y_test

    def test_optimize_hyperparameters(self, optimizer_and_data):
        """测试超参数优化"""
        optimizer, X_train, y_train, _, _ = optimizer_and_data
        result = optimizer.optimize_hyperparameters(X_train, y_train, cv=3)

        # 返回结构完整
        assert "optimized_model" in result
        assert "optimization_params" in result
        assert "expected_improvement" in result

        # 最优参数包含全部搜索维度
        best_params = result["optimization_params"]["best_params"]
        for key in ["n_estimators", "max_depth", "min_samples_split", "min_samples_leaf"]:
            assert key in best_params

        # 优化后模型可预测
        optimized_model = result["optimized_model"]
        y_pred = optimized_model.predict(X_train)
        assert len(y_pred) == len(X_train)

    def test_optimize_features(self, optimizer_and_data):
        """测试特征选择"""
        optimizer, X_train, y_train, _, _ = optimizer_and_data
        result = optimizer.optimize_features(X_train, y_train, k=8)

        assert "optimized_model" in result
        assert "optimization_params" in result
        assert "expected_improvement" in result

        params = result["optimization_params"]
        assert params["k"] == 8
        # 选中的特征索引数量等于 k
        assert len(params["selected_feature_indices"]) == 8
        # 特征得分数量等于原始特征数
        assert len(params["feature_scores"]) == 12

        # Pipeline 模型可在原始特征上预测
        y_pred = result["optimized_model"].predict(X_train)
        assert len(y_pred) == len(X_train)

    def test_optimize_model_compression(self, optimizer_and_data):
        """测试模型压缩"""
        optimizer, X_train, y_train, _, _ = optimizer_and_data
        result = optimizer.optimize_model_compression(X_train, y_train)

        assert "optimized_model" in result
        assert "optimization_params" in result
        assert "expected_improvement" in result

        params = result["optimization_params"]
        # 压缩后树数量应小于等于基线
        assert params["compressed_n_estimators"] <= params["original_n_estimators"]
        # 压缩后深度受限
        assert params["compressed_max_depth"] <= 5

        # 压缩模型可预测
        compressed_model = result["optimized_model"]
        y_pred = compressed_model.predict(X_train)
        assert len(y_pred) == len(X_train)

    def test_optimize_ensemble(self, optimizer_and_data):
        """测试集成学习"""
        optimizer, X_train, y_train, _, _ = optimizer_and_data
        result = optimizer.optimize_ensemble(X_train, y_train)

        assert "optimized_model" in result
        assert "optimization_params" in result
        assert "expected_improvement" in result

        params = result["optimization_params"]
        assert "random_forest" in params["estimators"]
        assert "gradient_boosting" in params["estimators"]
        assert "extra_trees" in params["estimators"]
        assert params["voting"] == "soft"

        # 集成模型可预测
        ensemble_model = result["optimized_model"]
        y_pred = ensemble_model.predict(X_train)
        assert len(y_pred) == len(X_train)

    def test_run_all_optimizations(self, optimizer_and_data):
        """测试全量优化流程"""
        optimizer, X_train, y_train, X_test, y_test = optimizer_and_data
        results = optimizer.run_all_optimizations(X_train, y_train, X_test, y_test)

        # 四种策略与基线结果均存在
        expected_strategies = {
            "hyperparameters", "features", "compression", "ensemble", "baseline",
        }
        assert expected_strategies.issubset(results.keys())
        assert "total_time_seconds" in results

        # 每个策略含测试集指标
        for name in ["hyperparameters", "features", "compression", "ensemble"]:
            entry = results[name]
            assert "test_accuracy" in entry
            assert "test_f1" in entry
            assert 0.0 <= entry["test_accuracy"] <= 1.0
            assert 0.0 <= entry["test_f1"] <= 1.0

        # 总耗时合理
        assert results["total_time_seconds"] > 0.0
