# Confluence MCP Server

一个用于 Confluence Server/Data Center 的 Model Context Protocol (MCP) Server，提供完整的知识库读写能力。

## 功能特性

- **搜索页面**: 使用 CQL 查询语言搜索 Confluence 页面
- **读取页面**: 获取页面详情，自动转换为 Markdown 格式
- **创建页面**: 支持 Markdown 和原生格式创建新页面
- **更新页面**: 更新现有页面的标题和内容
- **删除页面**: 删除指定页面
- **空间管理**: 列出空间、获取空间内容、获取子页面结构
- **格式转换**: 支持 Confluence Storage Format 与 Markdown 互转

## 安装

```bash
pip install -e .
```

## 配置

创建 `.env` 文件或设置环境变量：

```bash
CONFLUENCE_BASE_URL=https://your-confluence-domain.com/confluence
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token-or-password
CONFLUENCE_API_VERSION=latest
CONFLUENCE_TIMEOUT=30
```

## 使用

### 启动 MCP Server

```bash
confluence-mcp-server --url https://your-confluence/confluence --username user@example.com --api-token your-token
```

或使用环境变量：

```bash
source .env
confluence-mcp-server
```

### 命令行参数

```bash
confluence-mcp-server --help

Options:
  --url TEXT           Confluence base URL
  --username TEXT      Confluence username/email
  --api-token TEXT     Confluence API token or password
  --api-version TEXT   API version (default: latest)
  --timeout INTEGER    Request timeout in seconds
  -v, --version        Show the version and exit.
  --help               Show this message and exit.
```

## 支持的工具

### 内容操作

- `search_pages`: 使用 CQL 搜索页面
- `get_page`: 根据页面ID获取页面详情
- `create_page`: 创建新页面
- `update_page`: 更新现有页面
- `delete_page`: 删除页面
- `get_page_by_title`: 根据标题搜索页面

### 空间操作

- `list_spaces`: 列出所有空间
- `get_space`: 获取空间详情
- `get_space_content`: 获取空间中的内容列表
- `get_child_pages`: 获取父页面的子页面

## CQL 查询示例

```
text ~ "用户登录" AND space = "TECH"
title ~ "API" AND type = "page"
space = "PRD" AND label = "2024"
```

## 多 Agent 使用教程

### 在 TRAE 中使用

#### 方式一：通过项目技能导入（推荐）

1. 打开 TRAE IDE
2. 在项目面板中添加 `confluence-skill` 项目目录
3. TRAE 会自动识别 `SKILL.md` 和 `mcp.json` 配置
4. 在对话中直接使用自然语言触发技能

#### 方式二：手动配置 MCP Server

1. 在终端启动 MCP Server：
```bash
cd /path/to/confluence-skill
source .venv/bin/activate
confluence-mcp-server
```

2. 在 TRAE 的设置中添加 MCP Server：
   - 名称: `confluence-mcp-server`
   - URL: `http://localhost:8000`

### 在 Cursor 中使用

1. 确保项目目录中有 `.cursor/mcp.json` 配置文件
2. Cursor 会自动读取配置并启动 MCP Server
3. 在对话中使用 `@confluence-mcp-server` 触发技能

`.cursor/mcp.json` 配置示例：
```json
{
  "name": "confluence-mcp-server",
  "command": "python",
  "args": ["-m", "src.main"],
  "env": {
    "CONFLUENCE_BASE_URL": "${CONFLUENCE_BASE_URL}",
    "CONFLUENCE_USERNAME": "${CONFLUENCE_USERNAME}",
    "CONFLUENCE_API_TOKEN": "${CONFLUENCE_API_TOKEN}"
  },
  "description": "Confluence MCP Server for reading and writing Confluence pages"
}
```

### 使用 MCP Python SDK

```python
from mcp.stdio_client import StdioClient

async def main():
    async with StdioClient(command="python", args=["-m", "src.main"]) as client:
        # 搜索页面
        results = await client.call_tool("search_pages", {"cql": "text ~ 'Java'", "limit": 5})
        print(results)
        
        # 获取页面内容
        page = await client.call_tool("get_page", {"page_id": "63777422"})
        print(page.get("title"))
        print(page.get("body", {}).get("markdown"))
        
        # 创建页面
        new_page = await client.call_tool(
            "create_page",
            {
                "title": "新文档标题",
                "space_key": "TECH",
                "content": "# 新文档\n\n内容描述",
                "content_format": "markdown"
            }
        )
        print(new_page)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 使用 HTTP API

MCP Server 默认在 `http://localhost:8000` 提供 HTTP 接口。

#### 列出所有工具
```bash
curl http://localhost:8000/mcp/list_tools
```

#### 调用工具（POST）
```bash
curl -X POST http://localhost:8000/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_pages",
    "arguments": {
      "cql": "text ~ \"Java\"",
      "limit": 5
    }
  }'
```

### 在自定义 Agent 中集成

```python
import requests

class ConfluenceSkillClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def search_pages(self, cql, limit=20):
        return self._call_tool("search_pages", {"cql": cql, "limit": limit})
    
    def get_page(self, page_id):
        return self._call_tool("get_page", {"page_id": page_id})
    
    def create_page(self, title, space_key, content, content_format="markdown"):
        return self._call_tool(
            "create_page",
            {"title": title, "space_key": space_key, "content": content, "content_format": content_format}
        )
    
    def _call_tool(self, tool_name, arguments):
        response = requests.post(
            f"{self.base_url}/mcp/call_tool",
            json={"name": tool_name, "arguments": arguments}
        )
        return response.json()

client = ConfluenceSkillClient()
results = client.search_pages("text ~ '技术文档'")
print(results)
```

### 环境变量配置方式

#### 方式一：使用 .env 文件
```bash
cp .env.example .env
# 编辑 .env 文件配置
source .env
confluence-mcp-server
```

#### 方式二：命令行参数
```bash
confluence-mcp-server \
  --url https://docs.jk.com \
  --username zhengzih \
  --api-token your-password
```

#### 方式三：系统环境变量
```bash
export CONFLUENCE_BASE_URL=https://docs.jk.com
export CONFLUENCE_USERNAME=zhengzih
export CONFLUENCE_API_TOKEN=your-password
confluence-mcp-server
```

## 技术栈

- Python 3.10+
- MCP SDK (`mcp[cli]`)
- Requests
- BeautifulSoup4
- Markdown
- Click

## 许可证

MIT License