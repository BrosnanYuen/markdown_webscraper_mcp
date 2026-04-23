from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class MCPServerConfig:
    mcp_server_name: str
    mcp_server_url: str
    enable_wildcard_scraping: bool
    remove_header_footer: bool
    markdown_convert: bool
    time_delay: float
    total_timeout: float


def _validate_server_url(server_url: str) -> None:
    parsed = urlparse(server_url)
    if parsed.scheme not in {"http", "https", "stdio"}:
        raise ValueError("mcp_server_url scheme must be one of: http, https, stdio")


def load_config(config_path: str | Path) -> MCPServerConfig:
    path = Path(config_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    config = MCPServerConfig(
        mcp_server_name=raw.get("mcp_server_name", "My Webscraping MCP Server"),
        mcp_server_url=raw.get("mcp_server_url", "stdio://"),
        enable_wildcard_scraping=bool(raw.get("enable_wildcard_scraping", True)),
        remove_header_footer=bool(raw.get("remove_header_footer", True)),
        markdown_convert=bool(raw.get("markdown_convert", True)),
        time_delay=float(raw.get("time_delay", 2)),
        total_timeout=float(raw.get("total_timeout", 180)),
    )
    _validate_server_url(config.mcp_server_url)
    return config
