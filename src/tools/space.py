import logging
from typing import Optional

from src.common.connection import ConfluenceConnection
from src.common.server import mcp

logger = logging.getLogger("confluence-mcp-server")


@mcp.tool()
def list_spaces(
    limit: int = 20,
    start: int = 0,
    expand: str = "description.plain,homepage",
    space_type: Optional[str] = None,
) -> dict:
    """
    列出所有空间。

    Args:
        limit: 返回结果数量限制，默认20
        start: 起始偏移量，默认0
        expand: 需要展开的字段，逗号分隔
        space_type: 空间类型筛选，可选值: 'global', 'personal', 'template'

    Returns:
        包含空间列表的字典
    """
    logger.info(f"列出空间: limit={limit}, start={start}, type={space_type}")

    params = {
        "limit": limit,
        "start": start,
        "expand": expand,
    }

    if space_type:
        params["type"] = space_type

    try:
        response = ConfluenceConnection.get("/space", params=params)
        return response
    except Exception as e:
        logger.error(f"列出空间失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def get_space(space_key: str, expand: str = "description.plain,homepage") -> dict:
    """
    获取指定空间的详情。

    Args:
        space_key: 空间键（如 TEST）
        expand: 需要展开的字段

    Returns:
        空间详情字典
    """
    logger.info(f"获取空间: space_key={space_key}")

    params = {"expand": expand}

    try:
        response = ConfluenceConnection.get(f"/space/{space_key}", params=params)
        return response
    except Exception as e:
        logger.error(f"获取空间失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def get_space_content(
    space_key: str,
    content_type: str = "page",
    limit: int = 20,
    start: int = 0,
    expand: str = "space,version",
) -> dict:
    """
    获取空间中的内容列表。

    Args:
        space_key: 空间键
        content_type: 内容类型，可选值: 'page', 'blogpost'
        limit: 返回结果数量限制
        start: 起始偏移量
        expand: 需要展开的字段

    Returns:
        内容列表字典
    """
    logger.info(f"获取空间内容: space_key={space_key}, type={content_type}")

    params = {
        "type": content_type,
        "limit": limit,
        "start": start,
        "expand": expand,
    }

    try:
        response = ConfluenceConnection.get(
            f"/space/{space_key}/content", params=params
        )
        return response
    except Exception as e:
        logger.error(f"获取空间内容失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def get_child_pages(
    parent_id: str,
    limit: int = 20,
    start: int = 0,
    expand: str = "space,version",
) -> dict:
    """
    获取父页面的子页面列表。

    Args:
        parent_id: 父页面ID
        limit: 返回结果数量限制
        start: 起始偏移量
        expand: 需要展开的字段

    Returns:
        子页面列表字典
    """
    logger.info(f"获取子页面: parent_id={parent_id}")

    params = {
        "type": "page",
        "limit": limit,
        "start": start,
        "expand": expand,
    }

    try:
        response = ConfluenceConnection.get(
            f"/content/{parent_id}/child/page", params=params
        )
        return response
    except Exception as e:
        logger.error(f"获取子页面失败: {str(e)}")
        return {"error": str(e)}