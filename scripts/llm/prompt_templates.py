"""提示词模板库

管理 LLM 提取任务的提示词模板。
支持模板加载、变量渲染和模板列举。
模板文件存储在 C_llm_distilled/_metadata/prompt_templates/ 目录。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptTemplateLibrary:
    """提示词模板库

    Args:
        templates_dir: 模板文件目录
    """

    def __init__(self, templates_dir: Path | str):
        self.templates_dir = Path(templates_dir)
        # 目录不存在时自动创建，便于首次初始化
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def load(self, template_name: str) -> str:
        """加载模板内容

        Args:
            template_name: 模板名（不含 .txt 扩展名）

        Returns:
            模板文本内容

        Raises:
            FileNotFoundError: 模板不存在
        """
        file_path = self.templates_dir / f"{template_name}.txt"
        if not file_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_name} (path: {file_path})"
            )
        return file_path.read_text(encoding="utf-8")

    def render(self, template_name: str, **kwargs) -> str:
        """渲染模板（填充变量）

        Args:
            template_name: 模板名
            **kwargs: 模板变量

        Returns:
            渲染后的文本
        """
        template = self.load(template_name)
        # 使用 str.format 填充变量；模板内的 JSON 花括号需用 {{ }} 转义
        return template.format(**kwargs)

    def list_templates(self) -> list[str]:
        """列出所有可用模板名

        Returns:
            模板名列表（不含扩展名）
        """
        return [
            f.stem
            for f in self.templates_dir.glob("*.txt")
            if f.is_file()
        ]
