"""内容类 MCP tools 测试（mock ConfluenceConnection）。"""
from unittest.mock import patch

from src.tools import content as content_tools


class TestGetAndSearch:
    def test_get_page_adds_markdown(self, page_payload):
        page_payload["body"]["storage"]["value"] = (
            '<ac:structured-macro ac:name="code">'
            '<ac:parameter ac:name="language">python</ac:parameter>'
            "<ac:plain-text-body><![CDATA[print(1)]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )
        with patch.object(
            content_tools.ConfluenceConnection, "get", return_value=page_payload
        ):
            result = content_tools.get_page("100001")

        assert "error" not in result
        assert "markdown" in result["body"]
        assert "print(1)" in result["body"]["markdown"]

    def test_get_page_error(self):
        with patch.object(
            content_tools.ConfluenceConnection,
            "get",
            side_effect=Exception("boom"),
        ):
            result = content_tools.get_page("1")
        assert "error" in result

    def test_search_pages(self):
        with patch.object(
            content_tools.ConfluenceConnection,
            "get",
            return_value={"results": [], "size": 0},
        ) as mocked:
            result = content_tools.search_pages(cql='type=page', limit=5)
        assert result["size"] == 0
        assert mocked.call_args.args[0] == "/content/search"


class TestCreateUpdatePage:
    def test_create_page_markdown_simple(self, page_payload):
        with patch.object(
            content_tools.ConfluenceConnection, "post", return_value=page_payload
        ) as mocked:
            result = content_tools.create_page(
                title="测试页面",
                space_key="DEV",
                content="# Hi\n\nhello",
                mermaid_render_mode="macro",
            )

        assert result["id"] == "100001"
        assert result["mermaid_diagrams_count"] == 0
        body = mocked.call_args.kwargs["data"]["body"]["storage"]["value"]
        assert "Hi" in body or "hello" in body

    def test_create_page_with_drawio_two_step(self, page_payload):
        created = dict(page_payload)
        updated = dict(page_payload)
        updated["version"] = {"number": 2}

        md = "# D\n\n```drawio\n<mxfile><diagram>x</diagram></mxfile>\n```"

        with patch.object(
            content_tools.ConfluenceConnection, "post", return_value=created
        ), patch.object(
            content_tools.ConfluenceConnection,
            "upload_attachment_bytes",
            return_value={"id": "att-1", "title": "drawio_diagram_0.drawio"},
        ) as upload, patch.object(
            content_tools.ConfluenceConnection, "put", return_value=updated
        ) as put:
            result = content_tools.create_page(
                title="D",
                space_key="DEV",
                content=md,
            )

        assert upload.called
        assert put.called
        assert result.get("attachments_uploaded") == 1
        assert result.get("drawio_diagrams_count") == 1

    def test_update_page_markdown(self, page_payload):
        updated = dict(page_payload)
        updated["version"] = {"number": 2}
        with patch.object(
            content_tools.ConfluenceConnection, "get", return_value=page_payload
        ), patch.object(
            content_tools.ConfluenceConnection, "put", return_value=updated
        ) as put:
            result = content_tools.update_page(
                page_id="100001",
                content="# New\n\n```mermaid\nA-->B\n```",
                mermaid_render_mode="macro",
            )

        assert result["version"]["number"] == 2
        assert result["mermaid_diagrams_count"] == 1
        assert result["mermaid_render_mode"] == "macro"
        storage = put.call_args.kwargs["data"]["body"]["storage"]["value"]
        assert "mermaid-macro" in storage

    def test_delete_page(self):
        with patch.object(content_tools.ConfluenceConnection, "delete") as mocked:
            result = content_tools.delete_page("9")
        assert result == {"success": True, "page_id": "9"}
        mocked.assert_called_once_with("/content/9")


class TestUploadDrawio:
    def test_upload_drawio_validation(self):
        assert "error" in content_tools.upload_drawio("1", "")
        assert "error" in content_tools.upload_drawio("1", "not-xml")
        assert "error" in content_tools.upload_drawio(
            "1", "<mxfile/>", file_name="bad.txt"
        )

    def test_upload_drawio_insert_macro(self, page_payload):
        page_payload["body"]["storage"]["value"] = "<p>old</p>"
        with patch.object(
            content_tools.ConfluenceConnection,
            "upload_attachment_bytes",
            return_value={"id": "a1"},
        ), patch.object(
            content_tools.ConfluenceConnection, "get", return_value=page_payload
        ), patch.object(
            content_tools.ConfluenceConnection, "put", return_value=page_payload
        ) as put:
            result = content_tools.upload_drawio(
                page_id="100001",
                drawio_xml="<mxfile><diagram/></mxfile>",
                file_name="arch.drawio",
                insert_macro=True,
            )

        assert result["success"] is True
        assert result["macro_inserted"] is True
        new_body = put.call_args.kwargs["data"]["body"]["storage"]["value"]
        assert 'ac:name="drawio"' in new_body
        assert "arch.drawio" in new_body
