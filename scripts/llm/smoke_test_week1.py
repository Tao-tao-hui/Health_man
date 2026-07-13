"""Phase 4 Week 1 冒烟测试：验证 1 篇文献的端到端蒸馏流程

使用模拟文献数据测试完整的提取→验证→存储流水线。
需要 GLM-4-Flash API Key 已配置。

运行方式：
    python scripts/llm/smoke_test_week1.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.llm.glm_adapter import GlmAdapter
from scripts.llm.prompt_templates import PromptTemplateLibrary
from scripts.llm.validator import DualLayerValidator
from scripts.llm.master_orchestrator import MasterOrchestrator
from scripts.llm.llm_pipeline import LlmPipeline
from scripts.llm.llm_config import (
    get_credential_manager,
    get_audit_logger,
    get_prompt_templates_dir,
    get_distilled_dir,
)


def main():
    # 1. 初始化组件（使用 llm_config 集中管理）
    cm = get_credential_manager()
    api_key = cm.retrieve("glm_api_key")
    if not api_key:
        print("错误: GLM API Key 未配置。")
        print("请运行以下命令配置 API Key:")
        print('  python -c "from scripts.llm.llm_config import get_credential_manager as g; g().store(\'glm_api_key\', \'YOUR_API_KEY\')"')
        sys.exit(1)

    adapter = GlmAdapter(api_key=api_key)
    prompt_lib = PromptTemplateLibrary(get_prompt_templates_dir())
    validator = DualLayerValidator()
    audit_logger = get_audit_logger()
    master = MasterOrchestrator(adapter, prompt_lib, validator, audit_logger)

    pipeline = LlmPipeline(
        master=master,
        max_size_mb=500,
        audit_log_path=get_audit_logger().log_path,
    )

    # 2. 健康检查
    print("正在检查 GLM-4-Flash API 连通性...")
    if not adapter.health_check():
        print("错误: GLM-4-Flash API 不可达")
        sys.exit(1)
    print("GLM-4-Flash API 健康检查通过")

    # 3. 准备测试文献文本（模拟一篇含体脂率数据的摘要）
    test_literature = """
    研究对象：中国成年健康人群（n=500，18-65岁，男女各半）。
    方法：生物电阻抗法（BIA）测量体成分。
    结果：男性体脂率均值为 22.5% ± 5.3%，P5-P95 百分位范围为 10.2%-35.8%。
          女性体脂率均值为 32.1% ± 6.1%，P5-P95 百分位范围为 18.5%-45.2%。
    结论：建立了中国成人 BIA 体脂率参考范围。
    """

    # 4. 执行冒烟测试
    print("\n开始冒烟测试...")
    tasks = [
        {
            "indicator_id": "IND-SMOKE-TEST",
            "literature_texts": [test_literature],
            "prompt_template": "extract_reference_range",
        }
    ]

    dest_dir = get_distilled_dir()
    result = pipeline.run(tasks, dest_dir)

    # 5. 验证结果
    print(f"\n冒烟测试结果:")
    print(f"  总提取数: {result.total_extracted}")
    print(f"  验证通过: {result.total_validated}")
    print(f"  被拒绝: {result.total_rejected}")
    print(f"  Token 消耗: {result.total_tokens_consumed}")
    print(f"  成功: {result.success}")
    if result.errors:
        print(f"  错误: {result.errors}")

    # 6. 检查输出文件
    output_files = list(dest_dir.glob("*_distilled.json"))
    print(f"  输出文件: {[f.name for f in output_files]}")

    # 7. 哈希链验证
    audit = get_audit_logger()
    chain_valid = audit.verify_chain()
    print(f"  审计日志哈希链: {'完整' if chain_valid else '损坏'}")

    if result.success and result.total_validated >= 1:
        print("\n冒烟测试通过: 端到端蒸馏流程正常")
        # 清理测试数据
        test_file = dest_dir / "IND-SMOKE-TEST_distilled.json"
        if test_file.exists():
            test_file.unlink()
            print("已清理冒烟测试临时数据")
        return 0
    else:
        print(f"\n冒烟测试失败: {result.errors}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
