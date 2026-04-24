from __future__ import annotations

import asyncio
import time

import pytest

from markdown_webscraper_mcp.config import MCPServerConfig
from markdown_webscraper_mcp.service import (
    COMPLETED_STATUS,
    FAILED_STATUS,
    FETCHING_STATUS,
    TIMED_OUT_STATUS,
    ScrapeJobService,
    make_response,
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


async def _noop_notify(_: dict[str, str]) -> None:
    return


@pytest.mark.asyncio
async def test_service_completed_status(cfg: MCPServerConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ScrapeJobService(cfg)
    notified: list[dict[str, str]] = []

    def _ok(*_: str) -> None:
        return

    monkeypatch.setattr(service, "_run_scraper_sync", _ok)

    try:
        started = service.start_job(
            session_id="s1",
            mode="single",
            operation="get_website",
            url="https://example.com",
            dir_path="/tmp/x",
            notify=lambda payload: _capture(notified, payload),
        )
        assert started == make_response(status=FETCHING_STATUS, operation="get_website")

        await asyncio.sleep(0.05)
        assert (
            service.get_latest_status(session_id="s1", url="https://example.com", dir_path="/tmp/x")
            == make_response(status=COMPLETED_STATUS, operation="get_website")
        )
        assert notified == [make_response(status=COMPLETED_STATUS, operation="get_website")]
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_service_failed_status(cfg: MCPServerConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ScrapeJobService(cfg)
    notified: list[dict[str, str]] = []

    def _boom(*_: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_run_scraper_sync", _boom)

    try:
        service.start_job(
            session_id="s1",
            mode="single",
            operation="get_website",
            url="https://example.com",
            dir_path="/tmp/y",
            notify=lambda payload: _capture(notified, payload),
        )
        await asyncio.sleep(0.05)

        assert (
            service.get_latest_status(session_id="s1", url="https://example.com", dir_path="/tmp/y")
            == make_response(status=FAILED_STATUS, operation="get_website")
        )
        assert notified == [make_response(status=FAILED_STATUS, operation="get_website")]
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_service_timed_out_status(cfg: MCPServerConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ScrapeJobService(cfg)
    notified: list[dict[str, str]] = []

    def _slow(*_: str) -> None:
        time.sleep(0.5)

    monkeypatch.setattr(service, "_run_scraper_sync", _slow)

    try:
        service.start_job(
            session_id="s1",
            mode="single",
            operation="get_website",
            url="https://example.com",
            dir_path="/tmp/z",
            notify=lambda payload: _capture(notified, payload),
        )
        await asyncio.sleep(0.3)

        assert (
            service.get_latest_status(session_id="s1", url="https://example.com", dir_path="/tmp/z")
            == make_response(status=TIMED_OUT_STATUS, operation="get_website")
        )
        assert notified == [make_response(status=TIMED_OUT_STATUS, operation="get_website")]
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_service_queues_jobs_fifo_per_session(
    cfg: MCPServerConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ScrapeJobService(cfg)
    execution_order: list[str] = []

    def _slow_then_fast(mode: str, url: str, dir_path: str) -> None:
        if dir_path == "/tmp/first":
            time.sleep(0.15)
        execution_order.append(dir_path)

    monkeypatch.setattr(service, "_run_scraper_sync", _slow_then_fast)

    try:
        service.start_job(
            session_id="fifo-session",
            mode="single",
            operation="get_website",
            url="https://example.com/1",
            dir_path="/tmp/first",
            notify=_noop_notify,
        )
        service.start_job(
            session_id="fifo-session",
            mode="single",
            operation="get_website",
            url="https://example.com/2",
            dir_path="/tmp/second",
            notify=_noop_notify,
        )

        await asyncio.sleep(0.05)
        assert (
            service.get_latest_status(
                session_id="fifo-session",
                url="https://example.com/2",
                dir_path="/tmp/second",
            )
            == make_response(status=FETCHING_STATUS, operation="get_website")
        )

        await asyncio.sleep(0.25)
        assert execution_order == ["/tmp/first", "/tmp/second"]
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_service_creates_dedicated_worker_per_session(cfg: MCPServerConfig) -> None:
    service = ScrapeJobService(cfg)
    try:
        service.start_job(
            session_id="session-a",
            mode="single",
            operation="get_website",
            url="https://example.com/a",
            dir_path="/tmp/a",
            notify=_noop_notify,
        )
        service.start_job(
            session_id="session-b",
            mode="single",
            operation="get_website",
            url="https://example.com/b",
            dir_path="/tmp/b",
            notify=_noop_notify,
        )

        assert "session-a" in service._sessions
        assert "session-b" in service._sessions
        assert (
            service._sessions["session-a"].worker_executor
            is not service._sessions["session-b"].worker_executor
        )
    finally:
        await service.aclose()


async def _capture(items: list[dict[str, str]], payload: dict[str, str]) -> None:
    items.append(payload)
