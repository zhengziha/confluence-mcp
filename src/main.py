import sys
import logging

import click

from src.common.config import (
    set_confluence_config_from_cli,
    validate_confluence_config,
)
from src.common.server import mcp
from src.common.logging_utils import configure_logging
from src.version import __version__


class ConfluenceMCPServer:
    def __init__(self):
        configure_logging()
        self._logger = logging.getLogger(__name__)
        self._logger.info(f"Starting Confluence MCP Server v{__version__}")

    def run(self):
        mcp.run()


@click.command()
@click.option("--url", help="Confluence base URL (e.g., https://your-domain/confluence)")
@click.option("--username", help="Confluence username/email")
@click.option("--api-token", help="Confluence API token or password")
@click.option("--api-version", default="latest", help="API version (default: latest)")
@click.option("--timeout", default=30, type=int, help="Request timeout in seconds")
@click.version_option(__version__, "--version", "-v")
def cli(url, username, api_token, api_version, timeout):
    """Confluence MCP Server - Model Context Protocol server for Confluence."""

    config = {}
    if url:
        config["base_url"] = url
    if username:
        config["username"] = username
    if api_token:
        config["api_token"] = api_token
    if api_version:
        config["api_version"] = api_version
    if timeout:
        config["timeout"] = timeout

    if config:
        set_confluence_config_from_cli(config)

    is_valid, error_msg = validate_confluence_config()
    if not is_valid:
        click.echo(f"配置验证失败: {error_msg}", err=True)
        click.echo("请设置环境变量或通过命令行参数提供配置", err=True)
        sys.exit(1)

    server = ConfluenceMCPServer()
    server.run()


def main():
    cli()


if __name__ == "__main__":
    main()