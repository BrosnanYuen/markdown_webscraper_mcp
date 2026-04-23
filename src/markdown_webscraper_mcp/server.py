from __future__ import annotations

from urllib.parse import urlparse

from fastmcp import FastMCP

from .config import MCPServerConfig
from .service import ScrapeJobService


def create_server(config: MCPServerConfig) -> FastMCP:
    mcp = FastMCP(config.mcp_server_name)
    service = ScrapeJobService(config)

    @mcp.tool(name="get_website")
    async def get_website(url: str, dir_path: str) -> dict[str, str]:
        return service.start_job(mode="single", url=url, dir_path=dir_path)

    @mcp.tool(name="get_status_website")
    async def get_status_website(url: str, dir_path: str) -> dict[str, str]:
        return service.get_latest_status(url=url, dir_path=dir_path)

    if config.enable_wildcard_scraping:

        @mcp.tool(name="get_wildcard_website")
        async def get_wildcard_website(url: str, dir_path: str) -> dict[str, str]:
            return service.start_job(mode="wildcard", url=url, dir_path=dir_path)

    return mcp


def run_server(config: MCPServerConfig) -> None:
    mcp = create_server(config)
    parsed = urlparse(config.mcp_server_url)

    if parsed.scheme == "stdio":
        mcp.run(transport="stdio")
        return

    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        port = parsed.port
    else:
        port = 443 if parsed.scheme == "https" else 80

    mcp.run(transport="http", host=host, port=port, path="/")
