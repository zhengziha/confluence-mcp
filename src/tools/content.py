import logging
from typing import Optional

from src.common.connection import ConfluenceConnection
from src.tools.converters.drawio_handler import DrawioHandler
from src.tools.converters.mermaid_handler import MermaidHandler
from src.tools.format_converter import (
    confluence_to_markdown,
    markdown_to_confluence,
    markdown_to_confluence_with_attachments,
)
from src.common.server import mcp

logger = logging.getLogger("confluence-mcp-server")


@mcp.tool()
def search_pages(
    cql: str,
    limit: int = 20,
    start: int = 0,
    expand: str = "space,version",
) -> dict:
    """
    使用 CQL (Confluence Query Language) 搜索页面。

    Args:
        cql: CQL 查询语句，例如 'text ~ "关键词" AND space = "TEST"'
        limit: 返回结果数量限制，默认20
        start: 起始偏移量，默认0
        expand: 需要展开的字段，逗号分隔，可选值: space, version, body.view, body.storage, ancestors

    Returns:
        包含搜索结果的字典，包含 results 列表和分页信息
    """
    logger.info(f"搜索页面: cql={cql}, limit={limit}, start={start}")

    params = {
        "cql": cql,
        "limit": limit,
        "start": start,
        "expand": expand,
    }

    try:
        response = ConfluenceConnection.get("/content/search", params=params)
        return response
    except Exception as e:
        logger.error(f"搜索页面失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def get_page(
    page_id: str,
    expand: str = "body.storage,space,version,ancestors",
) -> dict:
    """
    根据页面ID获取页面详情。

    Args:
        page_id: Confluence页面ID
        expand: 需要展开的字段，逗号分隔

    Returns:
        页面详情字典，包含标题、内容、空间信息等
    """
    logger.info(f"获取页面: page_id={page_id}")

    params = {"expand": expand}

    try:
        response = ConfluenceConnection.get(f"/content/{page_id}", params=params)

        if "body" in response and "storage" in response["body"]:
            storage_value = response["body"]["storage"].get("value", "")
            response["body"]["markdown"] = confluence_to_markdown(storage_value)

        return response
    except Exception as e:
        logger.error(f"获取页面失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def create_page(
    title: str,
    space_key: str,
    content: str,
    content_format: str = "markdown",
    parent_id: Optional[str] = None,
    mermaid_render_mode: str = "macro",
) -> dict:
    """
    创建新页面。

    Args:
        title: 页面标题
        space_key: 空间键（如 TEST）
        content: 页面内容
        content_format: 内容格式，可选值: 'markdown' 或 'storage'
        parent_id: 父页面ID（可选）
        mermaid_render_mode: Mermaid 渲染模式，'macro'（需插件）或 'code_block'

    Returns:
        创建的页面详情字典
    """
    logger.info(f"创建页面: title={title}, space_key={space_key}")

    if content_format != "markdown":
        storage_value = content
        has_drawio = False
        mermaid_count = 0
    else:
        mermaid_count = len(MermaidHandler.extract_mermaid_blocks(content))
        has_drawio = len(DrawioHandler.extract_drawio_codeblocks(content)) > 0
        # 创建页时若需上传 draw.io，先用降级模式建占位页再二次更新
        first_mode = mermaid_render_mode
        storage_value = markdown_to_confluence(
            content, mermaid_render_mode=first_mode
        )

    data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": storage_value,
                "representation": "storage",
            }
        },
    }

    if parent_id:
        data["ancestors"] = [{"id": parent_id}]

    try:
        response = ConfluenceConnection.post("/content", data=data)
        page_id = response.get("id")

        if content_format == "markdown" and has_drawio and page_id:
            storage_with_attachments, attachments = markdown_to_confluence_with_attachments(
                content,
                mermaid_render_mode=mermaid_render_mode,
                page_id=page_id,
                upload_attachment_bytes=ConfluenceConnection.upload_attachment_bytes,
            )
            if attachments:
                current_version = response.get("version", {}).get("number", 1)
                update_data = {
                    "id": page_id,
                    "type": "page",
                    "title": title,
                    "body": {
                        "storage": {
                            "value": storage_with_attachments,
                            "representation": "storage",
                        }
                    },
                    "version": {
                        "number": current_version + 1,
                        "message": "Upload draw.io attachments",
                    },
                }
                response = ConfluenceConnection.put(f"/content/{page_id}", data=update_data)
                response["attachments_uploaded"] = len(attachments)

        if content_format == "markdown":
            response["mermaid_render_mode"] = mermaid_render_mode
            response["mermaid_diagrams_count"] = mermaid_count
            response["drawio_diagrams_count"] = (
                len(DrawioHandler.extract_drawio_codeblocks(content)) if has_drawio else 0
            )

        return response
    except Exception as e:
        logger.error(f"创建页面失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def update_page(
    page_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    content_format: str = "markdown",
    version_comment: str = "Updated via MCP",
    mermaid_render_mode: str = "macro",
) -> dict:
    """
    更新现有页面。

    Args:
        page_id: 要更新的页面ID
        title: 新的页面标题（可选）
        content: 新的页面内容（可选）
        content_format: 内容格式，可选值: 'markdown' 或 'storage'
        version_comment: 更新版本注释
        mermaid_render_mode: Mermaid 渲染模式，'macro'（需插件）或 'code_block'

    Returns:
        更新后的页面详情字典
    """
    logger.info(f"更新页面: page_id={page_id}")

    try:
        current_page = ConfluenceConnection.get(
            f"/content/{page_id}", params={"expand": "version"}
        )
    except Exception as e:
        logger.error(f"获取当前页面失败: {str(e)}")
        return {"error": str(e)}

    data = {"id": page_id, "type": "page"}

    if title:
        data["title"] = title
    else:
        data["title"] = current_page.get("title", "")

    if content:
        if content_format == "markdown":
            storage_value, attachments = markdown_to_confluence_with_attachments(
                content,
                mermaid_render_mode=mermaid_render_mode,
                page_id=page_id,
                upload_attachment_bytes=ConfluenceConnection.upload_attachment_bytes,
            )
            data["_attachments_uploaded"] = len(attachments)
            data["_mermaid_count"] = len(MermaidHandler.extract_mermaid_blocks(content))
            data["_drawio_count"] = len(DrawioHandler.extract_drawio_codeblocks(content))
        else:
            storage_value = content

        data["body"] = {
            "storage": {
                "value": storage_value,
                "representation": "storage",
            }
        }

    attachments_uploaded = data.pop("_attachments_uploaded", 0)
    mermaid_count = data.pop("_mermaid_count", 0)
    drawio_count = data.pop("_drawio_count", 0)

    current_version = current_page.get("version", {}).get("number", 1)
    data["version"] = {"number": current_version + 1, "message": version_comment}

    try:
        response = ConfluenceConnection.put(f"/content/{page_id}", data=data)
        if content and content_format == "markdown":
            response["mermaid_render_mode"] = mermaid_render_mode
            response["mermaid_diagrams_count"] = mermaid_count
            response["drawio_diagrams_count"] = drawio_count
            response["attachments_uploaded"] = attachments_uploaded
        return response
    except Exception as e:
        logger.error(f"更新页面失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def delete_page(page_id: str) -> dict:
    """
    删除页面。

    Args:
        page_id: 要删除的页面ID

    Returns:
        删除结果字典，成功时包含 success: True
    """
    logger.info(f"删除页面: page_id={page_id}")

    try:
        ConfluenceConnection.delete(f"/content/{page_id}")
        return {"success": True, "page_id": page_id}
    except Exception as e:
        logger.error(f"删除页面失败: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def get_page_by_title(
    title: str,
    space_key: str,
    expand: str = "body.storage,space,version",
) -> dict:
    """
    根据标题和空间搜索页面。

    Args:
        title: 页面标题（精确匹配）
        space_key: 空间键
        expand: 需要展开的字段

    Returns:
        页面详情字典，如果找到多个结果则返回列表
    """
    logger.info(f"按标题搜索页面: title={title}, space_key={space_key}")

    cql = f'title = "{title}" AND space = "{space_key}"'
    return search_pages(cql=cql, limit=5, expand=expand)


@mcp.tool()
def upload_drawio(
    page_id: str,
    drawio_xml: str,
    file_name: Optional[str] = None,
    insert_macro: bool = True,
) -> dict:
    """
    上传 Draw.io XML 为页面附件，可选在页面末尾插入 draw.io 宏。

    Args:
        page_id: 目标页面 ID
        drawio_xml: Draw.io XML（mxfile 或 mxGraphModel）
        file_name: 附件文件名（默认自动生成，需以 .drawio 结尾）
        insert_macro: 是否把 draw.io 宏追加到页面正文末尾

    Returns:
        上传结果，含附件信息及是否已插入宏
    """
    logger.info(f"上传 draw.io: page_id={page_id}")

    xml = (drawio_xml or "").strip()
    if not xml:
        return {"error": "drawio_xml 不能为空"}
    if not (xml.startswith("<mxfile") or xml.startswith("<mxGraphModel")):
        return {"error": "drawio_xml 格式无效：应以 <mxfile 或 <mxGraphModel 开头"}

    name = file_name or DrawioHandler.generate_attachment_filename(0)
    if not name.endswith(".drawio"):
        return {"error": "file_name 必须以 .drawio 结尾"}

    try:
        attachment = ConfluenceConnection.upload_attachment_bytes(
            page_id=page_id,
            content=xml.encode("utf-8"),
            file_name=name,
            content_type="application/vnd.jgraph.mxfile",
            comment="Draw.io diagram uploaded via MCP",
        )

        result = {
            "success": True,
            "page_id": page_id,
            "file_name": name,
            "attachment_id": attachment.get("id"),
            "macro_inserted": False,
        }

        if insert_macro:
            page = ConfluenceConnection.get(
                f"/content/{page_id}",
                params={"expand": "body.storage,version"},
            )
            current_body = page.get("body", {}).get("storage", {}).get("value", "")
            macro = DrawioHandler.markdown_to_drawio_macro(name)
            if macro not in current_body:
                new_body = current_body + "\n" + macro
                ConfluenceConnection.put(
                    f"/content/{page_id}",
                    data={
                        "id": page_id,
                        "type": "page",
                        "title": page.get("title", ""),
                        "body": {
                            "storage": {
                                "value": new_body,
                                "representation": "storage",
                            }
                        },
                        "version": {
                            "number": page.get("version", {}).get("number", 1) + 1,
                            "message": f"Insert draw.io macro: {name}",
                        },
                    },
                )
                result["macro_inserted"] = True

        return result
    except Exception as e:
        logger.error(f"上传 draw.io 失败: {str(e)}")
        return {"error": str(e)}
