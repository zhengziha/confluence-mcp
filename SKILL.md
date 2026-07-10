---
name: confluence-knowledge-base
description: "用于读写 Confluence 知识库，支持搜索、读取、创建、更新页面，以及格式转换"
author: "Developer"
version: "0.1.0"
---

# Confluence 知识库操作技能

## 1. 技能概述

本技能提供对 Confluence Server/Data Center 知识库的完整读写能力，支持开发文档、技术文档、PRD 文档的检索和管理。通过 MCP Server 调用 Confluence REST API 实现。

## 2. 触发条件

当用户提出以下类型的请求时，触发本技能：
- "帮我查一下 Confluence 上关于 xxx 的文档"
- "搜索技术文档中关于 xxx 的内容"
- "在 Confluence 创建一个新页面"
- "更新 Confluence 上的 xxx 页面"
- "获取某个页面的内容"
- "列出某个空间的所有页面"

## 3. 可用工具

### 3.1 内容操作工具

| 工具名 | 功能描述 | 主要参数 |
|--------|----------|----------|
| `search_pages` | 使用 CQL 搜索页面 | `cql`: 查询语句 |
| `get_page` | 根据页面ID获取页面详情 | `page_id`: 页面ID |
| `create_page` | 创建新页面 | `title`, `space_key`, `content`, `content_format`, `parent_id` |
| `update_page` | 更新现有页面 | `page_id`, `title`, `content`, `content_format` |
| `delete_page` | 删除页面 | `page_id`: 页面ID |
| `get_page_by_title` | 根据标题搜索页面 | `title`, `space_key` |

### 3.2 空间操作工具

| 工具名 | 功能描述 | 主要参数 |
|--------|----------|----------|
| `list_spaces` | 列出所有空间 | `limit`, `space_type` |
| `get_space` | 获取空间详情 | `space_key`: 空间键 |
| `get_space_content` | 获取空间中的内容列表 | `space_key`, `content_type` |
| `get_child_pages` | 获取父页面的子页面 | `parent_id`: 父页面ID |

## 4. 执行步骤

### 4.1 搜索文档

1. 分析用户查询，提取关键词和目标空间
2. 构建 CQL 查询语句
3. 调用 `search_pages` 获取结果
4. 返回搜索结果列表

### 4.2 读取页面内容

1. 获取页面 ID（通过搜索或用户提供）
2. 调用 `get_page` 获取页面详情
3. 页面内容会自动包含 Markdown 格式版本（在 `body.markdown` 字段）
4. 返回页面内容给用户

### 4.3 创建页面

1. 获取页面标题、目标空间、内容
2. 确定是否需要设置父页面
3. 调用 `create_page`，内容格式默认使用 Markdown
4. 返回创建结果

### 4.4 更新页面

1. 获取页面 ID 和更新内容
2. 调用 `update_page`，可以只更新标题或只更新内容
3. 返回更新结果

### 4.5 浏览空间结构

1. 调用 `list_spaces` 或 `get_space` 获取空间信息
2. 调用 `get_space_content` 获取空间内页面列表
3. 调用 `get_child_pages` 获取页面层级结构
4. 返回结构化的目录信息

## 5. 输入参数说明

### 5.1 content_format 参数

- `markdown`（默认）: 使用 Markdown 格式，会自动转换为 Confluence Storage Format
- `storage`: 使用 Confluence 原生 HTML 格式

### 5.2 CQL 查询示例

```
text ~ "用户登录" AND space = "TECH"
title ~ "API" AND type = "page"
space = "PRD" AND label = "2024"
```

## 6. 输出格式

所有工具返回 JSON 格式结果，包含：
- `results`: 结果列表（搜索类工具）
- `title`: 页面标题
- `body.markdown`: Markdown 格式内容
- `body.storage.value`: 原生 HTML 格式内容
- `space`: 空间信息
- `version`: 版本信息
- `error`: 错误信息（失败时）

## 7. 错误处理

- 网络连接失败：返回清晰的错误信息
- 认证失败：提示用户检查配置
- 权限不足：提示用户当前账号权限不够
- 页面不存在：提示用户确认页面 ID 是否正确

## 8. 配置要求

在使用前需要配置环境变量：

```bash
CONFLUENCE_BASE_URL=https://your-confluence-domain.com/confluence
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token-or-password
```

## 9. 示例

### 示例 1: 搜索文档

**用户**: "帮我找一下关于用户认证的技术文档"

**执行**:
```python
search_pages(cql='text ~ "用户认证" AND space = "TECH"', limit=10)
```

### 示例 2: 读取页面

**用户**: "获取页面 123456 的内容"

**执行**:
```python
get_page(page_id='123456')
```

### 示例 3: 创建页面

**用户**: "在 TECH 空间创建一个新页面，标题为 '新功能设计文档'"

**执行**:
```python
create_page(
    title='新功能设计文档',
    space_key='TECH',
    content='# 新功能设计文档\n\n## 概述\n这是一个新功能的设计文档。',
    content_format='markdown'
)
```

### 示例 4: 更新页面

**用户**: "更新页面 123456 的内容"

**执行**:
```python
update_page(
    page_id='123456',
    content='更新后的内容...',
    content_format='markdown',
    version_comment='更新内容'
)
```