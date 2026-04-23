from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


pytestmark = pytest.mark.integration


def _integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION") == "1"


async def _extract_status(result) -> str:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and "status" in structured:
        return str(structured["status"])

    for content in getattr(result, "content", []):
        text = getattr(content, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and "status" in payload:
                return str(payload["status"])
        except json.JSONDecodeError:
            if "status" in text:
                return text

    raise AssertionError(f"Unable to parse status from result: {result}")


async def _wait_for_completed(
    session: ClientSession,
    *,
    url: str,
    dir_path: str,
    timeout_seconds: float = 240,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        res = await session.call_tool("get_status_website", arguments={"url": url, "dir_path": dir_path})
        status = await _extract_status(res)
        if status == "fetch completed and markdown saved!":
            return status
        if status in {"fetching timed out!", "failed to fetch!"}:
            return status
        await asyncio.sleep(2)
    return "fetching timed out!"


@pytest.mark.skipif(not _integration_enabled(), reason="Set RUN_INTEGRATION=1 to run integration tests.")
@pytest.mark.asyncio
async def test_integration_mcp_tools_live(tmp_path: Path) -> None:
    port = 8891
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "mcp_server_name": "My Webscraping MCP Server",
                "mcp_server_url": f"http://127.0.0.1:{port}/mcp",
                "enable_wildcard_scraping": True,
                "remove_header_footer": True,
                "markdown_convert": True,
                "time_delay": 1,
                "total_timeout": 180,
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = str(repo_root / "src")

    server_proc = subprocess.Popen(
        [sys.executable, "-m", "markdown_webscraper_mcp.cli", "--config", str(config_path)],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for _ in range(40):
            if server_proc.poll() is not None:
                raise AssertionError("MCP server exited before tests started")
            try:
                async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        break
            except Exception:  # noqa: BLE001
                await asyncio.sleep(0.5)
        else:
            raise AssertionError("MCP server did not become ready")

        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                site_dir = tmp_path / "example_site"
                pdf_dir = tmp_path / "ti_pdf"
                wildcard_dir = tmp_path / "wildcard_site"

                result_site = await session.call_tool(
                    "get_website",
                    arguments={"url": "https://example.com/", "dir_path": str(site_dir)},
                )
                assert await _extract_status(result_site) == "fetching website and converting to markdown in progress!"

                site_status = await _wait_for_completed(
                    session,
                    url="https://example.com/",
                    dir_path=str(site_dir),
                )
                assert site_status == "fetch completed and markdown saved!"

                result_pdf = await session.call_tool(
                    "get_website",
                    arguments={"url": "https://www.ti.com/lit/ds/sprs590g/sprs590g.pdf", "dir_path": str(pdf_dir)},
                )
                assert await _extract_status(result_pdf) == "fetching website and converting to markdown in progress!"

                pdf_status = await _wait_for_completed(
                    session,
                    url="https://www.ti.com/lit/ds/sprs590g/sprs590g.pdf",
                    dir_path=str(pdf_dir),
                )
                assert pdf_status == "fetch completed and markdown saved!"

                result_wildcard = await session.call_tool(
                    "get_wildcard_website",
                    arguments={"url": "https://example.com/", "dir_path": str(wildcard_dir)},
                )
                assert await _extract_status(result_wildcard) == "fetching website and converting to markdown in progress!"

                wildcard_status = await _wait_for_completed(
                    session,
                    url="https://example.com/",
                    dir_path=str(wildcard_dir),
                )
                assert wildcard_status == "fetch completed and markdown saved!"

        assert list((site_dir / "raw_html").rglob("*.html"))
        assert list((site_dir / "markdown").rglob("*.md"))

        assert list((pdf_dir / "raw_html").rglob("*.pdf"))
        assert list((pdf_dir / "markdown").rglob("*.md"))

        assert list((wildcard_dir / "raw_html").rglob("*.html"))
        assert list((wildcard_dir / "markdown").rglob("*.md"))
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
            server_proc.wait(timeout=5)
