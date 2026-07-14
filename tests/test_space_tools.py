"""空间类 MCP tools 测试。"""
from unittest.mock import patch

from src.tools import space as space_tools


class TestSpaceTools:
    def test_list_spaces(self):
        with patch.object(
            space_tools.ConfluenceConnection,
            "get",
            return_value={"results": [{"key": "DEV"}], "size": 1},
        ) as mocked:
            result = space_tools.list_spaces(limit=10)
        assert result["size"] == 1
        assert mocked.call_args.args[0] == "/space"

    def test_get_space(self):
        with patch.object(
            space_tools.ConfluenceConnection,
            "get",
            return_value={"key": "DEV", "name": "Dev"},
        ):
            result = space_tools.get_space("DEV")
        assert result["key"] == "DEV"

    def test_get_space_content(self):
        with patch.object(
            space_tools.ConfluenceConnection,
            "get",
            return_value={"page": {"results": []}},
        ) as mocked:
            space_tools.get_space_content("DEV", content_type="page")
        assert "/space/DEV/content" in mocked.call_args.args[0]

    def test_get_child_pages(self):
        with patch.object(
            space_tools.ConfluenceConnection,
            "get",
            return_value={"results": [{"id": "2"}]},
        ) as mocked:
            result = space_tools.get_child_pages("1")
        assert result["results"][0]["id"] == "2"
        assert mocked.call_args.args[0] == "/content/1/child/page"
