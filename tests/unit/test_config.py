from __future__ import annotations

import json

import pytest

from markdown_webscraper_mcp.config import load_config


def test_load_config_defaults(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")

    cfg = load_config(path)

    assert cfg.mcp_server_name == "My Webscraping MCP Server"
    assert cfg.mcp_server_url == "stdio://"
    assert cfg.enable_wildcard_scraping is True
    assert cfg.total_timeout == 180.0


def test_load_config_rejects_invalid_url_scheme(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mcp_server_url": "ftp://localhost:9999"}), encoding="utf-8")

    with pytest.raises(ValueError, match="mcp_server_url scheme"):
        load_config(path)


def test_load_config_rejects_http_url_with_path(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"mcp_server_url": "http://localhost:8888/mcp"}), encoding="utf-8")

    with pytest.raises(ValueError, match="must not include a path"):
        load_config(path)
