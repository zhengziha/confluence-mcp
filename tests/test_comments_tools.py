"""评论类 MCP tools 测试。"""
from unittest.mock import patch

from src.tools import comments as comment_tools


class TestGetComments:
    def test_get_comments_adds_markdown(self):
        payload = {
            "size": 1,
            "results": [
                {
                    "id": "c1",
                    "body": {
                        "storage": {
                            "value": "<p>你好 <strong>世界</strong></p>",
                            "representation": "storage",
                        }
                    },
                    "version": {
                        "by": {"displayName": "张三"},
                        "when": "2025-06-15T10:00:00.000Z",
                    },
                    "ancestors": [],
                }
            ],
        }
        with patch.object(
            comment_tools.ConfluenceConnection, "get", return_value=payload
        ):
            result = comment_tools.get_comments("100")

        assert result["size"] == 1
        comment = result["results"][0]
        assert "markdown" in comment["body"]
        assert "世界" in comment["body"]["markdown"]
        assert comment["author_name"] == "张三"
        assert comment["parent_comment_id"] is None

    def test_get_comments_nested_parent(self):
        payload = {
            "size": 1,
            "results": [
                {
                    "id": "c2",
                    "body": {"storage": {"value": "<p>reply</p>"}},
                    "version": {"by": {"username": "u1"}},
                    "ancestors": [{"id": "c1"}],
                }
            ],
        }
        with patch.object(
            comment_tools.ConfluenceConnection, "get", return_value=payload
        ):
            result = comment_tools.get_comments("100")
        assert result["results"][0]["parent_comment_id"] == "c1"


class TestAddComment:
    def test_add_markdown_comment(self):
        with patch.object(
            comment_tools.ConfluenceConnection,
            "post",
            return_value={"id": "c9", "type": "comment"},
        ) as mocked:
            result = comment_tools.add_comment(
                page_id="100",
                content="**重要** 请看",
                content_format="markdown",
            )

        assert result["id"] == "c9"
        data = mocked.call_args.kwargs["data"]
        assert data["type"] == "comment"
        assert data["container"]["id"] == "100"
        assert "重要" in data["body"]["storage"]["value"] or "strong" in data["body"][
            "storage"
        ]["value"]

    def test_add_plain_text_and_reply(self):
        with patch.object(
            comment_tools.ConfluenceConnection,
            "post",
            return_value={"id": "c10"},
        ) as mocked:
            comment_tools.add_comment(
                page_id="100",
                content="ok <tag>",
                content_format="plain_text",
                parent_comment_id="c1",
            )

        data = mocked.call_args.kwargs["data"]
        assert data["ancestors"] == [{"id": "c1"}]
        assert "&lt;tag&gt;" in data["body"]["storage"]["value"]

    def test_add_comment_error(self):
        with patch.object(
            comment_tools.ConfluenceConnection,
            "post",
            side_effect=Exception("fail"),
        ):
            result = comment_tools.add_comment("1", "x")
        assert "error" in result
