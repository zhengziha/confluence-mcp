"""format_converter 公开入口测试。"""
from src.tools.format_converter import (
    confluence_to_markdown,
    markdown_to_confluence,
    markdown_to_confluence_with_attachments,
)


class TestFormatConverterAPI:
    def test_empty_inputs(self):
        assert confluence_to_markdown("") == ""
        assert markdown_to_confluence("") == "<p></p>"
        storage, atts = markdown_to_confluence_with_attachments("")
        assert storage == "<p></p>"
        assert atts == []

    def test_markdown_to_confluence_mermaid_modes(self):
        md = "# T\n\n```mermaid\nA-->B\n```\n"
        macro = markdown_to_confluence(md, mermaid_render_mode="macro")
        assert "mermaid-macro" in macro

        code = markdown_to_confluence(md, mermaid_render_mode="code_block")
        assert "A-->B" in code

    def test_roundtrip_headings_and_code(self):
        md = "# 标题\n\n段落文字\n\n```python\nprint(1)\n```\n"
        storage = markdown_to_confluence(md)
        back = confluence_to_markdown(storage)
        assert "标题" in back
        assert "print(1)" in back

    def test_with_attachments_upload(self):
        calls = []

        def upload(**kwargs):
            calls.append(kwargs)
            return {"id": "1", "title": kwargs["file_name"]}

        md = "```drawio\n<mxGraphModel/>\n```"
        storage, atts = markdown_to_confluence_with_attachments(
            md,
            page_id="9",
            upload_attachment_bytes=upload,
        )
        assert len(atts) == 1
        assert len(calls) == 1
        assert 'ac:name="drawio"' in storage
