"""Markdown ↔ Confluence Storage Format 转换入口。

底层复用 mcp-server-confluence 的转换器实现。
对外保持原有函数签名，供 content.py 等模块调用。
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.tools.converters import (
    MarkdownToStorageConverter,
    StorageToMarkdownConverter,
)

logger = logging.getLogger("confluence-mcp-server")

_md_to_storage = MarkdownToStorageConverter()
_storage_to_md = StorageToMarkdownConverter()


def confluence_to_markdown(html_content: str, page_title: Optional[str] = None) -> str:
    """将 Confluence Storage Format 转换为 Markdown。"""
    if not html_content:
        return ""

    try:
        return _storage_to_md.convert(html_content, page_title=page_title)
    except Exception as e:
        logger.error(f"Confluence转Markdown失败: {str(e)}")
        return html_content


def markdown_to_confluence(
    markdown_content: str,
    mermaid_render_mode: str = "macro",
    page_id: Optional[str] = None,
    upload_attachment_bytes=None,
) -> str:
    """将 Markdown 转换为 Confluence Storage Format（仅返回正文）。"""
    storage, _ = markdown_to_confluence_with_attachments(
        markdown_content,
        mermaid_render_mode=mermaid_render_mode,
        page_id=page_id,
        upload_attachment_bytes=upload_attachment_bytes,
    )
    return storage


def markdown_to_confluence_with_attachments(
    markdown_content: str,
    mermaid_render_mode: str = "macro",
    page_id: Optional[str] = None,
    upload_attachment_bytes=None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """将 Markdown 转换为 Storage Format，并返回已上传附件列表。"""
    if not markdown_content:
        return "<p></p>", []

    try:
        return _md_to_storage.convert(
            markdown_content,
            mermaid_render_mode=mermaid_render_mode,
            page_id=page_id,
            upload_attachment_bytes=upload_attachment_bytes,
        )
    except Exception as e:
        logger.error(f"Markdown转Confluence失败: {str(e)}")
        return f"<p>{markdown_content}</p>", []
