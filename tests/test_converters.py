"""Storage Format ↔ Markdown 转换器测试。"""
from src.tools.converters.markdown_to_storage import MarkdownToStorageConverter
from src.tools.converters.storage_to_markdown import StorageToMarkdownConverter

from tests.sample_data import (
    TECH_DESIGN_STORAGE,
    API_DOC_STORAGE,
    MEETING_NOTES_STORAGE,
    ARCHITECTURE_MARKDOWN,
    SIMPLE_PAGE_MARKDOWN,
    COMPLEX_TABLE_MARKDOWN,
    DRAWIO_STORAGE,
    MULTI_DRAWIO_STORAGE,
    MIXED_DIAGRAM_STORAGE,
    DRAWIO_MARKDOWN,
)


class TestStorageToMarkdown:
    def setup_method(self):
        self.converter = StorageToMarkdownConverter()

    def test_tech_design_headings(self):
        result = self.converter.convert(TECH_DESIGN_STORAGE)
        assert "# 用户信用评分系统设计文档" in result
        assert "## 1. 系统架构" in result

    def test_tech_design_list_and_table(self):
        result = self.converter.convert(TECH_DESIGN_STORAGE)
        assert "评分引擎服务" in result
        assert "Spring Boot" in result
        assert "MySQL" in result

    def test_tech_design_mermaid_and_code(self):
        result = self.converter.convert(TECH_DESIGN_STORAGE)
        assert "```mermaid" in result
        assert "sequenceDiagram" in result
        assert "```java" in result
        assert "CreditScoreService" in result

    def test_tech_design_info_warning(self):
        result = self.converter.convert(TECH_DESIGN_STORAGE)
        assert "技术设计方案" in result
        assert "用户隐私" in result

    def test_api_doc(self):
        result = self.converter.convert(API_DOC_STORAGE)
        assert "/api/v1/users/" in result
        assert "```json" in result
        assert '"creditScore": 750' in result

    def test_meeting_notes(self):
        result = self.converter.convert(MEETING_NOTES_STORAGE)
        assert "2025-06-15" in result
        assert "张三" in result
        assert "7月15日" in result
        assert "数据库查询优化" in result

    def test_metadata_header(self):
        result = self.converter.convert("<p>内容</p>", page_title="测试标题")
        assert "title: 测试标题" in result
        assert self.converter.convert("<p>内容</p>").find("title:") == -1

    def test_empty_and_plain(self):
        assert isinstance(self.converter.convert(""), str)
        assert "这是一段纯文本" in self.converter.convert("<p>这是一段纯文本</p>")

    def test_multiple_code_blocks(self):
        storage = """
<ac:structured-macro ac:name="code">
<ac:parameter ac:name="language">python</ac:parameter>
<ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>
</ac:structured-macro>
<ac:structured-macro ac:name="code">
<ac:parameter ac:name="language">sql</ac:parameter>
<ac:plain-text-body><![CDATA[SELECT * FROM users;]]></ac:plain-text-body>
</ac:structured-macro>
"""
        result = self.converter.convert(storage)
        assert "```python" in result
        assert "```sql" in result


class TestMarkdownToStorage:
    def setup_method(self):
        self.converter = MarkdownToStorageConverter()

    def test_architecture_basics(self):
        result, atts = self.converter.convert(
            ARCHITECTURE_MARKDOWN, mermaid_render_mode="code_block"
        )
        assert "微服务架构设计" in result
        assert "<table" in result
        assert "user-service" in result
        assert 'ac:name="code"' in result
        assert atts == []

    def test_mermaid_macro_mode(self):
        result, atts = self.converter.convert(
            ARCHITECTURE_MARKDOWN, mermaid_render_mode="macro"
        )
        assert 'ac:name="mermaid-macro"' in result
        assert 'ac:name="expand"' not in result
        assert atts == []

    def test_mermaid_code_block_mode(self):
        result, _ = self.converter.convert(
            ARCHITECTURE_MARKDOWN, mermaid_render_mode="code_block"
        )
        assert 'ac:name="expand"' in result or "mermaid.live" in result

    def test_invalid_mermaid_mode_falls_back(self):
        result, _ = self.converter.convert(
            "```mermaid\nA-->B\n```", mermaid_render_mode="image"
        )
        # image 未实现，降级 code_block
        assert "A-->B" in result

    def test_simple_page_and_table(self):
        result, _ = self.converter.convert(SIMPLE_PAGE_MARKDOWN)
        assert "项目说明" in result
        assert "用户注册与登录" in result

        result2, _ = self.converter.convert(COMPLEX_TABLE_MARKDOWN)
        assert "bigint" in result2
        assert "uk_user_id" in result2

    def test_metadata_removed(self):
        md = "---\ntitle: 测试\npage_id: 123\n---\n\n# 正文内容"
        result, _ = self.converter.convert(md)
        assert "title: 测试" not in result
        assert "正文内容" in result

    def test_inline_code_and_links(self):
        result, _ = self.converter.convert(
            "使用 `SELECT * FROM users` 查询\n\n"
            "参考 [Spring Boot](https://spring.io/projects/spring-boot)"
        )
        assert "SELECT * FROM users" in result
        assert "spring.io" in result

    def test_info_warning_blockquote(self):
        info, _ = self.converter.convert("> ℹ️ Info: 这是一条提示信息")
        assert 'ac:name="info"' in info
        warn, _ = self.converter.convert("> ⚠️ Warning: 这是一条警告信息")
        assert 'ac:name="warning"' in warn

    def test_drawio_codeblock_without_upload_degrades(self):
        md = "```drawio\n<mxfile><diagram>x</diagram></mxfile>\n```"
        result, atts = self.converter.convert(md)
        assert atts == []
        assert 'ac:name="code"' in result
        assert "mxfile" in result

    def test_drawio_codeblock_with_upload(self):
        uploaded = []

        def fake_upload(*, page_id, content, file_name, content_type, comment):
            uploaded.append(
                {
                    "page_id": page_id,
                    "file_name": file_name,
                    "content": content,
                    "content_type": content_type,
                }
            )
            return {"id": "att-1", "title": file_name}

        md = "```drawio\n<mxfile><diagram>x</diagram></mxfile>\n```"
        result, atts = self.converter.convert(
            md,
            page_id="42",
            upload_attachment_bytes=fake_upload,
        )
        assert len(atts) == 1
        assert uploaded[0]["page_id"] == "42"
        assert uploaded[0]["file_name"].endswith(".drawio")
        assert 'ac:name="drawio"' in result
        assert "diagramName" in result


class TestDrawioRoundtrip:
    def setup_method(self):
        self.to_md = StorageToMarkdownConverter()
        self.to_storage = MarkdownToStorageConverter()

    def test_drawio_storage_to_markdown(self):
        result = self.to_md.convert(DRAWIO_STORAGE)
        assert "Draw.io" in result
        assert "system-architecture.drawio" in result
        assert "app.diagrams.net" in result

    def test_multi_and_mixed(self):
        multi = self.to_md.convert(MULTI_DRAWIO_STORAGE)
        assert "flow-chart.drawio" in multi
        assert "data-flow.drawio" in multi

        mixed = self.to_md.convert(MIXED_DIAGRAM_STORAGE)
        assert "architecture.drawio" in mixed
        assert "```mermaid" in mixed

    def test_drawio_markdown_to_storage(self):
        result, atts = self.to_storage.convert(DRAWIO_MARKDOWN)
        assert 'ac:name="drawio"' in result
        assert "system-architecture.drawio" in result
        assert "app.diagrams.net" not in result
        assert atts == []
        assert 'ac:schema-version="1"' in result
