"""Markdown 到 Storage Format 转换器

复用自 mcp-server-confluence (Coratch)。
同步转换；Mermaid 支持 macro / code_block。
Draw.io XML 在提供 page_id 时可上传附件并插入宏，否则降级为代码宏。
"""
import base64
import logging
import re
import zlib
from typing import Any, Callable, Dict, List, Optional, Tuple

import markdown
from bs4 import BeautifulSoup, Tag

from .drawio_handler import DrawioHandler
from .mermaid_handler import MermaidHandler

logger = logging.getLogger("confluence-mcp-server")

# (page_id, content, file_name, content_type, comment) -> attachment dict
UploadBytesFn = Callable[..., Dict[str, Any]]


class MarkdownToStorageConverter:
    """Markdown 到 Storage Format 转换器"""

    def __init__(self) -> None:
        # 不使用 codehilite，避免语法高亮 span，并保留 language 信息
        self.md = markdown.Markdown(
            extensions=[
                'extra',
                'fenced_code',
                'tables',
            ]
        )

    def convert(
        self,
        markdown_content: str,
        mermaid_render_mode: str = "macro",
        page_id: Optional[str] = None,
        upload_attachment_bytes: Optional[UploadBytesFn] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """转换 Markdown 到 Storage Format

        Args:
            markdown_content: Markdown 内容
            mermaid_render_mode: Mermaid 渲染模式
                - "macro": 使用 Confluence 原生 Mermaid 宏（需要 Mermaid 插件）
                - "code_block": 使用代码块 + Mermaid Live Editor 链接
            page_id: 页面 ID（上传 draw.io 附件时需要）
            upload_attachment_bytes: 附件上传回调，签名同
                ConfluenceConnection.upload_attachment_bytes

        Returns:
            (Confluence Storage Format 内容, 已上传附件列表)
        """
        logger.info(
            f"开始转换 Markdown 到 Storage Format (mermaid_render_mode={mermaid_render_mode})"
        )
        attachments: List[Dict[str, Any]] = []

        if mermaid_render_mode not in ("macro", "code_block"):
            logger.warning(
                f"不支持的 mermaid_render_mode={mermaid_render_mode}，降级为 code_block"
            )
            mermaid_render_mode = "code_block"

        markdown_content = self._remove_metadata(markdown_content)

        mermaid_placeholders = {}

        if mermaid_render_mode == "macro":
            mermaid_blocks = MermaidHandler.extract_mermaid_blocks(markdown_content)
            for idx, (original, code) in enumerate(mermaid_blocks):
                placeholder = f"MERMAIDBLOCK{idx}PLACEHOLDER"
                mermaid_placeholders[placeholder] = (
                    '<ac:structured-macro ac:name="mermaid-macro" ac:schema-version="1">'
                    '<ac:plain-text-body><![CDATA['
                    f'{code}'
                    ']]></ac:plain-text-body>'
                    '</ac:structured-macro>'
                )
                markdown_content = markdown_content.replace(original, placeholder)

        elif mermaid_render_mode == "code_block":
            mermaid_blocks = MermaidHandler.extract_mermaid_blocks(markdown_content)
            for idx, (original, code) in enumerate(mermaid_blocks):
                placeholder = f"MERMAIDBLOCK{idx}PLACEHOLDER"
                mermaid_placeholders[placeholder] = self._create_mermaid_code_block(code)
                markdown_content = markdown_content.replace(original, placeholder)

        drawio_placeholders = {}
        drawio_blocks = DrawioHandler.extract_markdown_drawio(markdown_content)

        for idx, (original, diagram_name) in enumerate(drawio_blocks):
            placeholder = f"DRAWIOBLOCK{idx}PLACEHOLDER"
            drawio_placeholders[placeholder] = DrawioHandler.markdown_to_drawio_macro(diagram_name)
            markdown_content = markdown_content.replace(original, placeholder)

        drawio_codeblocks = DrawioHandler.extract_drawio_codeblocks(markdown_content)
        if drawio_codeblocks and page_id and upload_attachment_bytes:
            for idx, (original, xml_content) in enumerate(drawio_codeblocks):
                filename = DrawioHandler.generate_attachment_filename(idx)
                placeholder = f"DRAWIOCODEBLOCK{idx}PLACEHOLDER"
                try:
                    attachment = upload_attachment_bytes(
                        page_id=page_id,
                        content=xml_content.encode("utf-8"),
                        file_name=filename,
                        content_type="application/vnd.jgraph.mxfile",
                        comment="Draw.io diagram uploaded via MCP",
                    )
                    attachments.append(attachment)
                    drawio_placeholders[placeholder] = (
                        DrawioHandler.markdown_to_drawio_macro(filename)
                    )
                    logger.info(f"上传 draw.io 附件成功: {filename}")
                except Exception as e:
                    logger.error(f"上传 draw.io 附件失败: {e}")
                    drawio_placeholders[placeholder] = (
                        '<ac:structured-macro ac:name="code">'
                        '<ac:parameter ac:name="language">xml</ac:parameter>'
                        '<ac:parameter ac:name="title">Draw.io Diagram XML</ac:parameter>'
                        f'<ac:plain-text-body><![CDATA[{xml_content}]]></ac:plain-text-body>'
                        '</ac:structured-macro>'
                    )
                markdown_content = markdown_content.replace(original, placeholder)
        elif drawio_codeblocks:
            logger.warning("draw.io 代码块需要 page_id 才能上传附件，降级为 XML 代码宏")
            for idx, (original, xml_content) in enumerate(drawio_codeblocks):
                placeholder = f"DRAWIOCODEBLOCK{idx}PLACEHOLDER"
                drawio_placeholders[placeholder] = (
                    '<ac:structured-macro ac:name="code">'
                    '<ac:parameter ac:name="language">xml</ac:parameter>'
                    '<ac:parameter ac:name="title">Draw.io Diagram XML</ac:parameter>'
                    f'<ac:plain-text-body><![CDATA[{xml_content}]]></ac:plain-text-body>'
                    '</ac:structured-macro>'
                )
                markdown_content = markdown_content.replace(original, placeholder)

        self.md.reset()
        html_content = self.md.convert(markdown_content)

        for placeholder, replacement in mermaid_placeholders.items():
            html_content = html_content.replace(f'<p>{placeholder}</p>', replacement)
            html_content = html_content.replace(placeholder, replacement)

        for placeholder, replacement in drawio_placeholders.items():
            html_content = html_content.replace(f'<p>{placeholder}</p>', replacement)
            html_content = html_content.replace(placeholder, replacement)

        storage_content = self._html_to_storage(html_content)

        logger.info(f"转换完成，上传了 {len(attachments)} 个附件")
        return storage_content, attachments

    def _create_mermaid_code_block(self, code: str) -> str:
        """创建 Mermaid 代码块的 Confluence 格式（可折叠 + Live Editor 链接）"""
        compress_obj = zlib.compressobj(level=9, wbits=-15)
        compressed = compress_obj.compress(code.encode('utf-8')) + compress_obj.flush()
        encoded = base64.urlsafe_b64encode(compressed).decode('utf-8')
        live_editor_url = f"https://mermaid.live/edit#pako:{encoded}"

        return (
            '<ac:structured-macro ac:name="expand">'
            '<ac:parameter ac:name="title">📝 点击展开查看 Mermaid 代码</ac:parameter>'
            '<ac:rich-text-body>'
            '<ac:structured-macro ac:name="code">'
            '<ac:parameter ac:name="language">mermaid</ac:parameter>'
            '<ac:parameter ac:name="title">Mermaid 源代码</ac:parameter>'
            '<ac:plain-text-body><![CDATA['
            f'{code}'
            ']]></ac:plain-text-body>'
            '</ac:structured-macro>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
            f'<p style="margin-top: 15px;">'
            f'<a href="{live_editor_url}" target="_blank" '
            f'style="display: inline-block; padding: 10px 20px; background-color: #0052CC; '
            f'color: white; text-decoration: none; border-radius: 3px; font-weight: bold;">'
            f'🎨 在 Mermaid Live Editor 中查看和编辑'
            f'</a>'
            f'</p>'
        )

    def _remove_metadata(self, markdown_content: str) -> str:
        """移除 YAML 元数据头"""
        pattern = re.compile(r'^---\s*\n.*?\n---\s*\n', re.DOTALL | re.MULTILINE)
        return pattern.sub('', markdown_content)

    def _html_to_storage(self, html_content: str) -> str:
        """转换 HTML 到 Confluence Storage Format"""
        soup = BeautifulSoup(html_content, 'html.parser')
        self._process_code_blocks(soup)
        self._process_tables(soup)
        self._process_blockquotes(soup)
        return str(soup)

    def _process_code_blocks(self, soup: BeautifulSoup) -> None:
        """处理代码块，转换为 Confluence 代码宏"""
        for div in soup.find_all('div', class_='codehilite'):
            pre = div.find('pre')
            if pre:
                code = pre.find('code')
                if code:
                    code_content = code.get_text()
                    language = ""
                    div_classes = div.get('class', [])
                    for cls in div_classes:
                        if cls.startswith('language-'):
                            language = cls.replace('language-', '')
                            break

                    if not language and code.get('class'):
                        for cls in code.get('class', []):
                            if cls.startswith('language-'):
                                language = cls.replace('language-', '')
                                break

                    macro = soup.new_tag('ac:structured-macro')
                    macro['ac:name'] = 'code'
                    if language:
                        param = soup.new_tag('ac:parameter')
                        param['ac:name'] = 'language'
                        param.string = language
                        macro.append(param)
                    body = soup.new_tag('ac:plain-text-body')
                    cdata = f'<![CDATA[{code_content}]]>'
                    body.append(BeautifulSoup(cdata, 'html.parser'))
                    macro.append(body)
                    div.replace_with(macro)

        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                code_content = code.get_text()
                if code_content.strip().startswith('MERMAIDBLOCK') and code_content.strip().endswith('PLACEHOLDER'):
                    continue
                if code_content.strip().startswith('DRAWIOCODEBLOCK') and code_content.strip().endswith('PLACEHOLDER'):
                    continue

                language = ""
                if code.get('class'):
                    for cls in code.get('class', []):
                        if cls.startswith('language-'):
                            language = cls.replace('language-', '')
                            break

                macro = soup.new_tag('ac:structured-macro')
                macro['ac:name'] = 'code'
                if language:
                    param = soup.new_tag('ac:parameter')
                    param['ac:name'] = 'language'
                    param.string = language
                    macro.append(param)
                body = soup.new_tag('ac:plain-text-body')
                cdata = f'<![CDATA[{code_content}]]>'
                body.append(BeautifulSoup(cdata, 'html.parser'))
                macro.append(body)
                pre.replace_with(macro)

    def _process_tables(self, soup: BeautifulSoup) -> None:
        for table in soup.find_all('table'):
            if not table.get('border'):
                table['border'] = '1'

    def _process_blockquotes(self, soup: BeautifulSoup) -> None:
        for blockquote in soup.find_all('blockquote'):
            text = blockquote.get_text().strip()
            if text.startswith('ℹ️ Info:') or text.startswith('Info:'):
                self._convert_to_info_macro(blockquote, soup)
            elif text.startswith('⚠️ Warning:') or text.startswith('Warning:'):
                self._convert_to_warning_macro(blockquote, soup)

    def _convert_to_info_macro(self, blockquote: Tag, soup: BeautifulSoup) -> None:
        content = str(blockquote)
        content = re.sub(r'<strong>.*?Info:.*?</strong><br/>', '', content)
        macro = soup.new_tag('ac:structured-macro')
        macro['ac:name'] = 'info'
        body = soup.new_tag('ac:rich-text-body')
        body.append(BeautifulSoup(content, 'html.parser'))
        macro.append(body)
        blockquote.replace_with(macro)

    def _convert_to_warning_macro(self, blockquote: Tag, soup: BeautifulSoup) -> None:
        content = str(blockquote)
        content = re.sub(r'<strong>.*?Warning:.*?</strong><br/>', '', content)
        macro = soup.new_tag('ac:structured-macro')
        macro['ac:name'] = 'warning'
        body = soup.new_tag('ac:rich-text-body')
        body.append(BeautifulSoup(content, 'html.parser'))
        macro.append(body)
        blockquote.replace_with(macro)
