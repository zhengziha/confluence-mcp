"""Storage Format 到 Markdown 转换器

复用自 mcp-server-confluence (Coratch)。
"""
import logging
import re
from typing import Optional

import html2text
from bs4 import BeautifulSoup

from .drawio_handler import DrawioHandler
from .mermaid_handler import MermaidHandler

logger = logging.getLogger("confluence-mcp-server")


class StorageToMarkdownConverter:
    """Storage Format 到 Markdown 转换器"""

    def __init__(self) -> None:
        self.h2t = html2text.HTML2Text()
        self.h2t.body_width = 0
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.ignore_emphasis = False
        self.h2t.skip_internal_links = False
        self.h2t.inline_links = True
        self.h2t.protect_links = True
        self.h2t.mark_code = True
        self.h2t.wrap_links = False
        self.h2t.wrap_list_items = False
        self.h2t.escape_snob = True

    def convert(self, storage_content: str, page_title: Optional[str] = None) -> str:
        """转换 Storage Format 到 Markdown

        Args:
            storage_content: Confluence Storage Format 内容
            page_title: 页面标题（可选，用于添加元数据头）

        Returns:
            Markdown 内容
        """
        logger.info("开始转换 Storage Format 到 Markdown")

        mermaid_blocks = MermaidHandler.extract_confluence_mermaid(storage_content)
        mermaid_placeholders = {}

        for idx, (original, code) in enumerate(mermaid_blocks):
            placeholder = f"___MERMAID_BLOCK_{idx}___"
            mermaid_placeholders[placeholder] = code
            storage_content = storage_content.replace(original, placeholder)

        drawio_blocks = DrawioHandler.extract_confluence_drawio(storage_content)
        drawio_placeholders = {}

        for idx, (original, params) in enumerate(drawio_blocks):
            placeholder = f"___DRAWIO_BLOCK_{idx}___"
            diagram_name = params.get('diagramName', params.get('attachment', 'diagram.drawio'))
            drawio_placeholders[placeholder] = diagram_name
            storage_content = storage_content.replace(original, placeholder)

        storage_content, code_placeholders = self._process_confluence_macros(storage_content)

        markdown_content = self.h2t.handle(storage_content)

        for placeholder, code in mermaid_placeholders.items():
            mermaid_block = f'\n```mermaid\n{code.rstrip()}\n```\n'
            markdown_content = markdown_content.replace(placeholder, mermaid_block)
            escaped_placeholder = placeholder.replace('_', r'\_')
            markdown_content = markdown_content.replace(escaped_placeholder, mermaid_block)

        for placeholder, diagram_name in drawio_placeholders.items():
            drawio_block = DrawioHandler.drawio_to_markdown(diagram_name)
            markdown_content = markdown_content.replace(placeholder, drawio_block)
            escaped_placeholder = placeholder.replace('_', r'\_')
            markdown_content = markdown_content.replace(escaped_placeholder, drawio_block)

        for placeholder, (language, code) in code_placeholders.items():
            code_block = f'\n```{language}\n{code.rstrip()}\n```\n'
            markdown_content = markdown_content.replace(placeholder, code_block)
            escaped_placeholder = placeholder.replace('_', r'\_')
            markdown_content = markdown_content.replace(escaped_placeholder, code_block)

        markdown_content = self._post_process(markdown_content)

        if page_title:
            metadata = f"---\ntitle: {page_title}\n---\n\n"
            markdown_content = metadata + markdown_content

        logger.info("转换完成")
        return markdown_content

    def _process_confluence_macros(self, content: str):
        """处理 Confluence 宏

        Returns:
            (处理后的内容, 代码块占位符字典)
        """
        soup = BeautifulSoup(content, "html.parser")
        code_placeholders = {}
        code_counter = 0

        for macro in soup.find_all("ac:structured-macro", {"ac:name": "expand"}):
            title_param = macro.find("ac:parameter", {"ac:name": "title"})
            title = title_param.get_text() if title_param else "展开内容"
            body = macro.find("ac:rich-text-body")
            if body:
                body_html = ''.join(str(child) for child in body.children)
                replacement = f'<!-- {title} -->\n{body_html}\n<!-- /expand -->'
                macro.replace_with(BeautifulSoup(replacement, 'html.parser'))

        soup = BeautifulSoup(str(soup), "html.parser")

        for macro in soup.find_all("ac:structured-macro"):
            macro_name = macro.get("ac:name", "")

            if macro_name in ["info", "note", "tip"]:
                body = macro.find("ac:rich-text-body")
                if body:
                    body_text = str(body)
                    macro.replace_with(BeautifulSoup(
                        f'<blockquote><strong>ℹ️ Info:</strong><br/>{body_text}</blockquote>',
                        'html.parser'
                    ))

            elif macro_name == "warning":
                body = macro.find("ac:rich-text-body")
                if body:
                    body_text = str(body)
                    macro.replace_with(BeautifulSoup(
                        f'<blockquote><strong>⚠️ Warning:</strong><br/>{body_text}</blockquote>',
                        'html.parser'
                    ))

            elif macro_name == "code":
                plain_text_body = macro.find("ac:plain-text-body")
                if plain_text_body:
                    code_content = plain_text_body.get_text()
                    language = ""
                    lang_param = macro.find("ac:parameter", {"ac:name": "language"})
                    if lang_param:
                        language = lang_param.get_text()

                    placeholder = f"___CODE_PLACEHOLDER_{code_counter}___"
                    code_placeholders[placeholder] = (language, code_content)
                    code_counter += 1
                    macro.replace_with(placeholder)

        return str(soup), code_placeholders

    def _post_process(self, markdown_content: str) -> str:
        """后处理 Markdown 内容"""
        markdown_content = re.sub(r'\*\*([^*]+)\*\* ([：:：])', r'**\1**\2', markdown_content)
        markdown_content = re.sub(
            r'^(#{1,6}) (\d+)\\\.', r'\1 \2.', markdown_content, flags=re.MULTILINE
        )

        lines = markdown_content.split('\n')
        processed_lines = []

        for line in lines:
            if '\\-' in line:
                if not line.strip().startswith('```'):
                    parts = line.split('\\-')
                    if len(parts) > 1:
                        processed_lines.append(parts[0].rstrip())
                        for part in parts[1:]:
                            if part.strip():
                                processed_lines.append('- ' + part.strip())
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)

        markdown_content = '\n'.join(processed_lines)
        markdown_content = re.sub(r'^\* \* \*$', '---', markdown_content, flags=re.MULTILINE)
        markdown_content = re.sub(r'```\n\n\n', '```\n\n', markdown_content)
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)

        lines = markdown_content.split('\n')
        lines = [line.rstrip() for line in lines]
        markdown_content = '\n'.join(lines)
        markdown_content = markdown_content.strip() + '\n'

        return markdown_content
