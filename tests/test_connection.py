"""ConfluenceConnection 单元测试（mock HTTP）。"""
from unittest.mock import MagicMock, patch

import pytest

from src.common.connection import ConfluenceConnection


class TestUploadAttachmentBytes:
    def test_upload_new_attachment(self):
        mock_session = MagicMock()
        # 检查同名：无结果
        with patch.object(ConfluenceConnection, "get_session", return_value=mock_session), patch.object(
            ConfluenceConnection, "get", return_value={"size": 0, "results": []}
        ):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "results": [{"id": "att-1", "title": "a.drawio"}]
            }
            mock_session.post.return_value = mock_resp
            mock_session.headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            result = ConfluenceConnection.upload_attachment_bytes(
                page_id="100",
                content=b"<mxfile/>",
                file_name="a.drawio",
                content_type="application/vnd.jgraph.mxfile",
                comment="test",
            )

        assert result["id"] == "att-1"
        assert mock_session.post.called
        kwargs = mock_session.post.call_args.kwargs
        assert "files" in kwargs
        assert kwargs["headers"]["X-Atlassian-Token"] == "nocheck"
        assert "Content-Type" not in {
            k for k in kwargs["headers"] if k.lower() == "content-type"
        } or kwargs["headers"].get("Content-Type") != "application/json"

    def test_upload_updates_existing(self):
        mock_session = MagicMock()
        with patch.object(ConfluenceConnection, "get_session", return_value=mock_session), patch.object(
            ConfluenceConnection,
            "get",
            return_value={"size": 1, "results": [{"id": "old-9"}]},
        ):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "old-9", "title": "a.drawio"}
            mock_session.post.return_value = mock_resp
            mock_session.headers = {"Content-Type": "application/json"}

            ConfluenceConnection.upload_attachment_bytes(
                page_id="100",
                content=b"data",
                file_name="a.drawio",
            )

        url = mock_session.post.call_args.args[0]
        assert "/attachment/old-9/data" in url

    def test_upload_from_file(self, tmp_path):
        f = tmp_path / "diag.drawio"
        f.write_bytes(b"<mxfile/>")

        with patch.object(
            ConfluenceConnection,
            "upload_attachment_bytes",
            return_value={"id": "1"},
        ) as mocked:
            result = ConfluenceConnection.upload_attachment(
                page_id="1", file_path=str(f)
            )
            assert result["id"] == "1"
            mocked.assert_called_once()
            assert mocked.call_args.kwargs["file_name"] == "diag.drawio"

    def test_upload_missing_file(self):
        with pytest.raises(FileNotFoundError):
            ConfluenceConnection.upload_attachment(
                page_id="1", file_path="/no/such/file.drawio"
            )


class TestApiBaseHelpers:
    def test_get_api_base_url(self):
        from src.common.config import get_api_base_url

        assert get_api_base_url().endswith("/rest/api/latest")

    def test_validate_config(self):
        from src.common.config import validate_confluence_config

        ok, msg = validate_confluence_config()
        assert ok is True
        assert msg == ""
