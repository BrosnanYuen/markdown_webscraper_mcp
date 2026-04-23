from __future__ import annotations

import pytest

from markdown_webscraper_mcp.config import MCPServerConfig
from markdown_webscraper_mcp.server import create_server


def _cfg(enable_wildcard_scraping: bool) -> MCPServerConfig:
    return MCPServerConfig(
        mcp_server_name="Test Server",
        mcp_server_url="stdio://",
        enable_wildcard_scraping=enable_wildcard_scraping,
        remove_header_footer=True,
        markdown_convert=True,
        time_delay=0,
        total_timeout=5,
    )


@pytest.mark.asyncio
async def test_create_server_registers_required_tools() -> None:
    mcp = create_server(_cfg(enable_wildcard_scraping=False))
    names = {tool.name for tool in await mcp.list_tools()}

    assert "get_website" in names
    assert "get_status_website" in names
    assert "get_wildcard_website" not in names


@pytest.mark.asyncio
async def test_create_server_registers_wildcard_tool_when_enabled() -> None:
    mcp = create_server(_cfg(enable_wildcard_scraping=True))
    names = {tool.name for tool in await mcp.list_tools()}

    assert "get_wildcard_website" in names
