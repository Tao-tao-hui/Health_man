"""PromptTemplateLibrary 单元测试

验证提示词模板库的加载、渲染和列举功能。
"""
import pytest
from pathlib import Path

from scripts.llm.prompt_templates import PromptTemplateLibrary


class TestPromptTemplateLibrary:
    """PromptTemplateLibrary 测试套件"""

    def test_load_returns_template_content(self, tmp_path):
        """测试加载模板返回内容"""
        # 创建测试模板文件
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取指标: {indicator_name}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        content = lib.load("extract_reference_range")
        assert "提取指标" in content
        assert "{indicator_name}" in content

    def test_render_fills_variables(self, tmp_path):
        """测试渲染模板填充变量"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text(
            "提取指标: {indicator_name}\n文献: {literature_text}", encoding="utf-8"
        )
        lib = PromptTemplateLibrary(templates_dir)
        rendered = lib.render(
            "extract_reference_range",
            indicator_name="体脂率",
            literature_text="某文献内容",
        )
        assert "体脂率" in rendered
        assert "某文献内容" in rendered
        assert "{" not in rendered

    def test_list_templates_returns_all(self, tmp_path):
        """测试列举所有模板"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        (templates_dir / "extract_reference_range.txt").write_text("a", encoding="utf-8")
        (templates_dir / "extract_percentile_table.txt").write_text("b", encoding="utf-8")
        lib = PromptTemplateLibrary(templates_dir)
        names = lib.list_templates()
        assert "extract_reference_range" in names
        assert "extract_percentile_table" in names
        assert len(names) == 2

    def test_load_nonexistent_raises_error(self, tmp_path):
        """测试加载不存在的模板抛出 FileNotFoundError"""
        templates_dir = tmp_path / "prompt_templates"
        templates_dir.mkdir()
        lib = PromptTemplateLibrary(templates_dir)
        with pytest.raises(FileNotFoundError, match="Template not found"):
            lib.load("nonexistent_template")
