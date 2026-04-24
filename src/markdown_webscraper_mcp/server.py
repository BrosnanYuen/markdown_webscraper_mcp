from __future__ import annotations

import json
from urllib.parse import urlparse

from fastmcp import Context, FastMCP
from mcp import types as mcp_types

from .config import MCPServerConfig
from .service import FAILED_STATUS, ScrapeJobService, TIMED_OUT_STATUS


def create_server(config: MCPServerConfig) -> FastMCP:
    mcp = FastMCP(config.mcp_server_name)
    service = ScrapeJobService(config)

    async def _notify_client(ctx: Context, payload: dict[str, str]) -> None:
        level: str = "info"
        if payload.get("status") in {FAILED_STATUS, TIMED_OUT_STATUS}:
            level = "error"

        await ctx.send_notification(
            mcp_types.LoggingMessageNotification(
                params=mcp_types.LoggingMessageNotificationParams(
                    level=level,
                    logger="markdown_webscraper_mcp",
                    data={"msg": json.dumps(payload)},
                )
            )
        )

    @mcp.tool(name="get_website")
    async def get_website(url: str, dir_path: str, ctx: Context) -> dict[str, str]:
        return service.start_job(
            session_id=ctx.session_id,
            mode="single",
            operation="get_website",
            url=url,
            dir_path=dir_path,
            notify=lambda payload: _notify_client(ctx, payload),
        )

    @mcp.tool(name="get_status_website")
    async def get_status_website(url: str, dir_path: str, ctx: Context) -> dict[str, str]:
        return service.get_latest_status(session_id=ctx.session_id, url=url, dir_path=dir_path)

    if config.enable_wildcard_scraping:

        @mcp.tool(name="get_wildcard_website")
        async def get_wildcard_website(url: str, dir_path: str, ctx: Context) -> dict[str, str]:
            return service.start_job(
                session_id=ctx.session_id,
                mode="wildcard",
                operation="get_wildcard_website",
                url=url,
                dir_path=dir_path,
                notify=lambda payload: _notify_client(ctx, payload),
            )

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
