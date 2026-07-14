"""Mermaid 图表双向转换处理器

复用自 mcp-server-confluence (Coratch)。
"""
import logging
import re
from typing import List, Tuple

logger = logging.getLogger("confluence-mcp-server")


class MermaidHandler:
    """Mermaid 图表转换处理器"""

    # Markdown 中的 Mermaid 代码块模式
    MD_MERMAID_PATTERN = re.compile(
        r'```mermaid\s*\n(.*?)\n```',
        re.DOTALL | re.MULTILINE
    )

    # Confluence Storage Format 中的 Mermaid 宏模式（兼容 mermaid-macro 和 mermaid）
    CONFLUENCE_MERMAID_PATTERN = re.compile(
        r'<ac:structured-macro\s+ac:name="mermaid(?:-macro)?"[^>]*>'
        r'.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>'
        r'.*?</ac:structured-macro>',
        re.DOTALL | re.MULTILINE
    )

    @classmethod
    def markdown_to_confluence(cls, markdown_content: str) -> str:
        """将 Markdown 中的 Mermaid 代码块转换为 Confluence 宏"""

        def replace_mermaid(match: re.Match) -> str:
            mermaid_code = match.group(1).strip()
            logger.debug(f"转换 Mermaid 代码块到 Confluence 宏 ({len(mermaid_code)} 字符)")
            return (
                '<ac:structured-macro ac:name="mermaid-macro" ac:schema-version="1">'
                '<ac:plain-text-body><![CDATA['
                f'{mermaid_code}'
                ']]></ac:plain-text-body>'
                '</ac:structured-macro>'
            )

        return cls.MD_MERMAID_PATTERN.sub(replace_mermaid, markdown_content)

    @classmethod
    def confluence_to_markdown(cls, confluence_content: str) -> str:
        """将 Confluence Mermaid 宏转换为 Markdown 代码块"""

        def replace_macro(match: re.Match) -> str:
            mermaid_code = match.group(1).strip()
            logger.debug(f"转换 Confluence Mermaid 宏到代码块 ({len(mermaid_code)} 字符)")
            return f'```mermaid\n{mermaid_code}\n```'

        return cls.CONFLUENCE_MERMAID_PATTERN.sub(replace_macro, confluence_content)

    @classmethod
    def extract_mermaid_blocks(cls, markdown_content: str) -> List[Tuple[str, str]]:
        """从 Markdown 中提取所有 Mermaid 代码块

        Returns:
            (原始块, Mermaid 代码) 的列表
        """
        matches = cls.MD_MERMAID_PATTERN.finditer(markdown_content)
        return [(match.group(0), match.group(1).strip()) for match in matches]

    @classmethod
    def extract_confluence_mermaid(cls, confluence_content: str) -> List[Tuple[str, str]]:
        """从 Confluence 内容中提取所有 Mermaid 宏

        Returns:
            (原始宏, Mermaid 代码) 的列表
        """
        matches = cls.CONFLUENCE_MERMAID_PATTERN.finditer(confluence_content)
        return [(match.group(0), match.group(1).strip()) for match in matches]
