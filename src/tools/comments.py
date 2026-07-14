"""页面评论相关 MCP tools。"""
import logging
from typing import Optional

from src.common.connection import ConfluenceConnection
from src.tools.format_converter import (
    confluence_to_markdown,
    markdown_to_confluence,
)
from src.common.server import mcp

logger = logging.getLogger("confluence-mcp-server")


@mcp.tool()
def get_comments(
    page_id: str,
    depth: str = "all",
    limit: int = 50,
    start: int = 0,
) -> dict:
    """
    获取页面评论（含嵌套回复），评论正文附带 Markdown。

    Args:
        page_id: 页面 ID
        depth: 'all' 获取嵌套回复，空字符串仅顶级评论
        limit: 返回数量限制，默认 50
        start: 分页起始偏移

    Returns:
        评论列表及分页信息；每条含 body.markdown
    """
    logger.info(f"获取评论: page_id={page_id}, depth={depth}, limit={limit}")

    params = {
        "expand": "body.storage,version,extensions.resolution,ancestors",
        "start": start,
        "limit": limit,
    }
    if depth:
        params["depth"] = depth

    try:
        data = ConfluenceConnection.get(
            f"/content/{page_id}/child/comment", params=params
        )
        for comment in data.get("results", []):
            storage = (
                comment.get("body", {}).get("storage", {}).get("value", "")
            )
            if storage:
                comment.setdefault("body", {})["markdown"] = confluence_to_markdown(
                    storage
                )

            version_info = comment.get("version", {})
            author = version_info.get("by", {})
            comment["author_name"] = author.get(
                "displayName", author.get("username", "未知")
            )
            ancestors = comment.get("ancestors", [])
            comment["parent_comment_id"] = (
                ancestors[-1]["id"] if ancestors else None
            )

        return data
    except Exception as e:
        logger.error(f"获取评论失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def add_comment(
    page_id: str,
    content: str,
    content_format: str = "markdown",
    parent_comment_id: Optional[str] = None,
) -> dict:
    """
    在页面上发布评论，支持回复已有评论。

    Args:
        page_id: 页面 ID
        content: 评论内容
        content_format: 'markdown'（默认）或 'plain_text' / 'storage'
        parent_comment_id: 父评论 ID（可选，用于回复）

    Returns:
        新评论详情
    """
    logger.info(
        f"发布评论: page_id={page_id}, parent_comment_id={parent_comment_id}"
    )

    if content_format == "markdown":
        storage_value = markdown_to_confluence(content)
    elif content_format == "storage":
        storage_value = content
    else:
        # plain_text
        escaped = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        storage_value = f"<p>{escaped}</p>"

    data = {
        "type": "comment",
        "container": {"id": page_id, "type": "page"},
        "body": {
            "storage": {
                "value": storage_value,
                "representation": "storage",
            }
        },
    }
    if parent_comment_id:
        data["ancestors"] = [{"id": parent_comment_id}]

    try:
        response = ConfluenceConnection.post("/content", data=data)
        return response
    except Exception as e:
        logger.error(f"发布评论失败: {str(e)}")
        return {"error": str(e)}
