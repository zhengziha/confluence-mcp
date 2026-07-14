"""Wiki 场景样本数据

提供真实 wiki 使用场景的 Storage Format 和 Markdown 样本，
供转换器测试和 MCP 工具测试使用。
"""

# ============== Storage Format 样本 ==============

# 技术设计文档
TECH_DESIGN_STORAGE = """
<h1>用户信用评分系统设计文档</h1>
<ac:structured-macro ac:name="info">
<ac:rich-text-body><p>本文档描述用户信用评分系统的技术设计方案</p></ac:rich-text-body>
</ac:structured-macro>
<h2>1. 系统架构</h2>
<p>系统采用微服务架构，主要包含以下模块：</p>
<ul>
<li>评分引擎服务</li>
<li>数据采集服务</li>
<li>规则管理服务</li>
</ul>
<h2>2. 技术选型</h2>
<table>
<thead><tr><th>组件</th><th>技术</th><th>说明</th></tr></thead>
<tbody>
<tr><td>后端框架</td><td>Spring Boot 3.x</td><td>主力开发框架</td></tr>
<tr><td>数据库</td><td>MySQL 8.0</td><td>主数据存储</td></tr>
<tr><td>缓存</td><td>Redis 7.x</td><td>热点数据缓存</td></tr>
<tr><td>消息队列</td><td>Kafka</td><td>异步事件处理</td></tr>
</tbody>
</table>
<h2>3. 核心流程</h2>
<ac:structured-macro ac:name="mermaid">
<ac:plain-text-body><![CDATA[
sequenceDiagram
    participant Client as 客户端
    participant Gateway as API网关
    participant Score as 评分引擎
    participant DB as 数据库
    Client->>Gateway: 请求评分
    Gateway->>Score: 转发请求
    Score->>DB: 查询用户数据
    DB-->>Score: 返回数据
    Score-->>Gateway: 返回评分结果
    Gateway-->>Client: 响应
]]></ac:plain-text-body>
</ac:structured-macro>
<h2>4. 代码示例</h2>
<ac:structured-macro ac:name="code">
<ac:parameter ac:name="language">java</ac:parameter>
<ac:plain-text-body><![CDATA[
@Service
public class CreditScoreService {
    @Autowired
    private UserRepository userRepository;

    public CreditScore calculate(String userId) {
        User user = userRepository.findById(userId);
        return scoreEngine.evaluate(user);
    }
}
]]></ac:plain-text-body>
</ac:structured-macro>
<ac:structured-macro ac:name="warning">
<ac:rich-text-body><p>评分结果涉及用户隐私，需要加密存储</p></ac:rich-text-body>
</ac:structured-macro>
"""

# API 接口文档
API_DOC_STORAGE = """
<h1>用户服务 API 文档</h1>
<h2>1. 获取用户信息</h2>
<p><strong>请求方式：</strong>GET</p>
<p><strong>请求路径：</strong>/api/v1/users/{userId}</p>
<h3>请求参数</h3>
<table>
<thead><tr><th>参数名</th><th>类型</th><th>必填</th><th>说明</th></tr></thead>
<tbody>
<tr><td>userId</td><td>String</td><td>是</td><td>用户ID</td></tr>
</tbody>
</table>
<h3>响应示例</h3>
<ac:structured-macro ac:name="code">
<ac:parameter ac:name="language">json</ac:parameter>
<ac:plain-text-body><![CDATA[
{
  "code": 200,
  "data": {
    "userId": "U12345",
    "name": "张三",
    "creditScore": 750
  }
}
]]></ac:plain-text-body>
</ac:structured-macro>
<h2>2. 更新用户信息</h2>
<p><strong>请求方式：</strong>POST</p>
<p><strong>请求路径：</strong>/api/v1/users/{userId}</p>
<ac:structured-macro ac:name="info">
<ac:rich-text-body><p>更新操作需要管理员权限</p></ac:rich-text-body>
</ac:structured-macro>
"""

# 会议纪要
MEETING_NOTES_STORAGE = """
<h1>2025-06-15 技术评审会议纪要</h1>
<h2>参会人员</h2>
<ul>
<li>张三（技术负责人）</li>
<li>李四（产品经理）</li>
<li>王五（开发工程师）</li>
</ul>
<h2>议题</h2>
<ol>
<li>信用评分系统上线计划</li>
<li>性能优化方案讨论</li>
<li>安全合规检查</li>
</ol>
<h2>决议</h2>
<p>经讨论决定：</p>
<ol>
<li>系统计划 <strong>7月15日</strong> 上线</li>
<li>需要完成以下优化：
<ul>
<li>数据库查询优化</li>
<li>缓存策略调整</li>
<li>接口限流配置</li>
</ul>
</li>
<li>安全审计在上线前完成</li>
</ol>
<ac:structured-macro ac:name="warning">
<ac:rich-text-body><p>上线前必须通过安全审计和压力测试</p></ac:rich-text-body>
</ac:structured-macro>
"""

# ============== Markdown 样本 ==============

# 带 Mermaid 的架构文档
ARCHITECTURE_MARKDOWN = """# 微服务架构设计

## 系统拓扑

```mermaid
graph TB
    LB[负载均衡] --> GW[API Gateway]
    GW --> US[用户服务]
    GW --> CS[信用服务]
    GW --> PS[支付服务]
    US --> DB1[(MySQL)]
    CS --> DB2[(MySQL)]
    CS --> RD[Redis]
    PS --> MQ[Kafka]
```

## 服务列表

| 服务名 | 端口 | 说明 |
|--------|------|------|
| user-service | 8081 | 用户管理 |
| credit-service | 8082 | 信用评分 |
| payment-service | 8083 | 支付处理 |

## 部署流程

```mermaid
flowchart LR
    DEV[开发] --> TEST[测试]
    TEST --> UAT[预发布]
    UAT --> PROD[生产]
```

## 配置示例

```yaml
spring:
  application:
    name: credit-service
  datasource:
    url: jdbc:mysql://localhost:3306/credit
```
"""

# 简单文本页面
SIMPLE_PAGE_MARKDOWN = """# 项目说明

这是一个简单的项目说明页面。

## 功能列表

- 用户注册与登录
- 信用评分查询
- 还款计划管理

## 联系方式

如有问题请联系技术支持团队。
"""

# 复杂表格页面
COMPLEX_TABLE_MARKDOWN = """# 数据库表结构设计

## user_info 表

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | bigint(20) | 是 | AUTO_INCREMENT | 主键 |
| user_id | varchar(64) | 是 | - | 用户ID |
| name | varchar(100) | 是 | - | 用户姓名 |
| credit_score | int(11) | 否 | 0 | 信用评分 |
| status | tinyint(4) | 是 | 1 | 状态：1-正常 2-冻结 |
| created_at | timestamp | 是 | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | timestamp | 是 | CURRENT_TIMESTAMP | 更新时间 |

## 索引设计

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| uk_user_id | user_id | UNIQUE | 用户ID唯一索引 |
| idx_status | status | NORMAL | 状态查询索引 |
| idx_created_at | created_at | NORMAL | 创建时间索引 |
"""

# ============== Draw.io 样本 ==============

# 包含 draw.io 图表的技术文档
DRAWIO_STORAGE = """
<h1>系统架构图</h1>
<p>以下是系统的整体架构：</p>
<ac:structured-macro ac:name="drawio" ac:schema-version="1" ac:macro-id="abc123">
<ac:parameter ac:name="diagramName">system-architecture.drawio</ac:parameter>
<ac:parameter ac:name="attachment">system-architecture.drawio</ac:parameter>
<ac:parameter ac:name="pageSize">false</ac:parameter>
</ac:structured-macro>
<h2>模块说明</h2>
<p>系统包含以下核心模块：</p>
<ul>
<li>用户服务</li>
<li>订单服务</li>
</ul>
"""

# 包含多个 draw.io 图表的文档
MULTI_DRAWIO_STORAGE = """
<h1>流程设计</h1>
<ac:structured-macro ac:name="drawio" ac:schema-version="1">
<ac:parameter ac:name="diagramName">flow-chart.drawio</ac:parameter>
<ac:parameter ac:name="attachment">flow-chart.drawio</ac:parameter>
</ac:structured-macro>
<p>上图为业务流程，下图为数据流：</p>
<ac:structured-macro ac:name="drawio" ac:schema-version="1">
<ac:parameter ac:name="diagramName">data-flow.drawio</ac:parameter>
<ac:parameter ac:name="attachment">data-flow.drawio</ac:parameter>
</ac:structured-macro>
"""

# 同时包含 draw.io 和 Mermaid 的文档
MIXED_DIAGRAM_STORAGE = """
<h1>架构文档</h1>
<ac:structured-macro ac:name="drawio" ac:schema-version="1">
<ac:parameter ac:name="diagramName">architecture.drawio</ac:parameter>
<ac:parameter ac:name="attachment">architecture.drawio</ac:parameter>
</ac:structured-macro>
<h2>时序图</h2>
<ac:structured-macro ac:name="mermaid">
<ac:plain-text-body><![CDATA[
sequenceDiagram
    A->>B: 请求
    B-->>A: 响应
]]></ac:plain-text-body>
</ac:structured-macro>
"""

# 带 draw.io 标记的 Markdown
DRAWIO_MARKDOWN = """# 系统架构图

以下是系统的整体架构：

> \U0001f4ca **Draw.io 图表**: system-architecture.drawio
> [draw.io 在线编辑器](https://app.diagrams.net/)

## 模块说明

系统包含以下核心模块：

- 用户服务
- 订单服务
"""
