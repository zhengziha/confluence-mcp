"""共享测试 fixtures。"""
import pytest

from src.common import config
from src.common.connection import ConfluenceConnection


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """每个测试设置 Confluence 配置，并重置连接单例。"""
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://wiki.test.com/confluence")
    monkeypatch.setenv("CONFLUENCE_USERNAME", "testuser")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "test-token-12345")
    monkeypatch.setenv("CONFLUENCE_CONTEXT_PATH", "/confluence")
    monkeypatch.setenv("CONFLUENCE_API_VERSION", "latest")
    monkeypatch.setenv("CONFLUENCE_TIMEOUT", "30")

    config.CONFLUENCE_CFG.update(
        {
            "base_url": "https://wiki.test.com/confluence",
            "username": "testuser",
            "api_token": "test-token-12345",
            "context_path": "/confluence",
            "api_version": "latest",
            "timeout": 30,
        }
    )

    ConfluenceConnection._session = None
    ConfluenceConnection._is_authenticated = False
    ConfluenceConnection._login_attempts = 0

    yield

    ConfluenceConnection._session = None
    ConfluenceConnection._is_authenticated = False
    ConfluenceConnection._login_attempts = 0


@pytest.fixture
def page_payload():
    """模拟 Confluence 页面 API 响应。"""
    return {
        "id": "100001",
        "type": "page",
        "title": "测试页面",
        "space": {"key": "DEV", "name": "Dev Space"},
        "version": {"number": 1, "message": ""},
        "body": {
            "storage": {
                "value": "<p>Hello</p>",
                "representation": "storage",
            }
        },
        "_links": {"webui": "/pages/viewpage.action?pageId=100001"},
    }
