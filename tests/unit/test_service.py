from __future__ import annotations

import asyncio

import pytest

from markdown_webscraper_mcp.config import MCPServerConfig
from markdown_webscraper_mcp.service import (
    COMPLETED_RESPONSE,
    FAILED_RESPONSE,
    FETCHING_RESPONSE,
    TIMED_OUT_RESPONSE,
    ScrapeJobService,
)


@pytest.fixture
def cfg() -> MCPServerConfig:
    return MCPServerConfig(
        mcp_server_name="Test Server",
        mcp_server_url="stdio://",
        enable_wildcard_scraping=True,
        remove_header_footer=True,
        markdown_convert=True,
        time_delay=0,
        total_timeout=0.2,
    )


@pytest.mark.asyncio
async def test_service_completed_status(cfg: MCPServerConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ScrapeJobService(cfg)

    def _ok(**_: str) -> None:
        return

    monkeypatch.setattr(service, "_run_scraper_sync", _ok)

    started = service.start_job(mode="single", url="https://example.com", dir_path="/tmp/x")
    assert started == FETCHING_RESPONSE

    await asyncio.sleep(0.05)
    assert service.get_latest_status(url="https://example.com", dir_path="/tmp/x") == COMPLETED_RESPONSE


@pytest.mark.asyncio
async def test_service_failed_status(cfg: MCPServerConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ScrapeJobService(cfg)

    def _boom(**_: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_run_scraper_sync", _boom)

    service.start_job(mode="single", url="https://example.com", dir_path="/tmp/y")
    await asyncio.sleep(0.05)

    assert service.get_latest_status(url="https://example.com", dir_path="/tmp/y") == FAILED_RESPONSE


@pytest.mark.asyncio
async def test_service_timed_out_status(cfg: MCPServerConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ScrapeJobService(cfg)

    def _slow(**_: str) -> None:
        import time

        time.sleep(0.5)

    monkeypatch.setattr(service, "_run_scraper_sync", _slow)

    service.start_job(mode="single", url="https://example.com", dir_path="/tmp/z")
    await asyncio.sleep(0.3)

    assert service.get_latest_status(url="https://example.com", dir_path="/tmp/z") == TIMED_OUT_RESPONSE
