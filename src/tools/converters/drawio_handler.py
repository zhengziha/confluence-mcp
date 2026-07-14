"""Draw.io 图表双向转换处理器

复用自 mcp-server-confluence (Coratch)。
处理 Confluence Storage Format 中的 draw.io 宏与 Markdown 之间的双向转换。
draw.io 图表以附件方式存储，宏通过 diagramName/attachment 参数引用。
"""
import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger("confluence-mcp-server")


class DrawioHandler:
    """Draw.io 图表转换处理器"""

    CONFLUENCE_DRAWIO_PATTERN = re.compile(
        r'<ac:structured-macro[^>]*\bac:name="drawio"[^>]*>'
        r'(.*?)'
        r'</ac:structured-macro>',
        re.DOTALL | re.MULTILINE
    )

    MD_DRAWIO_PATTERN = re.compile(
        r'> ?\U0001f4ca ?\*\*Draw\.io (?:图表|Diagram)\*\*[：:]\s*(.+?)$',
        re.MULTILINE
    )

    MD_DRAWIO_CODEBLOCK_PATTERN = re.compile(
        r'```drawio\s*\n(.*?)\n```',
        re.DOTALL | re.MULTILINE
    )

    @classmethod
    def extract_confluence_drawio(cls, confluence_content: str) -> List[Tuple[str, Dict[str, str]]]:
        """从 Confluence Storage Format 中提取所有 draw.io 宏

        Returns:
            (原始宏文本, 参数字典) 的列表
        """
        results = []
        for match in cls.CONFLUENCE_DRAWIO_PATTERN.finditer(confluence_content):
            full_macro = match.group(0)
            params = cls._extract_params(match.group(1))
            if params:
                logger.debug(f"提取到 draw.io 图表: {params.get('diagramName', 'unknown')}")
                results.append((full_macro, params))
        return results

    @classmethod
    def _extract_params(cls, macro_inner: str) -> Dict[str, str]:
        params = {}
        param_pattern = re.compile(
            r'<ac:parameter\s+ac:name="([^"]+)"[^>]*>(.*?)</ac:parameter>',
            re.DOTALL
        )
        for param_match in param_pattern.finditer(macro_inner):
            params[param_match.group(1)] = param_match.group(2).strip()
        return params

    @classmethod
    def drawio_to_markdown(cls, diagram_name: str) -> str:
        """将 draw.io 图表信息转换为 Markdown 格式"""
        return (
            f'> \U0001f4ca **Draw.io 图表**: {diagram_name}\n'
            f'> [draw.io 在线编辑器](https://app.diagrams.net/)'
        )

    @classmethod
    def markdown_to_drawio_macro(cls, diagram_name: str) -> str:
        """将 Markdown 中的 draw.io 标记还原为 Confluence 宏"""
        return (
            '<ac:structured-macro ac:name="drawio" ac:schema-version="1">'
            f'<ac:parameter ac:name="diagramName">{diagram_name}</ac:parameter>'
            f'<ac:parameter ac:name="attachment">{diagram_name}</ac:parameter>'
            '</ac:structured-macro>'
        )

    @classmethod
    def extract_markdown_drawio(cls, markdown_content: str) -> List[Tuple[str, str]]:
        """从 Markdown 中提取所有 draw.io 图表引用标记（blockquote 格式）

        Returns:
            (原始标记文本, 图表名称) 的列表
        """
        results = []
        for match in cls.MD_DRAWIO_PATTERN.finditer(markdown_content):
            full_match = match.group(0)
            diagram_name = match.group(1).strip()

            link_line_pattern = re.compile(
                re.escape(full_match) + r'\n> ?\[draw\.io[^\]]*\]\([^\)]+\)',
                re.MULTILINE
            )
            link_match = link_line_pattern.search(markdown_content)
            if link_match:
                full_match = link_match.group(0)

            logger.debug(f"提取到 Markdown draw.io 标记: {diagram_name}")
            results.append((full_match, diagram_name))

        return results

    @classmethod
    def extract_drawio_codeblocks(cls, markdown_content: str) -> List[Tuple[str, str]]:
        """从 Markdown 中提取所有 draw.io XML 代码块（```drawio 格式）

        Returns:
            (原始代码块文本, XML 内容) 的列表
        """
        results = []
        for match in cls.MD_DRAWIO_CODEBLOCK_PATTERN.finditer(markdown_content):
            full_match = match.group(0)
            xml_content = match.group(1).strip()
            logger.debug(f"提取到 draw.io XML 代码块 ({len(xml_content)} bytes)")
            results.append((full_match, xml_content))
        return results

    @staticmethod
    def generate_attachment_filename(index: int) -> str:
        """生成 draw.io 附件文件名"""
        return f"drawio_diagram_{index}.drawio"
