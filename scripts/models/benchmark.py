"""AI模型性能基准测试与优化对比脚本

运行流程：
1. 生成合成数据集（1000样本，12维特征，3分类）
2. 训练基线模型并评估性能
3. 依次执行4种优化策略并评估
4. 输出结构化对比报告（JSON + 控制台表格）

使用方法：
    python -m scripts.models.benchmark
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.models.data_generator import HealthDataGenerator
from scripts.models.health_risk_model import HealthRiskModel
from scripts.models.model_optimizer import ModelOptimizer

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# 结果输出目录
RESULTS_DIR = project_root / "scripts" / "models" / "results"


def measure_inference_time(model, X_test: np.ndarray, n_runs: int = 5) -> float:
    """多次测量平均推理时间（毫秒/样本）"""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        model.predict(X_test)
        elapsed = (time.perf_counter() - start) / max(len(X_test), 1) * 1000
        times.append(elapsed)
    # 取中位数，减少抖动
    return float(np.median(times))


def measure_memory_mb(model) -> float:
    """估算模型内存占用（MB）"""
    if hasattr(model, "_estimate_memory_mb"):
        return model._estimate_memory_mb()
    # 对于Pipeline/VotingClassifier，估算各组件总和
    total_bytes = 0
    if hasattr(model, "estimators_"):
        for est in model.estimators_:
            if hasattr(est, "tree_"):
                total_bytes += est.tree_.node_count * 100
            elif hasattr(est, "estimators_"):
                for sub_est in est.estimators_:
                    if hasattr(sub_est, "tree_"):
                        total_bytes += sub_est.tree_.node_count * 100
    return total_bytes / (1024 * 1024)


def evaluate_model(model, X_test, y_test, name: str) -> dict:
    """统一评估模型性能，返回完整指标字典"""
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
    )

    # 预测
    y_pred = model.predict(X_test)

    # 推理时间（多次测量取中位数）
    inference_time_ms = measure_inference_time(model, X_test)

    # 内存占用
    memory_mb = measure_memory_mb(model)

    metrics = {
        "name": name,
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(
            precision_score(y_test, y_pred, average="weighted", zero_division=0)
        ),
        "recall": float(
            recall_score(y_test, y_pred, average="weighted", zero_division=0)
        ),
        "f1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        "inference_time_ms": inference_time_ms,
        "memory_mb": float(memory_mb),
    }
    logger.info(
        "%s: accuracy=%.4f, f1=%.4f, 推理=%.4fms, 内存=%.4fMB",
        name, metrics["accuracy"], metrics["f1"],
        metrics["inference_time_ms"], metrics["memory_mb"],
    )
    return metrics


def run_benchmark() -> dict:
    """运行完整基准测试与优化对比"""
    logger.info("=" * 70)
    logger.info("AI模型性能基准测试开始")
    logger.info("=" * 70)

    # === 1. 数据生成 ===
    logger.info("--- 步骤1: 生成合成数据集 ---")
    generator = HealthDataGenerator()
    X_train, X_test, y_train, y_test = generator.generate_train_test_split(
        n_samples=1000, test_size=0.2, random_state=42
    )
    logger.info(
        "数据集: 训练集=%d, 测试集=%d, 特征维度=%d",
        len(X_train), len(X_test), X_train.shape[1],
    )

    # === 2. 基线模型训练与评估 ===
    logger.info("--- 步骤2: 训练基线模型 ---")
    baseline_model = HealthRiskModel(
        n_estimators=100, max_depth=10, random_state=42
    )
    baseline_model.train(X_train, y_train)
    baseline_metrics = evaluate_model(
        baseline_model, X_test, y_test, "基线模型(RandomForest)"
    )

    # === 3. 运行优化策略 ===
    logger.info("--- 步骤3: 执行优化策略 ---")
    optimizer = ModelOptimizer(baseline_model)

    all_metrics = {"baseline": baseline_metrics}
    optimization_details = {}

    # 策略1: 超参数调优
    logger.info(">>> 策略1: 超参数调优 (GridSearchCV)")
    try:
        result = optimizer.optimize_hyperparameters(X_train, y_train, cv=3)
        opt_model = result["optimized_model"]
        metrics = evaluate_model(opt_model, X_test, y_test, "超参数调优")
        all_metrics["hyperparameters"] = metrics
        optimization_details["hyperparameters"] = result["optimization_params"]
    except Exception as e:
        logger.error("超参数调优失败: %s", e)
        all_metrics["hyperparameters"] = {"error": str(e)}

    # 策略2: 特征选择
    logger.info(">>> 策略2: 特征选择 (SelectKBest)")
    try:
        result = optimizer.optimize_features(X_train, y_train, k=8)
        opt_model = result["optimized_model"]
        metrics = evaluate_model(opt_model, X_test, y_test, "特征选择")
        all_metrics["feature_selection"] = metrics
        optimization_details["feature_selection"] = {
            "k": result["optimization_params"]["k"],
            "selected_indices": result["optimization_params"][
                "selected_feature_indices"
            ],
        }
    except Exception as e:
        logger.error("特征选择失败: %s", e)
        all_metrics["feature_selection"] = {"error": str(e)}

    # 策略3: 模型压缩
    logger.info(">>> 策略3: 模型压缩 (减少树数量和深度)")
    try:
        result = optimizer.optimize_model_compression(X_train, y_train)
        opt_model = result["optimized_model"]
        metrics = evaluate_model(opt_model, X_test, y_test, "模型压缩")
        all_metrics["compression"] = metrics
        optimization_details["compression"] = result["optimization_params"]
    except Exception as e:
        logger.error("模型压缩失败: %s", e)
        all_metrics["compression"] = {"error": str(e)}

    # 策略4: 集成学习
    logger.info(">>> 策略4: 集成学习 (RF+GB+ET Voting)")
    try:
        result = optimizer.optimize_ensemble(X_train, y_train)
        opt_model = result["optimized_model"]
        metrics = evaluate_model(opt_model, X_test, y_test, "集成学习")
        all_metrics["ensemble"] = metrics
        optimization_details["ensemble"] = result["optimization_params"]
    except Exception as e:
        logger.error("集成学习失败: %s", e)
        all_metrics["ensemble"] = {"error": str(e)}

    # === 4. 汇总报告 ===
    logger.info("--- 步骤4: 生成对比报告 ---")
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": {
            "n_samples": 1000,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": X_train.shape[1],
            "class_distribution": {
                "train_low": int((y_train == 0).sum()),
                "train_medium": int((y_train == 1).sum()),
                "train_high": int((y_train == 2).sum()),
            },
        },
        "metrics": all_metrics,
        "optimization_details": optimization_details,
    }

    # 计算相对基线的改进
    improvements = {}
    baseline_acc = baseline_metrics["accuracy"]
    baseline_f1 = baseline_metrics["f1"]
    baseline_time = baseline_metrics["inference_time_ms"]
    baseline_mem = baseline_metrics["memory_mb"]

    for name, m in all_metrics.items():
        if name == "baseline" or "error" in m:
            continue
        improvements[name] = {
            "accuracy_delta": m["accuracy"] - baseline_acc,
            "f1_delta": m["f1"] - baseline_f1,
            "inference_time_ratio": m["inference_time_ms"] / baseline_time
            if baseline_time > 0
            else 0,
            "memory_ratio": m["memory_mb"] / baseline_mem
            if baseline_mem > 0
            else 0,
        }
    report["improvements"] = improvements

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "optimization_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("报告已保存至: %s", report_path)

    # 控制台输出对比表格
    print("\n" + "=" * 80)
    print("AI模型优化前后性能对比报告")
    print("=" * 80)
    print(
        f"{'模型':<25} {'准确率':>8} {'F1':>8} "
        f"{'推理(ms)':>10} {'内存(MB)':>10}"
    )
    print("-" * 80)
    for name, m in all_metrics.items():
        if "error" in m:
            print(f"{name:<25} {'ERROR':>8}")
            continue
        print(
            f"{m['name']:<25} {m['accuracy']:>8.4f} {m['f1']:>8.4f} "
            f"{m['inference_time_ms']:>10.4f} {m['memory_mb']:>10.4f}"
        )
    print("-" * 80)
    print("\n相对基线改进：")
    print(f"{'策略':<25} {'Δ准确率':>10} {'ΔF1':>10} {'推理比':>10} {'内存比':>10}")
    print("-" * 80)
    for name, imp in improvements.items():
        print(
            f"{name:<25} {imp['accuracy_delta']:>+10.4f} "
            f"{imp['f1_delta']:>+10.4f} "
            f"{imp['inference_time_ratio']:>10.2f}x "
            f"{imp['memory_ratio']:>10.2f}x"
        )
    print("=" * 80)

    return report


if __name__ == "__main__":
    run_benchmark()
