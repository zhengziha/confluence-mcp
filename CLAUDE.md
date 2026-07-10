---
skills:
  - name: confluence-skill
    type: mcp
    server:
      command: python
      args: ["-m", "src.main"]
      env:
        CONFLUENCE_BASE_URL: "${CONFLUENCE_BASE_URL}"
        CONFLUENCE_USERNAME: "${CONFLUENCE_USERNAME}"
        CONFLUENCE_API_TOKEN: "${CONFLUENCE_API_TOKEN}"
        CONFLUENCE_CONTEXT_PATH: "${CONFLUENCE_CONTEXT_PATH}"
        CONFLUENCE_API_VERSION: "${CONFLUENCE_API_VERSION}"
---

# Confluence 知识库操作技能

## 技能概述

本技能提供对 Confluence Server/Data Center 知识库的完整读写能力，支持开发文档、技术文档、PRD 文档的检索和管理。

## 触发条件

当用户提出以下类型的请求时，触发本技能：
- "帮我查一下 Confluence 上关于 xxx 的文档"
- "搜索技术文档中关于 xxx 的内容"
- "在 Confluence 创建一个新页面"
- "更新 Confluence 上的 xxx 页面"
- "获取某个页面的内容"
- "列出某个空间的所有页面"

## 可用工具

### 内容操作工具
- `search_pages(cql, limit)` - 使用 CQL 搜索页面
- `get_page(page_id)` - 根据页面ID获取页面详情
- `create_page(title, space_key, content, content_format='markdown', parent_id)` - 创建新页面
- `update_page(page_id, title, content, content_format='markdown')` - 更新现有页面
- `delete_page(page_id)` - 删除页面
- `get_page_by_title(title, space_key)` - 根据标题搜索页面

### 空间操作工具
- `list_spaces(limit, space_type)` - 列出所有空间
- `get_space(space_key)` - 获取空间详情
- `get_space_content(space_key, content_type)` - 获取空间中的内容列表
- `get_child_pages(parent_id)` - 获取父页面的子页面

## 使用指南

### 搜索文档
1. 分析用户查询，提取关键词和目标空间
2. 构建 CQL 查询语句
3. 调用 `search_pages` 获取结果
4. 返回搜索结果列表

### 读取页面内容
1. 获取页面 ID（通过搜索或用户提供）
2. 调用 `get_page` 获取页面详情
3. 页面内容会自动包含 Markdown 格式版本（在 `body.markdown` 字段）

### 创建页面
1. 获取页面标题、目标空间、内容
2. 确定是否需要设置父页面
3. 调用 `create_page`，内容格式默认使用 Markdown

## CQL 查询示例

```
text ~ "用户登录" AND space = "TECH"
title ~ "API" AND type = "page"
space = "PRD" AND label = "2024"
```

## 配置要求

在使用前需要配置环境变量：

```bash
CONFLUENCE_BASE_URL=https://your-confluence-domain.com
CONFLUENCE_USERNAME=your-username
CONFLUENCE_API_TOKEN=your-password-or-api-token
CONFLUENCE_CONTEXT_PATH=/confluence
CONFLUENCE_API_VERSION=latest
```